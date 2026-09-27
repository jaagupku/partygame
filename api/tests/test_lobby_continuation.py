import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException, Request

from partygame import schemas
from partygame.schemas.lobby import ContinueGame
from partygame.service import continuation
from partygame.service.connection_access import connection_cookie_name
from partygame.service.game_sessions import compose_rounds
from partygame.service.player import ClientController
from partygame.service.stats import GameStatsArchiver
from partygame.state import GameKeyFactory, GameStateRepository
from tests.test_game_sessions import bundle
from tests.test_state_repo_cleanup import FakeRedis


class Transaction:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def __getattr__(self, name):
        def queue(*args, **kwargs):
            self.commands.append((name, args, kwargs))

        return queue

    async def execute(self):
        for name, args, kwargs in self.commands:
            await getattr(self.redis, name)(*args, **kwargs)


class ReplayRedis(FakeRedis):
    def __init__(self):
        super().__init__()
        self.locks = {}

    @asynccontextmanager
    async def lock(self, key, **kwargs):
        async with self.locks.setdefault(key, asyncio.Lock()):
            yield

    def pipeline(self, transaction=False):
        return Transaction(self)

    async def hdel(self, key, *fields):
        for field in fields:
            self.hashes.get(key, {}).pop(field, None)

    async def hincrby(self, key, field, amount):
        await self.hset(key, field, int(await self.hget(key, field) or 0) + amount)

    async def srem(self, key, *members):
        self.sets.get(key, set()).difference_update(members)

    async def publish(self, *args):
        self.published.append(args)


def request(token, *, player=False):
    return Request(
        {
            "type": "http",
            "headers": [
                (b"cookie", f"{connection_cookie_name('g1', player=player)}={token}".encode())
            ],
        }
    )


@pytest_asyncio.fixture
async def game(monkeypatch):
    redis = ReplayRedis()
    repo = GameStateRepository(redis)
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        host_id="host",
        starter_id="host",
        definition_id="test-quiz",
        state=schemas.GameState.RUNNING,
        phase="finished",
        current_step=1,
    )
    await repo.create_lobby(lobby)
    for pid in ["host", "player"]:
        await repo.create_player(
            schemas.Player(id=pid, game_id=lobby.id, name=pid, score=42, avatar_preset_key="fox")
        )
    tokens = {pid: await repo.issue_connection_token(lobby.id, pid) for pid in ["host", "player"]}
    tokens["display"] = await repo.issue_connection_token(lobby.id)
    prepared = compose_rounds([bundle()], definition_id="test-quiz", title="Frozen quiz")
    await repo.set_component_state(
        lobby.id, "prepared_session", {"snapshot": prepared.model_dump(mode="json")}
    )
    await repo.set_component_state(
        lobby.id,
        "game_setup",
        {"settings": schemas.CreateGame(definition_id="test-quiz").model_dump(mode="json")},
    )
    await repo.set_component_state(lobby.id, "step_archive:0", {"answers": {"player": 42}})
    await repo.set_component_state(lobby.id, "end_game", {"revealed": True})
    await repo.set_step_cache(lobby.id, {"answers": {"player": 42}})
    archive = AsyncMock()
    monkeypatch.setattr(GameStatsArchiver, "archive_finished_game", archive)
    return repo, tokens, archive


def payload(host_enabled=True, **kwargs):
    return ContinueGame(
        expected_run_id="g1",
        settings=schemas.CreateGame(definition_id="test-quiz", host_enabled=host_enabled, **kwargs),
    )


@pytest.mark.asyncio
async def test_replay_preserves_identity_resets_runtime_and_broadcasts(game):
    repo, tokens, archive = game
    result = await continuation.continue_game(
        repo, "g1", request(tokens["host"], player=True), payload()
    )
    assert result.id == "g1" and result.join_code == "ABCDE"
    assert result.run_id != "g1" and result.phase == "waiting"
    assert result.host_id == "host" and result.starter_id == "host"
    assert result.state == schemas.GameState.WAITING_FOR_PLAYERS
    assert all(p.score == 0 and p.avatar_preset_key == "fox" for p in result.players)
    for pid in ["host", "player"]:
        assert await repo.verify_connection_token("g1", tokens[pid], pid)
    assert await repo.verify_connection_token("g1", tokens["display"])
    assert await repo.get_step_cache("g1") == {}
    assert await repo.get_component_state("g1", "step_archive:0") == {}
    assert await repo.get_component_state("g1", "end_game") == {}
    assert await repo.get_state_revision("g1") == 1
    assert len(repo.redis.published) == 3
    snapshot = json.loads(repo.redis.published[0][1])
    assert snapshot["lobby"]["run_id"] == result.run_id
    assert snapshot["active_step"] is None and snapshot["end_game"] is None
    assert snapshot["host_answer"] is None
    archive.assert_awaited_once()
    assert archive.call_args.kwargs == {"strict": True}
    assert await repo.get_game_id_from_join_code("ABCDE") == "g1"
    assert repo.redis.ttls[GameKeyFactory.game_meta("g1")] > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("token_kind", ["player", "missing"])
async def test_ordinary_players_and_public_displays_cannot_configure(game, token_kind):
    repo, tokens, _ = game
    with pytest.raises(HTTPException) as error:
        await continuation.require_manager(
            repo, "g1", request(tokens.get(token_kind, ""), player=True)
        )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_hostless_starter_can_configure_and_host_mode_can_change(game):
    repo, tokens, _ = game
    await repo.set_lobby_fields("g1", host_enabled=False)
    await repo.redis.hdel(GameKeyFactory.game_meta("g1"), "host_id")
    result = await continuation.continue_game(
        repo, "g1", request(tokens["host"], player=True), payload()
    )
    assert result.host_enabled and result.host_id == "host"


@pytest.mark.asyncio
async def test_disabling_host_clears_persisted_host(game):
    repo, tokens, _ = game
    await continuation.continue_game(
        repo, "g1", request(tokens["host"], player=True), payload(False)
    )
    assert (await repo.get_lobby_meta("g1")).host_id is None


@pytest.mark.asyncio
async def test_archive_failure_leaves_everything_untouched(game):
    repo, tokens, archive = game
    archive.side_effect = RuntimeError("database unavailable")
    with pytest.raises(HTTPException) as error:
        await continuation.continue_game(
            repo, "g1", request(tokens["host"], player=True), payload()
        )
    assert error.value.status_code == 503
    assert (await repo.get_lobby_meta("g1")).phase == "finished"
    assert await repo.get_player_score("g1", "player") == 42
    assert await repo.get_component_state("g1", "step_archive:0")


@pytest.mark.asyncio
async def test_generation_failure_leaves_finished_game_untouched(game, monkeypatch):
    repo, tokens, archive = game
    prepare = AsyncMock(side_effect=HTTPException(409, "price_content_unavailable"))
    monkeypatch.setattr(continuation, "prepare_session", prepare)
    with pytest.raises(HTTPException):
        await continuation.continue_game(
            repo, "g1", request(tokens["host"], player=True), payload(game_type="price_guessing")
        )
    assert (await repo.get_lobby_meta("g1")).phase == "finished"
    archive.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_continuation_does_not_replace_next_run(game):
    repo, tokens, archive = game
    results = await asyncio.gather(
        *[
            continuation.continue_game(repo, "g1", request(tokens["host"], player=True), payload())
            for _ in range(2)
        ],
        return_exceptions=True,
    )
    assert sum(isinstance(result, schemas.Lobby) for result in results) == 1
    assert (
        sum(isinstance(result, HTTPException) and result.status_code == 409 for result in results)
        == 1
    )
    archive.assert_awaited_once()


@pytest.mark.asyncio
async def test_settings_and_legacy_price_setup(game):
    repo, _, _ = game
    settings = schemas.CreateGame(
        game_type="price_guessing", price_settings={"questions": 5, "mode": "compare"}
    )
    await repo.set_lobby_fields("g1", game_type="price_guessing", host_enabled=False)
    await repo.set_component_state(
        "g1", "game_setup", {"settings": settings.model_dump(mode="json")}
    )
    lobby = await repo.get_lobby_meta("g1")
    setup = await continuation.read_setup(repo, lobby)
    assert setup.settings == settings and setup.settings_complete
    await repo.delete_component("g1", "game_setup")
    assert not (await continuation.read_setup(repo, lobby)).settings_complete


@pytest.mark.asyncio
async def test_price_replay_uses_new_preparation_and_settings(game, monkeypatch):
    repo, tokens, _ = game
    await repo.set_lobby_fields("g1", game_type="price_guessing")
    prepared = compose_rounds([bundle()], definition_id="price_guessing", title="Price Guessing")
    prepared.session_id = "new-price-run"
    prepare = AsyncMock(return_value=prepared)
    monkeypatch.setattr(continuation, "prepare_session", prepare)
    result = await continuation.continue_game(
        repo,
        "g1",
        request(tokens["host"], player=True),
        payload(game_type="price_guessing", price_settings={"questions": 5}),
    )
    assert result.run_id == "new-price-run"
    assert prepare.call_args.args[0].price_settings.questions == 5
    assert (await continuation.read_setup(repo, result)).settings.price_settings.questions == 5


@pytest.mark.asyncio
async def test_history_uses_run_identity(game):
    repo, _, _ = game
    lobby = await repo.get_lobby_meta("g1")
    archiver = GameStatsArchiver(repo)
    first = await archiver._build_record_values(lobby)
    second = await archiver._build_record_values(lobby.model_copy(update={"run_id": "second"}))
    assert first["game_id"] == "g1" and second["game_id"] == "second"
    assert first["summary"]["lobby_id"] == second["summary"]["lobby_id"] == "g1"


@pytest.mark.asyncio
async def test_stale_commands_and_timers_do_not_mutate_next_run(game, monkeypatch):
    repo, tokens, _ = game
    old = await repo.get_lobby_meta("g1")
    player = await repo.get_player("g1", "host")
    controller = ClientController(AsyncMock(), repo.redis, old, player)
    await continuation.continue_game(repo, "g1", request(tokens["host"], player=True), payload())
    await controller.process_input({"type_": "start_game", "run_id": "g1"})
    await controller.process_input({"type_": "start_game"})
    assert (await repo.get_lobby_meta("g1")).phase == "waiting"
    # A previously scheduled task wakes into a new run at the same step/phase.
    controller.lobby = old.model_copy(update={"current_step": 0, "run_id": "g1"})
    await repo.set_lobby_fields("g1", phase="round_intro")
    mutate = AsyncMock()
    monkeypatch.setattr(controller.runtime, "open_current_step_after_round_intro", mutate)
    await controller._finish_round_intro(0)
    mutate.assert_not_awaited()


@pytest.mark.asyncio
async def test_reaction_waiting_for_reset_lock_cannot_write_into_new_run(game, monkeypatch):
    repo, _, _ = game
    lobby = await repo.get_lobby_meta("g1")
    controller = ClientController(
        AsyncMock(), repo.redis, lobby, await repo.get_player("g1", "player")
    )
    record = AsyncMock()
    monkeypatch.setattr(controller.runtime, "record_player_reaction", record)
    async with repo.mutation_lock("g1"):
        task = asyncio.create_task(
            controller.process_input({"type_": "player_reaction", "reaction": "🔥", "run_id": "g1"})
        )
        await asyncio.sleep(0)
        await repo.set_lobby_fields(
            "g1", run_id="second", phase="waiting", state=schemas.GameState.WAITING_FOR_PLAYERS
        )
    await task
    record.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_frozen_session_does_not_silently_reload_source(game, monkeypatch):
    repo, tokens, archive = game
    await repo.set_lobby_fields("g1", session_version=1)
    await repo.delete_component("g1", "prepared_session")
    prepare = AsyncMock()
    monkeypatch.setattr(continuation, "prepare_session", prepare)
    with pytest.raises(HTTPException) as error:
        await continuation.continue_game(
            repo, "g1", request(tokens["host"], player=True), payload()
        )
    assert error.value.status_code == 409
    prepare.assert_not_awaited()
    archive.assert_not_awaited()
    assert (await repo.get_lobby_meta("g1")).phase == "finished"


@pytest.mark.asyncio
async def test_permissions_are_rechecked_after_preparation(game, monkeypatch):
    repo, tokens, archive = game

    async def prepare(*args):
        await repo.set_lobby_fields("g1", host_id="player")
        return compose_rounds([bundle()], definition_id="price_guessing", title="Prices")

    monkeypatch.setattr(continuation, "prepare_session", prepare)
    with pytest.raises(HTTPException) as error:
        await continuation.continue_game(
            repo, "g1", request(tokens["host"], player=True), payload(game_type="price_guessing")
        )
    assert error.value.status_code == 403
    archive.assert_not_awaited()
    assert (await repo.get_lobby_meta("g1")).phase == "finished"


@pytest.mark.asyncio
async def test_creator_display_cannot_read_setup_or_prepare_rematch(game):
    repo, tokens, archive = game
    display_request = request(tokens["display"])
    with pytest.raises(HTTPException) as error:
        await continuation.require_manager(repo, "g1", display_request)
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        await continuation.continue_game(repo, "g1", display_request, payload())
    assert error.value.status_code == 403
    archive.assert_not_awaited()
    assert (await repo.get_lobby_meta("g1")).phase == "finished"
