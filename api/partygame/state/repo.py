import json
from collections.abc import Iterable

from redis.asyncio import Redis

from partygame import schemas
from partygame.state.keys import GameKeyFactory


class GameStateRepository:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def reserve_join_code(self, join_code: str, game_id: str):
        await self.redis.set(GameKeyFactory.join_code(join_code), game_id)

    async def get_game_id_from_join_code(self, join_code: str) -> str | None:
        return await self.redis.get(GameKeyFactory.join_code(join_code))

    async def create_lobby(self, lobby: schemas.Lobby):
        await self.reserve_join_code(lobby.join_code, lobby.id)
        meta = lobby.model_dump(mode="json", exclude={"players"}, exclude_none=True)
        meta.setdefault("definition_id", "quiz_demo")
        meta.setdefault("current_step", 0)
        meta.setdefault("phase", "waiting")
        await self.redis.hset(GameKeyFactory.game_meta(lobby.id), mapping=meta)

    async def lobby_exists(self, game_id: str) -> bool:
        return await self.redis.hexists(GameKeyFactory.game_meta(game_id), "id")

    async def get_lobby_meta(self, game_id: str) -> schemas.Lobby | None:
        data = await self.redis.hgetall(GameKeyFactory.game_meta(game_id))
        if not data:
            return None
        filtered = {
            key: data[key]
            for key in (
                "id",
                "join_code",
                "host_id",
                "state",
                "connection",
                "active_game",
                "definition_id",
                "current_step",
                "phase",
            )
            if key in data
        }
        return schemas.Lobby.model_validate(filtered)

    async def set_lobby_fields(self, game_id: str, **fields):
        update_fields = {k: str(v) for k, v in fields.items() if v is not None}
        if update_fields:
            await self.redis.hset(GameKeyFactory.game_meta(game_id), mapping=update_fields)

    async def get_player_ids(self, game_id: str, withscores: bool = True):
        return await self.redis.zrange(
            GameKeyFactory.game_scores(game_id), 0, -1, withscores=withscores
        )

    async def create_player(self, player: schemas.Player):
        key = GameKeyFactory.game_player(player.game_id, player.id)
        await self.redis.hset(
            key,
            mapping=player.model_dump(mode="json", exclude={"score"}, exclude_none=True),
        )
        await self.redis.zadd(
            GameKeyFactory.game_scores(player.game_id), mapping={player.id: player.score}
        )

    async def get_player(self, game_id: str, player_id: str) -> schemas.Player | None:
        key = GameKeyFactory.game_player(game_id, player_id)
        if not await self.redis.hexists(key, "name"):
            return None
        player = schemas.Player.model_validate(await self.redis.hgetall(key))
        score = await self.redis.zscore(GameKeyFactory.game_scores(game_id), player_id)
        player.score = int(score or 0)
        return player

    async def get_players(self, game_id: str) -> list[schemas.Player]:
        player_ids = await self.get_player_ids(game_id)
        players = []
        for player_id, score in player_ids:
            player_data = await self.redis.hgetall(GameKeyFactory.game_player(game_id, player_id))
            if not player_data:
                continue
            player = schemas.Player.model_validate(player_data)
            player.score = int(score)
            players.append(player)
        return players

    async def remove_player(self, game_id: str, player_id: str):
        await self.redis.zrem(GameKeyFactory.game_scores(game_id), player_id)
        await self.redis.delete(GameKeyFactory.game_player(game_id, player_id))

    async def set_player_status(
        self,
        game_id: str,
        player_id: str,
        status: schemas.ConnectionStatus,
    ):
        await self.redis.hset(GameKeyFactory.game_player(game_id, player_id), "status", str(status))

    async def get_player_score(self, game_id: str, player_id: str) -> int:
        score = await self.redis.zscore(GameKeyFactory.game_scores(game_id), player_id)
        return int(score or 0)

    async def set_player_score(self, game_id: str, player_id: str, score: int):
        await self.redis.zadd(GameKeyFactory.game_scores(game_id), mapping={player_id: score})

    async def set_component_state(
        self,
        game_id: str,
        component_id: str,
        fields: dict,
    ):
        serialized = {}
        for key, value in fields.items():
            if isinstance(value, (dict, list)):
                serialized[key] = json.dumps(value)
            elif value is None:
                serialized[key] = ""
            else:
                serialized[key] = str(value)
        await self.redis.hset(
            GameKeyFactory.game_component(game_id, component_id), mapping=serialized
        )

    async def get_component_state(self, game_id: str, component_id: str) -> dict:
        data = await self.redis.hgetall(GameKeyFactory.game_component(game_id, component_id))
        if not data:
            return {}

        decoded = {}
        for key, value in data.items():
            if isinstance(value, str) and value and value[0] in "[{":
                try:
                    decoded[key] = json.loads(value)
                except json.JSONDecodeError:
                    decoded[key] = value
            else:
                decoded[key] = value
        return decoded

    async def delete_component(self, game_id: str, component_id: str):
        await self.redis.delete(GameKeyFactory.game_component(game_id, component_id))

    async def set_step_cache(self, game_id: str, fields: dict):
        await self.redis.hset(GameKeyFactory.game_steps(game_id), mapping=fields)

    async def get_step_cache(self, game_id: str) -> dict:
        return await self.redis.hgetall(GameKeyFactory.game_steps(game_id))

    async def publish_many(
        self,
        channel_payloads: Iterable[tuple[str, str]],
    ):
        async with self.redis.pipeline(transaction=False) as pipe:
            for channel, payload in channel_payloads:
                pipe.publish(channel, payload)
            await pipe.execute()
