from dataclasses import dataclass
from time import time
from typing import TYPE_CHECKING, Literal

from partygame import schemas
from partygame.service.runtime.price_reveal import (
    price_reveal_speed,
    remaining_price_reveal_seconds,
)
from partygame.service.runtime.snapshots import ROUND_INTRO_DURATION_SECONDS

if TYPE_CHECKING:
    from partygame.service.game import GameRuntimeService

HOSTLESS_ANSWER_REVEAL_DELAY_SECONDS = 4.0
HOSTLESS_END_GAME_AUTOPLAY_DELAY_SECONDS = 4.5

ScheduledTransitionKind = Literal[
    "round_intro",
    "price_transition",
    "hostless_answer_reveal",
    "hostless_end_game_stage",
    "timer_expired",
]


@dataclass(frozen=True)
class ScheduledTransition:
    kind: ScheduledTransitionKind
    delay_seconds: float


class RuntimeTransitionScheduler:
    async def next_transition(
        self,
        *,
        lobby: schemas.Lobby,
        snapshot: schemas.RuntimeSnapshotEvent,
        runtime: GameRuntimeService,
    ) -> ScheduledTransition | None:
        if lobby.game_type == "price_guessing" and lobby.phase == "price_transition":
            state = await runtime.get_step_state(lobby.id)
            deadline = runtime.timing.to_float(state.get("price_transition_ends_at"))
            if deadline is not None:
                return ScheduledTransition(
                    "price_transition", max(0.0, deadline - time())
                )
            return None

        if snapshot.active_item and snapshot.active_item.type_ == "round_intro":
            return ScheduledTransition("round_intro", ROUND_INTRO_DURATION_SECONDS)

        if (
            not lobby.host_enabled
            and snapshot.end_game is not None
            and snapshot.end_game.revealed
            and snapshot.end_game.autoplay_enabled
            and snapshot.end_game.sequence_stage != "scoreboard"
        ):
            return ScheduledTransition(
                "hostless_end_game_stage",
                (
                    12.0
                    if snapshot.end_game.sequence_stage == "stats"
                    else HOSTLESS_END_GAME_AUTOPLAY_DELAY_SECONDS
                ),
            )

        if (
            not lobby.host_enabled
            and snapshot.active_step is not None
            and lobby.phase == "step_complete"
            and snapshot.display_phase == "answer_reveal"
        ):
            current_step = await runtime.get_current_step(lobby)
            if current_step is None or not runtime.is_hostless_auto_progress_step(
                lobby, current_step
            ):
                return None
            if current_step.product_question is not None:
                state = await runtime.get_step_state(lobby.id)
                return ScheduledTransition(
                    "hostless_answer_reveal",
                    remaining_price_reveal_seconds(
                        state, current_step.product_question.reveal_seconds
                    )
                    / price_reveal_speed(state),
                )
            return ScheduledTransition(
                "hostless_answer_reveal",
                HOSTLESS_ANSWER_REVEAL_DELAY_SECONDS,
            )

        if (
            snapshot.active_step is None
            or snapshot.active_step.timer.ends_at is None
            or lobby.phase != "question_active"
        ):
            return None

        current_step = await runtime.get_current_step(lobby)
        if current_step is None:
            return None
        if not snapshot.active_step.timer.enforced and not (
            not lobby.host_enabled
            and runtime.is_hostless_auto_progress_step(lobby, current_step)
        ):
            return None

        return ScheduledTransition(
            "timer_expired",
            max(0, snapshot.active_step.timer.ends_at - time()),
        )
