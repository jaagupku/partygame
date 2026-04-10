import pytest

from partygame.schemas import Lobby
from partygame.schemas.game_definition import (
    EvaluationRule,
    EvaluationType,
    GameDefinition,
    PlayerInputDefinition,
    PlayerInputKind,
    RoundDefinition,
    StepDefinition,
    TimerDefinition,
)
from partygame.service.game import GameRuntimeService
from partygame import schemas


class FakeRepo:
    def __init__(self):
        self.lobby_fields = {}
        self.steps = {}
        self.scores = {"p1": 0, "p2": 5}

    async def set_lobby_fields(self, game_id: str, **fields):
        self.lobby_fields.setdefault(game_id, {}).update(fields)

    async def set_step_cache(self, game_id: str, fields: dict):
        self.steps.setdefault(game_id, {}).update(fields)

    async def get_step_cache(self, game_id: str) -> dict:
        return self.steps.get(game_id, {})

    async def get_player_score(self, game_id: str, player_id: str) -> int:
        return self.scores.get(player_id, 0)

    async def set_player_score(self, game_id: str, player_id: str, score: int):
        self.scores[player_id] = score


class MixedDefinitionProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Test",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="buzzer_step",
                            title="Buzz in",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.BUZZER),
                            evaluation=EvaluationRule(type_=EvaluationType.HOST_JUDGED, points=2),
                            timer=TimerDefinition(seconds=10, enforced=False),
                        ),
                        StepDefinition(
                            id="number_step",
                            title="Closest number",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NUMBER),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.CLOSEST_NUMBER,
                                points=4,
                                answer=27,
                            ),
                        ),
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


@pytest.mark.asyncio
async def test_start_game_skips_buzzer_when_host_disabled():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    updated_lobby, step = await service.start_game(lobby)

    assert updated_lobby.state == "running"
    assert updated_lobby.phase == "question_active"
    assert step is not None
    assert step.id == "number_step"


@pytest.mark.asyncio
async def test_buzzer_submission_locks_first_player():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    events, handled = await service.submit_player_input(lobby, "p1", "buzz")

    assert handled is True
    assert [event.type_ for event in events] == ["buzzer_state", "buzzer_clicked"]
    assert repo.steps["g1"]["buzzed_player_id"] == "p1"
    assert repo.steps["g1"]["buzzer_active"] is False


@pytest.mark.asyncio
async def test_close_step_moves_buzzer_round_to_host_review():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")

    events = await service.close_step(lobby)

    assert lobby.phase == "host_review"
    assert repo.lobby_fields["g1"]["phase"] == "host_review"
    assert events[-1].type_ == "runtime_snapshot"


@pytest.mark.asyncio
async def test_review_submission_awards_points_and_completes_review():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.close_step(lobby)

    events = await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )

    assert len(events) == 1
    assert events[0].type_ == "update_score"
    assert repo.scores["p1"] == 2
    assert lobby.phase == "step_complete"


@pytest.mark.asyncio
async def test_submit_player_input_is_rejected_after_step_closes():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.close_step(lobby)

    events, handled = await service.submit_player_input(lobby, "p1", 27)

    assert events == []
    assert handled is False


@pytest.mark.asyncio
async def test_snapshot_disables_input_when_step_is_not_active():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.close_step(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.input_enabled is False


@pytest.mark.asyncio
async def test_player_cannot_submit_twice_for_same_step():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    first_events, first_handled = await service.submit_player_input(lobby, "p1", 27)
    second_events, second_handled = await service.submit_player_input(lobby, "p1", 28)

    assert first_events == []
    assert first_handled is True
    assert second_events == []
    assert second_handled is False
    assert repo.steps["g1"]["answers"] == {"p1": 27}


@pytest.mark.asyncio
async def test_snapshot_includes_submitted_player_ids():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.submit_player_input(lobby, "p2", 26)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.submitted_player_ids == ["p1", "p2"]
