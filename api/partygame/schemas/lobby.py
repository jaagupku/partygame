from uuid import uuid4
from typing import List, Literal
from enum import StrEnum, auto

from pydantic import BaseModel, Field


class ConnectionStatus(StrEnum):
    CONNECTED = auto()
    DISCONNECTED = auto()


class GameState(StrEnum):
    WAITING_FOR_PLAYERS = auto()
    RUNNING = auto()
    PAUSED = auto()


class ControllerComponent(StrEnum):
    BUZZER_GAME = auto()


class DisplayComponent(StrEnum):
    QUESTIONARE = auto()


class CreateGame(BaseModel):
    ...


class ComponentType(StrEnum):
    DISPLAY = auto()
    CONTROLLER = auto()


class ComponentSpec(BaseModel):
    type_: Literal["component_spec"] = "component_spec"
    display: DisplayComponent
    controller: ControllerComponent


class JoinRequest(BaseModel):
    join_code: str
    player_name: str
    player_id: str | None = None


class Player(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    game_id: str
    name: str = Field(min_length=1, max_length=32)
    score: int = 0
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED


class BaseComponent(BaseModel):
    type_: ControllerComponent


class Lobby(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    join_code: str
    players: List[Player] = []
    host_id: str | None = None
    state: GameState = GameState.WAITING_FOR_PLAYERS
    connection: ConnectionStatus = ConnectionStatus.CONNECTED
    active_game: str | None = None


class ConnectedToLobby(BaseModel):
    player: Player
    lobby: Lobby
