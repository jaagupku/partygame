from redis.asyncio import Redis
from fastapi import HTTPException

from partygame import schemas
from partygame.utils import get_unique_join_code


async def get_players(redis: Redis, game_id: str):
    player_ids = await redis.zrange(f"scores.{game_id}", 0, -1, withscores=True)
    players = []
    for id_, score in player_ids:
        player = schemas.Player.model_validate(await redis.hgetall(f"player.{id_}"))
        player.score = int(score)
        players.append(player)
    return players


async def create(redis: Redis):
    lobby = schemas.Lobby(
        join_code=await get_unique_join_code(redis),
    )
    await redis.set(f"join.{lobby.join_code}", lobby.id)
    await redis.hset(f"lobby.{lobby.id}", mapping=lobby.model_dump(exclude={"players"}, exclude_none=True))
    return lobby


async def get(redis: Redis, game_id: str):
    if await redis.hexists(f"lobby.{game_id}", "id"):
        lobby = schemas.Lobby.model_validate(await redis.hgetall(f"lobby.{game_id}"))
        lobby.players = await get_players(redis, game_id)
        return lobby
    raise HTTPException(status_code=404, detail="Lobby data not found.")


async def get_id(redis: Redis, join_code: str):
    return await redis.get(f"join.{join_code}")


class GameController:
    def __init__(self, redis: Redis, lobby: schemas.Lobby):
        self.redis = redis
        self.lobby = lobby
