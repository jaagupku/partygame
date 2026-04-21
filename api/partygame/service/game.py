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

END_GAME_COMPONENT_ID = "end_game"
PLAYER_METRICS_COMPONENT_ID = "player_metrics"
END_GAME_SEQUENCE_STAGES = (
    "third_place",
    "second_place",
    "first_place",
    "stats",
    "scoreboard",
)
HOSTLESS_AUTO_EVALUATION_TYPES = {
    EvaluationType.EXACT_TEXT,
    EvaluationType.EXACT_NUMBER,
    EvaluationType.CLOSEST_NUMBER,
    EvaluationType.ORDERING_MATCH,
    EvaluationType.MULTI_SELECT_WEIGHTED,
}


class GameRuntimeService:
    def __init__(
        self,
        repo: GameStateRepository,
        definition_provider: DefinitionProvider | None = None,
    ):
        self.repo = repo
        self.definition_provider = definition_provider or FileDefinitionProvider()

    async def _flatten_steps_with_metadata(
        self,
        lobby: schemas.Lobby,
    ) -> list[tuple[StepDefinition, bool]]:
        definition_id = lobby.definition_id or "quiz_demo"
        definition = await self.definition_provider.load(definition_id)
        steps: list[tuple[StepDefinition, bool]] = []
        for round_definition in definition.rounds:
            compatible_steps = [
                step
                for step in round_definition.steps
                if lobby.host_enabled or self._is_hostless_compatible_step(lobby, step)
            ]
            for index, step in enumerate(compatible_steps):
                steps.append((step, index == len(compatible_steps) - 1))
        return steps

    async def _flatten_steps(self, lobby: schemas.Lobby) -> list[StepDefinition]:
        return [step for step, _is_round_end in await self._flatten_steps_with_metadata(lobby)]

    async def get_current_step(self, lobby: schemas.Lobby) -> StepDefinition | None:
        steps = await self._flatten_steps_with_metadata(lobby)
        if lobby.current_step >= len(steps):
            return None
        return steps[lobby.current_step][0]

    async def is_current_step_round_end(self, lobby: schemas.Lobby) -> bool:
        steps = await self._flatten_steps_with_metadata(lobby)
        if lobby.current_step >= len(steps):
            return False
        return steps[lobby.current_step][1]

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
        if await self._should_skip_answer_reveal(lobby, step):
            if lobby.phase == "question_active":
                return await self.close_step(lobby)
            return await self.advance_step(lobby)

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

    async def reveal_end_game(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        if lobby.phase != "finished":
            return []
        await self._set_end_game_state(
            lobby.id,
            {
                "revealed": True,
                "sequence_stage": END_GAME_SEQUENCE_STAGES[0],
            },
        )
        return [await self.build_snapshot(lobby)]

    async def advance_end_game_stage(self, lobby: schemas.Lobby) -> list[schemas.BaseEvent]:
        if lobby.phase != "finished":
            return []
        end_game_state = await self._get_end_game_state(lobby.id)
        if not end_game_state.get("revealed"):
            return []
        stage = str(end_game_state.get("sequence_stage") or END_GAME_SEQUENCE_STAGES[0])
        try:
            next_index = min(
                END_GAME_SEQUENCE_STAGES.index(stage) + 1,
                len(END_GAME_SEQUENCE_STAGES) - 1,
            )
        except ValueError:
            next_index = 0
        await self._set_end_game_state(
            lobby.id,
            {"sequence_stage": END_GAME_SEQUENCE_STAGES[next_index]},
        )
        return [await self.build_snapshot(lobby)]

    async def toggle_end_game_autoplay(
        self, lobby: schemas.Lobby, enabled: bool
    ) -> list[schemas.BaseEvent]:
        if lobby.phase != "finished":
            return []
        await self._set_end_game_state(lobby.id, {"autoplay_enabled": enabled})
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
        metric_updates = {
            player_id: {"answered_count": 1, "correct_count": 0, "wrong_count": 1}
            for player_id in answers
        }
        evaluation_type = await self._resolve_evaluation_type(lobby, step)

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
                    metric_updates[player_id]["correct_count"] = 1
                    metric_updates[player_id]["wrong_count"] = 0
        elif evaluation_type == EvaluationType.EXACT_NUMBER:
            try:
                expected = float(step.evaluation.answer)
            except (TypeError, ValueError):
                expected = None
            if expected is not None:
                for player_id, value in answers.items():
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError):
                        continue
                    if numeric == expected:
                        new_score = (
                            await self.repo.get_player_score(lobby.id, player_id)
                            + step.evaluation.points
                        )
                        await self.repo.set_player_score(lobby.id, player_id, new_score)
                        updates[player_id] = new_score
                        metric_updates[player_id]["correct_count"] = 1
                        metric_updates[player_id]["wrong_count"] = 0
        elif evaluation_type == EvaluationType.CLOSEST_NUMBER:
            try:
                target = float(step.evaluation.answer)
            except (TypeError, ValueError):
                target = None
            diffs: list[tuple[float, str]] = []
            if target is not None:
                for player_id, value in answers.items():
                    try:
                        diffs.append((abs(float(value) - target), player_id))
                    except (TypeError, ValueError):
                        continue
            if diffs:
                diffs.sort(key=lambda item: item[0])
                winner = diffs[0][1]
                new_score = (
                    await self.repo.get_player_score(lobby.id, winner) + step.evaluation.points
                )
                await self.repo.set_player_score(lobby.id, winner, new_score)
                updates[winner] = new_score
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
        return schemas.ScoresUpdatedEvent(updates=updates)

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
            evaluation_type = await self._resolve_evaluation_type(lobby, step)
            active_step = schemas.RuntimeStepState(
                id=step.id,
                title=step.title,
                body=step.body,
                evaluation_type=str(evaluation_type),
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
                    enforced=await self._is_timer_effectively_enforced(lobby, step),
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
        end_game = await self._build_end_game_state(lobby, players)

        return schemas.RuntimeSnapshotEvent(
            revision=snapshot_revision,
            lobby=schemas.RuntimeLobbyState(
                id=lobby.id,
                join_code=lobby.join_code,
                definition_id=lobby.definition_id,
                host_enabled=lobby.host_enabled,
                starter_id=lobby.starter_id,
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
            end_game=end_game,
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

    async def _initialize_end_game_state(self, lobby_id: str, *, auto_reveal: bool):
        await self.repo.set_component_state(
            lobby_id,
            END_GAME_COMPONENT_ID,
            {
                "state": {
                    "revealed": auto_reveal,
                    "sequence_stage": END_GAME_SEQUENCE_STAGES[0],
                    "autoplay_enabled": auto_reveal,
                }
            },
        )
        await self.repo.set_component_state(
            lobby_id,
            PLAYER_METRICS_COMPONENT_ID,
            {"metrics": {}},
        )

    async def _get_end_game_state(self, lobby_id: str) -> dict[str, Any]:
        state = await self.repo.get_component_state(lobby_id, END_GAME_COMPONENT_ID)
        payload = state.get("state")
        if isinstance(payload, dict):
            return payload
        return {
            "revealed": False,
            "sequence_stage": END_GAME_SEQUENCE_STAGES[0],
            "autoplay_enabled": False,
        }

    async def _set_end_game_state(self, lobby_id: str, updates: dict[str, Any]):
        current = await self._get_end_game_state(lobby_id)
        current.update(updates)
        await self.repo.set_component_state(
            lobby_id,
            END_GAME_COMPONENT_ID,
            {"state": current},
        )

    async def _get_player_metrics(self, lobby_id: str) -> dict[str, dict[str, Any]]:
        state = await self.repo.get_component_state(lobby_id, PLAYER_METRICS_COMPONENT_ID)
        metrics = state.get("metrics")
        if isinstance(metrics, dict):
            return metrics
        return {}

    async def _apply_player_metric_updates(
        self,
        lobby_id: str,
        updates: dict[str, dict[str, Any]],
    ):
        if not updates:
            return
        metrics = await self._get_player_metrics(lobby_id)
        for player_id, changes in updates.items():
            current = metrics.setdefault(
                player_id,
                {
                    "answered_count": 0,
                    "correct_count": 0,
                    "wrong_count": 0,
                    "fastest_buzz_seconds": None,
                },
            )
            current["answered_count"] += int(changes.get("answered_count", 0))
            current["correct_count"] += int(changes.get("correct_count", 0))
            current["wrong_count"] += int(changes.get("wrong_count", 0))
            next_fastest = self._to_float(changes.get("fastest_buzz_seconds"))
            current_fastest = self._to_float(current.get("fastest_buzz_seconds"))
            if next_fastest is not None and (
                current_fastest is None or next_fastest < current_fastest
            ):
                current["fastest_buzz_seconds"] = next_fastest
        await self.repo.set_component_state(
            lobby_id,
            PLAYER_METRICS_COMPONENT_ID,
            {"metrics": metrics},
        )

    async def _build_end_game_state(
        self,
        lobby: schemas.Lobby,
        players: list[schemas.Player],
    ) -> schemas.EndGameState | None:
        if lobby.phase != "finished":
            return None

        end_game_state = await self._get_end_game_state(lobby.id)
        metrics = await self._get_player_metrics(lobby.id)
        standings = self._build_final_standings(players, lobby.host_id)
        stats_cards = self._build_end_game_stats(standings, metrics)
        return schemas.EndGameState(
            revealed=bool(end_game_state.get("revealed")),
            sequence_stage=str(end_game_state.get("sequence_stage") or END_GAME_SEQUENCE_STAGES[0]),
            autoplay_enabled=bool(end_game_state.get("autoplay_enabled")),
            final_standings=standings,
            podium=standings[:3],
            stats_cards=stats_cards,
        )

    def _build_final_standings(
        self,
        players: list[schemas.Player],
        host_id: str | None,
    ) -> list[schemas.FinalStandingEntry]:
        ranked_players = [player for player in players if player.id != host_id]
        ranked_players.sort(key=lambda player: (-player.score, player.name.casefold(), player.id))
        standings: list[schemas.FinalStandingEntry] = []
        last_score: int | None = None
        last_place = 0
        for index, player in enumerate(ranked_players, start=1):
            if player.score != last_score:
                last_place = index
                last_score = player.score
            standings.append(
                schemas.FinalStandingEntry(
                    player_id=player.id,
                    name=player.name,
                    score=player.score,
                    place=last_place,
                    avatar_kind=player.avatar_kind,
                    avatar_preset_key=player.avatar_preset_key,
                    avatar_url=player.avatar_url,
                )
            )
        return standings

    def _build_end_game_stats(
        self,
        standings: list[schemas.FinalStandingEntry],
        metrics: dict[str, dict[str, Any]],
    ) -> list[schemas.EndGameStatCard]:
        eligible_ids = {entry.player_id for entry in standings}
        filtered_metrics = {
            player_id: data for player_id, data in metrics.items() if player_id in eligible_ids
        }
        stats: list[schemas.EndGameStatCard] = []

        def add_stat(
            *,
            stat_id: str,
            label: str,
            description: str,
            values: dict[str, float | int],
            unit: str | None = None,
            higher_is_better: bool = True,
            require_positive: bool = True,
        ):
            if not values:
                return
            filtered_values = {
                player_id: value
                for player_id, value in values.items()
                if not require_positive or value > 0
            }
            if not filtered_values:
                return
            best_value = (
                max(filtered_values.values()) if higher_is_better else min(filtered_values.values())
            )
            winners = sorted(
                [player_id for player_id, value in filtered_values.items() if value == best_value]
            )
            stats.append(
                schemas.EndGameStatCard(
                    id=stat_id,
                    label=label,
                    winner_player_ids=winners,
                    value=round(best_value, 3) if isinstance(best_value, float) else best_value,
                    unit=unit,
                    description=description,
                )
            )

        add_stat(
            stat_id="most_correct",
            label="Most Correct Answers",
            description="Players with the most correct answers across the game.",
            values={
                player_id: int(data.get("correct_count", 0))
                for player_id, data in filtered_metrics.items()
            },
        )
        add_stat(
            stat_id="most_wrong",
            label="Most Wrong Answers",
            description="Players who collected the most incorrect reviewed or auto-judged answers.",
            values={
                player_id: int(data.get("wrong_count", 0))
                for player_id, data in filtered_metrics.items()
            },
        )
        add_stat(
            stat_id="fastest_buzz",
            label="Fastest Buzz",
            description="Quickest accepted buzzer reaction time.",
            values={
                player_id: float(data["fastest_buzz_seconds"])
                for player_id, data in filtered_metrics.items()
                if self._to_float(data.get("fastest_buzz_seconds")) is not None
            },
            unit="seconds",
            higher_is_better=False,
        )
        add_stat(
            stat_id="highest_accuracy",
            label="Highest Accuracy",
            description="Best correct-answer rate among players who answered at least once.",
            values={
                player_id: round(
                    int(data.get("correct_count", 0)) / int(data.get("answered_count", 0)) * 100,
                    2,
                )
                for player_id, data in filtered_metrics.items()
                if int(data.get("answered_count", 0)) > 0
            },
            unit="percent",
        )
        return stats

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
            zoom_start=media.zoom_start,
            zoom_origin_x=media.zoom_origin_x,
            zoom_origin_y=media.zoom_origin_y,
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

    def _buzzer_reaction_seconds(self, step_state: dict[str, Any]) -> float | None:
        opened_at = self._to_float(step_state.get("buzzer_opened_at"))
        if opened_at is None:
            return None
        return max(0.0, time() - opened_at)

    async def _has_active_host_player(self, lobby: schemas.Lobby) -> bool:
        if not lobby.host_enabled:
            return False
        if not lobby.host_id:
            return True
        players = await self.repo.get_players(lobby.id)
        return any(
            player.id == lobby.host_id and player.status == schemas.ConnectionStatus.CONNECTED
            for player in players
        )

    async def _resolve_evaluation_type(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> EvaluationType:
        evaluation_type = step.evaluation.type_
        if evaluation_type != EvaluationType.HOST_JUDGED or await self._has_active_host_player(lobby):
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

    async def _all_answerable_players_submitted(
        self,
        lobby: schemas.Lobby,
        step_state: dict[str, Any] | None = None,
    ) -> bool:
        players = await self.repo.get_players(lobby.id)
        answerable_player_ids = {
            player.id for player in players if player.id and player.id != lobby.host_id
        }
        state = step_state or await self.get_step_state(lobby.id)
        submitted_player_ids = set(state.get("answers", {}).keys())
        return answerable_player_ids <= submitted_player_ids

    def _is_information_slide(self, step: StepDefinition) -> bool:
        return (
            step.player_input.kind == PlayerInputKind.NONE
            and step.evaluation.type_ == EvaluationType.NONE
        )

    def _has_usable_answer_for_evaluation(
        self,
        step: StepDefinition,
        evaluation_type: EvaluationType,
    ) -> bool:
        answer = step.evaluation.answer
        if evaluation_type in (EvaluationType.EXACT_TEXT,):
            return isinstance(answer, str) and bool(answer.strip())
        if evaluation_type in (EvaluationType.EXACT_NUMBER, EvaluationType.CLOSEST_NUMBER):
            try:
                return answer is not None and float(answer) == float(answer)
            except (TypeError, ValueError):
                return False
        if evaluation_type == EvaluationType.ORDERING_MATCH:
            return isinstance(answer, list) and any(str(value).strip() for value in answer)
        if evaluation_type == EvaluationType.MULTI_SELECT_WEIGHTED:
            option_scores = answer.get("option_scores") if isinstance(answer, dict) else None
            return isinstance(option_scores, list) and len(option_scores) > 0
        return False

    def _is_hostless_auto_progress_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        if lobby.host_enabled or self._is_information_slide(step):
            return False
        evaluation_type = (
            self._fallback_evaluation_type(step.player_input)
            if step.evaluation.type_ == EvaluationType.HOST_JUDGED
            else step.evaluation.type_
        )
        return (
            evaluation_type in HOSTLESS_AUTO_EVALUATION_TYPES
            and self._has_usable_answer_for_evaluation(step, evaluation_type)
        )

    async def _should_auto_close_on_all_submissions(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        if await self._has_active_host_player(lobby) or self._is_information_slide(step):
            return False
        evaluation_type = await self._resolve_evaluation_type(lobby, step)
        return (
            evaluation_type in HOSTLESS_AUTO_EVALUATION_TYPES
            and self._has_usable_answer_for_evaluation(step, evaluation_type)
        )

    async def _is_timer_effectively_enforced(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return step.timer.enforced or await self._should_auto_close_on_all_submissions(lobby, step)

    def _is_hostless_compatible_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        if lobby.host_enabled:
            return True
        if step.player_input.kind == PlayerInputKind.BUZZER:
            return False
        if self._is_information_slide(step):
            return True
        return self._is_hostless_auto_progress_step(lobby, step)

    async def _should_skip_answer_reveal(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return await self._resolve_evaluation_type(lobby, step) == EvaluationType.NONE

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
