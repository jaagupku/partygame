from fastapi import Request, Response

from partygame.core.config import settings


def connection_cookie_name(game_id: str, *, player: bool = False) -> str:
    return f"partygame_{'player' if player else 'display'}_{game_id}"


def set_connection_cookie(
    response: Response, request: Request, game_id: str, token: str, *, player: bool = False
):
    response.set_cookie(
        connection_cookie_name(game_id, player=player),
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=settings.SESSION_TTL_SECONDS,
        path="/api/v1",
    )
