from datetime import UTC, datetime
from random import Random
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from partygame import schemas
from partygame.api.api_v1.endpoints.game_types import list_game_types
from partygame.schemas.game_definition import (
    DefinitionTheme,
    EvaluationRule,
    GameDefinition,
    PlayerInputDefinition,
    RoundDefinition,
    StepDefinition,
)
from partygame.schemas.game_session import (
    DatasetSnapshot,
    RoundBundle,
    RoundGenerator,
    SourceMetadata,
)
from partygame.service import lobby as lobby_service
from partygame.service.definitions import PostgresDefinitionProvider
from partygame.service.game import GameRuntimeService
from partygame.service.game_sessions import (
    SESSION_COMPONENT_ID,
    compose_rounds,
    load_session_definition,
    prepare_session,
)
from partygame.service.player import public_runtime_snapshot
from partygame.service.stats import GameStatsArchiver
from partygame.state import GameKeyFactory, GameStateRepository
from tests.test_game_runtime import FakeRepo
from tests.test_state_repo_cleanup import FakeRedis


def definition():
    return GameDefinition(
        id="test-quiz",
        title="Original quiz",
        theme=DefinitionTheme(palette="forest"),
        rounds=[
            RoundDefinition(
                id="round",
                steps=[
                    StepDefinition(
                        id="question",
                        title="Guess the number",
                        player_input=PlayerInputDefinition(kind="number"),
                        evaluation=EvaluationRule(type_="exact_number", answer=42, points=7),
                    )
                ],
            )
        ],
    )


def bundle(source=None):
    game = definition()
    return RoundBundle(
        rounds=game.rounds,
        theme=game.theme,
        source=source or SourceMetadata(source_id=game.id),
    )


@pytest.mark.asyncio
async def test_catalog_and_legacy_request_defaults():
    catalog = await list_game_types()
    assert [(entry.id, entry.availability) for entry in catalog] == [
        ("trivia", "available"),
        ("price_guessing", "available"),
    ]
    assert catalog[0].host_modes == ("hosted", "automatic")
    assert schemas.CreateGame().game_type == "trivia"


@pytest.mark.asyncio
@pytest.mark.parametrize("game_type", ["unknown", "mixed"])
async def test_unavailable_types_never_load_definitions(game_type):
    provider = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await prepare_session(schemas.CreateGame(game_type=game_type), None, provider)
    assert error.value.status_code == 422
    provider.load.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type,status", [(PermissionError, 403), (FileNotFoundError, 404)])
async def test_preparation_enforces_definition_access(error_type, status):
    provider = AsyncMock(spec=PostgresDefinitionProvider)
    provider.require_playable.side_effect = error_type("Unavailable definition")
    with pytest.raises(HTTPException) as error:
        await prepare_session(schemas.CreateGame(), None, provider)
    assert error.value.status_code == status
    provider.load.assert_not_called()


def test_composer_preserves_order_scoring_and_source_ids_without_mutation():
    first = bundle()
    second = bundle(SourceMetadata(source_id="another"))
    second.theme = DefinitionTheme(palette="candy")
    second.rounds[0].steps[0].title = "Second question"
    prepared = compose_rounds([first, second], definition_id="mix", title="Mixed")
    rounds = prepared.definition.rounds
    assert [r.steps[0].title for r in rounds] == ["Guess the number", "Second question"]
    assert len({r.id for r in rounds}) == 2
    assert len({r.steps[0].id for r in rounds}) == 2
    assert [r.steps[0].evaluation.points for r in rounds] == [7, 7]
    assert prepared.definition.theme.palette == "forest"
    assert [origin.source_round_id for origin in prepared.origins] == ["round", "round"]
    assert prepared.origins[1].step_ids == {"b1-r0-s0": "question"}
    assert first.rounds[0].steps[0].id == "question"
    prepared.definition.rounds[0].steps[0].evaluation.answer = 99
    assert first.rounds[0].steps[0].evaluation.answer == 42


@pytest.mark.asyncio
async def test_lobby_snapshot_survives_source_deletion_and_tracks_cleanup(monkeypatch):
    redis = FakeRedis()
    provider = AsyncMock(spec=PostgresDefinitionProvider)
    original = definition()
    provider.require_playable.return_value = original
    monkeypatch.setattr(lobby_service, "get_default_definition_provider", lambda: provider)
    lobby = await lobby_service.create(redis, schemas.CreateGame(definition_id=original.id))
    assert lobby.game_type == "trivia"
    assert lobby.session_version == 1
    assert "origins" not in lobby.model_dump()
    repo = GameStateRepository(redis)
    restored = await repo.get_lobby_meta(lobby.id)
    original.title = "Edited"
    original.rounds.clear()
    provider.load.side_effect = FileNotFoundError("Deleted")
    runtime = GameRuntimeService(repo, provider, archive_game_stats=False)
    assert (await runtime.get_current_step(restored)).evaluation.answer == 42
    assert (await runtime.get_definition_theme(restored)).palette == "forest"
    record = await GameStatsArchiver(repo, definition_provider=provider)._build_record_values(
        restored
    )
    assert record["definition_title"] == "Original quiz"
    assert record["step_count"] == 1
    provider.load.assert_not_called()
    key = GameKeyFactory.game_component(lobby.id, SESSION_COMPONENT_ID)
    assert key in redis.ttls
    await repo.apply_game_ttl(lobby.id, 30)
    assert redis.ttls[key] == 30
    await repo.delete_game(lobby.id)
    assert await repo.get_component_state(lobby.id, SESSION_COMPONENT_ID) == {}


@pytest.mark.asyncio
async def test_missing_snapshot_fails_closed_but_legacy_lobby_loads_source():
    provider = AsyncMock()
    provider.load.return_value = definition()
    repo = FakeRepo()
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", session_version=1)
    with pytest.raises(RuntimeError, match="missing"):
        await load_session_definition(repo, lobby, provider)
    provider.load.assert_not_called()
    lobby.session_version = None
    assert await load_session_definition(repo, lobby, provider) == definition()


@pytest.mark.asyncio
@pytest.mark.parametrize("host_enabled", [True, False])
async def test_composed_session_scores_across_rounds_and_finishes_once(host_enabled):
    prepared = compose_rounds([bundle(), bundle()], definition_id="mixed", title="Mixed")
    repo = FakeRepo()
    await repo.set_component_state(
        "g1", SESSION_COMPONENT_ID, {"snapshot": prepared.model_dump(mode="json")}
    )
    provider = AsyncMock()
    runtime = GameRuntimeService(repo, provider, archive_game_stats=False)
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", session_version=1, host_enabled=host_enabled)
    await runtime.start_game(lobby)
    for index in range(2):
        snapshot = public_runtime_snapshot(await runtime.build_snapshot(lobby))
        assert snapshot.host_answer is None
        assert snapshot.active_step.evaluation_answer is None
        assert "origins" not in snapshot.model_dump_json()
        await repo.set_step_cache("g1", {"answers": {"p1": 42}})
        await runtime.close_step(lobby)
        assert await repo.get_player_score("g1", "p1") == 7 * (index + 1)
        await runtime.advance_step(lobby)
        assert lobby.phase == ("finished" if index == 1 else "question_active")
    assert len(repo.applied_ttls) == 1
    provider.load.assert_not_called()


class GeneratedSettings(BaseModel):
    count: int


class FixtureGenerator:
    def generate(self, settings: GeneratedSettings, *, seed: int, dataset: DatasetSnapshot):
        records = Random(seed).sample(dataset.records, settings.count)
        result = bundle(
            SourceMetadata(
                source_id=dataset.source_id,
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.version,
                captured_at=dataset.captured_at,
                generator_version="fixture-v1",
                seed=seed,
            )
        )
        result.rounds[0].steps = [
            StepDefinition(id=str(index), title=record["title"])
            for index, record in enumerate(records)
        ]
        return [result]


def test_generator_contract_is_reproducible_from_versioned_dataset():
    generator: RoundGenerator[GeneratedSettings] = FixtureGenerator()
    dataset = DatasetSnapshot(
        source_id="fixture",
        dataset_id="items",
        version="1",
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
        records=[{"title": str(index)} for index in range(20)],
    )
    settings = GeneratedSettings(count=5)
    first = generator.generate(settings, seed=123, dataset=dataset)
    assert first == generator.generate(settings, seed=123, dataset=dataset)
    assert first != generator.generate(settings, seed=321, dataset=dataset)
    assert first[0].source.dataset_version == "1"
    assert first[0].source.captured_at == dataset.captured_at


@pytest.mark.asyncio
async def test_unsupported_session_version_never_loads_source():
    provider = AsyncMock()
    lobby = schemas.Lobby(id="g1", join_code="ABCDE", session_version=2)
    with pytest.raises(RuntimeError, match="Unsupported"):
        await load_session_definition(FakeRepo(), lobby, provider)
    provider.load.assert_not_called()


@pytest.mark.asyncio
async def test_failed_lobby_creation_cleans_up_prepared_record(monkeypatch):
    redis = FakeRedis()
    provider = AsyncMock()
    provider.load.return_value = definition()
    monkeypatch.setattr(lobby_service, "get_default_definition_provider", lambda: provider)
    monkeypatch.setattr(GameStateRepository, "create_lobby", AsyncMock(side_effect=RuntimeError))
    with pytest.raises(RuntimeError):
        await lobby_service.create(redis)
    assert not redis.hashes
    assert not redis.sets
