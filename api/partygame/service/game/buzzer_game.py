import logging
from typing import List
from uuid import uuid4

from redis.asyncio import Redis

from partygame.service.game.base_class import GameABC
from partygame.service.lobby import GameController
from partygame.schemas.buzzer import BuzzerGameSchema, BuzzerState
from partygame.schemas.events import BuzzerClickedEvent, BuzzerStateEvent, Event

log = logging.getLogger(__name__)


class BuzzerGame(GameABC):
    def __init__(self, *, redis: Redis, lobby: GameController, id_: str, state: BuzzerState, player_id: str):
        self.redis = redis
        self.lobby = lobby
        self.id = id_
        self.state = state
        self.player_id = player_id
    
    def schema(self):
        return BuzzerGameSchema(id=self.id, buzzer_state=self.state, buzzed_player=self.player_id)

    @staticmethod
    def key(id_: str):
        return f"buzzergame.{id_}"

    @staticmethod
    async def load(redis: Redis, lobby: GameController, id_: str):
        schema = BuzzerGameSchema.model_validate(await redis.hgetall(BuzzerGame.key(id_)))
        return BuzzerGame(
            redis=redis,
            lobby=lobby,
            id_=schema.id,
            state=schema.buzzer_state, 
            player_id=schema.buzzed_player
        )
    
    @staticmethod
    async def new(redis: Redis, lobby: GameController):
        game = BuzzerGame(
            redis=redis,
            lobby=lobby,
            id_=uuid4().hex,
            state=BuzzerState.DEACTIVE,
            player_id=""
        )
        await redis.hset(BuzzerGame.key(game.id), mapping=game.schema().model_dump())
        return game
    
    async def activate(self, event=None):
        await self.redis.hset(self.key(self.id), "buzzer_state", BuzzerState.ACTIVE)
        await self.redis.hset(self.key(self.id), "buzzed_player", "")
        self.state = BuzzerState.ACTIVE
        self.player_id = ""

        if event is None:
            event = BuzzerStateEvent(state=self.state)
        
        await self.lobby.send(event)
        await self.lobby.broadcast(event)

    async def deactivate(self, event=None):
        await self.redis.hset(self.key(self.id), "buzzer_state", BuzzerState.DEACTIVE)
        self.state = BuzzerState.DEACTIVE

        if event is None:
            event = BuzzerStateEvent(state=self.state)
        
        await self.lobby.send(event)
        await self.lobby.broadcast(event)
    
    async def press(self, player_id: str):
        await self.redis.hset(self.key(self.id), "buzzed_player", player_id)
        self.player_id = player_id
    
    async def handle(self, event: dict) -> bool:
        log.info(f"Handling event {event['type_']}")
        match event["type_"]:
            case Event.BUZZER_STATE:
                buzzer_state = BuzzerStateEvent.model_validate(event)
                if buzzer_state.state == BuzzerState.ACTIVE:
                    await self.activate()
                else:
                    await self.deactivate()
                return True
            case Event.BUZZER_CLICKED:
                buzzer_clicked = BuzzerClickedEvent.model_validate(event)
                await self.deactivate()
                await self.press(buzzer_clicked.player_id)
                await self.lobby.send(event)
                return True
        return False

    async def broadcast_state_controller(self, players=None):
        buzzer_state = BuzzerStateEvent(state=self.state)
        if players is not None:
            await self.lobby.broadcast(buzzer_state, players)

    async def broadcast_state_host(self):
        buzzer_state = BuzzerStateEvent(state=self.state)
        if self.player_id:
            player_clicked = BuzzerClickedEvent(player_id=self.player_id)
            await self.lobby.send(player_clicked)
        await self.lobby.send(buzzer_state)
