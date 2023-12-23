import json
import logging
import asyncio

from pydantic import BaseModel
from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.schemas.events import Event
from partygame.utils import get_unique_join_code, publish
from partygame.service.player import player_channel, remove as remove_player
from partygame.service.game import init_game, load_game, GameABC

log = logging.getLogger(__name__)


async def get_player_ids(redis: Redis, game_id: str, withscores=True):
    return await redis.zrange(f"scores.{game_id}", 0, -1, withscores=withscores)


async def get_players(redis: Redis, game_id: str):
    player_ids = await get_player_ids(redis, game_id)
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
    await redis.hset(
        f"lobby.{lobby.id}",
        mapping=lobby.model_dump(exclude={"players"}, exclude_none=True),
    )
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
    def __init__(self, websocket: WebSocket, redis: Redis, lobby: schemas.Lobby):
        self.websocket = websocket
        self.redis = redis
        self.lobby = lobby

        self.game_channel = f"game.{self.lobby.id}.host"
        self.hkey = f"lobby.{self.lobby.id}"
        self.running_game: GameABC | None = None

    async def connect(self):
        await self.websocket.accept()
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.game_channel)
        self.send_task = asyncio.create_task(self.publish_websocket())

        if self.lobby.active_game is not None:
            self.running_game = await load_game(
                self.redis, self, schemas.GameType.BUZZER_GAME, self.lobby.active_game
            )
            await self.running_game.broadcast_state_host()
        # Game Running

    async def disconnect(self):
        if self.send_task is not None:
            self.send_task.cancel()
        if self.pubsub is not None:
            await self.pubsub.unsubscribe(self.game_channel)
        # Game Paused

    async def publish_websocket(self):
        try:
            while True:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1
                )
                if message is None:
                    continue
                if message["type"] == "message":
                    await self.process_controller(message["data"])
        except Exception as e:
            log.error(e)

    async def send(self, payload: dict | BaseModel | str):
        if isinstance(payload, BaseModel):
            await self.websocket.send_text(payload.model_dump_json())
        elif isinstance(payload, dict):
            await self.websocket.send_json(payload)
        else:
            await self.websocket.send_text(payload)

    async def get_player_score(self, player_id: str) -> int:
        return await self.redis.zscore(f"scores.{self.lobby.id}", player_id)

    async def set_player_score(self, player_id: str, score: int):
        await self.redis.zadd(f"scores.{self.lobby.id}", mapping={player_id: score})
        event = schemas.UpadteScoreEvent(player_id=player_id, set_score=score)
        await self.send(event)
        await self.broadcast(event, [player_id])

    async def broadcast(self, msg: dict | BaseModel | str, players=None):
        if players is None:
            players = await get_player_ids(self.redis, self.lobby.id, withscores=False)
        await asyncio.gather(
            *[
                publish(self.redis, player_channel(self.lobby.id, player_id), msg)
                for player_id in players
            ]
        )

    async def kick_player(self, event: schemas.KickPlayerEvent):
        if self.lobby.host_id == event.player_id:
            return
        await remove_player(
            self.redis, lobby_id=self.lobby.id, player_id=event.player_id
        )
        await self.broadcast(event, [event.player_id])
        self.lobby = await get(self.redis, self.lobby.id)
        await self.send(event)

    async def set_host(self, event: schemas.SetHostEvent):
        prev_host = self.lobby.host_id
        self.lobby.host_id = event.player_id
        await self.redis.hset(f"lobby.{self.lobby.id}", "host_id", event.player_id)
        await self.broadcast(event, [prev_host, event.player_id])
        await self.send(event)

    async def process_input(self, msg: dict):
        if "type_" not in msg:
            return
        match msg["type_"]:
            case Event.SET_HOST:
                await self.set_host(schemas.SetHostEvent.model_validate(msg))
            case Event.KICK_PLAYER:
                await self.kick_player(schemas.KickPlayerEvent.model_validate(msg))

    async def activate_game(self, game_type: schemas.GameType):
        self.running_game = await init_game(self.redis, self, game_type)
        self.lobby.active_game = self.running_game.id
        await self.redis.hset(
            f"lobby.{self.lobby.id}", "active_game", self.running_game.id
        )

    async def process_controller(self, msg: str):
        data = json.loads(msg)
        match data["type_"]:
            case Event.PLAYER_JOINED:
                await self.websocket.send_text(msg)
                self.lobby = await get(self.redis, self.lobby.id)
                if len(self.lobby.players) == 1:
                    event = schemas.PlayerJoinedEvent.model_validate(data)
                    await self.set_host(schemas.SetHostEvent(player_id=event.player.id))
            case Event.START_GAME:
                # TODO: Check that this comes from host
                await self.websocket.send_text(msg)
                await self.redis.hset(self.hkey, "state", schemas.GameState.RUNNING)
                self.lobby.state = schemas.GameState.RUNNING

                await self.activate_game(schemas.GameType.BUZZER_GAME)

                await self.broadcast(msg)
            case Event.PLAYER_CONNECTED:
                if self.running_game is not None:
                    event = schemas.PlayerConnectedEvent.model_validate(data)
                    await self.running_game.broadcast_state_controller(
                        [event.player_id], self.lobby.host_id == event.player_id
                    )
                await self.websocket.send_text(msg)
            case _:
                is_handled = False
                if self.running_game is not None:
                    is_handled = await self.running_game.handle(data)

                if not is_handled:
                    await self.websocket.send_text(msg)
