import logging
from typing import TYPE_CHECKING

from partygame.service.components.base_class import ComponentABC
from partygame.state import GameStateRepository

if TYPE_CHECKING:
    from partygame.service.lobby import GameController

log = logging.getLogger(__name__)


class EmptyComponent(ComponentABC):
    component_type = "empty"

    def __init__(self):
        self.id = ""

    @classmethod
    async def load(
        cls,
        repo: GameStateRepository,
        controller: "GameController",
        game_id: str,
        component_id: str,
    ) -> "EmptyComponent":
        return cls()

    @classmethod
    async def new(
        cls,
        repo: GameStateRepository,
        controller: "GameController",
        game_id: str,
    ) -> "EmptyComponent":
        return cls()

    async def delete(self):
        return None

    async def handle(self, event: dict) -> bool:
        return False

    async def broadcast_state_controller(self, players=None, is_host=False):
        return None

    async def broadcast_state_host(self):
        return None
