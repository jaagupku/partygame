import json
import os
from io import BytesIO
import zipfile

import pytest
import pytest_asyncio
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from partygame.api.api_v1.endpoints import definitions as definitions_endpoints
from partygame.db.postgres import Base
from partygame.schemas import GameDefinition, MediaKind
from partygame.service.definitions import (
    DefinitionProvider,
    DefinitionSummary,
    DefinitionValidationError,
    FileDefinitionProvider,
    GameDefinitionPayload,
    PostgresDefinitionProvider,
)
from partygame.service.media import LocalFilesystemMediaStorage
from partygame.state.auth_models import UserRecord, UserRole
from partygame.state.definition_models import DefinitionVisibility, GameDefinitionRecord


def _request_with_body(body: bytes) -> Request:
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/definitions/import",
        "headers": [],
    }
    return Request(scope, receive)


def _user() -> UserRecord:
    return UserRecord(
        id="user-1",
        email="user@example.com",
        display_name="User",
        password_hash="hash",
        role=UserRole.USER.value,
    )


def _admin_user() -> UserRecord:
    return UserRecord(
        id="admin-1",
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
        role=UserRole.ADMIN.value,
    )


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


def _media_definition(definition_id: str = "media_night", media_src: str = "/api/v1/media/asset"):
    return GameDefinition.model_validate(
        {
            "id": definition_id,
            "title": "Media Night",
            "rounds": [
                {
                    "id": "round1",
                    "steps": [
                        {
                            "id": "step1",
                            "title": "Name the picture",
                            "media": {
                                "type_": "image",
                                "src": media_src,
                                "reveal": "none",
                                "loop": False,
                            },
                        },
                        {
                            "id": "step2",
                            "title": "Watch this",
                            "media": {
                                "type_": "video",
                                "src": "https://youtu.be/example",
                                "reveal": "none",
                                "loop": False,
                            },
                        },
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


@pytest.mark.asyncio
async def test_create_definition_generates_id_when_payload_id_is_blank(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path)
    payload = GameDefinitionPayload.model_validate(
        _music_definition().model_dump() | {"id": "", "visibility": "private"}
    )

    saved = await definitions_endpoints.create_definition(
        definition=payload,
        definition_provider=provider,
        current_user=_user(),
    )

    assert saved.id.startswith("music_night_")
    assert await provider.load(saved.id)


@pytest.mark.asyncio
async def test_create_definition_rejects_invalid_nonblank_id(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path)
    payload = GameDefinitionPayload.model_validate(
        _music_definition().model_dump() | {"id": "Bad Definition ID", "visibility": "private"}
    )

    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.create_definition(
            definition=payload,
            definition_provider=provider,
            current_user=_user(),
        )

    assert error.value.status_code == 422


def test_game_definition_rejects_blank_and_url_unsafe_ids():
    for definition_id in ["", "Bad Definition ID", "definition/with/slash"]:
        with pytest.raises(ValueError):
            _music_definition(definition_id=definition_id)


@pytest.mark.asyncio
async def test_export_definition_includes_definition_manifest_and_uploaded_media(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path / "games")
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")
    asset = await storage.save(
        content=b"<svg>hello</svg>",
        kind=MediaKind.IMAGE,
        filename="question.svg",
        content_type="image/svg+xml",
    )
    await provider.create(_media_definition(media_src=asset.public_url))

    response = await definitions_endpoints.export_definition(
        definition_id="media_night",
        definition_provider=provider,
        media_storage=storage,
    )

    assert response.media_type == "application/zip"
    with zipfile.ZipFile(BytesIO(response.body)) as archive:
        names = set(archive.namelist())
        definition = json.loads(archive.read("definition.json"))
        manifest = json.loads(archive.read("manifest.json"))

        assert "definition.json" in names
        assert "manifest.json" in names
        assert manifest["version"] == 1
        assert manifest["media"][0]["src"] == asset.public_url
        assert manifest["media"][0]["archive_path"] in names
        assert archive.read(manifest["media"][0]["archive_path"]) == b"<svg>hello</svg>"
        assert definition["rounds"][0]["steps"][0]["media"]["src"] == asset.public_url
        assert definition["rounds"][0]["steps"][1]["media"]["src"] == "https://youtu.be/example"


@pytest.mark.asyncio
async def test_import_definition_rewrites_media_and_creates_copy_id_on_conflict(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path / "games")
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")
    source_asset = await storage.save(
        content=b"<svg>hello</svg>",
        kind=MediaKind.IMAGE,
        filename="question.svg",
        content_type="image/svg+xml",
    )
    await provider.create(_media_definition(media_src=source_asset.public_url))
    export_response = await definitions_endpoints.export_definition(
        definition_id="media_night",
        definition_provider=provider,
        media_storage=storage,
    )

    imported = await definitions_endpoints.import_definition(
        request=_request_with_body(export_response.body),
        definition_provider=provider,
        media_storage=storage,
        current_user=_user(),
    )

    assert imported.id == "media_night_copy"
    imported_media = imported.rounds[0].steps[0].media
    assert imported_media is not None
    assert imported_media.src != source_asset.public_url
    assert imported_media.src.startswith("/api/v1/media/")
    imported_asset_id = imported_media.src.rsplit("/", 1)[1]
    imported_asset = await storage.get(imported_asset_id)
    imported_file = await storage.open(imported_asset)
    assert imported_file.read_bytes() == b"<svg>hello</svg>"
    assert imported.rounds[0].steps[1].media.src == "https://youtu.be/example"


@pytest.mark.asyncio
async def test_import_definition_cleans_up_media_when_create_fails(tmp_path):
    export_provider = FileDefinitionProvider(games_dir=tmp_path / "export_games")
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")
    source_asset = await storage.save(
        content=b"<svg>hello</svg>",
        kind=MediaKind.IMAGE,
        filename="question.svg",
        content_type="image/svg+xml",
    )
    await export_provider.create(_media_definition(media_src=source_asset.public_url))
    export_response = await definitions_endpoints.export_definition(
        definition_id="media_night",
        definition_provider=export_provider,
        media_storage=storage,
    )

    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.import_definition(
            request=_request_with_body(export_response.body),
            definition_provider=CreateFailingDefinitionProvider(),
            media_storage=storage,
            current_user=_user(),
        )

    assert error.value.status_code == 409
    saved_metadata = sorted((tmp_path / "media" / "metadata").glob("*.json"))
    assert [path.stem for path in saved_metadata] == [source_asset.id]


@pytest.mark.asyncio
async def test_import_definition_rejects_oversized_archive_body():
    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.read_limited_request_body(
            _request_with_body(b"12345"),
            max_bytes=4,
        )

    assert error.value.status_code == 413


@pytest.mark.asyncio
async def test_import_definition_rejects_malformed_zip(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path / "games")
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")

    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.import_definition(
            request=_request_with_body(b"not a zip"),
            definition_provider=provider,
            media_storage=storage,
            current_user=_user(),
        )

    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_import_definition_rejects_missing_definition_json(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path / "games")
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")
    archive_body = BytesIO()
    with zipfile.ZipFile(archive_body, mode="w") as archive:
        archive.writestr("manifest.json", json.dumps({"version": 1, "media": []}))

    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.import_definition(
            request=_request_with_body(archive_body.getvalue()),
            definition_provider=provider,
            media_storage=storage,
            current_user=_user(),
        )

    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_import_definition_rejects_missing_manifest_media_file(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path / "games")
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")
    archive_body = BytesIO()
    with zipfile.ZipFile(archive_body, mode="w") as archive:
        archive.writestr("definition.json", _media_definition().model_dump_json())
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "version": 1,
                    "media": [
                        {
                            "src": "/api/v1/media/missing",
                            "archive_path": "media/missing.svg",
                            "kind": "image",
                            "filename": "missing.svg",
                            "content_type": "image/svg+xml",
                        }
                    ],
                }
            ),
        )

    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.import_definition(
            request=_request_with_body(archive_body.getvalue()),
            definition_provider=provider,
            media_storage=storage,
            current_user=_user(),
        )

    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_import_definition_rejects_invalid_definition_json(tmp_path):
    provider = FileDefinitionProvider(games_dir=tmp_path / "games")
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")
    archive_body = BytesIO()
    with zipfile.ZipFile(archive_body, mode="w") as archive:
        archive.writestr("definition.json", json.dumps({"id": "broken"}))
        archive.writestr("manifest.json", json.dumps({"version": 1, "media": []}))

    with pytest.raises(HTTPException) as error:
        await definitions_endpoints.import_definition(
            request=_request_with_body(archive_body.getvalue()),
            definition_provider=provider,
            media_storage=storage,
            current_user=_user(),
        )

    assert error.value.status_code == 422


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
async def test_private_definitions_are_editable_and_playable_by_owner(postgres_provider):
    owner = _user()
    async with postgres_provider.sessionmaker() as session:
        session.add(owner)
        await session.commit()

    saved = await postgres_provider.create_for_user(
        _music_definition(),
        owner,
        DefinitionVisibility.PRIVATE,
    )
    owner_summaries = await postgres_provider.list_definitions_for_user(owner)

    assert saved.visibility == DefinitionVisibility.PRIVATE
    assert saved.owner_user_id == owner.id
    assert saved.can_edit is True
    assert owner_summaries[0].can_edit is True
    assert owner_summaries[0].owner_user_id == owner.id
    assert await postgres_provider.require_playable("music_night", owner)


@pytest.mark.asyncio
async def test_admin_can_edit_and_play_any_private_definition(postgres_provider):
    owner = _user()
    admin = _admin_user()
    async with postgres_provider.sessionmaker() as session:
        session.add_all([owner, admin])
        await session.commit()
    await postgres_provider.create_for_user(
        _music_definition(),
        owner,
        DefinitionVisibility.PRIVATE,
    )

    admin_view = await postgres_provider.load_for_user("music_night", admin)
    updated_definition = _music_definition()
    updated_definition.title = "Admin Updated Music Night"
    updated = await postgres_provider.update_for_user(
        "music_night",
        updated_definition,
        admin,
        DefinitionVisibility.PRIVATE,
    )

    assert admin_view.can_edit is True
    assert await postgres_provider.require_playable("music_night", admin)
    assert updated.title == "Admin Updated Music Night"


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


class CreateFailingDefinitionProvider(DefinitionProvider):
    async def load(self, definition_id: str) -> GameDefinition:
        raise FileNotFoundError(f"Definition '{definition_id}' was not found")

    async def list_definitions(self):
        return []

    async def create(self, definition: GameDefinition):
        raise FileExistsError(f"Definition '{definition.id}' already exists")

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
