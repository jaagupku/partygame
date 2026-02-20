from abc import ABC, abstractmethod

from partygame.schemas.game import GameSchema, PlaySchema


class GameService(ABC):

    @abstractmethod
    def get(self, id: str): ...

    @abstractmethod
    def get_all(self): ...

    @abstractmethod
    def create(self, game: GameSchema): ...

    @abstractmethod
    def update(self, id: str, game: GameSchema): ...

    @abstractmethod
    def update_play(self, id: str, play_nr: int, play: PlaySchema): ...

    @abstractmethod
    def delete(self, id: str): ...
