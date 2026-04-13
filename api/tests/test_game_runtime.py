import pytest

from partygame.schemas import Lobby
from partygame.schemas.game_definition import (
    EvaluationRule,
    EvaluationType,
    GameDefinition,
    ImageRevealMode,
    MediaDefinition,
    MediaType,
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
        self.players = [
            schemas.Player(id="p1", game_id="g1", name="Alice"),
            schemas.Player(id="p2", game_id="g1", name="Bob"),
        ]
        self.applied_ttls = []
        self.state_revision = 0

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

    async def get_players(self, game_id: str) -> list[schemas.Player]:
        return [player for player in self.players if player.game_id == game_id]

    async def get_state_revision(self, game_id: str) -> int:
        return self.state_revision

    async def apply_game_ttl(self, game_id: str, ttl_seconds: int):
        self.applied_ttls.append((game_id, ttl_seconds))


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
                            media=MediaDefinition(
                                type_=MediaType.IMAGE,
                                src="/media/question.png",
                                reveal=ImageRevealMode.BLUR_TO_CLEAR,
                            ),
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.BUZZER),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=2,
                                answer="Correct Answer",
                            ),
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
    assert repo.steps["g1"]["media_reveal_state"] == "paused"
    assert repo.steps["g1"]["display_phase"] == "question_active"


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

    assert [event.type_ for event in events] == ["buzzer_reviewed", "update_score"]
    assert repo.scores["p1"] == 2
    assert lobby.phase == "step_complete"
    assert repo.steps["g1"]["media_reveal_state"] == "revealed"
    assert repo.steps["g1"]["revealed_answer_value"] == "Correct Answer"


@pytest.mark.asyncio
async def test_rejected_buzzer_disables_player_and_keeps_step_in_review():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")

    events = await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=False),
    )

    assert [event.type_ for event in events] == ["buzzer_reviewed"]
    assert lobby.phase == "host_review"
    assert repo.steps["g1"]["buzzed_player_id"] == ""
    assert repo.steps["g1"]["disabled_buzzer_player_ids"] == ["p1"]
    assert repo.steps["g1"]["media_reveal_state"] == "paused"


@pytest.mark.asyncio
async def test_reactivating_buzzer_keeps_rejected_player_disabled():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=False),
    )

    events = await service.set_buzzer_state(lobby, True)

    assert [event.type_ for event in events] == ["buzzer_state", "runtime_snapshot"]
    assert lobby.phase == "question_active"
    assert repo.steps["g1"]["buzzed_player_id"] == ""
    assert repo.steps["g1"]["disabled_buzzer_player_ids"] == ["p1"]
    assert repo.steps["g1"]["media_reveal_state"] == "running"


@pytest.mark.asyncio
async def test_disabled_player_cannot_buzz_again_after_reactivation():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=False),
    )
    await service.set_buzzer_state(lobby, True)

    blocked_events, blocked_handled = await service.submit_player_input(lobby, "p1", "buzz")
    allowed_events, allowed_handled = await service.submit_player_input(lobby, "p2", "buzz")

    assert blocked_events == []
    assert blocked_handled is False
    assert [event.type_ for event in allowed_events] == ["buzzer_state", "buzzer_clicked"]
    assert allowed_handled is True


@pytest.mark.asyncio
async def test_snapshot_includes_players():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    snapshot = await service.build_snapshot(lobby)

    assert [player.id for player in snapshot.players] == ["p1", "p2"]
    assert [player.name for player in snapshot.players] == ["Alice", "Bob"]


@pytest.mark.asyncio
async def test_accepted_buzzer_review_snapshot_includes_revealed_answer():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.media is not None
    assert snapshot.active_step.media.reveal_state == "revealed"
    assert snapshot.revealed_answer is not None
    assert snapshot.revealed_answer.value == "Correct Answer"


@pytest.mark.asyncio
async def test_snapshot_starts_in_question_phase_with_hidden_scoreboard():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.display_phase == "question_active"
    assert snapshot.scoreboard_visible is False


@pytest.mark.asyncio
async def test_show_answer_reveal_moves_auto_step_to_answer_phase_without_advancing():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)

    events = await service.show_answer_reveal(lobby)

    assert [event.type_ for event in events] == ["runtime_snapshot"]
    assert lobby.current_step == 0
    assert lobby.phase == "step_complete"
    assert repo.steps["g1"]["display_phase"] == "answer_reveal"
    assert repo.steps["g1"]["revealed_answer_value"] == 27


@pytest.mark.asyncio
async def test_auto_evaluate_marks_all_submissions_reviewed():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.submit_player_input(lobby, "p2", 10)

    scores_event = await service.evaluate_auto_step(lobby)
    review_events = await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )

    assert scores_event.updates == {"p1": 4}
    assert repo.steps["g1"]["reviewed_player_ids"] == ["p1", "p2"]
    assert review_events == []


@pytest.mark.asyncio
async def test_show_question_returns_answer_reveal_to_question_phase():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.show_answer_reveal(lobby)

    events = await service.show_question(lobby)

    assert [event.type_ for event in events] == ["runtime_snapshot"]
    assert repo.steps["g1"]["display_phase"] == "question_active"


@pytest.mark.asyncio
async def test_scoreboard_visibility_is_reflected_in_snapshot():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.set_scoreboard_visibility(lobby, True)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.scoreboard_visible is True


@pytest.mark.asyncio
async def test_reset_current_step_restarts_active_question_state():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=False),
    )

    events = await service.reset_current_step(lobby)

    assert [event.type_ for event in events] == ["runtime_snapshot"]
    assert lobby.phase == "question_active"
    assert repo.steps["g1"]["buzzer_active"] is True
    assert repo.steps["g1"]["buzzed_player_id"] == ""
    assert repo.steps["g1"]["disabled_buzzer_player_ids"] == []
    assert repo.steps["g1"]["answers"] == {}
    assert repo.steps["g1"]["reviewed_player_ids"] == []
    assert repo.steps["g1"]["revealed_answer_value"] is None
    assert repo.steps["g1"]["media_reveal_state"] == "running"


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


@pytest.mark.asyncio
async def test_start_game_applies_finished_ttl_when_definition_has_no_steps():
    class EmptyDefinitionProvider:
        async def load(self, definition_id: str) -> GameDefinition:
            return GameDefinition(id=definition_id, title="Empty", rounds=[])

        async def list_definitions(self):
            return []

    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=EmptyDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    updated_lobby, step = await service.start_game(lobby)

    assert step is None
    assert updated_lobby.phase == "finished"
    assert repo.applied_ttls == [("g1", 900)]


@pytest.mark.asyncio
async def test_advance_step_applies_finished_ttl_at_end_of_game():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    events = await service.advance_step(lobby)

    assert lobby.phase == "finished"
    assert [event.type_ for event in events] == ["step_advanced", "runtime_snapshot"]
    assert repo.applied_ttls == [("g1", 900)]
