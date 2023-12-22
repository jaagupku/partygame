from typing import Literal
from enum import StrEnum, auto

from pydantic import BaseModel

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


class BuzzerStateEvent(BaseEvent):
    type_: str = Event.BUZZER_STATE
    state: Literal["active"] | Literal["deactive"]


class BuzzerClickedEvent(BaseEvent):
    type_: str = Event.BUZZER_CLICKED
    player_id: str
