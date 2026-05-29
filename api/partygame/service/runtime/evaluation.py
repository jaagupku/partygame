from math import asin, cos, radians, sin, sqrt
from collections.abc import Awaitable, Callable
from typing import Any, TYPE_CHECKING

from partygame import schemas
from partygame.schemas.game_definition import (
    EvaluationType,
    PlayerInputDefinition,
    PlayerInputKind,
    StepDefinition,
)

if TYPE_CHECKING:
    from partygame.state.repo import GameStateRepository
    from partygame.service.runtime.timing import TimingState

HOSTLESS_AUTO_EVALUATION_TYPES = {
    EvaluationType.EXACT_TEXT,
    EvaluationType.EXACT_NUMBER,
    EvaluationType.CLOSEST_NUMBER,
    EvaluationType.ORDERING_MATCH,
    EvaluationType.MULTI_SELECT_WEIGHTED,
    EvaluationType.MAP_DISTANCE,
}

DRAWING_CANVAS_WIDTH = 512
DRAWING_CANVAS_HEIGHT = 384
MAX_DRAWING_STROKES = 80
MAX_DRAWING_POINTS = 1_600
MAX_DRAWING_PAYLOAD_CHARS = 60_000
DRAWING_COLORS = {
    "#0f172a",
    "#ef4444",
    "#f97316",
    "#eab308",
    "#22c55e",
    "#06b6d4",
    "#3b82f6",
    "#a855f7",
    "#ec4899",
    "#ffffff",
}
DRAWING_LABEL_PREFIX = "Drawing"


class EvaluationRuntime:
    def __init__(
        self,
        repo: "GameStateRepository",
        timing: "TimingState",
        get_step_state: Callable[[str], Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        self.repo = repo
        self.timing = timing
        self.get_step_state = get_step_state

    def max_points_for_step(self, step: StepDefinition, evaluation_type: EvaluationType) -> int:
        return self._max_points_for_step(step, evaluation_type)

    def _max_points_for_step(self, step: StepDefinition, evaluation_type: EvaluationType) -> int:
        if evaluation_type == EvaluationType.CLOSEST_NUMBER:
            band_points = [band.points for band in step.evaluation.number_bands]
            return max([step.evaluation.points, *band_points])

        if evaluation_type == EvaluationType.MAP_DISTANCE:
            answer = self._map_distance_answer(step)
            if answer is not None:
                return int(answer.get("max_points", step.evaluation.points) or 0)
            return step.evaluation.points

        if evaluation_type != EvaluationType.MULTI_SELECT_WEIGHTED:
            return step.evaluation.points

        answer = step.evaluation.answer
        option_scores = answer.get("option_scores") if isinstance(answer, dict) else None
        if not isinstance(option_scores, list):
            return step.evaluation.points

        max_points = 0
        for entry in option_scores:
            if not isinstance(entry, dict):
                continue
            points = entry.get("points")
            if isinstance(points, int) and points > 0:
                max_points += points
        return max_points

    def _map_distance_answer(self, step: StepDefinition) -> dict[str, Any] | None:
        answer = step.evaluation.answer
        if not isinstance(answer, dict):
            return None
        correct_point = answer.get("correct_point")
        if self._coerce_map_point(correct_point) is None:
            return None
        return answer

    def is_valid_map_submission(self, step: StepDefinition, value: Any) -> bool:
        return self._is_valid_map_submission(step, value)

    def _is_valid_map_submission(self, step: StepDefinition, value: Any) -> bool:
        point = self._coerce_map_point(value)
        if point is None or step.player_input.map is None:
            return False
        bounds = step.player_input.map.bounds
        return (
            bounds.south <= point["lat"] <= bounds.north
            and bounds.west <= point["lng"] <= bounds.east
        )

    def score_map_distance_answer(self, step: StepDefinition, value: Any) -> int:
        return self._score_map_distance_answer(step, value)

    def _score_map_distance_answer(self, step: StepDefinition, value: Any) -> int:
        answer = self._map_distance_answer(step)
        submitted = self._coerce_map_point(value)
        if answer is None or submitted is None:
            return 0
        correct = self._coerce_map_point(answer.get("correct_point"))
        if correct is None:
            return 0

        distance_m = self._haversine_distance_m(submitted, correct)
        max_points = max(0, int(answer.get("max_points", step.evaluation.points) or 0))
        if answer.get("scoring_mode") == "linear":
            zero_distance = self.timing.to_float(answer.get("zero_distance_m")) or 0.0
            full_credit_distance = self.timing.to_float(answer.get("full_credit_distance_m")) or 0.0
            if zero_distance <= 0:
                return 0
            if distance_m <= full_credit_distance:
                return max_points
            if distance_m >= zero_distance:
                return 0
            ratio = (distance_m - full_credit_distance) / (zero_distance - full_credit_distance)
            return max(0, min(max_points, round(max_points * (1 - ratio))))

        bands = answer.get("bands")
        if not isinstance(bands, list):
            return 0
        band_entries = [band for band in bands if isinstance(band, dict)]
        for band in sorted(
            band_entries,
            key=lambda entry: self.timing.to_float(entry.get("distance_m")) or 0.0,
        ):
            band_distance = self.timing.to_float(band.get("distance_m"))
            if band_distance is None:
                continue
            if distance_m <= band_distance:
                return max(0, min(max_points, int(band.get("points") or 0)))
        return 0

    def _coerce_map_point(self, value: Any) -> dict[str, float] | None:
        if not isinstance(value, dict):
            return None
        try:
            lat = self.timing.to_float(value.get("lat"))
            lng = self.timing.to_float(value.get("lng"))
        except TypeError, ValueError:
            return None
        if lat is None or lng is None:
            return None
        if lat < -90 or lat > 90 or lng < -180 or lng > 180:
            return None
        return {"lat": lat, "lng": lng}

    def _haversine_distance_m(
        self,
        left: dict[str, float],
        right: dict[str, float],
    ) -> float:
        earth_radius_m = 6_371_000
        left_lat = radians(left["lat"])
        right_lat = radians(right["lat"])
        delta_lat = radians(right["lat"] - left["lat"])
        delta_lng = radians(right["lng"] - left["lng"])
        half_chord = (
            sin(delta_lat / 2) ** 2 + cos(left_lat) * cos(right_lat) * sin(delta_lng / 2) ** 2
        )
        return 2 * earth_radius_m * asin(sqrt(half_chord))

    async def _has_active_host_player(self, lobby: schemas.Lobby) -> bool:
        if not lobby.host_enabled:
            return False
        if not lobby.host_id:
            return True
        players = await self.repo.get_players(lobby.id)
        return any(
            player.id == lobby.host_id and player.status == schemas.ConnectionStatus.CONNECTED
            for player in players
        )

    async def _resolve_evaluation_type(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> EvaluationType:
        evaluation_type = step.evaluation.type_
        if evaluation_type != EvaluationType.HOST_JUDGED or await self._has_active_host_player(
            lobby
        ):
            return evaluation_type
        return self._fallback_evaluation_type(step.player_input)

    async def resolve_evaluation_type(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> EvaluationType:
        return await self._resolve_evaluation_type(lobby, step)

    def _fallback_evaluation_type(
        self,
        player_input: PlayerInputDefinition,
    ) -> EvaluationType:
        if player_input.kind == PlayerInputKind.TEXT:
            return EvaluationType.EXACT_TEXT
        if player_input.kind == PlayerInputKind.RADIO:
            return EvaluationType.EXACT_TEXT
        if player_input.kind == PlayerInputKind.NUMBER:
            return EvaluationType.EXACT_NUMBER
        if player_input.kind == PlayerInputKind.ORDERING:
            return EvaluationType.ORDERING_MATCH
        if player_input.kind == PlayerInputKind.CHECKBOX:
            return EvaluationType.NONE
        if player_input.kind == PlayerInputKind.MAP:
            return EvaluationType.MAP_DISTANCE
        if player_input.kind == PlayerInputKind.DRAWING:
            return EvaluationType.NONE
        return EvaluationType.NONE

    async def _all_answerable_players_submitted(
        self,
        lobby: schemas.Lobby,
        step_state: dict[str, Any] | None = None,
    ) -> bool:
        players = await self.repo.get_players(lobby.id)
        answerable_player_ids = {
            player.id for player in players if player.id and player.id != lobby.host_id
        }
        if step_state is not None:
            state = step_state
        elif self.get_step_state is not None:
            state = await self.get_step_state(lobby.id)
        else:
            state = {}
        submitted_player_ids = set(state.get("answers", {}).keys())
        return answerable_player_ids <= submitted_player_ids

    async def all_answerable_players_submitted(
        self,
        lobby: schemas.Lobby,
        step_state: dict[str, Any] | None = None,
    ) -> bool:
        return await self._all_answerable_players_submitted(lobby, step_state)

    def is_information_slide(self, step: StepDefinition) -> bool:
        return self._is_information_slide(step)

    def _is_information_slide(self, step: StepDefinition) -> bool:
        return (
            step.player_input.kind == PlayerInputKind.NONE
            and step.evaluation.type_ == EvaluationType.NONE
        )

    def _has_usable_answer_for_evaluation(
        self,
        step: StepDefinition,
        evaluation_type: EvaluationType,
    ) -> bool:
        answer = step.evaluation.answer
        if evaluation_type in (EvaluationType.EXACT_TEXT,):
            return bool(self._exact_text_answers(step))
        if evaluation_type in (EvaluationType.EXACT_NUMBER, EvaluationType.CLOSEST_NUMBER):
            try:
                return answer is not None and float(answer) == float(answer)
            except TypeError, ValueError:
                return False
        if evaluation_type == EvaluationType.ORDERING_MATCH:
            return isinstance(answer, list) and any(str(value).strip() for value in answer)
        if evaluation_type == EvaluationType.MULTI_SELECT_WEIGHTED:
            option_scores = answer.get("option_scores") if isinstance(answer, dict) else None
            return isinstance(option_scores, list) and len(option_scores) > 0
        if evaluation_type == EvaluationType.MAP_DISTANCE:
            return self._map_distance_answer(step) is not None
        return False

    def _is_hostless_auto_progress_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        if lobby.host_enabled or self._is_information_slide(step):
            return False
        evaluation_type = (
            self._fallback_evaluation_type(step.player_input)
            if step.evaluation.type_ == EvaluationType.HOST_JUDGED
            else step.evaluation.type_
        )
        return (
            evaluation_type in HOSTLESS_AUTO_EVALUATION_TYPES
            and self._has_usable_answer_for_evaluation(step, evaluation_type)
        )

    async def _should_auto_close_on_all_submissions(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        if await self._has_active_host_player(lobby) or self._is_information_slide(step):
            return False
        evaluation_type = await self._resolve_evaluation_type(lobby, step)
        return (
            evaluation_type in HOSTLESS_AUTO_EVALUATION_TYPES
            and self._has_usable_answer_for_evaluation(step, evaluation_type)
        )

    async def should_auto_close_on_all_submissions(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return await self._should_auto_close_on_all_submissions(lobby, step)

    async def is_timer_effectively_enforced(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return await self._is_timer_effectively_enforced(lobby, step)

    async def _is_timer_effectively_enforced(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return step.timer.enforced or await self._should_auto_close_on_all_submissions(lobby, step)

    def _is_hostless_compatible_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        if lobby.host_enabled:
            return True
        if step.player_input.kind == PlayerInputKind.BUZZER:
            return False
        if step.player_input.kind == PlayerInputKind.DRAWING:
            return False
        if self._is_information_slide(step):
            return True
        return self._is_hostless_auto_progress_step(lobby, step)

    def is_hostless_compatible_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return self._is_hostless_compatible_step(lobby, step)

    def is_hostless_auto_progress_step(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return self._is_hostless_auto_progress_step(lobby, step)

    async def should_skip_answer_reveal(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return await self._should_skip_answer_reveal(lobby, step)

    async def _should_skip_answer_reveal(
        self,
        lobby: schemas.Lobby,
        step: StepDefinition,
    ) -> bool:
        return await self._resolve_evaluation_type(lobby, step) == EvaluationType.NONE

    def _exact_text_answers(self, step: StepDefinition) -> list[str]:
        answer = step.evaluation.answer
        if isinstance(answer, list):
            return [normalized for value in answer if (normalized := str(value).strip().casefold())]
        if isinstance(answer, str):
            normalized = answer.strip().casefold()
            return [normalized] if normalized else []
        return []

    def exact_text_answers(self, step: StepDefinition) -> list[str]:
        return self._exact_text_answers(step)

    def _matches_exact_text_answer(
        self,
        value: Any,
        accepted_answers: list[str],
        max_distance: int,
    ) -> bool:
        submitted = str(value).strip().casefold()
        if not submitted or not accepted_answers:
            return False
        distance = max(0, max_distance)
        return any(
            self._levenshtein_distance(submitted, answer, distance) <= distance
            for answer in accepted_answers
        )

    def matches_exact_text_answer(
        self,
        value: Any,
        accepted_answers: list[str],
        max_distance: int,
    ) -> bool:
        return self._matches_exact_text_answer(value, accepted_answers, max_distance)

    def is_valid_drawing_submission(self, value: Any) -> bool:
        return self._is_valid_drawing_submission(value)

    def _is_valid_drawing_submission(self, value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        if len(str(value)) > MAX_DRAWING_PAYLOAD_CHARS:
            return False
        if (
            value.get("width") != DRAWING_CANVAS_WIDTH
            or value.get("height") != DRAWING_CANVAS_HEIGHT
        ):
            return False
        strokes = value.get("strokes")
        if not isinstance(strokes, list) or not strokes or len(strokes) > MAX_DRAWING_STROKES:
            return False

        total_points = 0
        for stroke in strokes:
            if not isinstance(stroke, dict):
                return False
            color = stroke.get("color")
            size = stroke.get("size")
            eraser = stroke.get("eraser", False)
            points = stroke.get("points")
            if not isinstance(color, str) or color.lower() not in DRAWING_COLORS:
                return False
            if not isinstance(size, int | float) or size < 2 or size > 32:
                return False
            if not isinstance(eraser, bool):
                return False
            if not isinstance(points, list) or len(points) < 1:
                return False
            total_points += len(points)
            if total_points > MAX_DRAWING_POINTS:
                return False
            for point in points:
                if not isinstance(point, dict):
                    return False
                x = self.timing.to_float(point.get("x"))
                y = self.timing.to_float(point.get("y"))
                if x is None or y is None or x < 0 or x > 1 or y < 0 or y > 1:
                    return False
        return True

    def _drawing_label(self, index: int) -> str:
        letters = ""
        value = index
        while True:
            letters = chr(ord("A") + (value % 26)) + letters
            value = value // 26 - 1
            if value < 0:
                break
        return f"{DRAWING_LABEL_PREFIX} {letters}"

    def drawing_label(self, index: int) -> str:
        return self._drawing_label(index)

    def _levenshtein_distance(self, left: str, right: str, max_distance: int) -> int:
        if left == right:
            return 0
        if abs(len(left) - len(right)) > max_distance:
            return max_distance + 1
        if len(left) > len(right):
            left, right = right, left

        previous = list(range(len(left) + 1))
        for right_index, right_char in enumerate(right, start=1):
            current = [right_index]
            row_min = current[0]
            for left_index, left_char in enumerate(left, start=1):
                insert_cost = current[left_index - 1] + 1
                delete_cost = previous[left_index] + 1
                replace_cost = previous[left_index - 1] + (left_char != right_char)
                current.append(min(insert_cost, delete_cost, replace_cost))
                row_min = min(row_min, current[-1])
            if row_min > max_distance:
                return max_distance + 1
            previous = current
        return previous[-1]
