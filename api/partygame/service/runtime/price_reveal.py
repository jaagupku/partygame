from time import time
from typing import Any

PRICE_READY_SPEED_BONUS = 0.15


def price_reveal_speed(state: dict[str, Any]) -> float:
    return 1.0 + PRICE_READY_SPEED_BONUS * len(state.get("price_ready_player_ids", []))


def remaining_price_reveal_seconds(
    state: dict[str, Any], duration: float, *, now: float | None = None
) -> float:
    now = time() if now is None else now
    remaining = state.get("price_reveal_remaining_seconds")
    if remaining in (None, ""):
        remaining = duration
    updated_at = state.get("price_reveal_updated_at")
    if updated_at in (None, ""):
        return max(0.0, float(remaining))
    return max(
        0.0, float(remaining) - max(0.0, now - float(updated_at)) * price_reveal_speed(state)
    )
