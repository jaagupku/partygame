from typing import Any, TYPE_CHECKING
from abc import ABC, abstractmethod

from partygame.state import GameStateRepository

if TYPE_CHECKING:
    from partygame.service.lobby import GameController


class ComponentABC(ABC):
    component_type: str

    @classmethod
    @abstractmethod
    async def load(
        cls,
        repo: GameStateRepository,
        controller: "GameController",
        game_id: str,
        component_id: str,
    ) -> "ComponentABC": ...

    @classmethod
    @abstractmethod
    async def new(
        cls,
        repo: GameStateRepository,
        controller: "GameController",
        game_id: str,
    ) -> "ComponentABC": ...

    @abstractmethod
    async def delete(self): ...

    @abstractmethod
    async def handle(self, event: dict[str, Any]) -> bool: ...

    @abstractmethod
    async def broadcast_state_controller(
        self, players: list[str] | None = None, is_host: bool = False
    ): ...

    @abstractmethod
    async def broadcast_state_host(self): ...
