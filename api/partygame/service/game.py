from __future__ import annotations

from time import time
from typing import Any

from partygame import schemas
from partygame.core.config import settings
from partygame.schemas.game_definition import (
    EvaluationType,
    ImageRevealMode,
    MediaDefinition,
    MediaType,
    PlayerInputDefinition,
    PlayerInputKind,
    StepDefinition,
)
from partygame.service.definitions import DefinitionProvider, FileDefinitionProvider
from partygame.state import GameStateRepository


class GameRuntimeService:
    def __init__(
        self,
        repo: GameStateRepository,
        definition_provider: DefinitionProvider | None = None,
    ):
        self.repo = repo
        self.definition_provider = definition_provider or FileDefinitionProvider()

    async def _flatten_steps(self, lobby: schemas.Lobby) -> list[StepDefinition]:
        definition_id = lobby.definition_id or "quiz_demo"
        definition = await self.definition_provider.load(definition_id)
        steps: list[StepDefinition] = []
        for round_definition in definition.rounds:
            for step in round_definition.steps:
                if not lobby.host_enabled and step.player_input.kind == PlayerInputKind.BUZZER:
                    continue
                steps.append(step)
        return steps

    async def get_current_step(self, lobby: schemas.Lobby) -> StepDefinition | None:
        steps = await self._flatten_steps(lobby)
        if lobby.current_step >= len(steps):
            return None
        return steps[lobby.current_step]

    async def start_game(self, lobby: schemas.Lobby) -> tuple[schemas.Lobby, StepDefinition | None]:
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
                "answers": {},
                "evaluated": False,
                "buzzer_active": lobby.host_enabled
                and step.player_input.kind == PlayerInputKind.BUZZER,
                "buzzed_player_id": "",
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
        answers[player_id] = value
        await self.repo.set_step_cache(lobby.id, {"answers": answers})
        return [], True

    async def set_buzzer_state(self, lobby: schemas.Lobby, active: bool) -> list[schemas.BaseEvent]:
        step = await self.get_current_step(lobby)
        if step is None or step.player_input.kind != PlayerInputKind.BUZZER:
            return []
        state = await self.get_step_state(lobby.id)
        updates: dict[str, Any] = {"buzzer_active": active}
        if active:
            updates["buzzed_player_id"] = ""
            updates.update(self._resume_reveal_state(state, step))
            updates.update(self._resume_timer_state(state))
            await self.repo.set_lobby_fields(lobby.id, phase="question_active")
            lobby.phase = "question_active"
        elif lobby.phase == "question_active":
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

        if step.player_input.kind == PlayerInputKind.BUZZER:
            updates: dict[str, Any] = {"reviewed_player_ids": reviewed_player_ids}
            disabled_player_ids = list(state.get("disabled_buzzer_player_ids", []))
            if event.accepted:
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
                updates["buzzed_player_id"] = event.player_id
                await self.repo.set_step_cache(lobby.id, updates)
                await self.repo.set_lobby_fields(lobby.id, phase="step_complete")
                lobby.phase = "step_complete"
                events.append(score_event)
            else:
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

        await self.repo.set_step_cache(lobby.id, {"reviewed_player_ids": reviewed_player_ids})

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

    async def evaluate_auto_step(self, lobby: schemas.Lobby) -> schemas.ScoresUpdatedEvent:
        step = await self.get_current_step(lobby)
        if step is None:
            return schemas.ScoresUpdatedEvent()
        state = await self.get_step_state(lobby.id)
        if state.get("evaluated"):
            return schemas.ScoresUpdatedEvent()

        answers = state.get("answers", {})
        reviewed_player_ids = list(answers.keys())
        updates: dict[str, int] = {}
        evaluation_type = self._resolve_evaluation_type(lobby, step)

        if evaluation_type == EvaluationType.EXACT_TEXT:
            expected = str(step.evaluation.answer or "").strip().casefold()
            for player_id, value in answers.items():
                if str(value).strip().casefold() == expected:
                    new_score = (
                        await self.repo.get_player_score(lobby.id, player_id)
                        + step.evaluation.points
                    )
                    await self.repo.set_player_score(lobby.id, player_id, new_score)
                    updates[player_id] = new_score
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
                    if delta == 0:
                        continue
                    new_score = await self.repo.get_player_score(lobby.id, player_id) + delta
                    await self.repo.set_player_score(lobby.id, player_id, new_score)
                    updates[player_id] = new_score

        await self.repo.set_step_cache(
            lobby.id,
            {
                "evaluated": True,
                "reviewed_player_ids": reviewed_player_ids,
            },
        )
        return schemas.ScoresUpdatedEvent(updates=updates)

    async def close_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        step = await self.get_current_step(lobby)
        if step is None:
            return []
        phase = "step_complete"
        events: list[schemas.BaseEvent] = []
        evaluation_type = self._resolve_evaluation_type(lobby, step)
        if evaluation_type in (
            EvaluationType.EXACT_TEXT,
            EvaluationType.EXACT_NUMBER,
            EvaluationType.CLOSEST_NUMBER,
            EvaluationType.ORDERING_MATCH,
            EvaluationType.MULTI_SELECT_WEIGHTED,
        ):
            scores_event = await self.evaluate_auto_step(lobby)
            if scores_event.updates:
                events.append(scores_event)
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
            await self.repo.set_step_cache(
                lobby.id,
                {"display_phase": "answer_reveal"} | self._answer_reveal_updates(step),
            )
        events.append(await self.build_snapshot(lobby))
        return events

    async def advance_step(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        next_step = lobby.current_step + 1
        await self.repo.set_lobby_fields(lobby.id, current_step=next_step)
        lobby.current_step = next_step
        step = await self.get_current_step(lobby)
        if step is None:
            await self.repo.set_lobby_fields(lobby.id, phase="finished")
            lobby.phase = "finished"
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

    async def build_snapshot(
        self,
        lobby: schemas.Lobby,
        *,
        revision: int | None = None,
    ) -> schemas.RuntimeSnapshotEvent:
        step = await self.get_current_step(lobby)
        step_state = await self.get_step_state(lobby.id)
        players = await self.repo.get_players(lobby.id)
        snapshot_revision = (
            revision if revision is not None else await self.repo.get_state_revision(lobby.id)
        )

        active_step = None
        if step is not None:
            active_step = schemas.RuntimeStepState(
                id=step.id,
                title=step.title,
                body=step.body,
                evaluation_type=str(self._resolve_evaluation_type(lobby, step)),
                evaluation_points=step.evaluation.points,
                input_enabled=lobby.phase == "question_active",
                input_kind=step.player_input.kind,
                input_prompt=step.player_input.prompt,
                input_placeholder=step.player_input.placeholder,
                input_options=step.player_input.options,
                slider_min=step.player_input.min_value,
                slider_max=step.player_input.max_value,
                slider_step=step.player_input.step,
                media=self._serialize_media(step.media, step_state),
                timer=schemas.RuntimeTimerState(
                    seconds=step.timer.seconds,
                    enforced=step.timer.enforced,
                    started_at=self._to_float(step_state.get("timer_started_at")),
                    ends_at=self._to_float(step_state.get("timer_ends_at")),
                    remaining_seconds=self._remaining_timer_seconds(step_state),
                ),
            )

        revealed_submission = None
        player_id = step_state.get("revealed_submission_player_id")
        if player_id:
            revealed_submission = schemas.RevealedSubmission(
                player_id=player_id,
                value=step_state.get("revealed_submission_value"),
            )

        revealed_answer = None
        if step_state.get("revealed_answer_value") not in (None, ""):
            revealed_answer = schemas.RevealedAnswer(value=step_state.get("revealed_answer_value"))

        host_answer = None
        if step is not None and self._step_has_revealable_answer(step):
            host_answer = schemas.RevealedAnswer(value=step.evaluation.answer)

        submissions = await self.build_submissions_event(lobby)

        return schemas.RuntimeSnapshotEvent(
            revision=snapshot_revision,
            lobby=schemas.RuntimeLobbyState(
                id=lobby.id,
                join_code=lobby.join_code,
                definition_id=lobby.definition_id,
                host_enabled=lobby.host_enabled,
                host_id=lobby.host_id,
                state=lobby.state,
                phase=lobby.phase,
                current_step=lobby.current_step,
            ),
            players=players,
            active_step=active_step,
            display_phase=str(step_state.get("display_phase") or "question_active"),
            scoreboard_visible=bool(step_state.get("scoreboard_visible")),
            buzzer_active=bool(step_state.get("buzzer_active")),
            buzzed_player_id=step_state.get("buzzed_player_id") or None,
            disabled_buzzer_player_ids=list(step_state.get("disabled_buzzer_player_ids", [])),
            submitted_player_ids=list(step_state.get("answers", {}).keys()),
            submission_count=len(step_state.get("answers", {})),
            pending_review_count=self._pending_review_count(step_state),
            revealed_submission=revealed_submission,
            revealed_answer=revealed_answer,
            host_answer=host_answer,
            submissions=submissions.items,
        )

    async def build_submissions_event(
        self, lobby: schemas.Lobby
    ) -> schemas.SubmissionsUpdatedEvent:
        state = await self.get_step_state(lobby.id)
        items = [
            schemas.SubmissionItem(
                player_id=player_id,
                value=value,
                reviewed=player_id in set(state.get("reviewed_player_ids", [])),
            )
            for player_id, value in state.get("answers", {}).items()
        ]
        return schemas.SubmissionsUpdatedEvent(items=items)

    async def sync_lobby(self, lobby: schemas.Lobby) -> schemas.RuntimeSnapshotEvent:
        return await self.build_snapshot(lobby)

    def _serialize_media(
        self,
        media: MediaDefinition | None,
        step_state: dict[str, Any],
    ) -> schemas.RuntimeMediaState | None:
        if media is None:
            return None
        return schemas.RuntimeMediaState(
            type_=str(media.type_),
            src=media.src,
            reveal=str(media.reveal),
            loop=media.loop,
            reveal_state=str(step_state.get("media_reveal_state") or "idle"),
            reveal_started_at=self._to_float(step_state.get("media_reveal_started_at")),
            reveal_elapsed_seconds=self._to_float(step_state.get("media_reveal_elapsed_seconds"))
            or 0.0,
            reveal_duration_seconds=self._to_float(step_state.get("media_reveal_duration_seconds")),
        )

    def _to_float(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        return float(value)

    def _remaining_timer_seconds(self, step_state: dict[str, Any]) -> float | None:
        ends_at = self._to_float(step_state.get("timer_ends_at"))
        if ends_at is not None:
            return max(0.0, ends_at - time())
        return self._to_float(step_state.get("timer_remaining_seconds"))

    def _resolve_evaluation_type(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> EvaluationType:
        evaluation_type = step.evaluation.type_
        if evaluation_type != EvaluationType.HOST_JUDGED or lobby.host_enabled:
            return evaluation_type
        return self._fallback_evaluation_type(step.player_input)

    def _fallback_evaluation_type(
        self,
        player_input: PlayerInputDefinition,
    ) -> EvaluationType:
        if player_input.kind == PlayerInputKind.TEXT:
            return EvaluationType.EXACT_TEXT
        if player_input.kind == PlayerInputKind.RADIO:
            return EvaluationType.EXACT_TEXT
        if player_input.kind == PlayerInputKind.NUMBER:
            return EvaluationType.EXACT_NUMBER
        if player_input.kind == PlayerInputKind.ORDERING:
            return EvaluationType.ORDERING_MATCH
        if player_input.kind == PlayerInputKind.CHECKBOX:
            return EvaluationType.NONE
        return EvaluationType.NONE

    def _pending_review_count(self, step_state: dict[str, Any]) -> int:
        reviewed = set(step_state.get("reviewed_player_ids", []))
        review_targets = set(step_state.get("answers", {}).keys())
        buzzed_player_id = step_state.get("buzzed_player_id") or ""
        if buzzed_player_id:
            review_targets.add(buzzed_player_id)
        return len([player_id for player_id in review_targets if player_id not in reviewed])

    def _answer_reveal_updates(self, step: StepDefinition) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if self._step_has_revealable_answer(step):
            updates["revealed_answer_value"] = step.evaluation.answer
        if self._uses_timed_image_reveal(step):
            duration = float(step.timer.seconds or 14)
            updates.update(
                {
                    "media_reveal_state": "revealed",
                    "media_reveal_started_at": None,
                    "media_reveal_elapsed_seconds": duration,
                    "media_reveal_duration_seconds": duration,
                }
            )
        return updates

    def _initial_reveal_state(self, step: StepDefinition, started_at: float) -> dict[str, Any]:
        if not self._uses_timed_image_reveal(step):
            return {
                "media_reveal_state": "idle",
                "media_reveal_started_at": None,
                "media_reveal_elapsed_seconds": 0.0,
                "media_reveal_duration_seconds": None,
            }
        duration = float(step.timer.seconds or 14)
        return {
            "media_reveal_state": "running",
            "media_reveal_started_at": started_at,
            "media_reveal_elapsed_seconds": 0.0,
            "media_reveal_duration_seconds": duration,
        }

    def _pause_reveal_state(self, step_state: dict[str, Any]) -> dict[str, Any]:
        if step_state.get("media_reveal_state") != "running":
            return {}
        started_at = self._to_float(step_state.get("media_reveal_started_at"))
        elapsed = self._to_float(step_state.get("media_reveal_elapsed_seconds")) or 0.0
        duration = self._to_float(step_state.get("media_reveal_duration_seconds"))
        if started_at is not None:
            elapsed += max(0.0, time() - started_at)
        if duration is not None:
            elapsed = min(elapsed, duration)
        return {
            "media_reveal_state": "paused",
            "media_reveal_started_at": None,
            "media_reveal_elapsed_seconds": elapsed,
        }

    def _pause_timer_state(self, step_state: dict[str, Any]) -> dict[str, Any]:
        remaining = self._remaining_timer_seconds(step_state)
        if remaining is None:
            return {}
        return {
            "timer_started_at": None,
            "timer_ends_at": None,
            "timer_remaining_seconds": remaining,
        }

    def _resume_reveal_state(
        self, step_state: dict[str, Any], step: StepDefinition
    ) -> dict[str, Any]:
        if not self._uses_timed_image_reveal(step):
            return {}
        reveal_state = step_state.get("media_reveal_state")
        if reveal_state == "revealed":
            return {}
        duration = self._to_float(step_state.get("media_reveal_duration_seconds"))
        elapsed = self._to_float(step_state.get("media_reveal_elapsed_seconds")) or 0.0
        if duration is not None and elapsed >= duration:
            return {
                "media_reveal_state": "revealed",
                "media_reveal_started_at": None,
                "media_reveal_elapsed_seconds": duration,
            }
        return {
            "media_reveal_state": "running",
            "media_reveal_started_at": time(),
            "media_reveal_elapsed_seconds": elapsed,
        }

    def _resume_timer_state(self, step_state: dict[str, Any]) -> dict[str, Any]:
        remaining = self._to_float(step_state.get("timer_remaining_seconds"))
        if remaining is None:
            return {}
        started_at = time()
        return {
            "timer_started_at": started_at,
            "timer_ends_at": started_at + max(remaining, 0.0),
            "timer_remaining_seconds": max(remaining, 0.0),
        }

    def _reveal_answer_state(self, step: StepDefinition) -> dict[str, Any]:
        return self._answer_reveal_updates(step)

    def _step_has_revealable_answer(self, step: StepDefinition) -> bool:
        answer = step.evaluation.answer
        if answer is None:
            return False
        if isinstance(answer, str):
            return bool(answer.strip())
        if isinstance(answer, list):
            return len(answer) > 0
        if isinstance(answer, dict):
            return len(answer) > 0
        return True

    def _uses_timed_image_reveal(self, step: StepDefinition) -> bool:
        return bool(
            step.media is not None
            and step.media.type_ == MediaType.IMAGE
            and step.media.reveal
            in (
                ImageRevealMode.BLUR_TO_CLEAR,
                ImageRevealMode.BLUR_CIRCLE,
                ImageRevealMode.ZOOM_OUT,
            )
        )
