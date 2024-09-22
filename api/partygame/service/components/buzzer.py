import logging
from uuid import uuid4
from enum import StrEnum, auto

from redis.asyncio import Redis

from partygame.service.components.base_class import ComponentABC
from partygame.service.lobby import GameController
from partygame.schemas.events import (
    BaseEvent,
    Event,
    UpadteScoreEvent,
)
from partygame.schemas.lobby import (
    ControllerComponent,
    BaseComponent,
    ComponentSpec,
    ComponentType,
)

log = logging.getLogger(__name__)


class BuzzerState(StrEnum):
    ACTIVE = auto()
    DEACTIVE = auto()


class BuzzerGameSchema(BaseComponent):
    type_: str = ControllerComponent.BUZZER_GAME
    id: str
    buzzer_state: BuzzerState
    buzzed_player: str


class BuzzerStateEvent(BaseEvent):
    type_: str = Event.BUZZER_STATE
    state: BuzzerState


class BuzzerClickedEvent(BaseEvent):
    type_: str = Event.BUZZER_CLICKED
    player_id: str


class BuzzerComponent(ComponentABC):
    def __init__(
        self,
        *,
        redis: Redis,
        controller: GameController,
        id_: str,
        state: BuzzerState,
        player_id: str,
    ):
        self.redis = redis
        self.controller = controller
        self.id = id_
        self.state = state
        self.player_id = player_id

    def schema(self):
        return BuzzerGameSchema(
            id=self.id, buzzer_state=self.state, buzzed_player=self.player_id
        )

    @staticmethod
    def key(id_: str):
        return f"buzzergame:{id_}"

    @staticmethod
    async def load(redis: Redis, controller: GameController, id_: str):
        schema = BuzzerGameSchema.model_validate(
            await redis.hgetall(BuzzerComponent.key(id_))
        )
        return BuzzerComponent(
            redis=redis,
            controller=controller,
            id_=schema.id,
            state=schema.buzzer_state,
            player_id=schema.buzzed_player,
        )

    @staticmethod
    async def new(redis: Redis, controller: GameController):
        game = BuzzerComponent(
            redis=redis,
            controller=controller,
            id_=uuid4().hex,
            state=BuzzerState.DEACTIVE,
            player_id="",
        )
        await redis.hset(
            BuzzerComponent.key(game.id), mapping=game.schema().model_dump()
        )
        return game

    async def delete(self):
        await self.redis.delete(self.key(self.id))

    async def activate(self, event=None):
        await self.redis.hset(self.key(self.id), "buzzer_state", BuzzerState.ACTIVE)
        await self.redis.hset(self.key(self.id), "buzzed_player", "")
        self.state = BuzzerState.ACTIVE
        self.player_id = ""

        if event is None:
            event = BuzzerStateEvent(state=self.state)

        await self.controller.send(event)
        await self.controller.broadcast(event)

    async def deactivate(self, event=None):
        await self.redis.hset(self.key(self.id), "buzzer_state", BuzzerState.DEACTIVE)
        self.state = BuzzerState.DEACTIVE

        if event is None:
            event = BuzzerStateEvent(state=self.state)

        await self.controller.send(event)
        await self.controller.broadcast(event)

    async def press(self, event: BuzzerClickedEvent):
        await self.redis.hset(self.key(self.id), "buzzed_player", event.player_id)
        self.player_id = event.player_id
        await self.controller.send(event)
        await self.controller.broadcast(event, [self.controller.lobby.host_id])

    async def update_score(self, event: UpadteScoreEvent):
        if event.set_score is not None:
            score = event.set_score
        else:
            score = int(await self.controller.get_player_score(event.player_id))
            score += event.add_score
        await self.controller.set_player_score(event.player_id, score)

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
                await self.press(buzzer_clicked)
                return True
            case Event.UPDATE_SCORE:
                update_score = UpadteScoreEvent.model_validate(event)
                await self.update_score(update_score)
                return True
        return False

    async def broadcast_state_controller(self, players=None, is_host=False):
        if players is not None:
            buzzer_state = BuzzerStateEvent(state=self.state)
            await self.controller.broadcast(buzzer_state, players)
        if is_host:
            player_clicked = BuzzerClickedEvent(player_id=self.player_id)
            await self.controller.broadcast(player_clicked)

    async def broadcast_state_host(self):
        buzzer_state = BuzzerStateEvent(state=self.state)
        if self.player_id:
            player_clicked = BuzzerClickedEvent(player_id=self.player_id)
            await self.controller.send(player_clicked)
        await self.controller.send(buzzer_state)
