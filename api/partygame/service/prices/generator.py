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
from partygame.service.prices.selection import GENERATOR_VERSION, select_varied, sequence_varied


class InsufficientPriceData(ValueError):
    pass


def comparable(left: PriceProduct, right: PriceProduct) -> bool:
    low, high = sorted((left.price_minor, right.price_minor))
    return (
        left.id != right.id
        and left.retailer == right.retailer
        and left.category == right.category
        and 11 * low <= 10 * high <= 30 * low
    )


class PriceGenerator:
    def generate(
        self, settings: PriceGameSettings, *, seed: int, dataset: DatasetSnapshot
    ) -> list[RoundBundle]:
        rng = Random(seed)
        products = [PriceProduct.model_validate(record) for record in dataset.records]
        products = list({(p.retailer, p.id): p for p in products}.values())
        products.sort(key=lambda p: (p.retailer, p.id))
        ranges = (
            ["groceries", "electronics"]
            if settings.product_range == "both"
            else [settings.product_range]
        )
        modes = (
            ["guess"] * ((settings.questions + 1) // 2) + ["compare"] * (settings.questions // 2)
            if settings.mode == "mixed"
            else [settings.mode] * settings.questions
        )
        # Compute capacities before assigning modes to ranges, so a valid balanced
        # game cannot fail just because a seed assigned too many pairs to one range.
        pools = {pool: [p for p in products if p.product_range == pool] for pool in ranges}
        pair_pools = {}
        for pool, candidates in pools.items():
            groups: dict[tuple[str, str], list[PriceProduct]] = {}
            for product in candidates:
                groups.setdefault((product.retailer, product.category), []).append(product)
            pairs = []
            for group in groups.values():
                rng.shuffle(group)
                graph = [
                    [j for j, right in enumerate(group) if comparable(left, right)]
                    for left in group
                ]
                pairs.extend([group[left], group[right]] for left, right in maximum_pairs(graph))
            rng.shuffle(pairs)
            pair_pools[pool] = pairs
        counts = {
            pool: sum(ranges[i % len(ranges)] == pool for i in range(settings.questions))
            for pool in ranges
        }
        compare_count = modes.count("compare")
        allocations = []
        for first in range(compare_count + 1):
            allocation = [first] if len(ranges) == 1 else [first, compare_count - first]
            if sum(allocation) != compare_count:
                continue
            if all(
                count <= counts[pool]
                and count <= len(pair_pools[pool])
                and counts[pool] + count <= len(pools[pool])
                for pool, count in zip(ranges, allocation, strict=True)
            ):
                allocations.append(allocation)
        if not allocations:
            raise InsufficientPriceData("Not enough unique comparable products")
        allocation = rng.choice(allocations)
        specs = [
            (mode, pool)
            for pool, count in zip(ranges, allocation, strict=True)
            for mode in ["compare"] * count + ["guess"] * (counts[pool] - count)
        ]
        selected: dict[int, list[PriceProduct]] = {}
        category_usage = Counter()
        for product_range in ranges:
            candidates = pools[product_range]
            pairs = pair_pools[product_range]
            compare_slots = [
                i
                for i, (mode, pool) in enumerate(specs)
                if mode == "compare" and pool == product_range
            ]
            if len(pairs) < len(compare_slots):
                raise InsufficientPriceData("Not enough comparable products")
            used = set()
            chosen_pairs = select_varied(pairs, len(compare_slots), category_usage)
            for index, pair in zip(compare_slots, chosen_pairs, strict=True):
                rng.shuffle(pair)
                selected[index] = pair
                used.update((p.retailer, p.id) for p in pair)
            singles = [p for p in candidates if (p.retailer, p.id) not in used]
            rng.shuffle(singles)
            guess_slots = [
                i
                for i, (mode, pool) in enumerate(specs)
                if mode == "guess" and pool == product_range
            ]
            if len(singles) < len(guess_slots):
                raise InsufficientPriceData("Not enough unique products")
            chosen_singles = select_varied([[p] for p in singles], len(guess_slots), category_usage)
            for index, bundle in zip(guess_slots, chosen_singles, strict=True):
                selected[index] = bundle
        order = list(range(settings.questions))
        rng.shuffle(order)
        order = sequence_varied(order, selected)
        steps = []
        for index in order:
            mode = specs[index][0]
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
                    price_question=PriceQuestion(mode=mode, products=cards, reveal=reveal),
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
