from enum import StrEnum, auto
from typing import Any, Literal

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


class BlurCircleBackgroundMode(StrEnum):
    BLUR = auto()
    SOLID = auto()


class PlayerInputKind(StrEnum):
    NONE = auto()
    BUZZER = auto()
    TEXT = auto()
    NUMBER = auto()
    ORDERING = auto()
    RADIO = auto()
    CHECKBOX = auto()
    MAP = auto()
    DRAWING = auto()


class EvaluationType(StrEnum):
    NONE = auto()
    HOST_JUDGED = auto()
    EXACT_TEXT = auto()
    EXACT_NUMBER = auto()
    CLOSEST_NUMBER = auto()
    ORDERING_MATCH = auto()
    MULTI_SELECT_WEIGHTED = auto()
    MAP_DISTANCE = auto()
    FAVORITE_VOTE = auto()


class DefinitionThemeMode(StrEnum):
    LIGHT = auto()
    DARK = auto()
    SYSTEM = auto()


class DefinitionThemePalette(StrEnum):
    PARTY = auto()
    MIDNIGHT = auto()
    CANDY = auto()
    FOREST = auto()


class DefinitionTheme(BaseModel):
    mode: DefinitionThemeMode = DefinitionThemeMode.SYSTEM
    palette: DefinitionThemePalette = DefinitionThemePalette.PARTY
    background: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    surface: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    ink: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    primary: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    accent: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class MapPoint(BaseModel):
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


class MapBounds(BaseModel):
    north: float = Field(ge=-90.0, le=90.0)
    south: float = Field(ge=-90.0, le=90.0)
    east: float = Field(ge=-180.0, le=180.0)
    west: float = Field(ge=-180.0, le=180.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> MapBounds:
        if self.north <= self.south:
            raise ValueError("map bounds north must be greater than south")
        if self.east <= self.west:
            raise ValueError("map bounds east must be greater than west")
        return self

    def contains(self, point: MapPoint) -> bool:
        return self.south <= point.lat <= self.north and self.west <= point.lng <= self.east


class MapInputConfig(BaseModel):
    selection_mode: Literal["point"] = "point"
    base_layer: Literal["osm", "light_nolabels"] = "osm"
    bounds: MapBounds
    initial_center: MapPoint
    initial_zoom: int = Field(ge=1, le=20)
    min_zoom: int | None = Field(default=None, ge=1, le=20)
    max_zoom: int | None = Field(default=None, ge=1, le=20)

    @model_validator(mode="after")
    def validate_map_config(self) -> MapInputConfig:
        if not self.bounds.contains(self.initial_center):
            raise ValueError("map initial_center must be inside bounds")
        if (
            self.min_zoom is not None
            and self.max_zoom is not None
            and self.min_zoom > self.max_zoom
        ):
            raise ValueError("map min_zoom must be less than or equal to max_zoom")
        if self.min_zoom is not None and self.initial_zoom < self.min_zoom:
            raise ValueError("map initial_zoom must be greater than or equal to min_zoom")
        if self.max_zoom is not None and self.initial_zoom > self.max_zoom:
            raise ValueError("map initial_zoom must be less than or equal to max_zoom")
        return self


class MapDistanceBand(BaseModel):
    distance_m: float = Field(ge=0.0)
    points: int
    label: str | None = None


class MapDistanceAnswer(BaseModel):
    correct_point: MapPoint
    scoring_mode: Literal["bands", "linear"] = "bands"
    max_points: int = Field(ge=0)
    zero_distance_m: float | None = Field(default=None, gt=0.0)
    full_credit_distance_m: float | None = Field(default=None, ge=0.0)
    bands: list[MapDistanceBand] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scoring(self) -> MapDistanceAnswer:
        if self.scoring_mode == "bands":
            if not self.bands:
                raise ValueError("map distance band scoring requires at least one band")
            sorted_bands = sorted(self.bands, key=lambda band: band.distance_m)
            previous_distance = -1.0
            for band in sorted_bands:
                if band.distance_m <= previous_distance:
                    raise ValueError("map distance bands must use unique increasing distances")
                previous_distance = band.distance_m
            self.bands = [
                band.model_copy(update={"points": min(max(band.points, 0), self.max_points)})
                for band in sorted_bands
            ]
        if self.scoring_mode == "linear":
            if self.zero_distance_m is None:
                raise ValueError("linear map distance scoring requires zero_distance_m")
            if (
                self.full_credit_distance_m is not None
                and self.full_credit_distance_m > self.zero_distance_m
            ):
                raise ValueError(
                    "full_credit_distance_m must be less than or equal to zero_distance_m"
                )
        return self


class MediaDefinition(BaseModel):
    type_: MediaType
    src: str
    reveal: ImageRevealMode = ImageRevealMode.NONE
    loop: bool = False
    autoplay: bool = True
    hide_youtube_title: bool = False
    blur_amount: float = Field(default=18.0, ge=0.0, le=80.0)
    blur_circle_start_size: float = Field(default=0.07, ge=0.01, le=1.0)
    blur_circle_background: BlurCircleBackgroundMode = BlurCircleBackgroundMode.BLUR
    blur_circle_background_color: str = "#0f172a"
    blur_reveal_curve: tuple[float, float, float, float] | None = None
    blur_circle_reveal_curve: tuple[float, float, float, float] | None = None
    zoom_reveal_curve: tuple[float, float, float, float] | None = None
    zoom_start: float | None = Field(default=None, ge=1.0)
    zoom_origin_x: float | None = Field(default=None, ge=0.0, le=1.0)
    zoom_origin_y: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_reveal_curves(self) -> MediaDefinition:
        for curve_name in (
            "blur_reveal_curve",
            "blur_circle_reveal_curve",
            "zoom_reveal_curve",
        ):
            curve = getattr(self, curve_name)
            if curve is None:
                continue
            for value in curve:
                if value < 0 or value > 1:
                    raise ValueError(f"{curve_name} values must be between 0 and 1")
        return self


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
    map: MapInputConfig | None = None

    @property
    def is_slider(self) -> bool:
        return self.min_value is not None and self.max_value is not None

    @model_validator(mode="after")
    def validate_input_shape(self) -> PlayerInputDefinition:
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
        if self.kind == PlayerInputKind.MAP:
            if self.options:
                raise ValueError("Map inputs cannot define options")
            if self.map is None:
                raise ValueError("Map inputs require map configuration")
        elif self.map is not None:
            raise ValueError("Only map inputs can define map configuration")
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
    max_distance: int = Field(default=2, ge=0)
    number_bands: list[NumberToleranceBand] = Field(default_factory=list)


class NumberToleranceBand(BaseModel):
    distance: float = Field(ge=0)
    points: int = Field(ge=0)
    label: str | None = None


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
    def validate_evaluation_shape(self) -> StepDefinition:
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
            PlayerInputKind.MAP: {
                EvaluationType.NONE,
                EvaluationType.HOST_JUDGED,
                EvaluationType.MAP_DISTANCE,
            },
            PlayerInputKind.DRAWING: {
                EvaluationType.NONE,
                EvaluationType.FAVORITE_VOTE,
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
                    raise ValueError(  # noqa: TRY004 - Pydantic validation error
                        "option_scores entries must be objects"
                    )
                option = entry.get("option")
                points = entry.get("points")
                if not isinstance(option, str) or option not in self.player_input.options:
                    raise ValueError(
                        "option_scores entries must reference defined checkbox options"
                    )
                if option in seen_options:
                    raise ValueError("option_scores entries must be unique")
                if not isinstance(points, int):
                    raise ValueError(  # noqa: TRY004 - Pydantic validation error
                        "option_scores points must be integers"
                    )
                seen_options.add(option)
        if self.evaluation.type_ == EvaluationType.MAP_DISTANCE:
            if self.player_input.map is None:
                raise ValueError("map_distance evaluation requires map input configuration")
            if not isinstance(self.evaluation.answer, dict):
                raise ValueError("map_distance evaluation requires an answer object")
            answer = MapDistanceAnswer.model_validate(self.evaluation.answer)
            if not self.player_input.map.bounds.contains(answer.correct_point):
                raise ValueError("map_distance correct_point must be inside map bounds")
            self.evaluation.answer = answer.model_dump(mode="json")
        return self


class RoundDefinition(BaseModel):
    id: str
    title: str | None = None
    steps: list[StepDefinition] = Field(default_factory=list)


class GameDefinition(BaseModel):
    id: str = Field(pattern=DEFINITION_ID_PATTERN)
    title: str
    description: str | None = None
    theme: DefinitionTheme | None = None
    rounds: list[RoundDefinition] = Field(default_factory=list)
