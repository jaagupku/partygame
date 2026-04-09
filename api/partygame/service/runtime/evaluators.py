from typing import Any

from partygame.schemas import EvaluationType, StepDefinition
from partygame.service.runtime.protocols import Evaluator


class HostJudgedEvaluator:
    type_name = EvaluationType.HOST_JUDGED

    async def evaluate(
        self,
        *,
        step: StepDefinition,
        answers: dict[str, Any],
        host_decisions: dict[str, bool] | None = None,
    ) -> dict[str, int]:
        decisions = host_decisions or {}
        points = step.evaluation.points
        return {player_id: points for player_id, accepted in decisions.items() if accepted}


class ClosestNumberEvaluator:
    type_name = EvaluationType.CLOSEST_NUMBER

    async def evaluate(
        self,
        *,
        step: StepDefinition,
        answers: dict[str, Any],
        host_decisions: dict[str, bool] | None = None,
    ) -> dict[str, int]:
        target = step.evaluation.config.get("target")
        if target is None or not answers:
            return {}
        diffs = []
        for player_id, value in answers.items():
            try:
                diffs.append((abs(float(value) - float(target)), player_id))
            except TypeError, ValueError:
                continue
        if not diffs:
            return {}
        diffs.sort(key=lambda item: item[0])
        return {diffs[0][1]: step.evaluation.points}


class ExactTextEvaluator:
    type_name = EvaluationType.EXACT_TEXT

    async def evaluate(
        self,
        *,
        step: StepDefinition,
        answers: dict[str, Any],
        host_decisions: dict[str, bool] | None = None,
    ) -> dict[str, int]:
        answer = str(step.evaluation.config.get("answer", "")).strip().casefold()
        if not answer:
            return {}
        points = step.evaluation.points
        updates = {}
        for player_id, value in answers.items():
            if str(value).strip().casefold() == answer:
                updates[player_id] = points
        return updates


class OrderingMatchEvaluator:
    type_name = EvaluationType.ORDERING_MATCH

    async def evaluate(
        self,
        *,
        step: StepDefinition,
        answers: dict[str, Any],
        host_decisions: dict[str, bool] | None = None,
    ) -> dict[str, int]:
        expected = step.evaluation.config.get("order")
        if not isinstance(expected, list):
            return {}
        updates = {}
        for player_id, value in answers.items():
            if isinstance(value, list) and value == expected:
                updates[player_id] = step.evaluation.points
        return updates


class EvaluatorRegistry:
    def __init__(self):
        evaluators: list[Evaluator] = [
            HostJudgedEvaluator(),
            ClosestNumberEvaluator(),
            ExactTextEvaluator(),
            OrderingMatchEvaluator(),
        ]
        self._evaluators = {evaluator.type_name: evaluator for evaluator in evaluators}

    def get(self, evaluation_type: EvaluationType) -> Evaluator:
        return self._evaluators[evaluation_type]
