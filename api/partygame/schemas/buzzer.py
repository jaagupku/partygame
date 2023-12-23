from enum import StrEnum, auto

from .lobby import GameType, BaseGame

class BuzzerState(StrEnum):
    ACTIVE = auto()
    DEACTIVE = auto()


class BuzzerGameSchema(BaseGame):
    type_: str = GameType.BUZZER_GAME
    id: str
    buzzer_state: BuzzerState
    buzzed_player: str
