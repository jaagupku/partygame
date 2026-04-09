from typing import Any
from enum import StrEnum, auto

from pydantic import BaseModel, Field


class ComponentType(StrEnum):
    DISPLAY_TEXT_IMAGE = auto()
    PLAYER_INPUT = auto()
    BUZZER = auto()


class InputKind(StrEnum):
    TEXT = auto()
    NUMBER = auto()
    ORDERING = auto()


class EvaluationType(StrEnum):
    HOST_JUDGED = auto()
    CLOSEST_NUMBER = auto()
    EXACT_TEXT = auto()
    ORDERING_MATCH = auto()


class ComponentDefinition(BaseModel):
    id: str
    type_: ComponentType
    props: dict[str, Any] = Field(default_factory=dict)


class EvaluationRule(BaseModel):
    type_: EvaluationType
    points: int = 1
    config: dict[str, Any] = Field(default_factory=dict)


class StepDefinition(BaseModel):
    id: str
    title: str | None = None
    components: list[ComponentDefinition] = Field(default_factory=list)
    evaluation: EvaluationRule


class RoundDefinition(BaseModel):
    id: str
    title: str | None = None
    steps: list[StepDefinition] = Field(default_factory=list)


class GameDefinition(BaseModel):
    id: str
    title: str
    rounds: list[RoundDefinition] = Field(default_factory=list)
