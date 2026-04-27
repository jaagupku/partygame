from typing import Any
from enum import StrEnum, auto

from pydantic import BaseModel, Field, model_validator

DEFINITION_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,79}$"


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
    MULTI_SELECT_WEIGHTED = auto()


class MediaDefinition(BaseModel):
    type_: MediaType
    src: str
    reveal: ImageRevealMode = ImageRevealMode.NONE
    loop: bool = False
    zoom_start: float | None = Field(default=None, ge=1.0)
    zoom_origin_x: float | None = Field(default=None, ge=0.0, le=1.0)
    zoom_origin_y: float | None = Field(default=None, ge=0.0, le=1.0)


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

    @model_validator(mode="after")
    def validate_evaluation_shape(self) -> "StepDefinition":
        allowed_evaluations = {
            PlayerInputKind.NONE: {EvaluationType.NONE},
            PlayerInputKind.BUZZER: {EvaluationType.HOST_JUDGED},
            PlayerInputKind.TEXT: {
                EvaluationType.NONE,
                EvaluationType.HOST_JUDGED,
                EvaluationType.EXACT_TEXT,
            },
            PlayerInputKind.NUMBER: {
                EvaluationType.NONE,
                EvaluationType.HOST_JUDGED,
                EvaluationType.EXACT_NUMBER,
                EvaluationType.CLOSEST_NUMBER,
            },
            PlayerInputKind.ORDERING: {
                EvaluationType.NONE,
                EvaluationType.HOST_JUDGED,
                EvaluationType.ORDERING_MATCH,
            },
            PlayerInputKind.RADIO: {
                EvaluationType.NONE,
                EvaluationType.HOST_JUDGED,
                EvaluationType.EXACT_TEXT,
            },
            PlayerInputKind.CHECKBOX: {
                EvaluationType.NONE,
                EvaluationType.HOST_JUDGED,
                EvaluationType.MULTI_SELECT_WEIGHTED,
            },
        }
        allowed = allowed_evaluations[self.player_input.kind]
        if self.evaluation.type_ not in allowed:
            raise ValueError(
                f"{self.evaluation.type_.value} evaluation is not allowed for {self.player_input.kind.value} input"
            )

        if self.evaluation.type_ == EvaluationType.MULTI_SELECT_WEIGHTED:
            if not isinstance(self.evaluation.answer, dict):
                raise ValueError("multi_select_weighted evaluation requires an answer object")
            option_scores = self.evaluation.answer.get("option_scores")
            if not isinstance(option_scores, list):
                raise ValueError("multi_select_weighted answer must include option_scores")
            seen_options: set[str] = set()
            for entry in option_scores:
                if not isinstance(entry, dict):
                    raise ValueError("option_scores entries must be objects")
                option = entry.get("option")
                points = entry.get("points")
                if not isinstance(option, str) or option not in self.player_input.options:
                    raise ValueError(
                        "option_scores entries must reference defined checkbox options"
                    )
                if option in seen_options:
                    raise ValueError("option_scores entries must be unique")
                if not isinstance(points, int):
                    raise ValueError("option_scores points must be integers")
                seen_options.add(option)
        return self


class RoundDefinition(BaseModel):
    id: str
    title: str | None = None
    steps: list[StepDefinition] = Field(default_factory=list)


class GameDefinition(BaseModel):
    id: str = Field(pattern=DEFINITION_ID_PATTERN)
    title: str
    description: str | None = None
    rounds: list[RoundDefinition] = Field(default_factory=list)
