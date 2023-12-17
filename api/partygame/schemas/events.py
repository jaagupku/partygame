from enum import StrEnum, auto

from pydantic import BaseModel

from .lobby import Player


class Event(StrEnum):
    PLAYER_CONNECTED = auto()
    PLAYER_DISCONNECTED = auto()
    PLAYER_JOINED = auto()


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
