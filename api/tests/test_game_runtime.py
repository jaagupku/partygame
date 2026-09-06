from time import time

import pytest
from pydantic import ValidationError

from partygame import schemas
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


class FakeRepo:
    def __init__(self):
        self.lobby_fields = {}
        self.steps = {}
        self.components = {}
        self.scores = {"p1": 0, "p2": 5}
        self.players = [
            schemas.Player(
                id="p1",
                game_id="g1",
                name="Alice",
                avatar_kind="preset",
                avatar_preset_key="fox",
            ),
            schemas.Player(
                id="p2",
                game_id="g1",
                name="Bob",
                avatar_kind="custom",
                avatar_url="/api/v1/media/p2-avatar",
                avatar_asset_id="p2-avatar",
            ),
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
        return [
            player.model_copy(update={"score": self.scores.get(player.id, player.score)})
            for player in self.players
            if player.game_id == game_id
        ]

    async def set_component_state(self, game_id: str, component_id: str, fields: dict):
        self.components.setdefault(game_id, {}).setdefault(component_id, {}).update(fields)

    async def get_component_state(self, game_id: str, component_id: str) -> dict:
        return self.components.get(game_id, {}).get(component_id, {})

    async def get_state_revision(self, game_id: str) -> int:
        return self.state_revision

    async def apply_game_ttl(self, game_id: str, ttl_seconds: int):
        self.applied_ttls.append((game_id, ttl_seconds))


class NoopStatsArchiver:
    def __init__(self, repo, *, definition_provider=None):
        pass

    async def mark_started(self, lobby_id: str):
        pass

    async def archive_finished_game(self, lobby: schemas.Lobby):
        pass


@pytest.fixture(autouse=True)
def disable_default_stats_archiver(monkeypatch):
    monkeypatch.setattr(
        "partygame.service.game.GameStatsArchiver",
        NoopStatsArchiver,
    )


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
                                blur_reveal_curve=(0.1, 0.2, 0.3, 0.4),
                                blur_circle_reveal_curve=(0.2, 0.3, 0.4, 0.5),
                                zoom_reveal_curve=(0.3, 0.4, 0.5, 0.6),
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


class ThemedDefinitionProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Themed Test",
            theme=schemas.DefinitionTheme(
                mode=schemas.DefinitionThemeMode.DARK,
                palette=schemas.DefinitionThemePalette.FOREST,
                primary="#4ade80",
            ),
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="info",
                            title="Info",
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


@pytest.mark.asyncio
async def test_runtime_snapshot_includes_definition_theme():
    repo = FakeRepo()
    lobby = Lobby(
        id="g1",
        join_code="ABCDE",
        host_enabled=True,
        players=[],
        connection="connected",
        state=schemas.GameState.RUNNING,
        definition_id="themed_test",
        current_step=0,
        phase="question_active",
    )
    service = GameRuntimeService(repo, definition_provider=ThemedDefinitionProvider())

    await service.initialize_step_state(lobby, (await service._flatten_steps(lobby))[0])
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.theme is not None
    assert snapshot.theme.mode == schemas.DefinitionThemeMode.DARK
    assert snapshot.theme.palette == schemas.DefinitionThemePalette.FOREST
    assert snapshot.theme.primary == "#4ade80"


class DrawingDefinitionProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Drawing Test",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="drawing_step",
                            title="Draw a cat",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.DRAWING),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.FAVORITE_VOTE,
                                points=2,
                                answer="Cats should have visible whiskers.",
                            ),
                        )
                    ],
                )
            ],
        )


def valid_drawing(color: str = "#0f172a") -> dict:
    color_index = {
        "#0f172a": 0,
        "#ef4444": 1,
        "#3b82f6": 6,
        "#22c55e": 4,
    }.get(color, 0)
    return {
        "w": 512,
        "h": 384,
        "s": [[color_index, 8, 0, [51, 77, 205, 192]]],
    }


def drawing_with_counts(stroke_count: int, points_per_stroke: int) -> dict:
    return {
        "w": 512,
        "h": 384,
        "s": [
            [
                0,
                8,
                0,
                [
                    coordinate
                    for point_index in range(points_per_stroke)
                    for coordinate in [
                        round(((point_index % 20) / 20) * 512),
                        round((point_index / max(points_per_stroke, 1)) * 384),
                    ]
                ],
            ]
            for _ in range(stroke_count)
        ],
    }


class NoneEvaluationProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="No reveal",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="intro",
                            title="Intro",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NONE),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.NONE,
                                points=0,
                                answer=None,
                            ),
                        ),
                        StepDefinition(
                            id="next_step",
                            title="Next",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_TEXT,
                                points=1,
                                answer="ok",
                            ),
                        ),
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class HostJudgedTextProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Host judged",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="host_judged_text",
                            title="Host judged text",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=2,
                                answer="Correct Answer",
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class ClosestNumberBandsProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Number bands",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="number_bands",
                            title="Year",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NUMBER),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.CLOSEST_NUMBER,
                                points=4,
                                answer=2000,
                                number_bands=[
                                    {"distance": 5, "points": 3},
                                    {"distance": 10, "points": 2},
                                    {"distance": 20, "points": 1},
                                ],
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class TwoExactNumberProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Two questions",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="first_number",
                            title="First number",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NUMBER),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_NUMBER,
                                points=1,
                                answer=1,
                            ),
                        ),
                        StepDefinition(
                            id="second_number",
                            title="Second number",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NUMBER),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_NUMBER,
                                points=1,
                                answer=2,
                            ),
                        ),
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class VideoDefinitionProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Video Test",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="video_step",
                            title="Watch this",
                            media=MediaDefinition(
                                type_=MediaType.VIDEO,
                                src="/media/question.mp4",
                            ),
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NONE),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.NONE,
                                points=0,
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class AudioDefinitionProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Audio Test",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="audio_step",
                            title="Listen to this",
                            media=MediaDefinition(
                                type_=MediaType.AUDIO,
                                src="/media/question.mp3",
                            ),
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NONE),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.NONE,
                                points=0,
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class ManualVideoDefinitionProvider(VideoDefinitionProvider):
    async def load(self, definition_id: str) -> GameDefinition:
        definition = await super().load(definition_id)
        media = definition.rounds[0].steps[0].media
        assert media is not None
        media.autoplay = False
        media.hide_youtube_title = True
        return definition


class HostlessCompatibilityProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Hostless",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="skip_host_judged_checkbox",
                            title="Skip checkbox",
                            player_input=PlayerInputDefinition(
                                kind=PlayerInputKind.CHECKBOX,
                                options=["A", "B"],
                            ),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=2,
                                answer={"option_scores": [{"option": "A", "points": 1}]},
                            ),
                        ),
                        StepDefinition(
                            id="skip_missing_answer",
                            title="Missing answer",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_TEXT,
                                points=1,
                                answer="",
                            ),
                        ),
                        StepDefinition(
                            id="info_slide",
                            title="Info",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NONE),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.NONE,
                                points=0,
                                answer=None,
                            ),
                        ),
                        StepDefinition(
                            id="host_judged_text",
                            title="Fallback answer",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=1,
                                answer="hello",
                            ),
                            timer=TimerDefinition(seconds=10, enforced=True),
                        ),
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class InactiveHostFallbackProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Inactive host fallback",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="inactive_host_step",
                            title="Fallback exact text",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=3,
                                answer="hello",
                            ),
                            timer=TimerDefinition(seconds=20, enforced=False),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class HostedTimedHostJudgedProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Hosted Timed",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="hosted_timed",
                            title="Hosted timed",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=3,
                                answer="hello",
                            ),
                            timer=TimerDefinition(seconds=30, enforced=False),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


class TwoRoundHostlessProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Two Round",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="r1s1",
                            title="Round 1",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_TEXT,
                                points=1,
                                answer="ok",
                            ),
                        )
                    ],
                ),
                RoundDefinition(
                    id="round2",
                    steps=[
                        StepDefinition(
                            id="r2s1",
                            title="Round 2",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_TEXT,
                                points=1,
                                answer="ok",
                            ),
                        )
                    ],
                ),
            ],
        )

    async def list_definitions(self):
        return []


class HostlessFilteredRoundsProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Filtered Rounds",
            rounds=[
                RoundDefinition(
                    id="visible1",
                    title="Visible One",
                    steps=[
                        StepDefinition(
                            id="visible1_step",
                            title="Visible 1",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_TEXT,
                                points=1,
                                answer="ok",
                            ),
                        )
                    ],
                ),
                RoundDefinition(
                    id="hidden",
                    title="Hidden Host Round",
                    steps=[
                        StepDefinition(
                            id="hidden_step",
                            title="Hidden",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.BUZZER),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=1,
                                answer="ok",
                            ),
                        )
                    ],
                ),
                RoundDefinition(
                    id="visible2",
                    title="Visible Two",
                    steps=[
                        StepDefinition(
                            id="visible2_step",
                            title="Visible 2",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.NUMBER),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_NUMBER,
                                points=1,
                                answer=2,
                            ),
                        )
                    ],
                ),
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
async def test_snapshot_includes_active_round_metadata_across_rounds():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=TwoRoundHostlessProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_round is not None
    assert snapshot.active_round.id == "round1"
    assert snapshot.active_round.title is None
    assert snapshot.active_round.number == 1
    assert snapshot.active_round.total == 2
    assert snapshot.active_item is not None
    assert snapshot.active_item.type_ == "step"
    assert snapshot.active_item.step.id == "r1s1"

    events = await service.advance_step(lobby)
    next_snapshot = events[-1]

    assert isinstance(next_snapshot, schemas.RuntimeSnapshotEvent)
    assert next_snapshot.active_round is not None
    assert next_snapshot.active_round.id == "round2"
    assert next_snapshot.active_round.number == 2
    assert next_snapshot.active_round.total == 2
    assert next_snapshot.active_item is not None
    assert next_snapshot.active_item.type_ == "step"
    assert next_snapshot.active_item.step.id == "r2s1"


@pytest.mark.asyncio
async def test_round_intro_snapshot_hides_active_step_until_opened():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    intro_snapshot = await service.begin_round_intro(lobby)

    assert lobby.phase == "round_intro"
    assert intro_snapshot.lobby.phase == "round_intro"
    assert intro_snapshot.active_round is not None
    assert intro_snapshot.active_round.id == "round1"
    assert intro_snapshot.active_item is not None
    assert intro_snapshot.active_item.type_ == "round_intro"
    assert intro_snapshot.active_item.round.id == "round1"
    assert intro_snapshot.active_item.duration_seconds == 5.0
    assert intro_snapshot.active_step is None
    assert repo.steps["g1"]["display_phase"] == "round_intro"

    opened_snapshot = await service.open_current_step_after_round_intro(lobby)

    assert opened_snapshot is not None
    assert lobby.phase == "question_active"
    assert opened_snapshot.active_step is not None
    assert opened_snapshot.active_step.id == "buzzer_step"
    assert opened_snapshot.active_item is not None
    assert opened_snapshot.active_item.type_ == "step"
    assert opened_snapshot.active_item.step.id == "buzzer_step"
    assert opened_snapshot.active_step.input_enabled is True
    assert repo.steps["g1"]["display_phase"] == "question_active"


@pytest.mark.asyncio
async def test_hostless_snapshot_round_metadata_uses_visible_rounds():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=HostlessFilteredRoundsProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_round is not None
    assert snapshot.active_round.id == "visible1"
    assert snapshot.active_round.title == "Visible One"
    assert snapshot.active_round.number == 1
    assert snapshot.active_round.total == 2

    await service.advance_step(lobby)
    next_snapshot = await service.build_snapshot(lobby)

    assert next_snapshot.active_round is not None
    assert next_snapshot.active_round.id == "visible2"
    assert next_snapshot.active_round.number == 2
    assert next_snapshot.active_round.total == 2


@pytest.mark.asyncio
async def test_start_game_skips_incompatible_hostless_steps_but_keeps_information_slide():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=HostlessCompatibilityProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    updated_lobby, step = await service.start_game(lobby)

    assert updated_lobby.state == "running"
    assert step is not None
    assert step.id == "info_slide"


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
async def test_disabling_buzzer_pauses_reveal_and_timer():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    repo.steps["g1"]["media_reveal_started_at"] = time() - 2
    repo.steps["g1"]["timer_started_at"] = time() - 2
    repo.steps["g1"]["timer_ends_at"] = time() + 8

    events = await service.set_buzzer_state(lobby, False)

    assert [event.type_ for event in events] == ["buzzer_state", "runtime_snapshot"]
    assert lobby.phase == "host_review"
    assert repo.steps["g1"]["buzzer_active"] is False
    assert repo.steps["g1"]["media_reveal_state"] == "paused"
    assert repo.steps["g1"]["media_reveal_started_at"] is None
    assert repo.steps["g1"]["media_reveal_elapsed_seconds"] > 0
    assert repo.steps["g1"]["timer_started_at"] is None
    assert repo.steps["g1"]["timer_ends_at"] is None
    assert repo.steps["g1"]["timer_remaining_seconds"] is not None


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

    assert [event.type_ for event in events] == ["answer_judged", "buzzer_reviewed", "update_score"]
    assert repo.scores["p1"] == 2
    assert lobby.phase == "step_complete"
    assert repo.steps["g1"]["display_phase"] == "answer_reveal"
    assert repo.steps["g1"]["media_reveal_state"] == "revealed"
    assert repo.steps["g1"]["revealed_answer_value"] == "Correct Answer"


@pytest.mark.asyncio
async def test_advancing_step_clears_buzzed_player_state():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )

    events = await service.advance_step(lobby)

    assert [event.type_ for event in events] == ["step_advanced", "runtime_snapshot"]
    assert repo.steps["g1"]["buzzed_player_id"] == ""
    assert repo.steps["g1"]["buzzer_active"] is False
    assert events[-1].buzzed_player_id is None


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

    assert [event.type_ for event in events] == ["answer_judged", "buzzer_reviewed"]
    assert lobby.phase == "host_review"
    assert repo.steps["g1"]["buzzed_player_id"] == ""
    assert repo.steps["g1"]["disabled_buzzer_player_ids"] == ["p1"]
    assert repo.steps["g1"]["media_reveal_state"] == "paused"


@pytest.mark.asyncio
async def test_rejected_buzzer_snapshot_prioritizes_reactivation_before_reveal():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=False),
    )

    snapshot = await service.build_snapshot(lobby)
    reveal_events = await service.show_answer_reveal(lobby)

    assert snapshot.next_host_action is not None
    assert snapshot.next_host_action.kind == "reactivate_buzzers"
    assert reveal_events[-1].display_phase == "question_active"
    assert repo.steps["g1"]["display_phase"] == "question_active"
    assert repo.steps["g1"]["revealed_answer_value"] is None


@pytest.mark.asyncio
async def test_rejected_buzzer_can_reveal_when_no_players_remain_eligible():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=False),
    )
    repo.steps["g1"]["disabled_buzzer_player_ids"] = ["p1", "p2"]

    snapshot = await service.build_snapshot(lobby)
    reveal_events = await service.show_answer_reveal(lobby)

    assert snapshot.next_host_action is not None
    assert snapshot.next_host_action.kind == "answer_reveal"
    assert reveal_events[-1].display_phase == "answer_reveal"
    assert repo.steps["g1"]["revealed_answer_value"] == "Correct Answer"


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


def test_media_definition_validates_reveal_curve_values():
    media = MediaDefinition(
        type_=MediaType.IMAGE,
        src="/media/question.png",
        blur_reveal_curve=(0, 0.25, 0.75, 1),
    )

    assert media.blur_reveal_curve == (0, 0.25, 0.75, 1)

    with pytest.raises(ValidationError):
        MediaDefinition(
            type_=MediaType.IMAGE,
            src="/media/question.png",
            blur_reveal_curve=(0, 1.2, 0.75, 1),
        )


@pytest.mark.asyncio
async def test_snapshot_includes_image_reveal_curves():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.media is not None
    assert snapshot.active_step.media.blur_reveal_curve == (0.1, 0.2, 0.3, 0.4)
    assert snapshot.active_step.media.blur_circle_reveal_curve == (0.2, 0.3, 0.4, 0.5)
    assert snapshot.active_step.media.zoom_reveal_curve == (0.3, 0.4, 0.5, 0.6)


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
    assert snapshot.display_phase == "answer_reveal"
    assert snapshot.next_host_action is not None
    assert snapshot.next_host_action.kind == "next_question"
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
async def test_host_judged_step_can_reveal_answer_before_reviews():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=HostJudgedTextProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "guess")
    await service.submit_player_input(lobby, "p2", "another")

    events = await service.show_answer_reveal(lobby)
    snapshot = events[-1]

    assert snapshot.type_ == "runtime_snapshot"
    assert lobby.phase == "host_review"
    assert repo.steps["g1"]["display_phase"] == "answer_reveal"
    assert repo.steps["g1"]["revealed_answer_value"] == "Correct Answer"
    assert snapshot.pending_review_count == 2
    assert snapshot.next_host_action is not None
    assert snapshot.next_host_action.kind == "blocked_review"


@pytest.mark.asyncio
async def test_host_judged_pending_review_snapshot_offers_reveal_before_blocking():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=HostJudgedTextProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "guess")
    await service.close_step(lobby)

    snapshot = await service.build_snapshot(lobby)

    assert lobby.phase == "host_review"
    assert snapshot.pending_review_count == 1
    assert snapshot.next_host_action is not None
    assert snapshot.next_host_action.kind == "answer_reveal"


@pytest.mark.asyncio
async def test_auto_evaluate_marks_all_submissions_reviewed():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.submit_player_input(lobby, "p2", 10)

    score_events = await service.evaluate_auto_step(lobby)
    review_events = await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )

    assert repo.scores["p1"] == 4
    assert score_events[-1].type_ == "scores_updated"
    assert score_events[-1].updates == {}
    assert repo.steps["g1"]["reviewed_player_ids"] == ["p1", "p2"]
    assert review_events == []


@pytest.mark.asyncio
async def test_closest_number_awards_winner_and_tolerance_bands():
    repo = FakeRepo()
    repo.players.extend(
        [
            schemas.Player(id="p3", game_id="g1", name="Cara"),
            schemas.Player(id="p4", game_id="g1", name="Dan"),
        ]
    )
    repo.scores = {"p1": 0, "p2": 0, "p3": 0, "p4": 0}
    service = GameRuntimeService(repo=repo, definition_provider=ClosestNumberBandsProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 1998)
    await service.submit_player_input(lobby, "p2", 2004)
    await service.submit_player_input(lobby, "p3", 2012)
    events, handled = await service.submit_player_input(lobby, "p4", 2030)

    assert handled is True
    assert events[-1].type_ == "runtime_snapshot"
    assert repo.scores == {"p1": 4, "p2": 3, "p3": 1, "p4": 0}
    assert repo.steps["g1"]["reviewed_player_ids"] == ["p1", "p2", "p3", "p4"]


@pytest.mark.asyncio
async def test_hostless_closes_step_when_all_players_have_answered():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    first_events, first_handled = await service.submit_player_input(lobby, "p1", 27)
    second_events, second_handled = await service.submit_player_input(lobby, "p2", 10)

    assert first_handled is True
    assert first_events == []
    assert second_handled is True
    assert [event.type_ for event in second_events] == [
        "answer_judged",
        "answer_judged",
        "scores_updated",
        "runtime_snapshot",
    ]
    assert lobby.phase == "step_complete"
    assert repo.steps["g1"]["display_phase"] == "answer_reveal"
    assert repo.steps["g1"]["revealed_answer_value"] == 27


@pytest.mark.asyncio
async def test_inactive_host_closes_step_when_all_players_have_answered():
    repo = FakeRepo()
    repo.players.append(
        schemas.Player(
            id="host",
            game_id="g1",
            name="Host",
            status=schemas.ConnectionStatus.DISCONNECTED,
        )
    )
    service = GameRuntimeService(repo=repo, definition_provider=InactiveHostFallbackProvider())
    lobby = Lobby(
        id="g1",
        join_code="ABCDE",
        definition_id="quiz_demo",
        host_enabled=True,
        host_id="host",
    )

    await service.start_game(lobby)
    first_events, first_handled = await service.submit_player_input(lobby, "p1", "hello")
    second_events, second_handled = await service.submit_player_input(lobby, "p2", "nope")

    assert first_handled is True
    assert first_events == []
    assert second_handled is True
    assert [event.type_ for event in second_events] == [
        "answer_judged",
        "answer_judged",
        "scores_updated",
        "runtime_snapshot",
    ]
    assert lobby.phase == "step_complete"
    assert repo.steps["g1"]["display_phase"] == "answer_reveal"
    assert repo.steps["g1"]["revealed_answer_value"] == "hello"
    assert repo.scores["p1"] == 3
    assert repo.scores["p2"] == 5


@pytest.mark.asyncio
async def test_hostless_advisory_timer_is_effectively_enforced_in_snapshot():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.timer.enforced is True


@pytest.mark.asyncio
async def test_inactive_host_advisory_timer_is_effectively_enforced_in_snapshot():
    repo = FakeRepo()
    repo.players.append(
        schemas.Player(
            id="host",
            game_id="g1",
            name="Host",
            status=schemas.ConnectionStatus.DISCONNECTED,
        )
    )
    service = GameRuntimeService(repo=repo, definition_provider=InactiveHostFallbackProvider())
    lobby = Lobby(
        id="g1",
        join_code="ABCDE",
        definition_id="quiz_demo",
        host_enabled=True,
        host_id="host",
    )

    await service.start_game(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.evaluation_type == "exact_text"
    assert snapshot.active_step.timer.enforced is True


@pytest.mark.asyncio
async def test_hosted_timed_question_reveals_when_all_players_submit():
    repo = FakeRepo()
    repo.players.append(
        schemas.Player(
            id="host",
            game_id="g1",
            name="Host",
            status=schemas.ConnectionStatus.CONNECTED,
        )
    )
    service = GameRuntimeService(repo=repo, definition_provider=HostedTimedHostJudgedProvider())
    lobby = Lobby(
        id="g1",
        join_code="ABCDE",
        definition_id="quiz_demo",
        host_enabled=True,
        host_id="host",
    )

    await service.start_game(lobby)
    first_events, first_handled = await service.submit_player_input(lobby, "p1", "hello")
    second_events, second_handled = await service.submit_player_input(lobby, "p2", "hello")

    assert first_handled is True
    assert first_events == []
    assert second_handled is True
    assert [event.type_ for event in second_events] == ["runtime_snapshot"]
    assert lobby.phase == "host_review"
    assert repo.steps["g1"]["display_phase"] == "answer_reveal"


@pytest.mark.asyncio
async def test_hostless_round_end_shows_scoreboard_during_answer_reveal():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=TwoRoundHostlessProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "ok")
    events, handled = await service.submit_player_input(lobby, "p2", "ok")

    assert handled is True
    assert [event.type_ for event in events] == [
        "answer_judged",
        "answer_judged",
        "scores_updated",
        "runtime_snapshot",
    ]
    assert repo.steps["g1"]["scoreboard_visible"] is True


@pytest.mark.asyncio
async def test_hostless_info_slide_stays_manual():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=HostlessCompatibilityProvider())
    lobby = Lobby(
        id="g1",
        join_code="ABCDE",
        definition_id="quiz_demo",
        host_enabled=False,
        starter_id="p1",
    )

    await service.start_game(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.input_kind == "none"
    assert lobby.phase == "question_active"


@pytest.mark.asyncio
async def test_hostless_falls_back_from_host_judged_text_when_answer_exists():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=HostlessCompatibilityProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.advance_step(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.id == "host_judged_text"
    assert snapshot.active_step.evaluation_type == "exact_text"


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
async def test_host_can_review_previous_answer_reveal_without_rewinding_live_step():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=TwoExactNumberProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 1)
    await service.show_answer_reveal(lobby)
    await service.advance_step(lobby)
    await service.submit_player_input(lobby, "p2", 2)
    await service.show_answer_reveal(lobby)

    live_snapshot = await service.build_snapshot(lobby)
    assert live_snapshot.active_step is not None
    assert live_snapshot.active_step.id == "second_number"
    assert live_snapshot.can_review_previous is True

    events = await service.show_previous_reveal(lobby)
    snapshot = events[-1]

    assert isinstance(snapshot, schemas.RuntimeSnapshotEvent)
    assert lobby.current_step == 1
    assert snapshot.lobby.current_step == 1
    assert snapshot.reviewing_history is True
    assert snapshot.review_step_index == 0
    assert snapshot.display_phase == "answer_reveal"
    assert snapshot.active_step is not None
    assert snapshot.active_step.id == "first_number"
    assert snapshot.active_step.input_enabled is False
    assert snapshot.submitted_player_ids == ["p1"]


@pytest.mark.asyncio
async def test_review_next_returns_to_live_answer_reveal():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=TwoExactNumberProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 1)
    await service.show_answer_reveal(lobby)
    await service.advance_step(lobby)
    await service.submit_player_input(lobby, "p2", 2)
    await service.show_answer_reveal(lobby)
    await service.show_previous_reveal(lobby)

    events = await service.show_next_reveal(lobby)
    snapshot = events[-1]

    assert isinstance(snapshot, schemas.RuntimeSnapshotEvent)
    assert snapshot.reviewing_history is False
    assert snapshot.review_step_index is None
    assert snapshot.active_step is not None
    assert snapshot.active_step.id == "second_number"
    assert snapshot.display_phase == "answer_reveal"


@pytest.mark.asyncio
async def test_review_mode_ignores_player_input_and_reset():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=TwoExactNumberProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 1)
    await service.show_answer_reveal(lobby)
    await service.advance_step(lobby)
    await service.submit_player_input(lobby, "p2", 2)
    await service.show_answer_reveal(lobby)
    await service.show_previous_reveal(lobby)

    events, handled = await service.submit_player_input(lobby, "p1", 2)
    reset_events = await service.reset_current_step(lobby)

    assert events == []
    assert handled is False
    assert reset_events == []
    snapshot = await service.build_snapshot(lobby)
    assert snapshot.reviewing_history is True
    assert snapshot.active_step is not None
    assert snapshot.active_step.id == "first_number"


@pytest.mark.asyncio
async def test_first_answer_reveal_has_no_previous_review():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=TwoExactNumberProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 1)
    await service.show_answer_reveal(lobby)

    snapshot = await service.build_snapshot(lobby)
    events = await service.show_previous_reveal(lobby)
    previous_snapshot = events[-1]

    assert snapshot.can_review_previous is False
    assert isinstance(previous_snapshot, schemas.RuntimeSnapshotEvent)
    assert previous_snapshot.reviewing_history is False
    assert previous_snapshot.active_step is not None
    assert previous_snapshot.active_step.id == "first_number"


@pytest.mark.asyncio
async def test_close_step_skips_answer_reveal_for_none_evaluation():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=NoneEvaluationProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)

    events = await service.close_step(lobby)

    assert [event.type_ for event in events] == ["step_advanced", "runtime_snapshot"]
    assert lobby.current_step == 1
    assert lobby.phase == "question_active"
    assert repo.steps["g1"]["step_id"] == "next_step"
    assert repo.steps["g1"]["revealed_answer_value"] is None


@pytest.mark.asyncio
async def test_show_answer_reveal_advances_none_evaluation_step():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=NoneEvaluationProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)

    events = await service.show_answer_reveal(lobby)

    assert [event.type_ for event in events] == ["step_advanced", "runtime_snapshot"]
    assert lobby.current_step == 1
    assert lobby.phase == "question_active"
    assert repo.steps["g1"]["step_id"] == "next_step"


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
async def test_video_media_pause_is_reflected_in_snapshot():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=VideoDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.set_media_paused(lobby, True)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.media is not None
    assert snapshot.active_step.media.paused is True


@pytest.mark.asyncio
async def test_video_media_can_start_paused_from_definition():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=ManualVideoDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.media is not None
    assert snapshot.active_step.media.autoplay is False
    assert snapshot.active_step.media.hide_youtube_title is True
    assert snapshot.active_step.media.paused is True


@pytest.mark.asyncio
async def test_video_media_restart_updates_playback_revision_and_resumes():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=VideoDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.set_media_playback(lobby, paused=True)
    await service.set_media_playback(lobby, restart=True)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.media is not None
    assert snapshot.active_step.media.paused is False
    assert snapshot.active_step.media.playback_revision == 1


@pytest.mark.asyncio
async def test_audio_media_restart_updates_playback_revision_and_resumes():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=AudioDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.set_media_playback(lobby, paused=True)
    await service.set_media_playback(lobby, restart=True)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.media is not None
    assert snapshot.active_step.media.paused is False
    assert snapshot.active_step.media.playback_revision == 1


@pytest.mark.asyncio
async def test_media_volume_is_clamped_and_reflected_in_snapshot():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=AudioDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.set_media_playback(lobby, volume=0)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.media is not None
    assert snapshot.active_step.media.volume == 0

    await service.set_media_playback(lobby, volume=1.5)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.active_step is not None
    assert snapshot.active_step.media is not None
    assert snapshot.active_step.media.volume == 1


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


@pytest.mark.asyncio
async def test_finished_snapshot_exposes_end_game_data_and_auto_reveals_without_host():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.submit_player_input(lobby, "p2", 10)
    await service.close_step(lobby)
    await service.advance_step(lobby)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.end_game is not None
    assert snapshot.end_game.revealed is True
    assert snapshot.end_game.autoplay_enabled is True
    assert snapshot.end_game.sequence_stage == "third_place"
    assert [entry.player_id for entry in snapshot.end_game.final_standings] == ["p2", "p1"]
    assert [entry.place for entry in snapshot.end_game.final_standings] == [1, 2]
    assert snapshot.end_game.final_standings[0].avatar_kind == "custom"
    assert snapshot.end_game.final_standings[0].avatar_url == "/api/v1/media/p2-avatar"
    assert snapshot.end_game.final_standings[1].avatar_kind == "preset"
    assert snapshot.end_game.final_standings[1].avatar_preset_key == "fox"


@pytest.mark.asyncio
async def test_finished_snapshot_waits_for_host_reveal_when_host_mode_enabled():
    repo = FakeRepo()
    repo.players.append(schemas.Player(id="host", game_id="g1", name="Host", score=99))
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(
        id="g1",
        join_code="ABCDE",
        definition_id="quiz_demo",
        host_enabled=True,
        host_id="host",
    )

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )
    await service.advance_step(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.submit_player_input(lobby, "p2", 10)
    await service.close_step(lobby)
    await service.advance_step(lobby)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.end_game is not None
    assert snapshot.end_game.revealed is False
    assert [entry.player_id for entry in snapshot.end_game.final_standings] == ["p1", "p2"]
    assert all(entry.player_id != "host" for entry in snapshot.end_game.final_standings)
    assert snapshot.end_game.final_standings[0].avatar_preset_key == "fox"


@pytest.mark.asyncio
async def test_end_game_stats_include_correct_wrong_accuracy_and_fastest_buzz():
    repo = FakeRepo()
    repo.players.append(schemas.Player(id="host", game_id="g1", name="Host", score=99))
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(
        id="g1",
        join_code="ABCDE",
        definition_id="quiz_demo",
        host_enabled=True,
        host_id="host",
    )

    await service.start_game(lobby)
    repo.steps["g1"]["buzzer_opened_at"] = str(time() - 1.25)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )
    await service.advance_step(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.submit_player_input(lobby, "p2", 10)
    await service.close_step(lobby)
    await service.advance_step(lobby)
    await service.reveal_end_game(lobby)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.end_game is not None
    stats_by_id = {card.id: card for card in snapshot.end_game.stats_cards}
    assert stats_by_id["most_correct"].winner_player_ids == ["p1"]
    assert stats_by_id["most_correct"].value == 2
    assert stats_by_id["most_wrong"].winner_player_ids == ["p2"]
    assert stats_by_id["most_wrong"].value == 1
    assert "highest_accuracy" not in stats_by_id  # Too few answers to qualify.
    assert stats_by_id["fastest_buzz"].winner_player_ids == ["p1"]
    assert stats_by_id["fastest_buzz"].value > 0


@pytest.mark.asyncio
async def test_end_game_stats_include_reaction_cards_and_freeze_after_finish():
    repo = FakeRepo()
    repo.players.append(schemas.Player(id="host", game_id="g1", name="Host", score=99))
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(
        id="g1",
        join_code="ABCDE",
        definition_id="quiz_demo",
        host_enabled=True,
        host_id="host",
    )

    await service.start_game(lobby)
    await service.record_player_reaction(lobby, "p1", "😂")
    await service.record_player_reaction(lobby, "p1", "😂")
    await service.record_player_reaction(lobby, "p2", "🤮")
    await service.record_player_reaction(lobby, "p2", "🤮")
    await service.record_player_reaction(lobby, "p2", "🤮")
    await service.record_player_reaction(lobby, "host", "🔥")
    await service.record_player_reaction(lobby, "host", "🔥")
    await service.record_player_reaction(lobby, "host", "🔥")
    await service.record_player_reaction(lobby, "host", "🔥")
    await service.advance_step(lobby)
    await service.advance_step(lobby)
    await service.record_player_reaction(lobby, "p1", "😂")
    await service.record_player_reaction(lobby, "p1", "😂")
    await service.reveal_end_game(lobby)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.end_game is not None
    stats_by_id = {card.id: card for card in snapshot.end_game.stats_cards}
    assert stats_by_id["most_reactions"].winner_player_ids == ["p2"]
    assert stats_by_id["most_reactions"].value == 3
    assert stats_by_id["signature_reaction"].winner_player_ids == ["p2"]
    assert stats_by_id["signature_reaction"].value == 3
    assert stats_by_id["signature_reaction"].emoji == "🤮"
    assert stats_by_id["signature_reaction"].reaction_key == "vomit"
    assert stats_by_id["signature_reaction"].headline is None
    assert stats_by_id["signature_reaction"].description is None
    assert stats_by_id["game_mood"].winner_player_ids == []
    assert stats_by_id["game_mood"].value == 3
    assert stats_by_id["game_mood"].emoji == "🤮"
    assert stats_by_id["game_mood"].reaction_key == "vomit"
    assert stats_by_id["game_mood"].headline is None
    assert stats_by_id["game_mood"].description is None


@pytest.mark.asyncio
async def test_fastest_buzz_ignores_rejected_buzz_attempts():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    repo.steps["g1"]["buzzer_opened_at"] = str(time() - 0.4)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=False),
    )
    await service.set_buzzer_state(lobby, True)
    repo.steps["g1"]["buzzer_opened_at"] = str(time() - 1.6)
    await service.submit_player_input(lobby, "p2", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p2", accepted=True),
    )
    await service.advance_step(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.close_step(lobby)
    await service.advance_step(lobby)
    await service.reveal_end_game(lobby)

    snapshot = await service.build_snapshot(lobby)

    assert snapshot.end_game is not None
    stats_by_id = {card.id: card for card in snapshot.end_game.stats_cards}
    assert stats_by_id["fastest_buzz"].winner_player_ids == ["p2"]


@pytest.mark.asyncio
async def test_end_game_stage_and_autoplay_changes_are_reflected_in_snapshot():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "buzz")
    await service.review_submission(
        lobby,
        schemas.ReviewSubmissionEvent(player_id="p1", accepted=True),
    )
    await service.advance_step(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.close_step(lobby)
    await service.advance_step(lobby)

    await service.reveal_end_game(lobby)
    await service.toggle_end_game_autoplay(lobby, True)
    await service.advance_end_game_stage(lobby)
    snapshot = await service.build_snapshot(lobby)

    assert snapshot.end_game is not None
    assert snapshot.end_game.revealed is True
    assert snapshot.end_game.autoplay_enabled is True
    assert snapshot.end_game.sequence_stage == "second_place"


@pytest.mark.asyncio
async def test_end_game_stage_advances_through_podium_reveal_order():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=MixedDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", 27)
    await service.submit_player_input(lobby, "p2", 10)
    await service.close_step(lobby)
    await service.advance_step(lobby)

    stages = []
    for _ in range(4):
        snapshot = await service.build_snapshot(lobby)
        assert snapshot.end_game is not None
        stages.append(snapshot.end_game.sequence_stage)
        await service.advance_end_game_stage(lobby)

    assert stages == ["third_place", "second_place", "first_place", "stats"]
    snapshot = await service.build_snapshot(lobby)
    assert snapshot.end_game is not None
    assert snapshot.end_game.sequence_stage == "scoreboard"


@pytest.mark.asyncio
async def test_drawing_submission_validation_and_vote_scoring():
    repo = FakeRepo()
    service = GameRuntimeService(repo, DrawingDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="drawing_test", host_enabled=True)
    lobby, _ = await service.start_game(lobby)

    invalid_events, invalid_handled = await service.submit_player_input(
        lobby,
        "p1",
        {"w": 512, "h": 384, "s": []},
    )
    assert invalid_events == []
    assert invalid_handled is False

    first_events, first_handled = await service.submit_player_input(
        lobby,
        "p1",
        valid_drawing("#ef4444"),
    )
    duplicate_events, duplicate_handled = await service.submit_player_input(
        lobby,
        "p1",
        valid_drawing("#3b82f6"),
    )
    second_events, second_handled = await service.submit_player_input(
        lobby,
        "p2",
        valid_drawing("#22c55e"),
    )
    assert first_events == []
    assert first_handled is True
    assert duplicate_events == []
    assert duplicate_handled is False
    assert second_events == []
    assert second_handled is True

    events = await service.close_step(lobby)
    assert isinstance(events[-1], schemas.RuntimeSnapshotEvent)
    assert repo.steps["g1"]["display_phase"] == "drawing_vote"
    assert events[-1].active_step is not None
    assert events[-1].active_step.evaluation_answer == "Cats should have visible whiskers."
    assert events[-1].drawing_items[0].player_id is None
    assert events[-1].drawing_items[0].player_name is None

    self_vote_events, self_vote_handled = await service.submit_drawing_vote(
        lobby,
        "p1",
        "drawing:0",
    )
    assert self_vote_events == []
    assert self_vote_handled is False

    first_vote_events, first_vote_handled = await service.submit_drawing_vote(
        lobby,
        "p1",
        "drawing:1",
    )
    duplicate_vote_events, duplicate_vote_handled = await service.submit_drawing_vote(
        lobby,
        "p1",
        "drawing:1",
    )
    assert first_vote_events == []
    assert first_vote_handled is True
    assert duplicate_vote_events == []
    assert duplicate_vote_handled is False

    final_events, final_handled = await service.submit_drawing_vote(lobby, "p2", "drawing:0")
    assert final_handled is True
    assert any(isinstance(event, schemas.ScoresUpdatedEvent) for event in final_events)
    assert repo.steps["g1"]["display_phase"] == "answer_reveal"
    assert repo.scores["p1"] == 2
    assert repo.scores["p2"] == 7

    final_snapshot = final_events[-1]
    assert isinstance(final_snapshot, schemas.RuntimeSnapshotEvent)
    assert [item.player_name for item in final_snapshot.drawing_items] == ["Alice", "Bob"]
    assert [item.vote_count for item in final_snapshot.drawing_items] == [1, 1]
    assert [item.points_awarded for item in final_snapshot.drawing_items] == [2, 2]


@pytest.mark.asyncio
async def test_show_answer_reveal_opens_drawing_vote_before_results():
    repo = FakeRepo()
    service = GameRuntimeService(repo, DrawingDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="drawing_test", host_enabled=True)
    lobby, _ = await service.start_game(lobby)

    await service.submit_player_input(lobby, "p1", valid_drawing("#ef4444"))
    await service.submit_player_input(lobby, "p2", valid_drawing("#22c55e"))

    events = await service.show_answer_reveal(lobby)

    assert isinstance(events[-1], schemas.RuntimeSnapshotEvent)
    assert repo.steps["g1"]["display_phase"] == "drawing_vote"
    assert events[-1].lobby.phase == "question_active"
    assert events[-1].drawing_items[0].player_id is None
    assert events[-1].drawing_items[0].player_name is None


@pytest.mark.asyncio
async def test_drawing_submission_accepts_expanded_limits():
    repo = FakeRepo()
    service = GameRuntimeService(repo, DrawingDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="drawing_test", host_enabled=True)
    lobby, _ = await service.start_game(lobby)

    events, handled = await service.submit_player_input(
        lobby,
        "p1",
        drawing_with_counts(stroke_count=320, points_per_stroke=20),
    )

    assert events == []
    assert handled is True


@pytest.mark.asyncio
async def test_drawing_submission_rejects_expanded_limit_overages():
    repo = FakeRepo()
    service = GameRuntimeService(repo, DrawingDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="drawing_test", host_enabled=True)
    lobby, _ = await service.start_game(lobby)

    too_many_strokes_events, too_many_strokes_handled = await service.submit_player_input(
        lobby,
        "p1",
        drawing_with_counts(stroke_count=321, points_per_stroke=1),
    )
    too_many_points_events, too_many_points_handled = await service.submit_player_input(
        lobby,
        "p1",
        drawing_with_counts(stroke_count=320, points_per_stroke=21),
    )
    too_large_payload = valid_drawing() | {"padding": "x" * 240_000}
    too_large_payload_events, too_large_payload_handled = await service.submit_player_input(
        lobby,
        "p1",
        too_large_payload,
    )

    assert too_many_strokes_events == []
    assert too_many_strokes_handled is False
    assert too_many_points_events == []
    assert too_many_points_handled is False
    assert too_large_payload_events == []
    assert too_large_payload_handled is False


@pytest.mark.asyncio
async def test_single_drawing_skips_vote_phase_and_reveals_results():
    repo = FakeRepo()
    service = GameRuntimeService(repo, DrawingDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="drawing_test", host_enabled=True)
    lobby, _ = await service.start_game(lobby)

    await service.submit_player_input(lobby, "p1", valid_drawing("#ef4444"))

    events = await service.close_step(lobby)

    assert repo.steps["g1"]["display_phase"] == "answer_reveal"
    assert repo.scores["p1"] == 0
    assert repo.scores["p2"] == 5
    snapshot = events[-1]
    assert isinstance(snapshot, schemas.RuntimeSnapshotEvent)
    assert snapshot.drawing_items[0].player_name == "Alice"
    assert snapshot.drawing_items[0].vote_count == 0
    assert snapshot.drawing_items[0].points_awarded == 0


@pytest.mark.asyncio
async def test_reset_closed_question_accepts_another_answer_from_same_player():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=HostJudgedTextProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=True)

    await service.start_game(lobby)
    _, handled = await service.submit_player_input(lobby, "p1", "first answer")
    assert handled is True
    await service.close_step(lobby)
    assert lobby.phase != "question_active"

    events = await service.reset_current_step(lobby)
    snapshot = events[0]
    assert snapshot.active_step.input_enabled is True
    assert snapshot.submitted_player_ids == []

    _, handled = await service.submit_player_input(lobby, "p1", "second answer")
    assert handled is True
    assert repo.steps[lobby.id]["answers"]["p1"] == "second answer"
