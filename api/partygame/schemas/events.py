from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field

from .lobby import GameState, Player
from .game_definition import PlayerInputKind


class Event(StrEnum):
    PLAYER_CONNECTED = auto()
    PLAYER_DISCONNECTED = auto()
    PLAYER_JOINED = auto()
    SET_HOST = auto()
    KICK_PLAYER = auto()
    START_GAME = auto()
    RESET_STEP = auto()
    SHOW_ANSWER_REVEAL = auto()
    SHOW_QUESTION = auto()
    SCOREBOARD_VISIBILITY = auto()
    UPDATE_SCORE = auto()
    STEP_ADVANCED = auto()
    SCORES_UPDATED = auto()
    PLAYER_INPUT_SUBMITTED = auto()
    BUZZER_STATE = auto()
    BUZZER_CLICKED = auto()
    RUNTIME_SNAPSHOT = auto()
    SUBMISSIONS_UPDATED = auto()
    REVEALED_SUBMISSION = auto()
    BUZZER_REVIEWED = auto()
    CLOSE_STEP = auto()
    REVIEW_SUBMISSION = auto()
    RUNTIME_PATCH = auto()
    RESYNC_REQUEST = auto()
    REVEAL_END_GAME = auto()
    ADVANCE_END_GAME_STAGE = auto()
    TOGGLE_END_GAME_AUTOPLAY = auto()


class BaseEvent(BaseModel):
    type_: str


class PlayerJoinedEvent(BaseEvent):
    type_: str = Event.PLAYER_JOINED
    player: Player


class PlayerConnectedEvent(BaseEvent):
    type_: str = Event.PLAYER_CONNECTED
    player_id: str


class PlayerDisconnectedEvent(BaseEvent):
    type_: str = Event.PLAYER_DISCONNECTED
    player_id: str


class SetHostEvent(BaseEvent):
    type_: str = Event.SET_HOST
    player_id: str


class KickPlayerEvent(BaseEvent):
    type_: str = Event.KICK_PLAYER
    player_id: str


class StartGameEvent(BaseEvent):
    type_: str = Event.START_GAME


class ResetStepEvent(BaseEvent):
    type_: str = Event.RESET_STEP


class ShowAnswerRevealEvent(BaseEvent):
    type_: str = Event.SHOW_ANSWER_REVEAL


class ShowQuestionEvent(BaseEvent):
    type_: str = Event.SHOW_QUESTION


class ScoreboardVisibilityEvent(BaseEvent):
    type_: str = Event.SCOREBOARD_VISIBILITY
    visible: bool


class UpdateScoreEvent(BaseEvent):
    type_: str = Event.UPDATE_SCORE
    player_id: str
    add_score: int = 0
    set_score: int | None = None


class PlayerInputSubmittedEvent(BaseEvent):
    type_: str = Event.PLAYER_INPUT_SUBMITTED
    component_id: str | None = None
    player_id: str
    value: Any


class StepAdvancedEvent(BaseEvent):
    type_: str = Event.STEP_ADVANCED
    step_index: int


class ScoresUpdatedEvent(BaseEvent):
    type_: str = Event.SCORES_UPDATED
    updates: dict[str, int] = Field(default_factory=dict)


class CloseStepEvent(BaseEvent):
    type_: str = Event.CLOSE_STEP


class ReviewSubmissionEvent(BaseEvent):
    type_: str = Event.REVIEW_SUBMISSION
    player_id: str
    accepted: bool
    points_override: int | None = None


class BuzzerStateEvent(BaseEvent):
    type_: str = Event.BUZZER_STATE
    active: bool


class BuzzerClickedEvent(BaseEvent):
    type_: str = Event.BUZZER_CLICKED
    player_id: str


class BuzzerReviewedEvent(BaseEvent):
    type_: str = Event.BUZZER_REVIEWED
    player_id: str
    accepted: bool
    disabled_buzzer_player_ids: list[str] = Field(default_factory=list)


class RuntimeTimerState(BaseModel):
    seconds: int | None = None
    enforced: bool = False
    started_at: float | None = None
    ends_at: float | None = None
    remaining_seconds: float | None = None


class RuntimeMediaState(BaseModel):
    type_: str
    src: str
    reveal: str | None = None
    loop: bool = False
    reveal_state: str = "idle"
    reveal_started_at: float | None = None
    reveal_elapsed_seconds: float = 0.0
    reveal_duration_seconds: float | None = None


class RuntimeStepState(BaseModel):
    id: str
    title: str
    body: str | None = None
    evaluation_type: str = ""
    evaluation_points: int = 0
    input_enabled: bool = False
    input_kind: PlayerInputKind = PlayerInputKind.NONE
    input_prompt: str | None = None
    input_placeholder: str | None = None
    input_options: list[str] = Field(default_factory=list)
    slider_min: float | None = None
    slider_max: float | None = None
    slider_step: float | None = None
    media: RuntimeMediaState | None = None
    timer: RuntimeTimerState = Field(default_factory=RuntimeTimerState)


class RuntimeLobbyState(BaseModel):
    id: str
    join_code: str
    definition_id: str | None = None
    host_enabled: bool = True
    starter_id: str | None = None
    host_id: str | None = None
    state: GameState
    phase: str = "waiting"
    current_step: int = 0


class RevealedSubmission(BaseModel):
    player_id: str
    value: Any


class RevealedAnswer(BaseModel):
    value: Any


class SubmissionItem(BaseModel):
    player_id: str
    value: Any
    reviewed: bool = False


class RuntimeSnapshotEvent(BaseEvent):
    type_: str = Event.RUNTIME_SNAPSHOT
    revision: int = 0
    lobby: RuntimeLobbyState
    players: list[Player] = Field(default_factory=list)
    active_step: RuntimeStepState | None = None
    display_phase: str = "question_active"
    scoreboard_visible: bool = False
    buzzer_active: bool = False
    buzzed_player_id: str | None = None
    disabled_buzzer_player_ids: list[str] = Field(default_factory=list)
    submitted_player_ids: list[str] = Field(default_factory=list)
    submission_count: int = 0
    pending_review_count: int = 0
    revealed_submission: RevealedSubmission | None = None
    revealed_answer: RevealedAnswer | None = None
    host_answer: RevealedAnswer | None = None
    submissions: list[SubmissionItem] = Field(default_factory=list)
    end_game: EndGameState | None = None


class RuntimePatchEvent(BaseEvent):
    type_: str = Event.RUNTIME_PATCH
    base_revision: int
    revision: int
    changes: dict[str, Any] = Field(default_factory=dict)


class SubmissionsUpdatedEvent(BaseEvent):
    type_: str = Event.SUBMISSIONS_UPDATED
    items: list[SubmissionItem] = Field(default_factory=list)


class RevealedSubmissionEvent(BaseEvent):
    type_: str = Event.REVEALED_SUBMISSION
    submission: RevealedSubmission | None = None


class ResyncRequestEvent(BaseEvent):
    type_: str = Event.RESYNC_REQUEST
    last_revision: int | None = None


class RevealEndGameEvent(BaseEvent):
    type_: str = Event.REVEAL_END_GAME


class AdvanceEndGameStageEvent(BaseEvent):
    type_: str = Event.ADVANCE_END_GAME_STAGE


class ToggleEndGameAutoplayEvent(BaseEvent):
    type_: str = Event.TOGGLE_END_GAME_AUTOPLAY
    enabled: bool


class FinalStandingEntry(BaseModel):
    player_id: str
    name: str
    score: int
    place: int
    avatar_kind: str | None = None
    avatar_preset_key: str | None = None
    avatar_url: str | None = None


class EndGameStatCard(BaseModel):
    id: str
    label: str
    winner_player_ids: list[str] = Field(default_factory=list)
    value: float | int
    unit: str | None = None
    description: str | None = None


class EndGameState(BaseModel):
    revealed: bool = False
    sequence_stage: str = "podium"
    autoplay_enabled: bool = False
    final_standings: list[FinalStandingEntry] = Field(default_factory=list)
    podium: list[FinalStandingEntry] = Field(default_factory=list)
    stats_cards: list[EndGameStatCard] = Field(default_factory=list)
