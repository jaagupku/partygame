from fastapi import APIRouter

from partygame.api.api_v1.endpoints import lobby

api_router = APIRouter()
api_router.include_router(lobby.router, prefix="/lobby", tags=["lobby"])