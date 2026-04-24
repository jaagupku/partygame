import json
import os

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from partygame.api.api_v1.endpoints import definitions as definitions_endpoints
from partygame.db.postgres import Base
from partygame.schemas import GameDefinition
from partygame.service.definitions import (
    DefinitionProvider,
    DefinitionSummary,
    DefinitionValidationError,
    FileDefinitionProvider,
    PostgresDefinitionProvider,
)
from partygame.state.definition_models import GameDefinitionRecord


def _write_definition(path, title: str):
    path.write_text(
        json.dumps(
            {
                "id": "quiz_demo",
                "title": title,
                "rounds": [
                    {
                        "id": "round1",
                        "steps": [
                            {
                                "id": "step1",
                                "title": "Question",
                                "player_input": {"kind": "text"},
                                "evaluation": {"type_": "host_judged", "points": 1},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _music_definition(definition_id: str = "music_night") -> GameDefinition:
    return GameDefinition.model_validate(
        {
            "id": definition_id,
            "title": "Music Night",
            "description": "Songs and sounds",
            "rounds": [
                {
                    "id": "round1",
                    "title": "Round 1",
                    "steps": [
                        {
                            "id": "step1",
                            "title": "Guess the artist",
                            "player_input": {"kind": "text"},
                            "evaluation": {"type_": "exact_text", "points": 2, "answer": "ABBA"},
                        }
                    ],
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_file_definition_provider_caches_unchanged_definitions(tmp_path):
    definition_path = tmp_path / "quiz_demo.json"
    _write_definition(definition_path, "Cached title")

    provider = FileDefinitionProvider(games_dir=tmp_path)

    first = await provider.load("quiz_demo")
    second = await provider.load("quiz_demo")

    assert second is first


@pytest.mark.asyncio
async def test_file_definition_provider_refreshes_cache_when_definition_changes(tmp_path):
    definition_path = tmp_path / "quiz_demo.json"
    _write_definition(definition_path, "Original title")

    provider = FileDefinitionProvider(games_dir=tmp_path)

    first = await provider.load("quiz_demo")
    _write_definition(definition_path, "Updated title")
    second = await provider.load("quiz_demo")

    assert second is not first
    assert second.title == "Updated title"


@pytest.mark.asyncio
async def test_file_definition_provider_creates_new_definition(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path)
    definition = _music_definition()

    saved = await provider.create(definition)

    assert saved.id == "music_night"
    assert (tmp_path / "music_night.json").exists()
    assert (
        json.loads((tmp_path / "music_night.json").read_text(encoding="utf-8"))["title"]
        == "Music Night"
    )


@pytest.mark.asyncio
async def test_file_definition_provider_updates_existing_definition(tmp_path):
    definition_path = tmp_path / "quiz_demo.json"
    _write_definition(definition_path, "Original title")
    provider = FileDefinitionProvider(games_dir=tmp_path)
    definition = await provider.load("quiz_demo")
    definition.title = "Updated from API"

    saved = await provider.update("quiz_demo", definition)

    assert saved.title == "Updated from API"
    assert json.loads(definition_path.read_text(encoding="utf-8"))["title"] == "Updated from API"


@pytest.mark.asyncio
async def test_file_definition_provider_rejects_duplicate_step_ids(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path)
    definition = GameDefinition.model_validate(
        {
            "id": "broken",
            "title": "Broken",
            "rounds": [
                {
                    "id": "round1",
                    "steps": [
                        {"id": "step1", "title": "One"},
                        {"id": "step1", "title": "Two"},
                    ],
                }
            ],
        }
    )

    with pytest.raises(DefinitionValidationError):
        await provider.create(definition)


@pytest.mark.asyncio
async def test_update_definition_rejects_id_mismatch(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path)
    payload = GameDefinition.model_validate(
        {
            "id": "second_game",
            "title": "Another",
            "rounds": [],
        }
    )

    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.update_definition(
            definition_id="first_game",
            definition=payload,
            definition_provider=provider,
        )

    assert error.value.status_code == 400


@pytest_asyncio.fixture()
async def postgres_provider():
    database_url = os.environ.get("POSTGRES_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield PostgresDefinitionProvider(sessionmaker=sessionmaker)
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_definition_provider_creates_loads_and_lists(postgres_provider):
    definition = _music_definition()

    saved = await postgres_provider.create(definition)
    loaded = await postgres_provider.load(definition.id)
    summaries = await postgres_provider.list_definitions()

    assert saved == definition
    assert loaded == definition
    assert summaries == [
        DefinitionSummary(
            id="music_night",
            title="Music Night",
            description="Songs and sounds",
        )
    ]


@pytest.mark.asyncio
async def test_postgres_definition_provider_rejects_duplicate_create(postgres_provider):
    definition = _music_definition()
    await postgres_provider.create(definition)

    with pytest.raises(FileExistsError):
        await postgres_provider.create(definition)


@pytest.mark.asyncio
async def test_postgres_definition_provider_updates_existing_definition(postgres_provider):
    definition = _music_definition()
    await postgres_provider.create(definition)
    definition.title = "Updated Music Night"

    saved = await postgres_provider.update(definition.id, definition)

    assert saved.title == "Updated Music Night"
    assert (await postgres_provider.load(definition.id)).title == "Updated Music Night"


@pytest.mark.asyncio
async def test_postgres_definition_provider_rejects_missing_definition(postgres_provider):
    with pytest.raises(FileNotFoundError):
        await postgres_provider.load("missing")


@pytest.mark.asyncio
async def test_alembic_game_definitions_table_shape_matches_model(postgres_provider):
    provider = postgres_provider
    async with provider.sessionmaker() as session:
        table_names = await session.run_sync(
            lambda sync_session: inspect(sync_session.get_bind()).get_table_names()
        )
        columns = await session.run_sync(
            lambda sync_session: {
                column["name"]
                for column in inspect(sync_session.get_bind()).get_columns(
                    GameDefinitionRecord.__tablename__
                )
            }
        )

    assert "game_definitions" in table_names
    assert {
        "id",
        "title",
        "description",
        "owner_user_id",
        "visibility",
        "payload",
        "created_at",
        "updated_at",
    } <= columns


class MissingDefinitionProvider(DefinitionProvider):
    async def load(self, definition_id: str) -> GameDefinition:
        raise FileNotFoundError(f"Definition '{definition_id}' was not found")

    async def list_definitions(self):
        return []

    async def create(self, definition: GameDefinition):
        return definition

    async def update(self, definition_id: str, definition: GameDefinition):
        return definition


@pytest.mark.asyncio
async def test_get_definition_maps_missing_definition_to_404():
    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.get_definition(
            definition_id="missing",
            definition_provider=MissingDefinitionProvider(),
        )

    assert error.value.status_code == 404


def test_none_input_rejects_non_none_evaluation():
    with pytest.raises(ValueError):
        GameDefinition.model_validate(
            {
                "id": "broken_none",
                "title": "Broken None",
                "rounds": [
                    {
                        "id": "round1",
                        "steps": [
                            {
                                "id": "step1",
                                "title": "No input",
                                "player_input": {"kind": "none"},
                                "evaluation": {"type_": "host_judged", "points": 1},
                            }
                        ],
                    }
                ],
            }
        )


def test_checkbox_weighted_evaluation_requires_checkbox_input():
    with pytest.raises(ValueError):
        GameDefinition.model_validate(
            {
                "id": "broken_weighted",
                "title": "Broken Weighted",
                "rounds": [
                    {
                        "id": "round1",
                        "steps": [
                            {
                                "id": "step1",
                                "title": "Wrong shape",
                                "player_input": {"kind": "radio", "options": ["A", "B"]},
                                "evaluation": {
                                    "type_": "multi_select_weighted",
                                    "points": 1,
                                    "answer": {
                                        "option_scores": [
                                            {"option": "A", "points": 1},
                                            {"option": "B", "points": -1},
                                        ]
                                    },
                                },
                            }
                        ],
                    }
                ],
            }
        )


def test_checkbox_weighted_evaluation_accepts_negative_points():
    definition = GameDefinition.model_validate(
        {
            "id": "weighted_checkbox",
            "title": "Weighted Checkbox",
            "rounds": [
                {
                    "id": "round1",
                    "steps": [
                        {
                            "id": "step1",
                            "title": "Pick options",
                            "player_input": {"kind": "checkbox", "options": ["A", "B"]},
                            "evaluation": {
                                "type_": "multi_select_weighted",
                                "points": 1,
                                "answer": {
                                    "option_scores": [
                                        {"option": "A", "points": 2},
                                        {"option": "B", "points": -1},
                                    ]
                                },
                            },
                        }
                    ],
                }
            ],
        }
    )

    assert definition.rounds[0].steps[0].evaluation.type_ == "multi_select_weighted"
