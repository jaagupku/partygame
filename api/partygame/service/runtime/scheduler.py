from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Literal

from partygame import schemas
from partygame.service.game import ROUND_INTRO_DURATION_SECONDS

HOSTLESS_ANSWER_REVEAL_DELAY_SECONDS = 4.0
HOSTLESS_END_GAME_AUTOPLAY_DELAY_SECONDS = 4.5

ScheduledTransitionKind = Literal[
    "round_intro",
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
        runtime,
    ) -> ScheduledTransition | None:
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
                HOSTLESS_END_GAME_AUTOPLAY_DELAY_SECONDS,
            )

        if (
            not lobby.host_enabled
            and snapshot.active_step is not None
            and lobby.phase == "step_complete"
            and snapshot.display_phase == "answer_reveal"
        ):
            current_step = await runtime.get_current_step(lobby)
            if current_step is None or not runtime._is_hostless_auto_progress_step(
                lobby, current_step
            ):
                return None
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
            not lobby.host_enabled and runtime._is_hostless_auto_progress_step(lobby, current_step)
        ):
            return None

        return ScheduledTransition(
            "timer_expired",
            max(0, snapshot.active_step.timer.ends_at - time()),
        )
