from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel


class GameType(BaseModel):
    id: str
    localization_key: str
    availability: Literal["available", "coming_soon"]
    host_modes: tuple[Literal["hosted", "automatic"], ...]


GAME_TYPES = (
    GameType(
        id="trivia",
        localization_key="trivia",
        availability="available",
        host_modes=("hosted", "automatic"),
    ),
    GameType(
        id="price_guessing",
        localization_key="priceGuessing",
        availability="available",
        host_modes=("hosted", "automatic"),
    ),
)


def require_game_type(game_type: str, *, host_enabled: bool) -> GameType:
    entry = next((entry for entry in GAME_TYPES if entry.id == game_type), None)
    if entry is None:
        raise HTTPException(status_code=422, detail="Unknown game type")
    if entry.availability != "available":
        raise HTTPException(status_code=422, detail="Game type is not available")
    mode = "hosted" if host_enabled else "automatic"
    if mode not in entry.host_modes:
        raise HTTPException(status_code=422, detail="Host mode is not supported")
    return entry
