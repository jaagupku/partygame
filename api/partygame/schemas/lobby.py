from enum import StrEnum, auto
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from partygame.schemas.calorie_game import CalorieGameSettings
from partygame.schemas.drawing_game import DrawingSettings
from partygame.schemas.price_game import PriceGameSettings


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
    drawing_settings: DrawingSettings | None = None
    price_settings: PriceGameSettings | None = None
    calorie_settings: CalorieGameSettings | None = None
    game_type: str = "trivia"
    definition_id: str = "quiz_demo"
    host_enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def price_defaults(cls, values):
        if isinstance(values, dict) and values.get("game_type") == "price_guessing":
            return {"host_enabled": False, "price_settings": {}, **values}
        if isinstance(values, dict) and values.get("game_type") == "calorie_guessing":
            return {"host_enabled": False, "calorie_settings": {}, **values}
        if isinstance(values, dict) and values.get("game_type") == "drawing_mashup":
            return {"host_enabled": False, "drawing_settings": {}, **values}
        return values

    @model_validator(mode="after")
    def normalized_price_settings(self):
        if self.game_type == "price_guessing" and self.price_settings is None:
            self.price_settings = PriceGameSettings()
        if self.game_type == "calorie_guessing" and self.calorie_settings is None:
            self.calorie_settings = CalorieGameSettings()
        if self.game_type == "drawing_mashup" and self.drawing_settings is None:
            self.drawing_settings = DrawingSettings()
        return self


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
    avatar_kind: Literal["preset", "custom"] | None = None
    avatar_preset_key: str | None = None
    avatar_url: str | None = None
    avatar_asset_id: str | None = None


class Player(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    game_id: str
    name: str = Field(min_length=1, max_length=32)
    score: int = 0
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    avatar_kind: Literal["preset", "custom"] | None = None
    avatar_preset_key: str | None = None
    avatar_url: str | None = None
    avatar_asset_id: str | None = None


class BaseComponent(BaseModel):
    type_: ControllerComponent


class Lobby(BaseModel):
    run_id: str | None = None
    definition_title: str | None = None
    game_type: str = "trivia"
    session_version: int | None = None
    id: str = Field(default_factory=lambda: uuid4().hex)
    join_code: str
    players: list[Player] = Field(default_factory=list)
    starter_id: str | None = None
    host_id: str | None = None
    host_enabled: bool = True
    state: GameState = GameState.WAITING_FOR_PLAYERS
    connection: ConnectionStatus = ConnectionStatus.CONNECTED
    active_game: str | None = None
    definition_id: str | None = None
    current_step: int = 0
    phase: str = "waiting"


class ConnectedToLobby(BaseModel):
    player: Player
    lobby: Lobby


class ContinueGame(BaseModel):
    expected_run_id: str
    settings: CreateGame


class LobbySetup(BaseModel):
    run_id: str
    settings: CreateGame
    settings_complete: bool = True
    definition_title: str | None = None
