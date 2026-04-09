from typing import Type

from partygame.schemas import ControllerComponent
from partygame.service.components.base_class import ComponentABC
from partygame.state import GameStateRepository


class ComponentRegistry:
    def __init__(self):
        self._registry: dict[str, Type[ComponentABC]] = {}
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        from partygame.service.components.buzzer import BuzzerComponent

        self._registry[ControllerComponent.BUZZER_GAME] = BuzzerComponent
        self._loaded = True

    def resolve(self, component_type: str) -> Type[ComponentABC]:
        self._ensure_loaded()
        return self._registry[component_type]


REGISTRY = ComponentRegistry()


async def init_game(
    repo: GameStateRepository,
    lobby,
    game_type: ControllerComponent,
    game_id: str,
) -> ComponentABC:
    component_cls = REGISTRY.resolve(game_type)
    return await component_cls.new(repo, lobby, game_id)


async def load_game(
    repo: GameStateRepository,
    lobby,
    game_type: ControllerComponent,
    game_id: str,
    component_id: str,
) -> ComponentABC:
    component_cls = REGISTRY.resolve(game_type)
    return await component_cls.load(repo, lobby, game_id, component_id)


__all__ = ("ComponentABC", "ComponentRegistry", "init_game", "load_game")
