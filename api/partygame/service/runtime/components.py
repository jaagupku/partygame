from typing import Any

from partygame.schemas.game_definition import ComponentType
from partygame.service.runtime.protocols import ComponentHandler


class DisplayTextImageHandler:
    type_name = ComponentType.DISPLAY_TEXT_IMAGE

    async def on_step_start(
        self, game_id: str, component_id: str, props: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "type_": self.type_name,
            "props": props,
            "answers": {},
        }

    async def handle_player_input(
        self,
        game_id: str,
        component_id: str,
        player_id: str,
        payload: dict[str, Any],
    ) -> bool:
        return False


class PlayerInputHandler:
    type_name = ComponentType.PLAYER_INPUT

    async def on_step_start(
        self, game_id: str, component_id: str, props: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "type_": self.type_name,
            "props": props,
            "answers": {},
        }

    async def handle_player_input(
        self,
        game_id: str,
        component_id: str,
        player_id: str,
        payload: dict[str, Any],
    ) -> bool:
        return True


class BuzzerRuntimeHandler:
    type_name = ComponentType.BUZZER

    async def on_step_start(
        self, game_id: str, component_id: str, props: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "type_": self.type_name,
            "props": props,
            "answers": {},
            "state": "deactive",
            "buzzed_player": "",
        }

    async def handle_player_input(
        self,
        game_id: str,
        component_id: str,
        player_id: str,
        payload: dict[str, Any],
    ) -> bool:
        return payload.get("type") == "buzz"


class RuntimeComponentRegistry:
    def __init__(self):
        handlers: list[ComponentHandler] = [
            DisplayTextImageHandler(),
            PlayerInputHandler(),
            BuzzerRuntimeHandler(),
        ]
        self._handlers = {handler.type_name: handler for handler in handlers}

    def get(self, component_type: ComponentType) -> ComponentHandler:
        return self._handlers[component_type]
