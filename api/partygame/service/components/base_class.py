from typing import Self, List, TYPE_CHECKING
from abc import ABC, abstractmethod

from redis.asyncio import Redis

if TYPE_CHECKING:
    from partygame.service.lobby import GameController


class ComponentABC(ABC):

    @staticmethod
    @abstractmethod
    def key(id_: str) -> str:
        ...

    @staticmethod
    @abstractmethod
    async def new(redis: Redis, lobby: "GameController") -> Self:
        ...

    @staticmethod
    @abstractmethod
    async def load(redis: Redis, lobby: "GameController", id_: str) -> Self:
        ...

    @abstractmethod
    async def delete(self):
        ...

    @abstractmethod
    async def handle(self, event: dict) -> bool:
        ...

    @abstractmethod
    async def broadcast_state_controller(self, players: List[str] | None=None):
        ...

    @abstractmethod
    async def broadcast_state_host(self):
        ...
