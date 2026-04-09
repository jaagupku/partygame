from typing import Any

from partygame import schemas
from partygame.schemas import (
    Event,
    StepAdvancedEvent,
    ScoresUpdatedEvent,
    ComponentStateUpdatedEvent,
)
from partygame.schemas.game_definition import StepDefinition
from partygame.service.definitions import DefinitionProvider, FileDefinitionProvider
from partygame.service.runtime.evaluators import EvaluatorRegistry
from partygame.service.runtime.components import RuntimeComponentRegistry
from partygame.state import GameStateRepository


class GameRuntimeService:
    def __init__(
        self,
        repo: GameStateRepository,
        definition_provider: DefinitionProvider | None = None,
        evaluator_registry: EvaluatorRegistry | None = None,
        component_registry: RuntimeComponentRegistry | None = None,
    ):
        self.repo = repo
        self.definition_provider = definition_provider or FileDefinitionProvider()
        self.evaluator_registry = evaluator_registry or EvaluatorRegistry()
        self.component_registry = component_registry or RuntimeComponentRegistry()

    async def _flatten_steps(self, lobby: schemas.Lobby) -> list[StepDefinition]:
        definition_id = lobby.definition_id or "quiz_demo"
        definition = await self.definition_provider.load(definition_id)
        steps: list[StepDefinition] = []
        for round_definition in definition.rounds:
            steps.extend(round_definition.steps)
        return steps

    async def start_game(self, lobby: schemas.Lobby) -> tuple[schemas.Lobby, StepDefinition | None]:
        await self.repo.set_lobby_fields(
            lobby.id,
            state=schemas.GameState.RUNNING,
            phase="step_active",
            current_step=0,
        )
        lobby.state = schemas.GameState.RUNNING
        lobby.phase = "step_active"
        lobby.current_step = 0

        steps = await self._flatten_steps(lobby)
        if not steps:
            return lobby, None
        step = steps[0]
        await self.repo.set_step_cache(lobby.id, {"step_id": step.id, "step_index": 0})
        return lobby, step

    async def get_current_step(self, lobby: schemas.Lobby) -> StepDefinition | None:
        steps = await self._flatten_steps(lobby)
        if lobby.current_step >= len(steps):
            return None
        return steps[lobby.current_step]

    async def activate_step_components(
        self,
        game_id: str,
        step: StepDefinition,
    ) -> list[ComponentStateUpdatedEvent]:
        events: list[ComponentStateUpdatedEvent] = []
        for component in step.components:
            handler = self.component_registry.get(component.type_)
            state = await handler.on_step_start(game_id, component.id, component.props)
            state["step_id"] = step.id
            await self.repo.set_component_state(game_id, component.id, state)
            events.append(ComponentStateUpdatedEvent(component_id=component.id, state=state))
        return events

    async def submit_player_input(
        self,
        game_id: str,
        component_id: str,
        player_id: str,
        value: Any,
    ):
        state = await self.repo.get_component_state(game_id, component_id)
        answers = state.get("answers", {})
        answers[player_id] = value
        state["answers"] = answers
        await self.repo.set_component_state(game_id, component_id, state)

    async def evaluate_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
        host_decisions: dict[str, bool] | None = None,
    ) -> ScoresUpdatedEvent:
        answers = {}
        for component in step.components:
            state = await self.repo.get_component_state(lobby.id, component.id)
            if "answers" in state:
                answers.update(state["answers"])

        evaluator = self.evaluator_registry.get(step.evaluation.type_)
        score_increments = await evaluator.evaluate(
            step=step,
            answers=answers,
            host_decisions=host_decisions,
        )

        score_updates: dict[str, int] = {}
        for player_id, increment in score_increments.items():
            current_score = await self.repo.get_player_score(lobby.id, player_id)
            new_score = current_score + increment
            await self.repo.set_player_score(lobby.id, player_id, new_score)
            score_updates[player_id] = new_score

        return ScoresUpdatedEvent(updates=score_updates)

    async def advance_step(self, lobby: schemas.Lobby) -> StepAdvancedEvent:
        next_step = lobby.current_step + 1
        await self.repo.set_lobby_fields(lobby.id, current_step=next_step)
        lobby.current_step = next_step
        return StepAdvancedEvent(step_index=next_step)

    async def handle_runtime_event(
        self,
        lobby: schemas.Lobby,
        event: dict,
    ) -> tuple[list[object], bool]:
        event_type = event.get("type_")
        if event_type == Event.PLAYER_INPUT_SUBMITTED:
            payload = schemas.PlayerInputSubmittedEvent.model_validate(event)
            await self.submit_player_input(
                lobby.id,
                payload.component_id,
                payload.player_id,
                payload.value,
            )
            return [payload], True

        if event_type == Event.STEP_ADVANCED:
            step_event = await self.advance_step(lobby)
            step = await self.get_current_step(lobby)
            if step is None:
                await self.repo.set_lobby_fields(lobby.id, phase="finished")
                lobby.phase = "finished"
                return [step_event], True
            component_events = await self.activate_step_components(lobby.id, step)
            return [step_event, *component_events], True

        if event_type == Event.SCORES_UPDATED:
            step = await self.get_current_step(lobby)
            if step is None:
                return [], True
            scores_event = await self.evaluate_step(lobby, step)
            return [scores_event], True

        return [], False
