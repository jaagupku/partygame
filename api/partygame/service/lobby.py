import json
import logging
import asyncio

from pydantic import BaseModel
from redis.asyncio import Redis
from fastapi import HTTPException, WebSocket

from partygame import schemas
from partygame.schemas.events import Event
from partygame.utils import get_unique_join_code, publish
from partygame.service.player import remove as remove_player
from partygame.service.components import init_game, load_game, ComponentABC
from partygame.service.game import GameRuntimeService
from partygame.state import GameStateRepository, GameKeyFactory

log = logging.getLogger(__name__)


async def get_player_ids(redis: Redis, game_id: str, withscores=True) -> list[str]:
    repo = GameStateRepository(redis)
    return await repo.get_player_ids(game_id, withscores=withscores)


async def get_players(redis: Redis, game_id: str):
    repo = GameStateRepository(redis)
    return await repo.get_players(game_id)


async def create(redis: Redis):
    repo = GameStateRepository(redis)
    lobby = schemas.Lobby(
        join_code=await get_unique_join_code(redis),
    )
    await repo.create_lobby(lobby)
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

        self.game_channel = GameKeyFactory.host_channel(self.lobby.id)

        from partygame.service.components.empty import EmptyComponent

        self.controller_component: ComponentABC = EmptyComponent()
        self.display_component: ComponentABC = EmptyComponent()

    async def connect(self):
        await self.websocket.accept()
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.game_channel)
        self.send_task = asyncio.create_task(self.publish_websocket())

        if self.lobby.active_game is not None:
            self.controller_component = await load_game(
                self.repo,
                self,
                schemas.ControllerComponent.BUZZER_GAME,
                self.lobby.id,
                self.lobby.active_game,
            )
            await self.controller_component.broadcast_state_host()

    async def disconnect(self):
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
                    await self.process_controller(message["data"])
        except Exception as error:
            log.error(error)

    async def send(self, payload: dict | BaseModel | str):
        if isinstance(payload, BaseModel):
            await self.websocket.send_text(payload.model_dump_json())
        elif isinstance(payload, dict):
            await self.websocket.send_json(payload)
        else:
            await self.websocket.send_text(payload)

    async def get_player_score(self, player_id: str) -> int:
        return await self.repo.get_player_score(self.lobby.id, player_id)

    async def set_player_score(self, player_id: str, score: int):
        await self.repo.set_player_score(self.lobby.id, player_id, score)
        event = schemas.UpdateScoreEvent(player_id=player_id, set_score=score)
        await self.send(event)
        await self.broadcast(event, [player_id])

    async def broadcast(
        self,
        msg: dict | BaseModel | str,
        players: list[str] | None = None,
        exclude: str | None = None,
    ):
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

    async def kick_player(self, event: schemas.KickPlayerEvent):
        if self.lobby.host_id == event.player_id:
            return
        await remove_player(self.redis, lobby_id=self.lobby.id, player_id=event.player_id)
        await self.broadcast(event, [event.player_id])
        self.lobby = await get(self.redis, self.lobby.id)
        await self.send(event)

    async def set_host(self, event: schemas.SetHostEvent):
        prev_host = self.lobby.host_id
        self.lobby.host_id = event.player_id
        await self.repo.set_lobby_fields(self.lobby.id, host_id=event.player_id)
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
            case _:
                await publish(self.redis, self.game_channel, msg)

    async def activate_game(self, game_type: schemas.ControllerComponent):
        self.controller_component = await init_game(self.repo, self, game_type, self.lobby.id)
        self.lobby.active_game = self.controller_component.id
        await self.repo.set_lobby_fields(self.lobby.id, active_game=self.lobby.active_game)

    async def start_game(self):
        self.lobby, step = await self.runtime.start_game(self.lobby)
        await self.activate_game(schemas.ControllerComponent.BUZZER_GAME)

        if step is not None:
            component_events = await self.runtime.activate_step_components(self.lobby.id, step)
            for event in component_events:
                await self.send(event)
                await self.broadcast(event)

        await self.controller_component.broadcast_state_controller(
            [player.id for player in self.lobby.players]
        )
        await self.display_component.broadcast_state_host()

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
                await self.websocket.send_text(msg)
                await self.broadcast(msg)
                await self.start_game()
            case Event.PLAYER_CONNECTED:
                event = schemas.PlayerConnectedEvent.model_validate(data)
                await self.controller_component.broadcast_state_controller(
                    [event.player_id], self.lobby.host_id == event.player_id
                )
                await self.websocket.send_text(msg)
            case _:
                runtime_events, handled = await self.runtime.handle_runtime_event(self.lobby, data)
                if handled:
                    for event in runtime_events:
                        await self.send(event)
                        await self.broadcast(event)
                    return
                if await self.controller_component.handle(data):
                    return
                if await self.display_component.handle(data):
                    return
                await self.websocket.send_text(msg)
