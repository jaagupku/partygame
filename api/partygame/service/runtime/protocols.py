from typing import Any, Protocol

from partygame.schemas import StepDefinition


class Evaluator(Protocol):
    type_name: str

    async def evaluate(
        self,
        *,
        step: StepDefinition,
        answers: dict[str, Any],
        host_decisions: dict[str, bool] | None = None,
    ) -> dict[str, int]: ...


class ComponentHandler(Protocol):
    type_name: str

    async def on_step_start(
        self, game_id: str, component_id: str, props: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def handle_player_input(
        self,
        game_id: str,
        component_id: str,
        player_id: str,
        payload: dict[str, Any],
    ) -> bool: ...
