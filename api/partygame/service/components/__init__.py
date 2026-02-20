from redis.asyncio import Redis

from partygame.schemas import ControllerComponent
from partygame.service.components.base_class import ComponentABC


async def init_game(redis: Redis, lobby, game_type: ControllerComponent) -> ComponentABC:
    match game_type:
        case ControllerComponent.BUZZER_GAME:
            from partygame.service.components.buzzer import BuzzerComponent

            return await BuzzerComponent.new(redis, lobby)


async def load_game(redis: Redis, lobby, game_type: ControllerComponent, id_: str) -> ComponentABC:
    match game_type:
        case ControllerComponent.BUZZER_GAME:
            from partygame.service.components.buzzer import BuzzerComponent

            return await BuzzerComponent.load(redis, lobby, id_)
