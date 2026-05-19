from __future__ import annotations

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
from partygame.state import GameStateRepository

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
    ):
        self.repo = repo
        self.definition_provider = definition_provider or get_default_definition_provider()
        self.timing = TimingState()
        self.evaluation = EvaluationRuntime(repo, self.timing, get_step_state=self.get_step_state)
        self.end_game = EndGameRuntime(repo, self.timing)
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
                if lobby.host_enabled or self._is_hostless_compatible_step(lobby, step)
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

    async def get_current_round(self, lobby: schemas.Lobby) -> schemas.RuntimeRoundState | None:
        steps = await self._flatten_steps_with_metadata(lobby)
        if lobby.current_step >= len(steps):
            return None
        current = steps[lobby.current_step]
        return self._runtime_round_state(current)

    async def is_current_step_round_end(self, lobby: schemas.Lobby) -> bool:
        steps = await self._flatten_steps_with_metadata(lobby)
        if lobby.current_step >= len(steps):
            return False
        return steps[lobby.current_step].is_round_end

    async def start_game(self, lobby: schemas.Lobby) -> tuple[schemas.Lobby, StepDefinition | None]:
        await self._initialize_end_game_state(lobby.id, auto_reveal=not lobby.host_enabled)
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
                **self._initial_reveal_state(step, started_at),
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

    async def submit_player_input(
        self,
        lobby: schemas.Lobby,
        player_id: str,
        value: Any,
    ) -> tuple[list[schemas.BaseEvent], bool]:
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
                "buzz_reaction_seconds": self._buzzer_reaction_seconds(state),
            }
            if lobby.phase != "host_review":
                await self.repo.set_lobby_fields(lobby.id, phase="host_review")
                lobby.phase = "host_review"
            reveal_updates = self._pause_reveal_state(state)
            updates.update(reveal_updates)
            updates.update(self._pause_timer_state(state))
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
        if step.player_input.kind == PlayerInputKind.MAP and not self._is_valid_map_submission(
            step, value
        ):
            return [], False
        answers[player_id] = value
        await self.repo.set_step_cache(lobby.id, {"answers": answers})
        if await self._should_auto_close_on_all_submissions(
            lobby, step
        ) and await self._all_answerable_players_submitted(lobby, state | {"answers": answers}):
            return await self.close_step(lobby), True
        return [], True

    async def set_buzzer_state(self, lobby: schemas.Lobby, active: bool) -> list[schemas.BaseEvent]:
        step = await self.get_current_step(lobby)
        if step is None or step.player_input.kind != PlayerInputKind.BUZZER:
            return []
        state = await self.get_step_state(lobby.id)
        updates: dict[str, Any] = {"buzzer_active": active}
        if active:
            updates["buzzed_player_id"] = ""
            updates["buzzer_opened_at"] = time()
            updates["buzz_reaction_seconds"] = None
            updates.update(self._resume_reveal_state(state, step))
            updates.update(self._resume_timer_state(state))
            await self.repo.set_lobby_fields(lobby.id, phase="question_active")
            lobby.phase = "question_active"
        else:
            updates.update(self._pause_reveal_state(state))
            updates.update(self._pause_timer_state(state))
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
            and self._pending_review_count(state) == 0
            and await self._has_eligible_buzzer_players(lobby, state)
        ):
            return [await self.build_snapshot(lobby)]
        if await self._should_skip_answer_reveal(lobby, step):
            if lobby.phase == "question_active":
                return await self.close_step(lobby)
            return await self.advance_step(lobby)

        updates: dict[str, Any] = {}

        if lobby.phase == "question_active":
            events = await self.close_step(lobby)
            state = await self.get_step_state(lobby.id)
            if lobby.phase == "host_review":
                return events
            if state.get("display_phase") == "answer_reveal":
                return events

        if state.get("display_phase") == "answer_reveal":
            return [await self.build_snapshot(lobby)]

        updates["display_phase"] = "answer_reveal"
        updates.update(self._answer_reveal_updates(step))
        await self.repo.set_step_cache(lobby.id, updates)
        return [await self.build_snapshot(lobby)]

    async def show_question(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        step = await self.get_current_step(lobby)
        if step is None:
            return []

        await self.repo.set_step_cache(lobby.id, {"display_phase": "question_active"})
        return [await self.build_snapshot(lobby)]

    async def set_scoreboard_visibility(
        self,
        lobby: schemas.Lobby,
        visible: bool,
    ) -> list[schemas.BaseEvent]:
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
                await self._apply_player_metric_updates(
                    lobby.id,
                    {
                        event.player_id: {
                            "answered_count": 1,
                            "correct_count": 1,
                            "fastest_buzz_seconds": self._to_float(
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
                updates.update(self._reveal_answer_state(step))
                updates["display_phase"] = "answer_reveal"
                updates["buzzed_player_id"] = event.player_id
                await self.repo.set_step_cache(lobby.id, updates)
                await self.repo.set_lobby_fields(lobby.id, phase="step_complete")
                lobby.phase = "step_complete"
                events.append(score_event)
            else:
                await self._apply_player_metric_updates(
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

        await self._apply_player_metric_updates(
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

        if self._pending_review_count(state | {"reviewed_player_ids": reviewed_player_ids}) == 0:
            await self.repo.set_lobby_fields(lobby.id, phase="step_complete")
            lobby.phase = "step_complete"

        return events

    async def evaluate_auto_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
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
        evaluation_type = await self._resolve_evaluation_type(lobby, step)

        if evaluation_type == EvaluationType.EXACT_TEXT:
            accepted_answers = self._exact_text_answers(step)
            max_distance = (
                step.evaluation.max_distance
                if step.player_input.kind == PlayerInputKind.TEXT
                else 0
            )
            for player_id, value in answers.items():
                if self._matches_exact_text_answer(value, accepted_answers, max_distance):
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
                diffs.sort(key=lambda item: item[0])
                winner = diffs[0][1]
                new_score = (
                    await self.repo.get_player_score(lobby.id, winner) + step.evaluation.points
                )
                await self.repo.set_player_score(lobby.id, winner, new_score)
                updates[winner] = new_score
                accepted_player_ids.add(winner)
                metric_updates[winner]["correct_count"] = 1
                metric_updates[winner]["wrong_count"] = 0
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
                delta = self._score_map_distance_answer(step, value)
                if delta <= 0:
                    continue
                new_score = await self.repo.get_player_score(lobby.id, player_id) + delta
                await self.repo.set_player_score(lobby.id, player_id, new_score)
                updates[player_id] = new_score
                accepted_player_ids.add(player_id)
                metric_updates[player_id]["correct_count"] = 1
                metric_updates[player_id]["wrong_count"] = 0

        await self._apply_player_metric_updates(lobby.id, metric_updates)

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

    async def close_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        step = await self.get_current_step(lobby)
        if step is None:
            return []
        if await self._should_skip_answer_reveal(lobby, step):
            return await self.advance_step(lobby)
        phase = "step_complete"
        events: list[schemas.BaseEvent] = []
        evaluation_type = await self._resolve_evaluation_type(lobby, step)
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
        elif step.player_input.kind == PlayerInputKind.BUZZER:
            phase = (
                "host_review"
                if self._pending_review_count(await self.get_step_state(lobby.id))
                else "step_complete"
            )
        else:
            phase = (
                "host_review"
                if step.evaluation.type_ == EvaluationType.HOST_JUDGED
                and self._pending_review_count(await self.get_step_state(lobby.id))
                else "step_complete"
            )
        await self.repo.set_lobby_fields(lobby.id, phase=phase)
        lobby.phase = phase
        if phase == "step_complete":
            if await self._should_skip_answer_reveal(lobby, step):
                step_updates = {"display_phase": "question_active"}
            else:
                step_updates = {
                    "display_phase": "answer_reveal",
                    "scoreboard_visible": (
                        not lobby.host_enabled and await self.is_current_step_round_end(lobby)
                    ),
                } | self._answer_reveal_updates(step)
            await self.repo.set_step_cache(lobby.id, step_updates)
        events.append(await self.build_snapshot(lobby))
        return events

    async def advance_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        next_step = lobby.current_step + 1
        await self.repo.set_step_cache(
            lobby.id,
            {
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
            await self._set_end_game_state(
                lobby.id,
                {
                    "revealed": not lobby.host_enabled,
                    "sequence_stage": END_GAME_SEQUENCE_STAGES[0],
                    "autoplay_enabled": not lobby.host_enabled,
                },
            )
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

    def _runtime_round_state(self, step: FlattenedStep) -> schemas.RuntimeRoundState:
        return self.snapshots._runtime_round_state(step)

    def _pending_review_count(self, step_state: dict[str, Any]) -> int:
        return self.snapshots._pending_review_count(step_state)

    def _step_has_revealable_answer(self, step: StepDefinition) -> bool:
        return self.snapshots._step_has_revealable_answer(step)

    async def _has_eligible_buzzer_players(
        self,
        lobby: schemas.Lobby,
        step_state: dict[str, Any],
        players: list[schemas.Player] | None = None,
    ) -> bool:
        return await self.snapshots._has_eligible_buzzer_players(lobby, step_state, players)

    async def _initialize_end_game_state(self, lobby_id: str, *, auto_reveal: bool):
        await self.end_game._initialize_end_game_state(lobby_id, auto_reveal=auto_reveal)

    async def _set_end_game_state(self, lobby_id: str, updates: dict[str, Any]):
        await self.end_game._set_end_game_state(lobby_id, updates)

    async def _apply_player_metric_updates(
        self,
        lobby_id: str,
        updates: dict[str, dict[str, Any]],
    ):
        await self.end_game._apply_player_metric_updates(lobby_id, updates)

    def _to_float(self, value: Any) -> float | None:
        return self.timing._to_float(value)

    def _buzzer_reaction_seconds(self, step_state: dict[str, Any]) -> float | None:
        return self.timing._buzzer_reaction_seconds(step_state)

    def _pause_reveal_state(self, step_state: dict[str, Any]) -> dict[str, Any]:
        return self.timing._pause_reveal_state(step_state)

    def _pause_timer_state(self, step_state: dict[str, Any]) -> dict[str, Any]:
        return self.timing._pause_timer_state(step_state)

    def _resume_reveal_state(
        self, step_state: dict[str, Any], step: StepDefinition
    ) -> dict[str, Any]:
        return self.timing._resume_reveal_state(step_state, step)

    def _resume_timer_state(self, step_state: dict[str, Any]) -> dict[str, Any]:
        return self.timing._resume_timer_state(step_state)

    def _answer_reveal_updates(self, step: StepDefinition) -> dict[str, Any]:
        return self.timing._answer_reveal_updates(step)

    def _initial_reveal_state(self, step: StepDefinition, started_at: float) -> dict[str, Any]:
        return self.timing._initial_reveal_state(step, started_at)

    def _reveal_answer_state(self, step: StepDefinition) -> dict[str, Any]:
        return self.timing._reveal_answer_state(step)

    def _is_valid_map_submission(self, step: StepDefinition, value: Any) -> bool:
        return self.evaluation._is_valid_map_submission(step, value)

    def _score_map_distance_answer(self, step: StepDefinition, value: Any) -> int:
        return self.evaluation._score_map_distance_answer(step, value)

    async def _resolve_evaluation_type(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> EvaluationType:
        return await self.evaluation._resolve_evaluation_type(lobby, step)

    async def _all_answerable_players_submitted(
        self,
        lobby: schemas.Lobby,
        step_state: dict[str, Any] | None = None,
    ) -> bool:
        return await self.evaluation._all_answerable_players_submitted(lobby, step_state)

    def _is_hostless_auto_progress_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return self.evaluation._is_hostless_auto_progress_step(lobby, step)

    async def _should_auto_close_on_all_submissions(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return await self.evaluation._should_auto_close_on_all_submissions(lobby, step)

    def _is_hostless_compatible_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return self.evaluation._is_hostless_compatible_step(lobby, step)

    async def _should_skip_answer_reveal(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return await self.evaluation._should_skip_answer_reveal(lobby, step)

    def _exact_text_answers(self, step: StepDefinition) -> list[str]:
        return self.evaluation._exact_text_answers(step)

    def _matches_exact_text_answer(
        self,
        value: Any,
        accepted_answers: list[str],
        max_distance: int,
    ) -> bool:
        return self.evaluation._matches_exact_text_answer(value, accepted_answers, max_distance)
