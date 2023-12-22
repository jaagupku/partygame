import asyncio
import logging

from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.schemas.events import Event
from partygame.schemas import Lobby, Player, ConnectionStatus
from partygame.utils import publish

log = logging.getLogger(__name__)


def player_channel(game_id: str, player_id: str):
    return f"game.{game_id}.{player_id}"


async def remove(
    redis: Redis,
    *,
    lobby_id: str,
    player_id: str,
):
    await redis.zrem(f"scores.{lobby_id}", player_id)
    await redis.delete(f"player.{player_id}")


async def create(
    redis: Redis,
    *,
    join_request: schemas.JoinRequest,
    game_id: str,
):
    player = Player(
        name=join_request.player_name,
        game_id=game_id,
    )
    await redis.hset(
        f"player.{player.id}",
        mapping=player.model_dump(exclude={"score"}, exclude_none=True),
    )
    await redis.zadd(f"scores.{game_id}", mapping={player.id: player.score})
    await publish(
        redis, f"game.{game_id}.host", schemas.PlayerJoinedEvent(player=player)
    )
    return player


async def get(redis: Redis, player_id: str):
    if await redis.hexists(f"player.{player_id}", "name"):
        player = Player.model_validate(await redis.hgetall(f"player.{player_id}"))
        player.score = await redis.zscore(f"scores.{player.game_id}", player_id)
        return player
    raise HTTPException(status_code=404, detail="Player data not found.")


class ClientController:
    def __init__(
        self, websocket: WebSocket, redis: Redis, lobby: Lobby, player: Player
    ):
        self.websocket = websocket
        self.redis = redis
        self.lobby = lobby
        self.player = player

        self.game_channel = f"game.{self.lobby.id}.host"
        self.player_channel = player_channel(self.lobby.id, self.player.id)
        self.player_key = f"player.{self.player.id}"

    async def connect(self):
        await self.websocket.accept()
        self.player.status = ConnectionStatus.CONNECTED
        await self.redis.hset(self.player_key, "status", self.player.status)
        await publish(
            self.redis,
            self.game_channel,
            schemas.PlayerConnectedEvent(player_id=self.player.id),
        )

        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.player_channel)
        self.send_task = asyncio.create_task(self.publish_websocket())

    async def disconnect(self):
        if self.send_task is not None:
            self.send_task.cancel()
        if self.pubsub is not None:
            await self.pubsub.unsubscribe(self.player_channel)

        self.player.status = ConnectionStatus.DISCONNECTED
        await self.redis.hset(self.player_key, "status", self.player.status)
        await publish(
            self.redis,
            self.game_channel,
            schemas.PlayerDisconnectedEvent(player_id=self.player.id),
        )

    async def publish_websocket(self):
        while True:
            message = await self.pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1
            )
            if message is None:
                continue
            if message["type"] == "message":
                await self.websocket.send_text(message["data"])

    async def process_input(self, msg: dict):
        match msg["type_"]:
            case _:
                await publish(
                    self.redis, self.game_channel, msg
                )
