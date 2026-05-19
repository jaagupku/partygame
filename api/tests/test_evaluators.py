import pytest

from partygame.schemas import Lobby
import partygame.schemas as schemas
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
        self.component_state = {}
        self.players = [
            schemas.Player(
                id="p1", game_id="g1", name="Player 1", status=schemas.ConnectionStatus.CONNECTED
            ),
            schemas.Player(
                id="p2", game_id="g1", name="Player 2", status=schemas.ConnectionStatus.CONNECTED
            ),
            schemas.Player(
                id="p3", game_id="g1", name="Player 3", status=schemas.ConnectionStatus.CONNECTED
            ),
        ]

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

    async def get_players(self, game_id: str):
        return self.players

    async def get_state_revision(self, game_id: str) -> int:
        return 0

    async def set_component_state(self, game_id: str, component_id: str, fields: dict):
        self.component_state.setdefault(game_id, {})[component_id] = fields

    async def get_component_state(self, game_id: str, component_id: str) -> dict:
        return self.component_state.get(game_id, {}).get(component_id, {})


class ExactTextDefinitionProvider:
    def __init__(
        self,
        answer="Paris",
        max_distance: int | None = None,
        input_kind: PlayerInputKind = PlayerInputKind.TEXT,
    ):
        self.answer = answer
        self.max_distance = max_distance
        self.input_kind = input_kind

    async def load(self, definition_id: str) -> GameDefinition:
        evaluation_kwargs = {
            "type_": EvaluationType.EXACT_TEXT,
            "points": 3,
            "answer": self.answer,
        }
        if self.max_distance is not None:
            evaluation_kwargs["max_distance"] = self.max_distance
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
                            player_input=PlayerInputDefinition(kind=self.input_kind),
                            evaluation=EvaluationRule(**evaluation_kwargs),
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

    score_events = await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 3
    assert repo.scores["p2"] == 3
    assert score_events[-1].updates == {}


@pytest.mark.asyncio
async def test_exact_text_evaluation_accepts_multiple_answers():
    repo = FakeRepo()
    service = GameRuntimeService(
        repo=repo,
        definition_provider=ExactTextDefinitionProvider(answer=["Paris", "City of Light"]),
    )
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "city of light")
    await service.submit_player_input(lobby, "p2", "Paris")
    await service.submit_player_input(lobby, "p3", "London")

    await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 3
    assert repo.scores["p2"] == 3
    assert repo.scores["p3"] == 0


@pytest.mark.asyncio
async def test_exact_text_evaluation_accepts_answers_within_default_distance():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=ExactTextDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "Pariss")
    await service.submit_player_input(lobby, "p2", "Pris")
    await service.submit_player_input(lobby, "p3", "London")

    await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 3
    assert repo.scores["p2"] == 3
    assert repo.scores["p3"] == 0


@pytest.mark.asyncio
async def test_exact_text_evaluation_rejects_answers_beyond_distance():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=ExactTextDefinitionProvider())
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "London")
    await service.submit_player_input(lobby, "p2", "Lyon")

    await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 0
    assert repo.scores["p2"] == 0


@pytest.mark.asyncio
async def test_exact_text_evaluation_zero_distance_preserves_exact_matching():
    repo = FakeRepo()
    service = GameRuntimeService(
        repo=repo,
        definition_provider=ExactTextDefinitionProvider(max_distance=0),
    )
    lobby = Lobby(id="g1", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "Paris")
    await service.submit_player_input(lobby, "p2", "Pariss")

    await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 3
    assert repo.scores["p2"] == 0


class HostJudgedFallbackProvider:
    def __init__(self, answer="blue", max_distance: int | None = None):
        self.answer = answer
        self.max_distance = max_distance

    async def load(self, definition_id: str) -> GameDefinition:
        evaluation_kwargs = {
            "type_": EvaluationType.HOST_JUDGED,
            "points": 2,
            "answer": self.answer,
        }
        if self.max_distance is not None:
            evaluation_kwargs["max_distance"] = self.max_distance
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
                            evaluation=EvaluationRule(**evaluation_kwargs),
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

    score_events = await service.evaluate_auto_step(lobby)

    assert score_events[-1].updates == {"p1": 2}


@pytest.mark.asyncio
async def test_host_disabled_host_judged_text_fallback_uses_aliases_and_distance():
    repo = FakeRepo()
    service = GameRuntimeService(
        repo=repo,
        definition_provider=HostJudgedFallbackProvider(answer=["blue", "azure"]),
    )
    lobby = Lobby(id="g2", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", "azur")
    await service.submit_player_input(lobby, "p2", "bleu")
    await service.submit_player_input(lobby, "p3", "green")

    await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 2
    assert repo.scores["p2"] == 2
    assert repo.scores["p3"] == 0


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

    score_events = await service.evaluate_auto_step(lobby)

    assert score_events[-1].updates == {"p1": 2}


class WeightedCheckboxProvider:
    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Checkbox scoring",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="checkbox_step",
                            title="Pick all that apply",
                            player_input=PlayerInputDefinition(
                                kind=PlayerInputKind.CHECKBOX,
                                options=["Mercury", "Venus", "Pluto"],
                            ),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.MULTI_SELECT_WEIGHTED,
                                points=99,
                                answer={
                                    "option_scores": [
                                        {"option": "Mercury", "points": 2},
                                        {"option": "Venus", "points": 3},
                                        {"option": "Pluto", "points": -1},
                                    ]
                                },
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


@pytest.mark.asyncio
async def test_multi_select_weighted_evaluation_sums_selected_option_points():
    repo = FakeRepo()
    service = GameRuntimeService(repo=repo, definition_provider=WeightedCheckboxProvider())
    lobby = Lobby(id="g4", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", ["Mercury", "Venus"])
    await service.submit_player_input(lobby, "p2", ["Pluto"])
    await service.submit_player_input(lobby, "p3", ["Unknown"])

    score_events = await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 5
    assert repo.scores["p2"] == 0
    assert score_events[-1].updates == {}
    snapshot = await service.build_snapshot(lobby)
    assert snapshot.active_step is not None
    assert snapshot.active_step.max_points == 5


class MapDistanceProvider:
    def __init__(self, answer: dict):
        self.answer = answer

    async def load(self, definition_id: str) -> GameDefinition:
        return GameDefinition(
            id=definition_id,
            title="Map scoring",
            rounds=[
                RoundDefinition(
                    id="round1",
                    steps=[
                        StepDefinition(
                            id="map_step",
                            title="Place it",
                            player_input=PlayerInputDefinition(
                                kind=PlayerInputKind.MAP,
                                map={
                                    "selection_mode": "point",
                                    "bounds": {
                                        "north": 1.0,
                                        "south": -1.0,
                                        "east": 1.0,
                                        "west": -1.0,
                                    },
                                    "initial_center": {"lat": 0.0, "lng": 0.0},
                                    "initial_zoom": 10,
                                },
                            ),
                            evaluation=EvaluationRule(
                                type_=EvaluationType.MAP_DISTANCE,
                                points=5,
                                answer=self.answer,
                            ),
                        )
                    ],
                )
            ],
        )

    async def list_definitions(self):
        return []


@pytest.mark.asyncio
async def test_map_distance_band_evaluation_scores_by_distance():
    repo = FakeRepo()
    service = GameRuntimeService(
        repo=repo,
        definition_provider=MapDistanceProvider(
            {
                "correct_point": {"lat": 0.0, "lng": 0.0},
                "scoring_mode": "bands",
                "max_points": 5,
                "zero_distance_m": 5000,
                "bands": [
                    {"distance_m": 100, "points": 5},
                    {"distance_m": 2000, "points": 3},
                ],
            }
        ),
    )
    lobby = Lobby(id="g5", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", {"lat": 0.0, "lng": 0.0})
    await service.submit_player_input(lobby, "p2", {"lat": 0.0, "lng": 0.01})
    await service.submit_player_input(lobby, "p3", {"lat": 0.0, "lng": 0.05})

    score_events = await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 5
    assert repo.scores["p2"] == 3
    assert repo.scores["p3"] == 0
    assert score_events[-1].updates == {}


@pytest.mark.asyncio
async def test_map_distance_linear_evaluation_decays_to_zero():
    repo = FakeRepo()
    service = GameRuntimeService(
        repo=repo,
        definition_provider=MapDistanceProvider(
            {
                "correct_point": {"lat": 0.0, "lng": 0.0},
                "scoring_mode": "linear",
                "max_points": 10,
                "full_credit_distance_m": 0,
                "zero_distance_m": 2000,
            }
        ),
    )
    lobby = Lobby(id="g6", join_code="ABCDE", definition_id="quiz_demo", host_enabled=False)

    await service.start_game(lobby)
    await service.submit_player_input(lobby, "p1", {"lat": 0.0, "lng": 0.0})
    await service.submit_player_input(lobby, "p2", {"lat": 0.0, "lng": 0.01})
    await service.submit_player_input(lobby, "p3", {"lat": 0.0, "lng": 0.05})

    await service.evaluate_auto_step(lobby)

    assert repo.scores["p1"] == 10
    assert 3 <= repo.scores["p2"] <= 5
    assert repo.scores["p3"] == 0
