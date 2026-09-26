"""Editorial selection policy for familiar Estonian shopping questions."""

import re
from collections import Counter

from partygame.schemas.price_game import PriceProduct

GENERATOR_VERSION = "price-v2"
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
    return product.retailer, product.category


def familiar(product: PriceProduct) -> bool:
    if product.product_range == "groceries":
        return bool(LOCAL_GROCERY_BRANDS.search(product.title)) and product.price_minor <= 3000
    return any(word in product.category.casefold() for word in HOUSEHOLD_ELECTRONICS)


def select_varied(bundles: list[list[PriceProduct]], count: int, usage: Counter):
    """Input order is seeded; favour unused categories, then familiar products.

    Bundles are already disjoint. Reordering them cannot change matching capacity.
    """
    remaining = list(bundles)
    selected = []
    for _ in range(count):
        index = min(
            range(len(remaining)),
            key=lambda i: (
                usage[category_key(remaining[i][0])],
                -sum(familiar(p) for p in remaining[i]),
            ),
        )
        bundle = remaining.pop(index)
        usage[category_key(bundle[0])] += 1
        selected.append(bundle)
    return selected


def sequence_varied(indices, selected):
    """Avoid consecutive categories whenever another category remains."""
    remaining = list(indices)
    order = []
    previous = None
    while remaining:
        counts = Counter(category_key(selected[i][0]) for i in remaining)
        index = min(
            range(len(remaining)),
            key=lambda j: (
                category_key(selected[remaining[j]][0]) == previous,
                -counts[category_key(selected[remaining[j]][0])],
            ),
        )
        item = remaining.pop(index)
        order.append(item)
        previous = category_key(selected[item][0])
    return order
