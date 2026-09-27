from collections import Counter
from random import Random

from partygame.schemas.game_definition import (
    EvaluationRule,
    HostBehavior,
    PlayerInputDefinition,
    RoundDefinition,
    StepDefinition,
    TimerDefinition,
)
from partygame.schemas.game_session import DatasetSnapshot, RoundBundle, SourceMetadata
from partygame.schemas.price_game import (
    PriceCard,
    PriceGameSettings,
    PriceProduct,
    PriceQuestion,
    PriceReveal,
)
from partygame.service.prices.matching import maximum_pairs
from partygame.service.prices.selection import (
    GENERATOR_VERSION,
    record_usage,
    select_varied,
    sequence_varied,
    variety_rank,
)


class InsufficientPriceData(ValueError):
    pass


def comparable(left: PriceProduct, right: PriceProduct) -> bool:
    low, high = sorted((left.price_minor, right.price_minor))
    return (left.retailer, left.id) != (
        right.retailer,
        right.id,
    ) and 11 * low <= 10 * high <= 30 * low


def selected_products(dataset, ranges):
    products = [PriceProduct.model_validate(record) for record in dataset.records]
    unique = {(p.retailer, p.id): p for p in products if p.product_range in ranges}
    return sorted(unique.values(), key=lambda p: (p.retailer, p.id))


def comparison_graph(products):
    return [[j for j, right in enumerate(products) if comparable(left, right)] for left in products]


def comparison_count(settings):
    return (
        settings.questions // 2
        if settings.mode == "mixed"
        else settings.questions if settings.mode == "compare" else 0
    )


def has_capacity(settings, products_count, pairs_count):
    count = comparison_count(settings)
    return products_count >= settings.questions + count and pairs_count >= count


def select_pairs(products, graph, count, usage):
    """Prefer cross-category pairs without reducing remaining matching capacity."""
    active = set(range(len(products)))
    selected = []

    def matching(vertices):
        indices = sorted(vertices)
        positions = {index: i for i, index in enumerate(indices)}
        reduced = [[positions[j] for j in graph[i] if j in vertices] for i in indices]
        return {(indices[a], indices[b]) for a, b in maximum_pairs(reduced)}

    pairs = matching(active)
    if len(pairs) < count:
        raise InsufficientPriceData("Not enough unique comparable products")
    while len(selected) < count:
        needed = count - len(selected) - 1
        candidates = [(a, b) for a in sorted(active) for b in graph[a] if b > a and b in active]

        def rank(edge):
            bundle = [products[i] for i in edge]
            variety = variety_rank(bundle, usage)
            return (
                variety[:2],
                bundle[0].product_range == bundle[1].product_range,
                variety[2:],
            )

        candidates.sort(key=rank)
        for a, b in candidates:
            remaining = active - {a, b}
            if (a, b) in pairs:
                rest = pairs - {(a, b)}
            else:
                rest = matching(remaining) if needed else set()
            if len(rest) < needed:
                continue
            bundle = [products[a], products[b]]
            selected.append(bundle)
            record_usage(bundle, usage)
            active = remaining
            pairs = rest
            break
        else:
            raise InsufficientPriceData("Not enough unique comparable products")
    return selected


class PriceGenerator:
    def generate(
        self, settings: PriceGameSettings, *, seed: int, dataset: DatasetSnapshot
    ) -> list[RoundBundle]:
        rng = Random(seed)
        products = selected_products(dataset, settings.product_ranges)
        rng.shuffle(products)
        compare_count = comparison_count(settings)
        if len(products) < settings.questions + compare_count:
            raise InsufficientPriceData("Not enough unique comparable products")
        usage = Counter()
        pairs = (
            select_pairs(products, comparison_graph(products), compare_count, usage)
            if compare_count
            else []
        )
        used = {(p.retailer, p.id) for pair in pairs for p in pair}
        singles = [[p] for p in products if (p.retailer, p.id) not in used]
        guesses = select_varied(singles, settings.questions - compare_count, usage)
        selected = dict(enumerate(pairs + guesses))
        for pair in pairs:
            rng.shuffle(pair)
        order = list(range(settings.questions))
        rng.shuffle(order)
        order = sequence_varied(order, selected)
        steps = []
        for index in order:
            mode = "compare" if len(selected[index]) == 2 else "guess"
            items = selected[index]
            cards = [
                PriceCard(id=str(i), title=p.title, detail=p.detail, image_url=p.image_url)
                for i, p in enumerate(items)
            ]
            reveal = [
                PriceReveal(
                    id=str(i),
                    price_minor=p.price_minor,
                    retailer=p.retailer,
                    source_url=p.source_url,
                    captured_at=p.captured_at,
                )
                for i, p in enumerate(items)
            ]
            steps.append(
                StepDefinition(
                    id=f"price-{index}",
                    title=items[0].title if mode == "guess" else " / ".join(p.title for p in items),
                    timer=TimerDefinition(seconds=settings.answer_seconds, enforced=True),
                    player_input=PlayerInputDefinition(
                        kind="number" if mode == "guess" else "radio",
                        options=[] if mode == "guess" else [c.id for c in cards],
                        min_value=0 if mode == "guess" else None,
                        step=0.01 if mode == "guess" else None,
                    ),
                    evaluation=EvaluationRule(
                        type_="price_closeness" if mode == "guess" else "exact_text",
                        points=1000,
                        answer=(
                            items[0].price_minor
                            if mode == "guess"
                            else str(max(range(2), key=lambda i: items[i].price_minor))
                        ),
                    ),
                    host_behavior=HostBehavior(allow_custom_points=False),
                    price_question=PriceQuestion(
                        mode=mode,
                        products=cards,
                        reveal=reveal,
                        reveal_seconds=settings.reveal_seconds,
                    ),
                )
            )
        return [
            RoundBundle(
                rounds=[RoundDefinition(id="prices", steps=steps)],
                source=SourceMetadata(
                    source_id=dataset.source_id,
                    dataset_id=dataset.dataset_id,
                    dataset_version=dataset.version,
                    captured_at=dataset.captured_at,
                    generator_version=GENERATOR_VERSION,
                    seed=seed,
                ),
            )
        ]
