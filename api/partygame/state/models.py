from typing import Any

from pydantic import BaseModel


class RuntimeStepState(BaseModel):
    game_id: str
    step_index: int = 0
    phase: str = "idle"


class ComponentState(BaseModel):
    id: str
    type_: str
    state: dict[str, Any]
