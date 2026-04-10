from typing import Any
from enum import StrEnum, auto

from pydantic import BaseModel, Field, model_validator


class MediaType(StrEnum):
    IMAGE = auto()
    AUDIO = auto()
    VIDEO = auto()


class ImageRevealMode(StrEnum):
    NONE = auto()
    BLUR_TO_CLEAR = auto()
    BLUR_CIRCLE = auto()
    ZOOM_OUT = auto()


class PlayerInputKind(StrEnum):
    NONE = auto()
    BUZZER = auto()
    TEXT = auto()
    NUMBER = auto()
    ORDERING = auto()
    RADIO = auto()
    CHECKBOX = auto()


class EvaluationType(StrEnum):
    NONE = auto()
    HOST_JUDGED = auto()
    EXACT_TEXT = auto()
    EXACT_NUMBER = auto()
    CLOSEST_NUMBER = auto()
    ORDERING_MATCH = auto()


class MediaDefinition(BaseModel):
    type_: MediaType
    src: str
    reveal: ImageRevealMode = ImageRevealMode.NONE
    loop: bool = False


class TimerDefinition(BaseModel):
    seconds: int | None = Field(default=None, ge=0)
    enforced: bool = False


class PlayerInputDefinition(BaseModel):
    kind: PlayerInputKind = PlayerInputKind.NONE
    prompt: str | None = None
    placeholder: str | None = None
    options: list[str] = Field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None

    @property
    def is_slider(self) -> bool:
        return self.min_value is not None and self.max_value is not None

    @model_validator(mode="after")
    def validate_input_shape(self) -> "PlayerInputDefinition":
        if (
            self.kind
            in (
                PlayerInputKind.ORDERING,
                PlayerInputKind.RADIO,
                PlayerInputKind.CHECKBOX,
            )
            and len(self.options) < 2
        ):
            raise ValueError(f"{self.kind.value.capitalize()} inputs require at least two options")
        if self.kind == PlayerInputKind.BUZZER and self.options:
            raise ValueError("Buzzer inputs cannot define options")
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value must be less than or equal to max_value")
        return self


class EvaluationRule(BaseModel):
    type_: EvaluationType = EvaluationType.NONE
    points: int = 1
    answer: Any = None


class HostBehavior(BaseModel):
    reveal_answers: bool = True
    show_submissions: bool = True
    allow_custom_points: bool = True


class StepDefinition(BaseModel):
    id: str
    title: str
    body: str | None = None
    media: MediaDefinition | None = None
    timer: TimerDefinition = Field(default_factory=TimerDefinition)
    player_input: PlayerInputDefinition = Field(default_factory=PlayerInputDefinition)
    evaluation: EvaluationRule = Field(default_factory=EvaluationRule)
    host_behavior: HostBehavior = Field(default_factory=HostBehavior)


class RoundDefinition(BaseModel):
    id: str
    title: str | None = None
    steps: list[StepDefinition] = Field(default_factory=list)


class GameDefinition(BaseModel):
    id: str
    title: str
    description: str | None = None
    rounds: list[RoundDefinition] = Field(default_factory=list)
