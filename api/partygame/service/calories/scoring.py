from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any


def parse_calories(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        number = Decimal(str(value))
        if (
            not number.is_finite()
            or number < 0
            or number > 1000000
            or number != number.to_integral_value()
        ):
            return None
        return int(number)
    except InvalidOperation, ValueError:
        return None


def calorie_points(value: Any, target: int) -> int:
    guess = parse_calories(value)
    if guess is None or target <= 0:
        return 0
    closeness = max(Decimal(0), 1 - Decimal(abs(guess - target)) / target)
    return int((1000 * closeness).quantize(Decimal(1), rounding=ROUND_HALF_UP))
