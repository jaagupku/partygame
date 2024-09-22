from abc import ABC, abstractmethod

from partygame.schemas.game import GameSchema, PlaySchema

class GameService(ABC):

    @abstractmethod
    def get(id: str):
        ...

    @abstractmethod
    def get_all():
        ...

    @abstractmethod
    def create(game: GameSchema):
        ...

    @abstractmethod
    def update(id: str, game: GameSchema):
        ...

    @abstractmethod
    def update_play(id: str, play_nr: int, play: PlaySchema):
        ...

    @abstractmethod
    def delete(id: str):
        ...
