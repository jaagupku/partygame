from redis.asyncio import Redis
from fastapi import APIRouter, Depends, WebSocket, HTTPException

from partygame import schemas
from partygame.api import deps
from partygame.utils import get_unique_join_code

router = APIRouter()


@router.post("/join", response_model=schemas.ConnectedToLobby)
async def join_lobby(
    *,
    redis: Redis = Depends(deps.get_redis),
    join_request: schemas.JoinRequest
):
    game_id = await redis.get(f"join.{join_request.join_code}")
    if game_id is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if join_request.player_id is not None:
        if await redis.hexists(f"player.{join_request.player_id}", "name"):
            joined_player = schemas.Player.model_validate(await redis.hgetall(f"player.{join_request.player_id}"))
        else:
            raise HTTPException(status_code=404, detail="Reconnect failed. Player data not found.")
    else:
        joined_player = schemas.Player(
            name=join_request.player_name,
        )
        await redis.hset(f"player.{joined_player.id}", mapping=joined_player.model_dump(exclude={"score"}))
        await redis.zadd(f"scores.{game_id}", mapping={joined_player.id: joined_player.score})

    player_ids = await redis.zrange(f"scores.{game_id}", 0, -1, withscores=True)
    players = []
    for id_, score in player_ids:
        player = schemas.Player.model_validate(await redis.hgetall(f"player.{id_}"))
        player.score = int(score)
        players.append(player)

    lobby = schemas.Lobby(
        id=game_id,
        join_code=join_request.join_code,
        players=players
    )
    return schemas.ConnectedToLobby(player=joined_player, lobby=lobby)


@router.post("/create", response_model=schemas.Lobby)
async def create_lobby(
    *,
    redis: Redis = Depends(deps.get_redis),
):
    lobby = schemas.Lobby(
        join_code=await get_unique_join_code(redis),
    )
    await redis.set(f"join.{lobby.join_code}", lobby.id)
    return lobby


@router.websocket("/session")
async def game_websocket(
    websocket: WebSocket,
    id: int,
    redis: Redis = Depends(deps.get_redis)
):
    ...
