from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field

from .lobby import Player


class Event(StrEnum):
    PLAYER_CONNECTED = auto()
    PLAYER_DISCONNECTED = auto()
    PLAYER_JOINED = auto()
    SET_HOST = auto()
    KICK_PLAYER = auto()
    START_GAME = auto()
    BUZZER_STATE = auto()
    BUZZER_CLICKED = auto()
    UPDATE_SCORE = auto()
    COMPONENT_STATE_UPDATED = auto()
    PLAYER_INPUT_SUBMITTED = auto()
    STEP_ADVANCED = auto()
    SCORES_UPDATED = auto()


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


class UpdateScoreEvent(BaseEvent):
    type_: str = Event.UPDATE_SCORE
    player_id: str
    add_score: int = 0
    set_score: int | None = None


class ComponentStateUpdatedEvent(BaseEvent):
    type_: str = Event.COMPONENT_STATE_UPDATED
    component_id: str
    state: dict[str, Any] = Field(default_factory=dict)


class PlayerInputSubmittedEvent(BaseEvent):
    type_: str = Event.PLAYER_INPUT_SUBMITTED
    component_id: str
    player_id: str
    value: Any


class StepAdvancedEvent(BaseEvent):
    type_: str = Event.STEP_ADVANCED
    step_index: int


class ScoresUpdatedEvent(BaseEvent):
    type_: str = Event.SCORES_UPDATED
    updates: dict[str, int] = Field(default_factory=dict)
