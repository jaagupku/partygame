import json

import pytest

from partygame.service.definitions import FileDefinitionProvider


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
