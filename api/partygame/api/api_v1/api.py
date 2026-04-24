from fastapi import APIRouter

from partygame.api.api_v1.endpoints import auth, definitions, game, lobby, media

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(lobby.router, prefix="/lobby", tags=["lobby"])
api_router.include_router(game.router, prefix="/game", tags=["game"])
api_router.include_router(definitions.router, prefix="/definitions", tags=["definitions"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
