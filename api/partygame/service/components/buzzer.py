import logging
from time import time
from uuid import uuid4
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from partygame.service.components.base_class import ComponentABC
from partygame.schemas.events import (
    BaseEvent,
    Event,
    UpdateScoreEvent,
    ComponentStateUpdatedEvent,
)
from partygame.schemas.lobby import ControllerComponent, BaseComponent
from partygame.state import GameStateRepository

if TYPE_CHECKING:
    from partygame.service.lobby import GameController

log = logging.getLogger(__name__)


class BuzzerState(StrEnum):
    ACTIVE = auto()
    DEACTIVE = auto()


class BuzzerGameSchema(BaseComponent):
    type_: str = ControllerComponent.BUZZER_GAME
    id: str
    buzzer_state: BuzzerState
    buzzed_player: str
    player_disabled_until: float


class BuzzerStateEvent(BaseEvent):
    type_: str = Event.BUZZER_STATE
    state: BuzzerState
    disable_activator: bool = False


class BuzzerClickedEvent(BaseEvent):
    type_: str = Event.BUZZER_CLICKED
    player_id: str


class BuzzerComponent(ComponentABC):
    component_type = ControllerComponent.BUZZER_GAME

    def __init__(
        self,
        *,
        repo: GameStateRepository,
        controller: "GameController",
        game_id: str,
        id_: str,
        state: BuzzerState,
        player_id: str,
        player_disabled_until: float,
    ):
        self.repo = repo
        self.controller = controller
        self.game_id = game_id
        self.id = id_
        self.state = state
        self.player_id = player_id
        self.player_disabled_until = player_disabled_until

    def schema(self):
        return BuzzerGameSchema(
            id=self.id,
            buzzer_state=self.state,
            buzzed_player=self.player_id,
            player_disabled_until=self.player_disabled_until,
        )

    @classmethod
    async def load(
        cls,
        repo: GameStateRepository,
        controller: "GameController",
        game_id: str,
        component_id: str,
    ):
        state = await repo.get_component_state(game_id, component_id)
        schema = BuzzerGameSchema.model_validate(state)
        return cls(
            repo=repo,
            controller=controller,
            game_id=game_id,
            id_=schema.id,
            state=schema.buzzer_state,
            player_id=schema.buzzed_player,
            player_disabled_until=schema.player_disabled_until,
        )

    @classmethod
    async def new(
        cls,
        repo: GameStateRepository,
        controller: "GameController",
        game_id: str,
    ):
        game = cls(
            repo=repo,
            controller=controller,
            game_id=game_id,
            id_=uuid4().hex,
            state=BuzzerState.DEACTIVE,
            player_id="",
            player_disabled_until=0,
        )
        await repo.set_component_state(game_id, game.id, game.schema().model_dump(mode="json"))
        return game

    async def delete(self):
        await self.repo.delete_component(self.game_id, self.id)

    async def _persist(self):
        await self.repo.set_component_state(
            self.game_id,
            self.id,
            self.schema().model_dump(mode="json"),
        )
        await self.controller.send(
            ComponentStateUpdatedEvent(
                component_id=self.id, state=self.schema().model_dump(mode="json")
            )
        )

    async def activate(self, event=None, disable_buzzed_player=False):
        exclude_player = None
        if disable_buzzed_player:
            self.player_disabled_until = time() + 15
            exclude_player = self.player_id
        else:
            self.player_id = ""
            self.player_disabled_until = 0
        self.state = BuzzerState.ACTIVE
        await self._persist()

        if event is None:
            event = BuzzerStateEvent(state=self.state)

        await self.controller.send(event)
        await self.controller.broadcast(event, exclude=exclude_player)

    async def deactivate(self, event=None):
        self.state = BuzzerState.DEACTIVE
        await self._persist()

        if event is None:
            event = BuzzerStateEvent(state=self.state)

        await self.controller.send(event)
        await self.controller.broadcast(event)

    async def press(self, event: BuzzerClickedEvent):
        self.player_id = event.player_id
        await self._persist()
        await self.controller.send(event)
        await self.controller.broadcast(event, [self.controller.lobby.host_id])

    async def update_score(self, event: UpdateScoreEvent):
        if event.set_score is not None:
            score = event.set_score
        else:
            score = await self.controller.get_player_score(event.player_id)
            score += event.add_score
        await self.controller.set_player_score(event.player_id, score)

    async def handle(self, event: dict) -> bool:
        log.info("Handling event %s", event["type_"])
        match event["type_"]:
            case Event.BUZZER_STATE:
                buzzer_state = BuzzerStateEvent.model_validate(event)
                if buzzer_state.state == BuzzerState.ACTIVE:
                    await self.activate(disable_buzzed_player=buzzer_state.disable_activator)
                else:
                    await self.deactivate()
                return True
            case Event.BUZZER_CLICKED:
                buzzer_clicked = BuzzerClickedEvent.model_validate(event)
                await self.deactivate()
                await self.press(buzzer_clicked)
                return True
            case Event.UPDATE_SCORE:
                update_score = UpdateScoreEvent.model_validate(event)
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
