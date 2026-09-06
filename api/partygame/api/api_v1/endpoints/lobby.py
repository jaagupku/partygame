from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis.asyncio import Redis

from partygame import schemas, service
from partygame.api import deps
from partygame.service.connection_access import connection_cookie_name, set_connection_cookie
from partygame.state import GameStateRepository

if TYPE_CHECKING:
    from partygame.state.auth_models import UserRecord

router = APIRouter()


@router.get("/join-code/{join_code}", response_model=schemas.Lobby)
async def get_lobby_by_join_code(join_code: str, *, redis: Redis = Depends(deps.get_redis)):
    game_id = await service.lobby.get_id_from_join_code(redis, join_code.upper())
    if game_id is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return await service.lobby.get(redis, game_id)


@router.get("/{game_id}/access")
async def get_lobby_access(game_id: str, request: Request, redis: Redis = Depends(deps.get_redis)):
    return {
        "can_manage": await GameStateRepository(redis).verify_connection_token(
            game_id, request.cookies.get(connection_cookie_name(game_id))
        )
    }


@router.get("/{game_id}", response_model=schemas.Lobby)
async def get_lobby(game_id: str, *, redis: Redis = Depends(deps.get_redis)):
    return await service.lobby.get(redis, game_id)


@router.post("/join", response_model=schemas.ConnectedToLobby)
async def join_lobby(
    request: Request,
    response: Response,
    *,
    redis: Redis = Depends(deps.get_redis),
    join_request: schemas.JoinRequest,
):
    game_id = await service.lobby.get_id_from_join_code(redis, join_request.join_code.upper())
    if game_id is None:
        raise HTTPException(status_code=404, detail="Game not found")

    lobby = await service.lobby.get(redis, game_id)
    joined_player = None

    if join_request.player_id is not None:
        try:
            joined_player = await service.player.get(redis, lobby.id, join_request.player_id)
        except HTTPException as error:
            if error.status_code != 404:
                raise

    repo = GameStateRepository(redis)
    if joined_player is not None and not await repo.verify_connection_token(
        game_id, request.cookies.get(connection_cookie_name(game_id, player=True)), joined_player.id
    ):
        raise HTTPException(
            status_code=403, detail="Player connection does not belong to this browser"
        )

    if joined_player is None:
        if lobby.state != schemas.lobby.GameState.WAITING_FOR_PLAYERS:
            raise HTTPException(status_code=403, detail="Game already started")
        joined_player = await service.player.create(
            redis,
            join_request=join_request,
            game_id=game_id,
        )

        token = await repo.issue_connection_token(game_id, joined_player.id)
        set_connection_cookie(response, request, game_id, token, player=True)

    return schemas.ConnectedToLobby(player=joined_player, lobby=lobby)


@router.post("/create", response_model=schemas.Lobby)
async def create_lobby(
    request: Request,
    response: Response,
    *,
    redis: Redis = Depends(deps.get_redis),
    current_user: UserRecord | None = Depends(deps.get_current_user_optional),
    # FastAPI copies this body default for each request.
    create_game: schemas.CreateGame = schemas.CreateGame(),  # noqa: B008
):
    lobby = await service.lobby.create(redis, create_game, current_user)
    token = await GameStateRepository(redis).issue_connection_token(lobby.id)
    set_connection_cookie(response, request, lobby.id, token)
    return lobby
