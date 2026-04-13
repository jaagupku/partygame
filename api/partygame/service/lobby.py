import asyncio
import logging

from pydantic import BaseModel
from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.core.config import settings
from partygame.schemas.events import Event
from partygame.utils import get_unique_join_code, publish
from partygame.service.player import remove as remove_player
from partygame.service.game import GameRuntimeService
from . import realtime
from partygame.state import GameStateRepository, GameKeyFactory

log = logging.getLogger(__name__)


async def get_player_ids(redis: Redis, game_id: str, withscores=True) -> list[str]:
    repo = GameStateRepository(redis)
    return await repo.get_player_ids(game_id, withscores=withscores)


async def get_players(redis: Redis, game_id: str):
    repo = GameStateRepository(redis)
    return await repo.get_players(game_id)


async def create(redis: Redis, create_game: schemas.CreateGame | None = None):
    repo = GameStateRepository(redis)
    payload = create_game or schemas.CreateGame()
    lobby = schemas.Lobby(
        join_code=await get_unique_join_code(redis),
        definition_id=payload.definition_id,
        host_enabled=payload.host_enabled,
    )
    await repo.create_lobby(lobby)
    await repo.apply_game_ttl(lobby.id, settings.GAME_IDLE_TTL_SECONDS)
    return lobby


async def get(redis: Redis, game_id: str):
    repo = GameStateRepository(redis)
    lobby = await repo.get_lobby_meta(game_id)
    if lobby is None:
        raise HTTPException(status_code=404, detail="Lobby data not found.")
    lobby.players = await repo.get_players(game_id)
    return lobby


async def get_id_from_join_code(redis: Redis, join_code: str):
    repo = GameStateRepository(redis)
    return await repo.get_game_id_from_join_code(join_code)


class GameController:
    def __init__(self, websocket: WebSocket, redis: Redis, lobby: schemas.Lobby):
        self.websocket = websocket
        self.redis = redis
        self.repo = GameStateRepository(redis)
        self.runtime = GameRuntimeService(self.repo)
        self.lobby = lobby
        self.game_channel = GameKeyFactory.display_channel(self.lobby.id)
        self.send_task: asyncio.Task | None = None
        self.pubsub = None

    async def connect(self):
        await self.websocket.accept()
        realtime.register_display(self.lobby.id, self)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.game_channel)
        self.send_task = asyncio.create_task(self.publish_websocket())
        await self.send(await self.runtime.sync_lobby(self.lobby))

    async def disconnect(self):
        realtime.unregister_display(self.lobby.id, self)
        if self.send_task is not None:
            self.send_task.cancel()
        if self.pubsub is not None:
            await self.pubsub.unsubscribe(self.game_channel)

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

    async def send(self, payload: dict | BaseModel | str):
        if isinstance(payload, schemas.RuntimeSnapshotEvent):
            payload = payload.model_copy(update={"host_answer": None, "submissions": []})
        if isinstance(payload, BaseModel):
            await self.websocket.send_text(payload.model_dump_json())
        elif isinstance(payload, dict):
            await self.websocket.send_json(payload)
        else:
            await self.websocket.send_text(payload)

    async def broadcast(
        self,
        msg: dict | BaseModel | str,
        players: list[str] | None = None,
        exclude: str | None = None,
    ):
        if isinstance(msg, schemas.RuntimeSnapshotEvent):
            msg = msg.model_copy(update={"host_answer": None, "submissions": []})
        if players is None:
            players = await self.repo.get_player_ids(self.lobby.id, withscores=False)
        players = [player_id for player_id in players if player_id]
        await asyncio.gather(
            *[
                publish(self.redis, GameKeyFactory.player_channel(self.lobby.id, player_id), msg)
                for player_id in players
                if player_id != exclude
            ]
        )

    async def broadcast_snapshot(self):
        snapshot = await self.runtime.build_snapshot(self.lobby)
        await self.send(snapshot)
        await self.broadcast(snapshot)

    async def kick_player(self, event: schemas.KickPlayerEvent):
        if self.lobby.host_id == event.player_id:
            return
        await remove_player(self.redis, lobby_id=self.lobby.id, player_id=event.player_id)
        await self.broadcast(event, [event.player_id])
        self.lobby = await get(self.redis, self.lobby.id)
        await self.send(event)
        await self.broadcast_snapshot()

    async def set_host(self, event: schemas.SetHostEvent):
        prev_host = self.lobby.host_id
        self.lobby.host_id = event.player_id
        await self.repo.set_lobby_fields(self.lobby.id, host_id=event.player_id)
        await self.broadcast(event, [prev_host, event.player_id])
        await self.send(event)
        await self.broadcast_snapshot()

    async def process_input(self, msg: dict):
        if "type_" not in msg:
            return
        match msg["type_"]:
            case Event.RESYNC_REQUEST:
                await self.send(await self.runtime.sync_lobby(self.lobby))
            case Event.SET_HOST:
                await self.set_host(schemas.SetHostEvent.model_validate(msg))
            case Event.KICK_PLAYER:
                await self.kick_player(schemas.KickPlayerEvent.model_validate(msg))
