from fastapi import APIRouter

from partygame.api.api_v1.endpoints import lobby, game

api_router = APIRouter()
api_router.include_router(lobby.router, prefix="/lobby", tags=["lobby"])
api_router.include_router(game.router, prefix="/game", tags=["game"])
