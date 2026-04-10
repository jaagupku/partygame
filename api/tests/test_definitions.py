import json

import pytest
from fastapi import HTTPException

from partygame.api.api_v1.endpoints import definitions as definitions_endpoints
from partygame.schemas import GameDefinition
from partygame.service.definitions import DefinitionValidationError, FileDefinitionProvider


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
    definition = GameDefinition.model_validate(
        {
            "id": "music_night",
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
