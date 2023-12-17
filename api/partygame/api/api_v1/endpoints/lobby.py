from redis.asyncio import Redis
from fastapi import APIRouter, Depends, HTTPException

from partygame import schemas, service
from partygame.api import deps

router = APIRouter()


@router.get("/{game_id}", response_model=schemas.Lobby)
async def get_lobby(
    game_id: str,
    *,
    redis: Redis = Depends(deps.get_redis)
):
    return await service.lobby.get(redis, game_id)


@router.post("/join", response_model=schemas.ConnectedToLobby)
async def join_lobby(
    *,
    redis: Redis = Depends(deps.get_redis),
    join_request: schemas.JoinRequest
):
    game_id = await service.lobby.get_id(redis, join_request.join_code)
    if game_id is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if join_request.player_id is not None:
        joined_player = await service.player.get(redis, join_request.player_id)
    else:
        joined_player = await service.player.create(
            redis,
            join_request=join_request,
            game_id=game_id,
        )

    lobby = await service.lobby.get(redis, game_id)
    return schemas.ConnectedToLobby(player=joined_player, lobby=lobby)


@router.post("/create", response_model=schemas.Lobby)
async def create_lobby(
    *,
    redis: Redis = Depends(deps.get_redis),
):
    return await service.lobby.create(redis)
