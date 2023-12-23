from redis.asyncio import Redis

from partygame.schemas import GameType
from partygame.service.game.base_class import GameABC


async def init_game(redis: Redis, lobby, game_type: GameType) -> GameABC:
    match game_type:
        case GameType.BUZZER_GAME:
            from partygame.service.game.buzzer_game import BuzzerGame
            return await BuzzerGame.new(redis, lobby)


async def load_game(redis: Redis, lobby, game_type: GameType, id_: str) -> GameABC:
    match game_type:
        case GameType.BUZZER_GAME:
            from partygame.service.game.buzzer_game import BuzzerGame
            return await BuzzerGame.load(redis, lobby, id_)
