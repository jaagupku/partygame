import asyncio
from unittest.mock import AsyncMock

import pytest

from partygame import schemas
from partygame.schemas.price_game import PriceGameSettings
from partygame.service.game import GameRuntimeService
from partygame.service.game_sessions import SESSION_COMPONENT_ID, compose_rounds
from partygame.service.player import ClientController, public_runtime_snapshot
from partygame.service.prices.generator import PriceGenerator
from partygame.service.runtime.scheduler import RuntimeTransitionScheduler
from tests.test_game_runtime import FakeRepo
from tests.test_player_controller import FakeRepo as ControllerRepo
from tests.test_price_game import dataset


async def setup(hosted=True):
    prepared = compose_rounds(
        PriceGenerator().generate(
            PriceGameSettings(mode="mixed", questions=5), seed=1, dataset=dataset()
        ),
        definition_id="price_guessing",
        title="Prices",
    )
    repo = FakeRepo()
    await repo.set_component_state(
        "g1", SESSION_COMPONENT_ID, {"snapshot": prepared.model_dump(mode="json")}
    )
    runtime = GameRuntimeService(repo, AsyncMock(), archive_game_stats=False)
    lobby = schemas.Lobby(
        id="g1",
        run_id="run",
        join_code="ABCDE",
        session_version=1,
        game_type="price_guessing",
        host_enabled=hosted,
    )
    await runtime.start_game(lobby)
    return runtime, lobby, repo


@pytest.mark.asyncio
@pytest.mark.parametrize("hosted", [True, False])
async def test_price_transition_preserves_full_answer_time_and_recovers(
    monkeypatch, hosted
):
    now = [1000.0]
    for module in ["game", "runtime.snapshots", "runtime.scheduler", "runtime.timing"]:
        monkeypatch.setattr(f"partygame.service.{module}.time", lambda: now[0])
    runtime, lobby, repo = await setup(hosted)
    first = await runtime.build_snapshot(lobby)
    assert first.active_step.price_transition is None
    assert await runtime.advance_step(lobby) == []  # Cannot skip an open question.
    await runtime.close_step(lobby)
    await runtime.advance_step(lobby)
    snapshot = public_runtime_snapshot(await runtime.build_snapshot(lobby))
    assert lobby.phase == "price_transition"
    assert snapshot.next_host_action.disabled
    assert not snapshot.active_step.input_enabled
    assert snapshot.active_step.timer.ends_at is None
    assert snapshot.active_step.timer.started_at is None
    assert snapshot.active_step.price_transition.duration_ms == 600
    assert snapshot.active_step.price_transition.elapsed_ms == 0
    assert snapshot.active_step.price_reveal == []
    assert snapshot.active_step.evaluation_answer is None
    assert (await runtime.submit_player_input(lobby, "p1", "1"))[1] is False
    for action in [
        runtime.advance_step,
        runtime.close_step,
        runtime.reset_current_step,
        runtime.show_answer_reveal,
        runtime.show_previous_reveal,
    ]:
        assert await action(lobby) == []
    assert lobby.current_step == 1
    assert not await runtime.finish_price_transition(lobby)
    now[0] += 0.25
    recovered = GameRuntimeService(repo, AsyncMock(), archive_game_stats=False)
    snapshot2 = await recovered.build_snapshot(lobby)
    assert (
        snapshot2.active_step.price_transition.id
        == snapshot.active_step.price_transition.id
    )
    assert snapshot2.active_step.price_transition.elapsed_ms == pytest.approx(250)
    scheduled = await RuntimeTransitionScheduler().next_transition(
        lobby=lobby, snapshot=snapshot2, runtime=recovered
    )
    assert scheduled.kind == "price_transition"
    assert scheduled.delay_seconds == pytest.approx(0.35)
    now[0] += 0.4
    assert await recovered.finish_price_transition(lobby)
    opened = await recovered.build_snapshot(lobby)
    assert opened.active_step.input_enabled
    assert opened.active_step.price_transition is None
    assert (
        opened.active_step.timer.ends_at - opened.active_step.timer.started_at
        == pytest.approx(opened.active_step.timer.seconds)
    )
    assert opened.active_step.timer.started_at == now[0]
    now[0] += 0.1
    assert not await recovered.finish_price_transition(lobby)
    assert (
        await recovered.build_snapshot(lobby)
    ).active_step.timer.started_at == opened.active_step.timer.started_at


@pytest.mark.asyncio
@pytest.mark.parametrize("stale", ["run", "step", "phase"])
async def test_controller_ignores_stale_transition_callback(stale):
    lobby = schemas.Lobby(
        id="g1",
        run_id="new",
        join_code="ABCDE",
        game_type="price_guessing",
        current_step=2,
        phase="question_active" if stale == "phase" else "price_transition",
    )
    controller = object.__new__(ClientController)
    controller.lobby = lobby
    controller.repo = ControllerRepo(lobby)
    controller.runtime = AsyncMock()
    controller.runtime.finish_price_transition.return_value = False
    controller._emit_runtime_state = AsyncMock()
    await controller._finish_price_transition(
        0, "old" if stale == "run" else "new", 1 if stale == "step" else 2
    )
    controller._emit_runtime_state.assert_not_awaited()
    if stale != "phase":
        controller.runtime.finish_price_transition.assert_not_awaited()


@pytest.mark.asyncio
async def test_last_price_question_finishes_without_travel():
    runtime, lobby, _ = await setup()
    lobby.current_step = 4
    await runtime.initialize_step_state(lobby, await runtime.get_current_step(lobby))
    await runtime.close_step(lobby)
    await runtime.advance_step(lobby)
    assert lobby.phase == "finished"
    assert (await runtime.build_snapshot(lobby)).active_step is None


@pytest.mark.asyncio
async def test_concurrent_controller_callbacks_open_the_question_once(monkeypatch):
    runtime, lobby, repo = await setup()
    await runtime.close_step(lobby)
    await runtime.advance_step(lobby)
    await repo.set_step_cache(lobby.id, {"price_transition_ends_at": 1})
    controller = object.__new__(ClientController)
    controller.lobby = lobby
    controller.repo = ControllerRepo(lobby)
    controller.runtime = runtime
    controller._emit_runtime_state = AsyncMock()
    await asyncio.gather(
        controller._finish_price_transition(0, lobby.run_id, lobby.current_step),
        controller._finish_price_transition(0, lobby.run_id, lobby.current_step),
    )
    controller._emit_runtime_state.assert_awaited_once()
    assert lobby.phase == "question_active"
