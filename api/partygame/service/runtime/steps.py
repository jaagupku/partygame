from __future__ import annotations

from dataclasses import dataclass

from partygame.schemas.game_definition import RoundDefinition, StepDefinition


@dataclass(frozen=True)
class FlattenedStep:
    step: StepDefinition
    round_definition: RoundDefinition
    round_number: int
    total_rounds: int
    is_round_end: bool
