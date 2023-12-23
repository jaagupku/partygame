from typing import Self, List
from abc import ABC, abstractmethod

from redis.asyncio import Redis


class GameABC(ABC):

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
    async def handle(self, event: dict) -> bool:
        ...
    
    @abstractmethod
    async def broadcast_state_controller(self, players: List[str]=None):
        ...

    @abstractmethod
    async def broadcast_state_host(self):
        ...
