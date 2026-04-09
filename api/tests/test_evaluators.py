import pytest

from partygame.schemas.game_definition import (
    StepDefinition,
    EvaluationRule,
    EvaluationType,
)
from partygame.service.runtime.evaluators import EvaluatorRegistry


@pytest.mark.asyncio
async def test_exact_text_evaluator_awards_only_matching_answer():
    registry = EvaluatorRegistry()
    evaluator = registry.get(EvaluationType.EXACT_TEXT)

    step = StepDefinition(
        id="s1",
        evaluation=EvaluationRule(
            type_=EvaluationType.EXACT_TEXT, points=3, config={"answer": "Paris"}
        ),
    )

    updates = await evaluator.evaluate(
        step=step,
        answers={"p1": "Paris", "p2": "London", "p3": "paris"},
    )

    assert updates == {"p1": 3, "p3": 3}


@pytest.mark.asyncio
async def test_closest_number_evaluator_awards_nearest_player():
    registry = EvaluatorRegistry()
    evaluator = registry.get(EvaluationType.CLOSEST_NUMBER)

    step = StepDefinition(
        id="s2",
        evaluation=EvaluationRule(
            type_=EvaluationType.CLOSEST_NUMBER, points=2, config={"target": 27}
        ),
    )

    updates = await evaluator.evaluate(
        step=step,
        answers={"p1": 40, "p2": 26, "p3": 30},
    )

    assert updates == {"p2": 2}


@pytest.mark.asyncio
async def test_ordering_match_evaluator_awards_exact_order_only():
    registry = EvaluatorRegistry()
    evaluator = registry.get(EvaluationType.ORDERING_MATCH)

    step = StepDefinition(
        id="s3",
        evaluation=EvaluationRule(
            type_=EvaluationType.ORDERING_MATCH,
            points=5,
            config={"order": ["A", "B", "C"]},
        ),
    )

    updates = await evaluator.evaluate(
        step=step,
        answers={"p1": ["A", "B", "C"], "p2": ["A", "C", "B"]},
    )

    assert updates == {"p1": 5}
