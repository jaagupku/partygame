from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any


def parse_euros(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        amount = Decimal(str(value))
        if (
            not amount.is_finite()
            or amount < 0
            or amount > Decimal(1000000000)
            or amount.as_tuple().exponent < -2
        ):
            return None
        cents = amount * 100
        if cents != cents.to_integral_value():
            return None
        return int(cents)
    except InvalidOperation, ValueError:
        return None


def price_points(value: Any, target_minor: int) -> int:
    guess = parse_euros(value)
    if guess is None or target_minor <= 0:
        return 0
    closeness = max(Decimal(0), 1 - Decimal(abs(guess - target_minor)) / target_minor)
    return int((1000 * closeness).quantize(Decimal(1), rounding=ROUND_HALF_UP))
