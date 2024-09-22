import logging

from redis.asyncio import Redis

from partygame.service.components.base_class import ComponentABC
from partygame.service.lobby import GameController

log = logging.getLogger(__name__)

class EmptyComponent(ComponentABC):
    def __init__(self):
        ...

    @staticmethod
    def key(id_: str):
        return f"empty:{id_}"

    @staticmethod
    async def load(redis: Redis, controller: GameController, id_: str):
        return EmptyComponent()

    @staticmethod
    async def new(redis: Redis, controller: GameController):
        return EmptyComponent()

    async def delete(self):
        pass

    async def handle(self, event: dict) -> bool:
        return False

    async def broadcast_state_controller(self, players=None, is_host=False):
        pass

    async def broadcast_state_host(self):
        pass
