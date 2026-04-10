import pytest

from partygame.schemas import Lobby
from partygame.schemas.game_definition import (
    EvaluationRule,
    EvaluationType,
    GameDefinition,
    PlayerInputDefinition,
    PlayerInputKind,
    RoundDefinition,
    StepDefinition,
)
from partygame.service.game import GameRuntimeService


class FakeRepo:
    def __init__(self):
        self.lobby_fields = {}
        self.steps = {}
        self.scores = {"p1": 0, "p2": 0, "p3": 0}

    async def set_lobby_fields(self, game_id: str, **fields):
        self.lobby_fields.setdefault(game_id, {}).update(fields)

    async def set_step_cache(self, game_id: str, fields: dict):
        self.steps.setdefault(game_id, {}).update(fields)

    async def get_step_cache(self, game_id: str) -> dict:
        return self.steps.get(game_id, {})

    async def get_player_score(self, game_id: str, player_id: str) -> int:
        return self.scores.get(player_id, 0)

    async def set_player_score(self, game_id: str, player_id: str, score: int):
        self.scores[player_id] = score


class ExactTextDefinitionProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Test",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="text_step",
                            title="Exact text",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.EXACT_TEXT,
                                points=3,
                                answer="Paris",
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


@pytest.mark.asyncio
async def test_exact_text_evaluation_awards_matching_answers():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=ExactTextDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "Paris")
    await service.submit_player_input(lobby, "p2", "paris")
    await service.submit_player_input(lobby, "p3", "London")

    score_event = await service.evaluate_auto_step(lobby)

    assert score_event.updates == {"p1": 3, "p2": 3}


class HostJudgedFallbackProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Fallback test",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="text_step",
                            title="Host judged text",
                            player_input=PlayerInputDefinition(kind=PlayerInputKind.TEXT),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=2,
                                answer="blue",
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


@pytest.mark.asyncio
async def test_host_disabled_host_judged_text_falls_back_to_exact_text():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=HostJudgedFallbackProvider())
    lobby = Lobby(id="g2", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "blue")
    await service.submit_player_input(lobby, "p2", "green")

    score_event = await service.evaluate_auto_step(lobby)

    assert score_event.updates == {"p1": 2}


class RadioFallbackProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Radio fallback",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="radio_step",
                            title="Pick one",
                            player_input=PlayerInputDefinition(
                                kind=PlayerInputKind.RADIO,
                                options=["Blue", "Green"],
                            ),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.HOST_JUDGED,
                                points=2,
                                answer="Blue",
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


@pytest.mark.asyncio
async def test_host_disabled_host_judged_radio_falls_back_to_exact_text():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=RadioFallbackProvider())
    lobby = Lobby(id="g3", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "Blue")
    await service.submit_player_input(lobby, "p2", "Green")

    score_event = await service.evaluate_auto_step(lobby)

    assert score_event.updates == {"p1": 2}
