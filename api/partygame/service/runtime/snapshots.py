from __future__ import annotations

from typing import Any

from partygame import schemas
from partygame.schemas.game_definition import (
    MediaDefinition,
    PlayerInputKind,
    StepDefinition,
)
from partygame.service.runtime.steps import FlattenedStep

ROUND_INTRO_DURATION_SECONDS = 5.0


class SnapshotBuilder:
    def __init__(self, runtime, repo, evaluation, timing, end_game):
        self.runtime = runtime
        self.repo = repo
        self.evaluation = evaluation
        self.timing = timing
        self.end_game = end_game

    async def build_snapshot(
        self,
        lobby: schemas.Lobby,
        *,
        revision: int | None = None,
    ) -> schemas.RuntimeSnapshotEvent:
        step = await self.runtime.get_current_step(lobby)
        active_round = await self.runtime.get_current_round(lobby)
        step_state = await self.runtime.get_step_state(lobby.id)
        players = await self.repo.get_players(lobby.id)
        snapshot_revision = (
            revision if revision is not None else await self.repo.get_state_revision(lobby.id)
        )

        active_step = None
        if step is not None and lobby.phase != "round_intro":
            active_step = await self._runtime_step_state(
                lobby,
                step,
                step_state,
                input_enabled=lobby.phase == "question_active",
            )

        active_item = None
        if active_round is not None and lobby.phase == "round_intro":
            active_item = schemas.RuntimeRoundIntroItemState(
                round=active_round,
                duration_seconds=ROUND_INTRO_DURATION_SECONDS,
            )
        elif active_step is not None:
            active_item = schemas.RuntimeStepItemState(step=active_step)

        next_item = await self._build_next_item(lobby)
        pending_review_count = self._pending_review_count(step_state)
        next_host_action = self._build_next_host_action(
            lobby,
            step,
            step_state,
            active_step,
            next_item,
            pending_review_count,
            has_eligible_buzzer_players=await self._has_eligible_buzzer_players(
                lobby, step_state, players
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
        end_game = await self.end_game._build_end_game_state(lobby, players)

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
            active_item=active_item,
            next_item=next_item,
            next_host_action=next_host_action,
            active_round=active_round,
            active_step=active_step,
            display_phase=str(step_state.get("display_phase") or "question_active"),
            scoreboard_visible=bool(step_state.get("scoreboard_visible")),
            buzzer_active=bool(step_state.get("buzzer_active")),
            buzzed_player_id=step_state.get("buzzed_player_id") or None,
            disabled_buzzer_player_ids=list(step_state.get("disabled_buzzer_player_ids", [])),
            submitted_player_ids=list(step_state.get("answers", {}).keys()),
            submission_count=len(step_state.get("answers", {})),
            pending_review_count=pending_review_count,
            revealed_submission=revealed_submission,
            revealed_answer=revealed_answer,
            host_answer=host_answer,
            submissions=submissions.items,
            end_game=end_game,
        )

    def _runtime_round_state(self, step: FlattenedStep) -> schemas.RuntimeRoundState:
        return schemas.RuntimeRoundState(
            id=step.round_definition.id,
            title=step.round_definition.title,
            number=step.round_number,
            total=step.total_rounds,
        )

    async def _runtime_step_state(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
        step_state: dict[str, Any],
        *,
        input_enabled: bool,
    ) -> schemas.RuntimeStepState:
        evaluation_type = await self.evaluation._resolve_evaluation_type(lobby, step)
        return schemas.RuntimeStepState(
            id=step.id,
            title=step.title,
            body=step.body,
            evaluation_type=str(evaluation_type),
            evaluation_points=step.evaluation.points,
            max_points=self.evaluation._max_points_for_step(step, evaluation_type),
            input_enabled=input_enabled,
            input_kind=step.player_input.kind,
            input_prompt=step.player_input.prompt,
            input_placeholder=step.player_input.placeholder,
            input_options=step.player_input.options,
            slider_min=step.player_input.min_value,
            slider_max=step.player_input.max_value,
            slider_step=step.player_input.step,
            map=step.player_input.map,
            media=self._serialize_media(step.media, step_state),
            timer=schemas.RuntimeTimerState(
                seconds=step.timer.seconds,
                enforced=await self.evaluation._is_timer_effectively_enforced(lobby, step),
                started_at=self.timing._to_float(step_state.get("timer_started_at")),
                ends_at=self.timing._to_float(step_state.get("timer_ends_at")),
                remaining_seconds=self.timing._remaining_timer_seconds(step_state),
            ),
        )

    async def _build_next_item(self, lobby: schemas.Lobby) -> schemas.RuntimeItemState | None:
        steps = await self.runtime._flatten_steps_with_metadata(lobby)
        next_index = lobby.current_step + 1
        if next_index >= len(steps):
            return None

        current = steps[lobby.current_step] if lobby.current_step < len(steps) else None
        next_step = steps[next_index]
        next_round = self._runtime_round_state(next_step)
        if current is not None and next_step.round_definition.id != current.round_definition.id:
            return schemas.RuntimeRoundIntroItemState(
                round=next_round,
                duration_seconds=ROUND_INTRO_DURATION_SECONDS,
            )

        return schemas.RuntimeStepItemState(
            step=await self._runtime_step_state(
                lobby,
                next_step.step,
                {},
                input_enabled=False,
            )
        )

    def _build_next_host_action(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition | None,
        step_state: dict[str, Any],
        active_step: schemas.RuntimeStepState | None,
        next_item: schemas.RuntimeItemState | None,
        pending_review_count: int,
        *,
        has_eligible_buzzer_players: bool,
    ) -> schemas.NextHostActionState | None:
        if lobby.phase == "finished":
            return None

        display_phase = str(step_state.get("display_phase") or "question_active")
        if lobby.phase == "host_review" and pending_review_count > 0:
            return schemas.NextHostActionState(kind="blocked_review", disabled=True)

        if (
            step is not None
            and step.player_input.kind == PlayerInputKind.BUZZER
            and lobby.phase == "host_review"
            and display_phase != "answer_reveal"
            and not bool(step_state.get("buzzer_active"))
            and pending_review_count == 0
            and has_eligible_buzzer_players
        ):
            return schemas.NextHostActionState(kind="reactivate_buzzers")

        if display_phase != "answer_reveal":
            return schemas.NextHostActionState(
                kind="answer_reveal",
                title=active_step.title if active_step is not None else None,
            )

        if next_item is None:
            return schemas.NextHostActionState(kind="finale")

        if next_item.type_ == "round_intro":
            return schemas.NextHostActionState(
                kind="round_intro",
                title=next_item.round.title or f"Round {next_item.round.number}",
            )

        return schemas.NextHostActionState(
            kind="next_question",
            title=next_item.step.title,
        )

    async def _has_eligible_buzzer_players(
        self,
        lobby: schemas.Lobby,
        step_state: dict[str, Any],
        players: list[schemas.Player] | None = None,
    ) -> bool:
        player_list = players if players is not None else await self.repo.get_players(lobby.id)
        disabled_player_ids = set(step_state.get("disabled_buzzer_player_ids", []))
        return any(
            player.id != lobby.host_id and player.id not in disabled_player_ids
            for player in player_list
        )

    async def build_submissions_event(
        self, lobby: schemas.Lobby
    ) -> schemas.SubmissionsUpdatedEvent:
        state = await self.runtime.get_step_state(lobby.id)
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
        return await self.runtime.build_snapshot(lobby)

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
            paused=bool(step_state.get("media_paused")),
            volume=float(
                1 if step_state.get("media_volume") is None else step_state.get("media_volume")
            ),
            reveal=str(media.reveal),
            loop=media.loop,
            autoplay=media.autoplay,
            hide_youtube_title=media.hide_youtube_title,
            playback_revision=int(step_state.get("media_playback_revision") or 0),
            blur_amount=media.blur_amount,
            blur_circle_start_size=media.blur_circle_start_size,
            blur_circle_background=str(media.blur_circle_background),
            blur_circle_background_color=media.blur_circle_background_color,
            blur_reveal_curve=media.blur_reveal_curve,
            blur_circle_reveal_curve=media.blur_circle_reveal_curve,
            zoom_reveal_curve=media.zoom_reveal_curve,
            zoom_start=media.zoom_start,
            zoom_origin_x=media.zoom_origin_x,
            zoom_origin_y=media.zoom_origin_y,
            reveal_state=str(step_state.get("media_reveal_state") or "idle"),
            reveal_started_at=self.timing._to_float(step_state.get("media_reveal_started_at")),
            reveal_elapsed_seconds=self.timing._to_float(
                step_state.get("media_reveal_elapsed_seconds")
            )
            or 0.0,
            reveal_duration_seconds=self.timing._to_float(
                step_state.get("media_reveal_duration_seconds")
            ),
        )

    def _pending_review_count(self, step_state: dict[str, Any]) -> int:
        reviewed = set(step_state.get("reviewed_player_ids", []))
        review_targets = set(step_state.get("answers", {}).keys())
        buzzed_player_id = step_state.get("buzzed_player_id") or ""
        if buzzed_player_id:
            review_targets.add(buzzed_player_id)
        return len([player_id for player_id in review_targets if player_id not in reviewed])

    def _step_has_revealable_answer(self, step: StepDefinition) -> bool:
        answer = step.evaluation.answer
        if answer is None:
            return False
        if isinstance(answer, str):
            return bool(answer.strip())
        if isinstance(answer, list):
            return any(str(value).strip() for value in answer)
        if isinstance(answer, dict):
            return len(answer) > 0
        return True
