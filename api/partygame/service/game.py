from __future__ import annotations

import logging
from time import time
from typing import Any
from uuid import uuid4

from partygame import schemas
from partygame.core.config import settings
from partygame.schemas.game_definition import (
    EvaluationType,
    MediaType,
    PlayerInputKind,
    RoundDefinition,
    StepDefinition,
)
from partygame.service.definitions import DefinitionProvider, get_default_definition_provider
from partygame.service.runtime.end_game import (
    END_GAME_COMPONENT_ID,
    END_GAME_SEQUENCE_STAGES,
    PLAYER_METRICS_COMPONENT_ID,
    REACTION_KEYS,
    EndGameRuntime,
)
from partygame.service.runtime.evaluation import (
    HOSTLESS_AUTO_EVALUATION_TYPES,
    EvaluationRuntime,
)
from partygame.service.runtime.snapshots import (
    ROUND_INTRO_DURATION_SECONDS,
    SnapshotBuilder,
)
from partygame.service.runtime.steps import FlattenedStep
from partygame.service.runtime.timing import TimingState
from partygame.service.stats import GameStatsArchiver
from partygame.state import GameStateRepository

log = logging.getLogger(__name__)

__all__ = (
    "END_GAME_COMPONENT_ID",
    "END_GAME_SEQUENCE_STAGES",
    "GameRuntimeService",
    "HOSTLESS_AUTO_EVALUATION_TYPES",
    "PLAYER_METRICS_COMPONENT_ID",
    "REACTION_KEYS",
    "ROUND_INTRO_DURATION_SECONDS",
)


class GameRuntimeService:
    def __init__(
        self,
        repo: GameStateRepository,
        definition_provider: DefinitionProvider | None = None,
        stats_archiver: GameStatsArchiver | None = None,
        archive_game_stats: bool = True,
    ):
        self.repo = repo
        self.definition_provider = definition_provider or get_default_definition_provider()
        self.timing = TimingState()
        self.evaluation = EvaluationRuntime(repo, self.timing, get_step_state=self.get_step_state)
        self.end_game = EndGameRuntime(repo, self.timing)
        self.stats_archiver = (
            stats_archiver
            if stats_archiver is not None
            else (
                GameStatsArchiver(
                    repo,
                    definition_provider=self.definition_provider,
                )
                if archive_game_stats
                else None
            )
        )
        self.snapshots = SnapshotBuilder(
            runtime=self,
            repo=repo,
            evaluation=self.evaluation,
            timing=self.timing,
            end_game=self.end_game,
        )

    async def _flatten_steps_with_metadata(
        self,
        lobby: schemas.Lobby,
    ) -> list[FlattenedStep]:
        definition_id = lobby.definition_id or "quiz_demo"
        definition = await self.definition_provider.load(definition_id)
        visible_rounds: list[tuple[RoundDefinition, list[StepDefinition]]] = []
        for round_definition in definition.rounds:
            compatible_steps = [
                step
                for step in round_definition.steps
                if lobby.host_enabled or self.evaluation.is_hostless_compatible_step(lobby, step)
            ]
            if compatible_steps:
                visible_rounds.append((round_definition, compatible_steps))

        steps: list[FlattenedStep] = []
        total_rounds = len(visible_rounds)
        for round_index, (round_definition, compatible_steps) in enumerate(visible_rounds):
            for index, step in enumerate(compatible_steps):
                steps.append(
                    FlattenedStep(
                        step=step,
                        round_definition=round_definition,
                        round_number=round_index + 1,
                        total_rounds=total_rounds,
                        is_round_end=index == len(compatible_steps) - 1,
                    )
                )
        return steps

    async def _flatten_steps(self, lobby: schemas.Lobby) -> list[StepDefinition]:
        return [item.step for item in await self._flatten_steps_with_metadata(lobby)]

    async def get_current_step(self, lobby: schemas.Lobby) -> StepDefinition | None:
        steps = await self._flatten_steps_with_metadata(lobby)
        if lobby.current_step >= len(steps):
            return None
        return steps[lobby.current_step].step

    def is_information_slide(self, step: StepDefinition) -> bool:
        return self.evaluation.is_information_slide(step)

    async def get_current_round(self, lobby: schemas.Lobby) -> schemas.RuntimeRoundState | None:
        steps = await self._flatten_steps_with_metadata(lobby)
        if lobby.current_step >= len(steps):
            return None
        current = steps[lobby.current_step]
        return self.snapshots.runtime_round_state(current)

    async def is_current_step_round_end(self, lobby: schemas.Lobby) -> bool:
        steps = await self._flatten_steps_with_metadata(lobby)
        if lobby.current_step >= len(steps):
            return False
        return steps[lobby.current_step].is_round_end

    async def start_game(self, lobby: schemas.Lobby) -> tuple[schemas.Lobby, StepDefinition | None]:
        await self.end_game.initialize_end_game_state(lobby.id, auto_reveal=not lobby.host_enabled)
        if self.stats_archiver is not None:
            await self.stats_archiver.mark_started(lobby.id)
        await self.repo.set_lobby_fields(
            lobby.id,
            state=schemas.GameState.RUNNING,
            phase="question_active",
            current_step=0,
        )
        lobby.state = schemas.GameState.RUNNING
        lobby.phase = "question_active"
        lobby.current_step = 0

        step = await self.get_current_step(lobby)
        if step is None:
            lobby.phase = "finished"
            await self.repo.set_lobby_fields(lobby.id, phase="finished")
            await self._archive_finished_game(lobby)
            await self.repo.apply_game_ttl(lobby.id, settings.GAME_FINISHED_TTL_SECONDS)
            return lobby, None
        await self.initialize_step_state(lobby, step)
        return lobby, step

    async def initialize_step_state(self, lobby: schemas.Lobby, step: StepDefinition):
        started_at = time()
        ends_at = None
        if step.timer.seconds is not None:
            ends_at = started_at + step.timer.seconds

        await self.repo.set_step_cache(
            lobby.id,
            {
                "step_id": step.id,
                "step_index": lobby.current_step,
                "display_phase": "question_active",
                "scoreboard_visible": False,
                "media_paused": (
                    step.media.type_ == MediaType.VIDEO and not step.media.autoplay
                    if step.media is not None
                    else False
                ),
                "media_playback_revision": 0,
                "media_volume": 1,
                "answers": {},
                "drawing_votes": {},
                "drawing_vote_order": [],
                "drawing_score_updates": {},
                "evaluated": False,
                "buzzer_active": lobby.host_enabled
                and step.player_input.kind == PlayerInputKind.BUZZER,
                "buzzed_player_id": "",
                "buzzer_opened_at": (
                    started_at
                    if lobby.host_enabled and step.player_input.kind == PlayerInputKind.BUZZER
                    else None
                ),
                "buzz_reaction_seconds": None,
                "disabled_buzzer_player_ids": [],
                "revealed_submission_player_id": "",
                "revealed_submission_value": None,
                "revealed_answer_value": None,
                "reviewed_player_ids": [],
                "timer_started_at": started_at,
                "timer_ends_at": ends_at,
                "timer_remaining_seconds": (
                    float(step.timer.seconds) if step.timer.seconds is not None else None
                ),
                "review_step_index": "",
                **self.timing.initial_reveal_state(step, started_at),
            },
        )

    async def begin_round_intro(self, lobby: schemas.Lobby) -> schemas.RuntimeSnapshotEvent:
        await self.repo.set_lobby_fields(lobby.id, phase="round_intro")
        lobby.phase = "round_intro"
        await self.repo.set_step_cache(
            lobby.id,
            {
                "display_phase": "round_intro",
                "scoreboard_visible": False,
                "buzzer_active": False,
                "buzzed_player_id": "",
                "buzzer_opened_at": None,
                "buzz_reaction_seconds": None,
            },
        )
        return await self.build_snapshot(lobby)

    async def open_current_step_after_round_intro(
        self,
        lobby: schemas.Lobby,
    ) -> schemas.RuntimeSnapshotEvent | None:
        if lobby.phase != "round_intro":
            return None
        step = await self.get_current_step(lobby)
        if step is None:
            return None
        await self.repo.set_lobby_fields(lobby.id, phase="question_active")
        lobby.phase = "question_active"
        await self.initialize_step_state(lobby, step)
        return await self.build_snapshot(lobby)

    async def get_step_state(self, lobby_id: str) -> dict[str, Any]:
        return await self.repo.get_step_cache(lobby_id)

    def _step_archive_component_id(self, step_index: int) -> str:
        return f"step_archive:{step_index}"

    def _review_step_index(self, step_state: dict[str, Any]) -> int | None:
        value = step_state.get("review_step_index")
        if value in (None, ""):
            return None
        try:
            return int(value)
        except TypeError, ValueError:
            return None

    async def get_archived_step_state(
        self,
        lobby_id: str,
        step_index: int,
    ) -> dict[str, Any]:
        return await self.repo.get_component_state(
            lobby_id,
            self._step_archive_component_id(step_index),
        )

    async def _archive_current_step_reveal(self, lobby: schemas.Lobby):
        state = await self.get_step_state(lobby.id)
        if state.get("display_phase") != "answer_reveal":
            return
        archived_state = dict(state)
        archived_state["display_phase"] = "answer_reveal"
        archived_state["review_step_index"] = ""
        await self.repo.set_component_state(
            lobby.id,
            self._step_archive_component_id(lobby.current_step),
            archived_state,
        )

    async def _has_archived_step(self, lobby_id: str, step_index: int) -> bool:
        return bool(await self.get_archived_step_state(lobby_id, step_index))

    async def submit_player_input(
        self,
        lobby: schemas.Lobby,
        player_id: str,
        value: Any,
    ) -> tuple[list[schemas.BaseEvent], bool]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return [], False
        step = await self.get_current_step(lobby)
        if step is None or player_id == lobby.host_id or lobby.phase != "question_active":
            return [], False

        state = await self.get_step_state(lobby.id)
        if step.player_input.kind == PlayerInputKind.BUZZER:
            disabled_player_ids = set(state.get("disabled_buzzer_player_ids", []))
            if (
                not state.get("buzzer_active")
                or state.get("buzzed_player_id")
                or player_id in disabled_player_ids
            ):
                return [], False
            updates: dict[str, Any] = {
                "buzzed_player_id": player_id,
                "buzzer_active": False,
                "buzz_reaction_seconds": self.timing.buzzer_reaction_seconds(state),
            }
            if lobby.phase != "host_review":
                await self.repo.set_lobby_fields(lobby.id, phase="host_review")
                lobby.phase = "host_review"
            reveal_updates = self.timing.pause_reveal_state(state)
            updates.update(reveal_updates)
            updates.update(self.timing.pause_timer_state(state))
            await self.repo.set_step_cache(
                lobby.id,
                updates,
            )
            return [
                schemas.BuzzerStateEvent(active=False),
                schemas.BuzzerClickedEvent(player_id=player_id),
            ], True

        answers = state.get("answers", {})
        if player_id in answers:
            return [], False
        if (
            step.player_input.kind == PlayerInputKind.MAP
            and not self.evaluation.is_valid_map_submission(step, value)
        ):
            return [], False
        if (
            step.player_input.kind == PlayerInputKind.DRAWING
            and not self.evaluation.is_valid_drawing_submission(value)
        ):
            return [], False
        answers[player_id] = value
        await self.repo.set_step_cache(lobby.id, {"answers": answers})
        if await self.evaluation.should_auto_close_on_all_submissions(
            lobby, step
        ) and await self.evaluation.all_answerable_players_submitted(
            lobby, state | {"answers": answers}
        ):
            return await self.close_step(lobby), True
        return [], True

    async def submit_drawing_vote(
        self,
        lobby: schemas.Lobby,
        player_id: str,
        drawing_id: str,
    ) -> tuple[list[schemas.BaseEvent], bool]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return [], False
        step = await self.get_current_step(lobby)
        if (
            step is None
            or player_id == lobby.host_id
            or lobby.phase != "question_active"
            or step.player_input.kind != PlayerInputKind.DRAWING
            or step.evaluation.type_ != EvaluationType.FAVORITE_VOTE
        ):
            return [], False

        state = await self.get_step_state(lobby.id)
        if state.get("display_phase") != "drawing_vote":
            return [], False
        votes = dict(state.get("drawing_votes", {}))
        if player_id in votes:
            return [], False

        target_player_id = self._drawing_player_id_for_vote_id(state, drawing_id)
        if not target_player_id or target_player_id == player_id:
            return [], False

        votes[player_id] = target_player_id
        await self.repo.set_step_cache(lobby.id, {"drawing_votes": votes})
        if await self._all_drawing_voters_submitted(lobby, state | {"drawing_votes": votes}):
            return await self.close_step(lobby), True
        return [], True

    async def set_buzzer_state(self, lobby: schemas.Lobby, active: bool) -> list[schemas.BaseEvent]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return []
        step = await self.get_current_step(lobby)
        if step is None or step.player_input.kind != PlayerInputKind.BUZZER:
            return []
        state = await self.get_step_state(lobby.id)
        updates: dict[str, Any] = {"buzzer_active": active}
        if active:
            updates["buzzed_player_id"] = ""
            updates["buzzer_opened_at"] = time()
            updates["buzz_reaction_seconds"] = None
            updates.update(self.timing.resume_reveal_state(state, step))
            updates.update(self.timing.resume_timer_state(state))
            await self.repo.set_lobby_fields(lobby.id, phase="question_active")
            lobby.phase = "question_active"
        else:
            updates.update(self.timing.pause_reveal_state(state))
            updates.update(self.timing.pause_timer_state(state))
            if lobby.phase == "question_active":
                await self.repo.set_lobby_fields(lobby.id, phase="host_review")
                lobby.phase = "host_review"
        await self.repo.set_step_cache(lobby.id, updates)
        return [schemas.BuzzerStateEvent(active=active), await self.build_snapshot(lobby)]

    async def reveal_submission(
        self,
        lobby: schemas.Lobby,
        player_id: str | None,
    ) -> schemas.RevealedSubmissionEvent:
        state = await self.get_step_state(lobby.id)
        answers = state.get("answers", {})
        submission = None
        if player_id is not None and player_id in answers:
            await self.repo.set_step_cache(
                lobby.id,
                {
                    "revealed_submission_player_id": player_id,
                    "revealed_submission_value": answers[player_id],
                },
            )
            submission = schemas.RevealedSubmission(player_id=player_id, value=answers[player_id])
        else:
            await self.repo.set_step_cache(
                lobby.id,
                {
                    "revealed_submission_player_id": "",
                    "revealed_submission_value": None,
                },
            )
        return schemas.RevealedSubmissionEvent(submission=submission)

    async def show_answer_reveal(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        step = await self.get_current_step(lobby)
        if step is None:
            return []
        state = await self.get_step_state(lobby.id)
        if (
            step.player_input.kind == PlayerInputKind.BUZZER
            and lobby.phase == "host_review"
            and state.get("display_phase") != "answer_reveal"
            and not bool(state.get("buzzer_active"))
            and self.snapshots.pending_review_count(state) == 0
            and await self.snapshots.has_eligible_buzzer_players(lobby, state)
        ):
            return [await self.build_snapshot(lobby)]
        if await self.evaluation.should_skip_answer_reveal(lobby, step):
            if lobby.phase == "question_active":
                return await self.close_step(lobby)
            return await self.advance_step(lobby)

        updates: dict[str, Any] = {}

        if lobby.phase == "question_active":
            events = await self.close_step(lobby)
            state = await self.get_step_state(lobby.id)
            if (
                lobby.phase == "host_review"
                and step.evaluation.type_ == EvaluationType.HOST_JUDGED
                and state.get("display_phase") != "answer_reveal"
            ):
                updates["display_phase"] = "answer_reveal"
                updates.update(self.timing.answer_reveal_updates(step))
                await self.repo.set_step_cache(lobby.id, updates)
                return [*events[:-1], await self.build_snapshot(lobby)]
            if lobby.phase == "host_review":
                return events
            if state.get("display_phase") == "answer_reveal":
                return events

        if state.get("display_phase") == "answer_reveal":
            return [await self.build_snapshot(lobby)]

        if (
            step.player_input.kind == PlayerInputKind.DRAWING
            and step.evaluation.type_ == EvaluationType.FAVORITE_VOTE
            and state.get("display_phase") == "drawing_vote"
        ):
            return await self.close_step(lobby)

        updates["display_phase"] = "answer_reveal"
        updates.update(self.timing.answer_reveal_updates(step))
        await self.repo.set_step_cache(lobby.id, updates)
        return [await self.build_snapshot(lobby)]

    async def show_question(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        step = await self.get_current_step(lobby)
        if step is None:
            return []

        await self.repo.set_step_cache(
            lobby.id,
            {"display_phase": "question_active", "review_step_index": ""},
        )
        return [await self.build_snapshot(lobby)]

    async def show_previous_reveal(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        live_state = await self.get_step_state(lobby.id)
        source_index = self._review_step_index(live_state)
        if source_index is None:
            if live_state.get("display_phase") != "answer_reveal":
                return [await self.build_snapshot(lobby)]
            source_index = lobby.current_step

        target_index = source_index - 1
        if target_index < 0 or not await self._has_archived_step(lobby.id, target_index):
            return [await self.build_snapshot(lobby)]

        await self.repo.set_step_cache(lobby.id, {"review_step_index": target_index})
        return [await self.build_snapshot(lobby)]

    async def show_next_reveal(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        live_state = await self.get_step_state(lobby.id)
        review_index = self._review_step_index(live_state)
        if review_index is None:
            return [await self.build_snapshot(lobby)]

        target_index = review_index + 1
        if target_index >= lobby.current_step:
            await self.repo.set_step_cache(lobby.id, {"review_step_index": ""})
            return [await self.build_snapshot(lobby)]

        if not await self._has_archived_step(lobby.id, target_index):
            await self.repo.set_step_cache(lobby.id, {"review_step_index": ""})
            return [await self.build_snapshot(lobby)]

        await self.repo.set_step_cache(lobby.id, {"review_step_index": target_index})
        return [await self.build_snapshot(lobby)]

    async def set_scoreboard_visibility(
        self,
        lobby: schemas.Lobby,
        visible: bool,
    ) -> list[schemas.BaseEvent]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return []
        step = await self.get_current_step(lobby)
        if step is None:
            return []

        await self.repo.set_step_cache(lobby.id, {"scoreboard_visible": visible})
        return [await self.build_snapshot(lobby)]

    async def set_media_playback(
        self,
        lobby: schemas.Lobby,
        paused: bool | None = None,
        restart: bool = False,
        volume: float | None = None,
    ) -> list[schemas.BaseEvent]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return []
        step = await self.get_current_step(lobby)
        if (
            step is None
            or step.media is None
            or step.media.type_
            not in {
                MediaType.AUDIO,
                MediaType.VIDEO,
            }
        ):
            return []

        state = await self.get_step_state(lobby.id)
        next_state = dict(state)
        if paused is not None:
            next_state["media_paused"] = paused
        if volume is not None:
            next_state["media_volume"] = max(0, min(1, volume))
        if restart:
            next_state["media_paused"] = False if paused is None else paused
            next_state["media_playback_revision"] = (
                int(state.get("media_playback_revision") or 0) + 1
            )

        updates = {
            key: value
            for key, value in {
                "media_paused": next_state.get("media_paused"),
                "media_playback_revision": next_state.get("media_playback_revision"),
                "media_volume": next_state.get("media_volume"),
            }.items()
            if state.get(key) != value
        }
        if not updates:
            return [await self.build_snapshot(lobby)]

        await self.repo.set_step_cache(lobby.id, updates)
        return [await self.build_snapshot(lobby)]

    async def set_media_paused(
        self,
        lobby: schemas.Lobby,
        paused: bool,
    ) -> list[schemas.BaseEvent]:
        return await self.set_media_playback(lobby, paused=paused)

    async def update_score(
        self, lobby: schemas.Lobby, event: schemas.UpdateScoreEvent
    ) -> schemas.UpdateScoreEvent:
        if event.set_score is not None:
            score = event.set_score
        else:
            score = await self.repo.get_player_score(lobby.id, event.player_id)
            score += event.add_score
        await self.repo.set_player_score(lobby.id, event.player_id, score)
        return schemas.UpdateScoreEvent(player_id=event.player_id, set_score=score)

    async def review_submission(
        self,
        lobby: schemas.Lobby,
        event: schemas.ReviewSubmissionEvent,
    ) -> list[schemas.BaseEvent]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return []
        step = await self.get_current_step(lobby)
        if step is None:
            return []
        state = await self.get_step_state(lobby.id)
        reviewed_player_ids = list(state.get("reviewed_player_ids", []))
        if event.player_id in reviewed_player_ids:
            return []

        answers = state.get("answers", {})
        buzzed_player_id = state.get("buzzed_player_id") or ""
        valid_player_ids = set(answers.keys())
        if buzzed_player_id:
            valid_player_ids.add(buzzed_player_id)
        if event.player_id not in valid_player_ids:
            return []

        reviewed_player_ids.append(event.player_id)
        events: list[schemas.BaseEvent] = []
        batch_id = uuid4().hex

        if step.player_input.kind == PlayerInputKind.BUZZER:
            updates: dict[str, Any] = {"reviewed_player_ids": reviewed_player_ids}
            disabled_player_ids = list(state.get("disabled_buzzer_player_ids", []))
            events.append(
                schemas.AnswerJudgedEvent(
                    player_id=event.player_id,
                    accepted=event.accepted,
                    source="host_review",
                    input_kind=step.player_input.kind,
                    batch_id=batch_id,
                )
            )
            if event.accepted:
                await self.end_game.apply_player_metric_updates(
                    lobby.id,
                    {
                        event.player_id: {
                            "answered_count": 1,
                            "correct_count": 1,
                            "fastest_buzz_seconds": self.timing.to_float(
                                state.get("buzz_reaction_seconds")
                            ),
                        }
                    },
                )
                events.append(
                    schemas.BuzzerReviewedEvent(
                        player_id=event.player_id,
                        accepted=event.accepted,
                        disabled_buzzer_player_ids=disabled_player_ids,
                    )
                )
                points = (
                    step.evaluation.points
                    if event.points_override is None
                    else event.points_override
                )
                score_event = await self.update_score(
                    lobby,
                    schemas.UpdateScoreEvent(player_id=event.player_id, add_score=points),
                )
                updates.update(self.timing.reveal_answer_state(step))
                updates["display_phase"] = "answer_reveal"
                updates["buzzed_player_id"] = event.player_id
                await self.repo.set_step_cache(lobby.id, updates)
                await self.repo.set_lobby_fields(lobby.id, phase="step_complete")
                lobby.phase = "step_complete"
                events.append(score_event)
            else:
                await self.end_game.apply_player_metric_updates(
                    lobby.id,
                    {
                        event.player_id: {
                            "answered_count": 1,
                            "wrong_count": 1,
                        }
                    },
                )
                if event.player_id not in disabled_player_ids:
                    disabled_player_ids.append(event.player_id)
                events.append(
                    schemas.BuzzerReviewedEvent(
                        player_id=event.player_id,
                        accepted=event.accepted,
                        disabled_buzzer_player_ids=disabled_player_ids,
                    )
                )
                updates.update(
                    {
                        "disabled_buzzer_player_ids": disabled_player_ids,
                        "buzzed_player_id": "",
                        "buzzer_active": False,
                    }
                )
                await self.repo.set_step_cache(lobby.id, updates)
                await self.repo.set_lobby_fields(lobby.id, phase="host_review")
                lobby.phase = "host_review"
            return events

        await self.end_game.apply_player_metric_updates(
            lobby.id,
            {
                event.player_id: {
                    "answered_count": 1,
                    "correct_count": 1 if event.accepted else 0,
                    "wrong_count": 0 if event.accepted else 1,
                }
            },
        )
        await self.repo.set_step_cache(lobby.id, {"reviewed_player_ids": reviewed_player_ids})
        events.append(
            schemas.AnswerJudgedEvent(
                player_id=event.player_id,
                accepted=event.accepted,
                source="host_review",
                input_kind=step.player_input.kind,
                batch_id=batch_id,
            )
        )

        if event.accepted:
            points = (
                step.evaluation.points if event.points_override is None else event.points_override
            )
            score_event = await self.update_score(
                lobby,
                schemas.UpdateScoreEvent(player_id=event.player_id, add_score=points),
            )
            events.append(score_event)

        if (
            self.snapshots.pending_review_count(
                state | {"reviewed_player_ids": reviewed_player_ids}
            )
            == 0
        ):
            await self.repo.set_lobby_fields(lobby.id, phase="step_complete")
            lobby.phase = "step_complete"

        return events

    async def evaluate_auto_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return [schemas.ScoresUpdatedEvent()]
        step = await self.get_current_step(lobby)
        if step is None:
            return [schemas.ScoresUpdatedEvent()]
        state = await self.get_step_state(lobby.id)
        if state.get("evaluated"):
            return [schemas.ScoresUpdatedEvent()]

        answers = state.get("answers", {})
        reviewed_player_ids = list(answers.keys())
        updates: dict[str, int] = {}
        metric_updates = {
            player_id: {"answered_count": 1, "correct_count": 0, "wrong_count": 1}
            for player_id in answers
        }
        accepted_player_ids: set[str] = set()
        evaluation_type = await self.evaluation.resolve_evaluation_type(lobby, step)

        if evaluation_type == EvaluationType.EXACT_TEXT:
            accepted_answers = self.evaluation.exact_text_answers(step)
            max_distance = (
                step.evaluation.max_distance
                if step.player_input.kind == PlayerInputKind.TEXT
                else 0
            )
            for player_id, value in answers.items():
                if self.evaluation.matches_exact_text_answer(value, accepted_answers, max_distance):
                    new_score = (
                        await self.repo.get_player_score(lobby.id, player_id)
                        + step.evaluation.points
                    )
                    await self.repo.set_player_score(lobby.id, player_id, new_score)
                    updates[player_id] = new_score
                    accepted_player_ids.add(player_id)
                    metric_updates[player_id]["correct_count"] = 1
                    metric_updates[player_id]["wrong_count"] = 0
        elif evaluation_type == EvaluationType.EXACT_NUMBER:
            try:
                expected = float(step.evaluation.answer)
            except TypeError, ValueError:
                expected = None
            if expected is not None:
                for player_id, value in answers.items():
                    try:
                        numeric = float(value)
                    except TypeError, ValueError:
                        continue
                    if numeric == expected:
                        new_score = (
                            await self.repo.get_player_score(lobby.id, player_id)
                            + step.evaluation.points
                        )
                        await self.repo.set_player_score(lobby.id, player_id, new_score)
                        updates[player_id] = new_score
                        accepted_player_ids.add(player_id)
                        metric_updates[player_id]["correct_count"] = 1
                        metric_updates[player_id]["wrong_count"] = 0
        elif evaluation_type == EvaluationType.CLOSEST_NUMBER:
            try:
                target = float(step.evaluation.answer)
            except TypeError, ValueError:
                target = None
            diffs: list[tuple[float, str]] = []
            if target is not None:
                for player_id, value in answers.items():
                    try:
                        diffs.append((abs(float(value) - target), player_id))
                    except TypeError, ValueError:
                        continue
            if diffs:
                diffs.sort(key=lambda item: (item[0], item[1]))
                winner = diffs[0][1]
                number_bands = sorted(
                    step.evaluation.number_bands,
                    key=lambda band: band.distance,
                )
                for difference, player_id in diffs:
                    delta = step.evaluation.points if player_id == winner else 0
                    if player_id != winner:
                        for band in number_bands:
                            if difference <= band.distance:
                                delta = band.points
                                break
                    if delta <= 0:
                        continue
                    new_score = await self.repo.get_player_score(lobby.id, player_id) + delta
                    await self.repo.set_player_score(lobby.id, player_id, new_score)
                    updates[player_id] = new_score
                    accepted_player_ids.add(player_id)
                    metric_updates[player_id]["correct_count"] = 1
                    metric_updates[player_id]["wrong_count"] = 0
        elif evaluation_type == EvaluationType.ORDERING_MATCH:
            expected = step.evaluation.answer
            if isinstance(expected, list):
                for player_id, value in answers.items():
                    if value == expected:
                        new_score = (
                            await self.repo.get_player_score(lobby.id, player_id)
                            + step.evaluation.points
                        )
                        await self.repo.set_player_score(lobby.id, player_id, new_score)
                        updates[player_id] = new_score
                        accepted_player_ids.add(player_id)
                        metric_updates[player_id]["correct_count"] = 1
                        metric_updates[player_id]["wrong_count"] = 0
        elif evaluation_type == EvaluationType.MULTI_SELECT_WEIGHTED:
            answer = step.evaluation.answer
            option_scores = answer.get("option_scores") if isinstance(answer, dict) else None
            if isinstance(option_scores, list):
                score_by_option: dict[str, int] = {}
                for entry in option_scores:
                    if not isinstance(entry, dict):
                        continue
                    option = entry.get("option")
                    points = entry.get("points")
                    if isinstance(option, str) and isinstance(points, int):
                        score_by_option[option] = points
                for player_id, value in answers.items():
                    if not isinstance(value, list):
                        continue
                    delta = sum(score_by_option.get(option, 0) for option in set(value))
                    if delta > 0:
                        new_score = await self.repo.get_player_score(lobby.id, player_id) + delta
                        await self.repo.set_player_score(lobby.id, player_id, new_score)
                        updates[player_id] = new_score
                        accepted_player_ids.add(player_id)
                        metric_updates[player_id]["correct_count"] = 1
                        metric_updates[player_id]["wrong_count"] = 0
        elif evaluation_type == EvaluationType.MAP_DISTANCE:
            for player_id, value in answers.items():
                delta = self.evaluation.score_map_distance_answer(step, value)
                if delta <= 0:
                    continue
                new_score = await self.repo.get_player_score(lobby.id, player_id) + delta
                await self.repo.set_player_score(lobby.id, player_id, new_score)
                updates[player_id] = new_score
                accepted_player_ids.add(player_id)
                metric_updates[player_id]["correct_count"] = 1
                metric_updates[player_id]["wrong_count"] = 0

        await self.end_game.apply_player_metric_updates(lobby.id, metric_updates)

        await self.repo.set_step_cache(
            lobby.id,
            {
                "evaluated": True,
                "reviewed_player_ids": reviewed_player_ids,
            },
        )
        batch_id = uuid4().hex
        judged_events = [
            schemas.AnswerJudgedEvent(
                player_id=player_id,
                accepted=player_id in accepted_player_ids,
                source="auto_evaluation",
                input_kind=step.player_input.kind,
                batch_id=batch_id,
                batch_index=index,
                batch_size=len(reviewed_player_ids),
            )
            for index, player_id in enumerate(reviewed_player_ids)
        ]
        return judged_events + [schemas.ScoresUpdatedEvent(updates=updates)]

    async def evaluate_drawing_vote_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        step = await self.get_current_step(lobby)
        if step is None or step.evaluation.type_ != EvaluationType.FAVORITE_VOTE:
            return [schemas.ScoresUpdatedEvent()]
        state = await self.get_step_state(lobby.id)
        if state.get("evaluated"):
            return [schemas.ScoresUpdatedEvent()]

        answers = state.get("answers", {})
        votes = state.get("drawing_votes", {})
        if not isinstance(answers, dict) or not isinstance(votes, dict):
            return [schemas.ScoresUpdatedEvent()]

        points_per_vote = max(0, int(step.evaluation.points))
        vote_counts: dict[str, int] = {player_id: 0 for player_id in answers.keys()}
        for voter_id, target_player_id in votes.items():
            if (
                isinstance(voter_id, str)
                and isinstance(target_player_id, str)
                and voter_id != target_player_id
                and target_player_id in answers
            ):
                vote_counts[target_player_id] = vote_counts.get(target_player_id, 0) + 1

        updates: dict[str, int] = {}
        score_updates_by_player: dict[str, int] = {}
        metric_updates: dict[str, dict[str, Any]] = {}
        for player_id, vote_count in vote_counts.items():
            delta = vote_count * points_per_vote
            score_updates_by_player[player_id] = delta
            metric_updates[player_id] = {
                "answered_count": 1,
                "correct_count": 1 if delta > 0 else 0,
                "wrong_count": 0 if delta > 0 else 1,
            }
            if delta <= 0:
                continue
            new_score = await self.repo.get_player_score(lobby.id, player_id) + delta
            await self.repo.set_player_score(lobby.id, player_id, new_score)
            updates[player_id] = new_score

        await self.end_game.apply_player_metric_updates(lobby.id, metric_updates)
        await self.repo.set_step_cache(
            lobby.id,
            {
                "evaluated": True,
                "reviewed_player_ids": list(answers.keys()),
                "drawing_score_updates": score_updates_by_player,
            },
        )
        return [schemas.ScoresUpdatedEvent(updates=updates)]

    async def close_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return []
        step = await self.get_current_step(lobby)
        if step is None:
            return []
        if await self.evaluation.should_skip_answer_reveal(lobby, step):
            return await self.advance_step(lobby)
        phase = "step_complete"
        events: list[schemas.BaseEvent] = []
        evaluation_type = await self.evaluation.resolve_evaluation_type(lobby, step)
        state = await self.get_step_state(lobby.id)
        if (
            step.player_input.kind == PlayerInputKind.DRAWING
            and evaluation_type == EvaluationType.FAVORITE_VOTE
            and state.get("display_phase") != "drawing_vote"
        ):
            drawing_vote_order = await self._ensure_drawing_vote_order(lobby.id, state)
            if len(drawing_vote_order) >= 2:
                await self.repo.set_lobby_fields(lobby.id, phase="question_active")
                lobby.phase = "question_active"
                await self.repo.set_step_cache(
                    lobby.id,
                    {
                        "display_phase": "drawing_vote",
                        "buzzer_active": False,
                        "buzzed_player_id": "",
                        "timer_ends_at": None,
                        "timer_remaining_seconds": None,
                    },
                )
                return [await self.build_snapshot(lobby)]

        if evaluation_type in (
            EvaluationType.EXACT_TEXT,
            EvaluationType.EXACT_NUMBER,
            EvaluationType.CLOSEST_NUMBER,
            EvaluationType.ORDERING_MATCH,
            EvaluationType.MULTI_SELECT_WEIGHTED,
            EvaluationType.MAP_DISTANCE,
        ):
            for auto_event in await self.evaluate_auto_step(lobby):
                if isinstance(auto_event, schemas.ScoresUpdatedEvent) and not auto_event.updates:
                    continue
                events.append(auto_event)
        elif evaluation_type == EvaluationType.FAVORITE_VOTE:
            for score_event in await self.evaluate_drawing_vote_step(lobby):
                if isinstance(score_event, schemas.ScoresUpdatedEvent) and not score_event.updates:
                    continue
                events.append(score_event)
        elif step.player_input.kind == PlayerInputKind.BUZZER:
            phase = (
                "host_review"
                if self.snapshots.pending_review_count(await self.get_step_state(lobby.id))
                else "step_complete"
            )
        else:
            phase = (
                "host_review"
                if step.evaluation.type_ == EvaluationType.HOST_JUDGED
                and self.snapshots.pending_review_count(await self.get_step_state(lobby.id))
                else "step_complete"
            )
        await self.repo.set_lobby_fields(lobby.id, phase=phase)
        lobby.phase = phase
        if phase == "step_complete":
            if await self.evaluation.should_skip_answer_reveal(lobby, step):
                step_updates = {"display_phase": "question_active"}
            else:
                step_updates = {
                    "display_phase": "answer_reveal",
                    "scoreboard_visible": (
                        not lobby.host_enabled and await self.is_current_step_round_end(lobby)
                    ),
                } | self.timing.answer_reveal_updates(step)
            await self.repo.set_step_cache(lobby.id, step_updates)
        events.append(await self.build_snapshot(lobby))
        return events

    async def advance_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return await self.show_next_reveal(lobby)
        await self._archive_current_step_reveal(lobby)
        next_step = lobby.current_step + 1
        await self.repo.set_step_cache(
            lobby.id,
            {
                "review_step_index": "",
                "buzzer_active": False,
                "buzzed_player_id": "",
                "buzzer_opened_at": None,
                "buzz_reaction_seconds": None,
            },
        )
        await self.repo.set_lobby_fields(lobby.id, current_step=next_step)
        lobby.current_step = next_step
        step = await self.get_current_step(lobby)
        if step is None:
            await self.repo.set_lobby_fields(lobby.id, phase="finished")
            lobby.phase = "finished"
            await self.end_game.set_end_game_state(
                lobby.id,
                {
                    "revealed": not lobby.host_enabled,
                    "sequence_stage": END_GAME_SEQUENCE_STAGES[0],
                    "autoplay_enabled": not lobby.host_enabled,
                },
            )
            await self._archive_finished_game(lobby)
            await self.repo.apply_game_ttl(lobby.id, settings.GAME_FINISHED_TTL_SECONDS)
            return [
                schemas.StepAdvancedEvent(step_index=next_step),
                await self.build_snapshot(lobby),
            ]
        await self.repo.set_lobby_fields(lobby.id, phase="question_active")
        lobby.phase = "question_active"
        await self.initialize_step_state(lobby, step)
        return [schemas.StepAdvancedEvent(step_index=next_step), await self.build_snapshot(lobby)]

    async def reset_current_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        if self._review_step_index(await self.get_step_state(lobby.id)) is not None:
            return []
        step = await self.get_current_step(lobby)
        if step is None:
            return []
        await self.repo.set_lobby_fields(lobby.id, phase="question_active")
        lobby.phase = "question_active"
        await self.initialize_step_state(lobby, step)
        return [await self.build_snapshot(lobby)]

    async def reveal_end_game(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        return await self.end_game.reveal_end_game(lobby, self.build_snapshot)

    async def advance_end_game_stage(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        return await self.end_game.advance_end_game_stage(lobby, self.build_snapshot)

    async def toggle_end_game_autoplay(
        self, lobby: schemas.Lobby, enabled: bool
    ) -> list[schemas.BaseEvent]:
        return await self.end_game.toggle_end_game_autoplay(lobby, enabled, self.build_snapshot)

    async def record_player_reaction(
        self,
        lobby: schemas.Lobby,
        player_id: str,
        reaction: str,
    ):
        await self.end_game.record_player_reaction(lobby, player_id, reaction)

    async def build_snapshot(
        self,
        lobby: schemas.Lobby,
        *,
        revision: int | None = None,
    ) -> schemas.RuntimeSnapshotEvent:
        return await self.snapshots.build_snapshot(lobby, revision=revision)

    async def sync_lobby(self, lobby: schemas.Lobby) -> schemas.RuntimeSnapshotEvent:
        return await self.build_snapshot(lobby)

    async def build_submissions_event(
        self, lobby: schemas.Lobby
    ) -> schemas.SubmissionsUpdatedEvent:
        return await self.snapshots.build_submissions_event(lobby)

    async def _archive_finished_game(self, lobby: schemas.Lobby):
        if self.stats_archiver is None:
            return
        try:
            await self.stats_archiver.archive_finished_game(lobby)
        except Exception:
            log.exception("Failed to run stats archive hook for game %s", lobby.id)

    async def _ensure_drawing_vote_order(
        self,
        lobby_id: str,
        step_state: dict[str, Any] | None = None,
    ) -> list[str]:
        state = step_state if step_state is not None else await self.get_step_state(lobby_id)
        answers = state.get("answers", {})
        if not isinstance(answers, dict):
            answers = {}
        existing_order = [
            player_id
            for player_id in state.get("drawing_vote_order", [])
            if isinstance(player_id, str) and player_id in answers
        ]
        missing_player_ids = sorted(
            player_id for player_id in answers.keys() if player_id not in existing_order
        )
        order = existing_order + missing_player_ids
        await self.repo.set_step_cache(lobby_id, {"drawing_vote_order": order})
        return order

    def _drawing_player_id_for_vote_id(
        self,
        step_state: dict[str, Any],
        drawing_id: str,
    ) -> str | None:
        if not isinstance(drawing_id, str) or not drawing_id.startswith("drawing:"):
            return None
        try:
            index = int(drawing_id.split(":", 1)[1])
        except ValueError:
            return None
        order = step_state.get("drawing_vote_order", [])
        if not isinstance(order, list) or index < 0 or index >= len(order):
            return None
        player_id = order[index]
        return player_id if isinstance(player_id, str) else None

    async def _all_drawing_voters_submitted(
        self,
        lobby: schemas.Lobby,
        step_state: dict[str, Any],
    ) -> bool:
        answers = step_state.get("answers", {})
        if not isinstance(answers, dict) or len(answers) < 2:
            return True
        players = await self.repo.get_players(lobby.id)
        answer_player_ids = set(answers.keys())
        voter_ids = {
            player.id
            for player in players
            if player.id and player.id != lobby.host_id and player.id in answer_player_ids
        }
        submitted_voter_ids = set(step_state.get("drawing_votes", {}).keys())
        return voter_ids <= submitted_voter_ids
