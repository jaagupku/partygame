import asyncio
import logging

from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.schemas import Lobby, Player, ConnectionStatus
from partygame.utils import publish
from partygame.state import GameStateRepository, GameKeyFactory

log = logging.getLogger(__name__)


def score_key(lobby_id: str) -> str:
    return GameKeyFactory.game_scores(lobby_id)


def player_channel(game_id: str, player_id: str) -> str:
    return GameKeyFactory.player_channel(game_id, player_id)


def key(game_id: str, player_id: str) -> str:
    return GameKeyFactory.game_player(game_id, player_id)


async def remove(
    redis: Redis,
    *,
    lobby_id: str,
    player_id: str,
):
    repo = GameStateRepository(redis)
    await repo.remove_player(lobby_id, player_id)


async def create(
    redis: Redis,
    *,
    join_request: schemas.JoinRequest,
    game_id: str,
):
    repo = GameStateRepository(redis)
    player = Player(
        name=join_request.player_name,
        game_id=game_id,
    )
    await repo.create_player(player)
    await publish(
        redis, GameKeyFactory.host_channel(game_id), schemas.PlayerJoinedEvent(player=player)
    )
    return player


async def get(redis: Redis, game_id: str, player_id: str):
    repo = GameStateRepository(redis)
    player = await repo.get_player(game_id, player_id)
    if player is not None:
        return player
    raise HTTPException(status_code=404, detail="Player data not found.")


class ClientController:
    def __init__(self, websocket: WebSocket, redis: Redis, lobby: Lobby, player: Player):
        self.websocket = websocket
        self.redis = redis
        self.repo = GameStateRepository(redis)
        self.lobby = lobby
        self.player = player

        self.game_channel = GameKeyFactory.host_channel(self.lobby.id)
        self.player_channel = player_channel(self.lobby.id, self.player.id)

    async def connect(self):
        await self.websocket.accept()
        self.player.status = ConnectionStatus.CONNECTED
        await self.repo.set_player_status(self.lobby.id, self.player.id, self.player.status)
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
        await self.repo.set_player_status(self.lobby.id, self.player.id, self.player.status)
        await publish(
            self.redis,
            self.game_channel,
            schemas.PlayerDisconnectedEvent(player_id=self.player.id),
        )

    async def publish_websocket(self):
        try:
            while True:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                if message is None:
                    continue
                if message["type"] == "message":
                    await self.websocket.send_text(message["data"])
        except Exception as error:
            log.error(error)

    async def process_input(self, msg: dict):
        match msg["type_"]:
            case _:
                await publish(self.redis, self.game_channel, msg)
