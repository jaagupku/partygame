from __future__ import annotations

from time import time
from typing import Any

from partygame.schemas.game_definition import ImageRevealMode, MediaType, StepDefinition


class TimingState:
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
            return any(str(value).strip() for value in answer)
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
