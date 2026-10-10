"""Editorial selection policy for familiar Estonian shopping questions."""

import re
from collections import Counter

from partygame.schemas.price_game import PriceProduct

GENERATOR_VERSION = "price-v4"
LOCAL_GROCERY_BRANDS = re.compile(
    r"\b(alma|tere|valio|kalev|põltsamaa|salvest|rakvere|maks & moorits|"
    r"saaremaa|farmi|leibur|eesti pagar|a. le coq|saku|rimi)\b",
    re.IGNORECASE,
)
HOUSEHOLD_ELECTRONICS = (
    "nutitelefon",
    "sulearvut",
    "sülearvut",
    "teler",
    "monitor",
    "korvaklap",
    "kõrvaklap",
    "kohvimasin",
    "veekeet",
    "tolmuime",
    "pesumasin",
    "kulmik",
    "külmik",
    "mikrolaine",
    "tahvelarvut",
    "nutikell",
    "mangukonsool",
    "mängukonsool",
    "kolar",
    "kõlar",
)


def category_key(product: PriceProduct):
    return product.product_range, product.retailer, product.category


def familiar(product: PriceProduct) -> bool:
    if product.product_range == "groceries":
        return bool(LOCAL_GROCERY_BRANDS.search(product.title)) and product.price_minor <= 3000
    return any(word in product.category.casefold() for word in HOUSEHOLD_ELECTRONICS)


def variety_rank(bundle, usage):
    """Count both cards; a large source must not crowd out smaller categories."""
    ranges = [usage[p.product_range] for p in bundle]
    categories = [usage[category_key(p)] for p in bundle]
    return max(ranges), sum(ranges), max(categories), sum(categories), -sum(map(familiar, bundle))


def record_usage(bundle, usage):
    for product in bundle:
        usage[product.product_range] += 1
        usage[category_key(product)] += 1


def select_varied(bundles: list[list[PriceProduct]], count: int, usage: Counter):
    remaining = list(bundles)
    selected = []
    for _ in range(count):
        index = min(range(len(remaining)), key=lambda i: variety_rank(remaining[i], usage))
        bundle = remaining.pop(index)
        record_usage(bundle, usage)
        selected.append(bundle)
    return selected


def mode_lag(totals, placed, kind, previous_kind):
    """Keep guesses and comparisons evenly spread: the kind furthest behind its share goes next."""
    return placed[kind] / totals[kind], kind == previous_kind


def sequence_varied(indices, selected):
    """Interleave question kinds, then minimize category overlap with the preceding question."""
    remaining = list(indices)
    order = []
    previous = set()
    previous_kind = None
    totals = Counter(len(selected[i]) for i in remaining)
    placed = Counter()
    while remaining:
        keys = {i: {category_key(p) for p in selected[i]} for i in remaining}
        counts = Counter(key for values in keys.values() for key in values)
        index = min(
            range(len(remaining)),
            key=lambda j: (
                mode_lag(totals, placed, len(selected[remaining[j]]), previous_kind),
                len(keys[remaining[j]] & previous),
                # Averaged so two-card comparisons are not favoured over single guesses.
                -sum(counts[key] for key in keys[remaining[j]]) / len(keys[remaining[j]]),
            ),
        )
        item = remaining.pop(index)
        order.append(item)
        previous = keys[item]
        previous_kind = len(selected[item])
        placed[previous_kind] += 1
    return order
