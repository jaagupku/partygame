import pytest

from partygame.schemas import Lobby
from partygame.schemas.game_definition import (
    GameDefinition,
    RoundDefinition,
    StepDefinition,
    ComponentDefinition,
    ComponentType,
    EvaluationRule,
    EvaluationType,
)
from partygame.service.game import GameRuntimeService


class FakeRepo:
    def __init__(self):
        self.lobby_fields = {}
        self.components = {}
        self.steps = {}
        self.scores = {"p1": 0, "p2": 5}

    async def set_lobby_fields(self, game_id: str, **fields):
        self.lobby_fields.setdefault(game_id, {}).update(fields)

    async def set_step_cache(self, game_id: str, fields: dict):
        self.steps[game_id] = fields

    async def set_component_state(self, game_id: str, component_id: str, fields: dict):
        self.components[(game_id, component_id)] = fields

    async def get_component_state(self, game_id: str, component_id: str) -> dict:
        return self.components.get((game_id, component_id), {})

    async def get_player_score(self, game_id: str, player_id: str) -> int:
        return self.scores.get(player_id, 0)

    async def set_player_score(self, game_id: str, player_id: str, score: int):
        self.scores[player_id] = score


class FakeDefinitionProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Test",
            rounds=[
                RoundDefinition(
                    id="r1",
                    steps=[
                        StepDefinition(
                            id="s1",
                            components=[
                                ComponentDefinition(
                                    id="display_1",
                                    type_=ComponentType.DISPLAY_TEXT_IMAGE,
                                    props={"text": "Question?", "image": None},
                                ),
                                ComponentDefinition(
                                    id="input_1",
                                    type_=ComponentType.PLAYER_INPUT,
                                    props={"kind": "text"},
                                ),
                            ],
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_TEXT,
                                points=2,
                                config={"answer": "yes"},
                            ),
                        )
                    ],
                )
            ],
        )


@pytest.mark.asyncio
async def test_start_game_sets_running_state_and_first_step():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=FakeDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo")

    updated_lobby, step = await service.start_game(lobby)

    assert updated_lobby.state == "running"
    assert updated_lobby.current_step == 0
    assert step is not None
    assert step.id == "s1"
    assert repo.lobby_fields["g1"]["phase"] == "step_active"
    assert repo.steps["g1"] == {"step_id": "s1", "step_index": 0}


@pytest.mark.asyncio
async def test_activate_and_evaluate_step_updates_scores():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=FakeDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo")

    _, step = await service.start_game(lobby)
    assert step is not None

    events = await service.activate_step_components(lobby.id, step)
    assert len(events) == 2

    await service.submit_player_input(lobby.id, "input_1", "p1", "yes")
    await service.submit_player_input(lobby.id, "input_1", "p2", "no")

    score_event = await service.evaluate_step(lobby, step)

    assert score_event.type_ == "scores_updated"
    assert score_event.updates == {"p1": 2}
    assert repo.scores["p1"] == 2
    assert repo.scores["p2"] == 5
