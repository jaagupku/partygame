from uuid import uuid4
from typing import List
from enum import StrEnum, auto

from pydantic import BaseModel, Field


class ConnectionStatus(StrEnum):
    CONNECTED = auto()
    DISCONNECTED = auto()


class GameState(StrEnum):
    WAITING_FOR_PLAYERS = auto()
    RUNNING = auto()
    PAUSED = auto()


class CreateGame(BaseModel):
    ...


class JoinRequest(BaseModel):
    join_code: str
    player_name: str
    player_id: str = None


class Player(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(min_length=1, max_length=32)
    score: int = 0
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED


class Lobby(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    join_code: str
    players: List[Player] = []
    host_id: str = None
    state: GameState = GameState.WAITING_FOR_PLAYERS


class ConnectedToLobby(BaseModel):
    player: Player
    lobby: Lobby
