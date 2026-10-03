from collections import Counter
from random import Random

from partygame.schemas.calorie_game import (
    CalorieCard,
    CalorieGameSettings,
    CalorieProduct,
    CalorieQuestion,
    CalorieReveal,
)
from partygame.schemas.game_definition import (
    EvaluationRule,
    HostBehavior,
    PlayerInputDefinition,
    RoundDefinition,
    StepDefinition,
    TimerDefinition,
)
from partygame.schemas.game_session import DatasetSnapshot, RoundBundle, SourceMetadata
from partygame.service.prices.matching import maximum_pairs

GENERATOR_VERSION = "calories-v1"


class InsufficientCalorieData(ValueError):
    pass


def products_from(dataset):
    products = [CalorieProduct.model_validate(p) for p in dataset.records]
    return sorted({p.id: p for p in products}.values(), key=lambda p: p.id)


def graph(products):
    return [
        [
            j
            for j, q in enumerate(products)
            if p.id != q.id and p.basis == q.basis and p.kcal != q.kcal
        ]
        for p in products
    ]


def pair_count(settings):
    return (
        settings.questions
        if settings.mode == "compare"
        else settings.questions // 2 if settings.mode == "mixed" else 0
    )


def has_capacity(settings, products):
    pairs = pair_count(settings)
    return len(products) >= settings.questions + pairs and (
        not pairs or len(maximum_pairs(graph(products))) >= pairs
    )


def select(settings, products, rng):
    rng.shuffle(products)
    # Add international content only until the Estonian pool can complete the game.
    pool = [p for p in products if p.estonia]
    others = [p for p in products if not p.estonia]
    rng.shuffle(others)
    while not has_capacity(settings, pool):
        if not others:
            raise InsufficientCalorieData("Not enough distinct products")
        pool.append(others.pop())
    usage = Counter()
    selected = []
    for remaining in range(pair_count(settings) - 1, -1, -1):
        edges = graph(pool)
        candidates = [(a, b) for a in range(len(pool)) for b in edges[a] if b > a]
        candidates.sort(
            key=lambda pair: (
                sum(not pool[i].estonia for i in pair),
                sum(usage[pool[i].category] for i in pair),
                pool[pair[0]].category == pool[pair[1]].category,
            )
        )
        for a, b in candidates:
            rest = [p for i, p in enumerate(pool) if i not in (a, b)]
            if remaining and len(maximum_pairs(graph(rest))) < remaining:
                continue
            pair = [pool[a], pool[b]]
            rng.shuffle(pair)
            selected.append(pair)
            usage.update(p.category for p in pair)
            pool = rest
            break
        else:
            raise InsufficientCalorieData("Not enough comparable products")
    while len(selected) < settings.questions:
        item = min(pool, key=lambda p: (not p.estonia, usage[p.category]))
        selected.append([item])
        usage[item.category] += 1
        pool.remove(item)
    rng.shuffle(selected)
    return selected


class CalorieGenerator:
    def generate(
        self, settings: CalorieGameSettings, *, seed: int, dataset: DatasetSnapshot
    ) -> list[RoundBundle]:
        selected = select(settings, products_from(dataset), Random(seed))
        steps = []
        for index, items in enumerate(selected):
            mode = "guess" if len(items) == 1 else "compare"
            cards = [
                CalorieCard(
                    id=str(i), title=p.title, detail=p.detail, image_url=p.image_url, basis=p.basis
                )
                for i, p in enumerate(items)
            ]
            reveal = [
                CalorieReveal(
                    id=str(i),
                    kcal=p.kcal,
                    basis=p.basis,
                    source_url=p.source_url,
                    captured_at=p.captured_at,
                )
                for i, p in enumerate(items)
            ]
            steps.append(
                StepDefinition(
                    id=f"calorie-{index}",
                    title=" / ".join(p.title for p in items),
                    timer=TimerDefinition(seconds=settings.answer_seconds, enforced=True),
                    player_input=PlayerInputDefinition(
                        kind="number" if mode == "guess" else "radio",
                        options=[] if mode == "guess" else [c.id for c in cards],
                        min_value=0 if mode == "guess" else None,
                        step=1 if mode == "guess" else None,
                    ),
                    evaluation=EvaluationRule(
                        type_="calorie_closeness" if mode == "guess" else "exact_text",
                        points=1000,
                        answer=(
                            items[0].kcal
                            if mode == "guess"
                            else str(max(range(2), key=lambda i: items[i].kcal))
                        ),
                    ),
                    host_behavior=HostBehavior(allow_custom_points=False),
                    calorie_question=CalorieQuestion(
                        mode=mode,
                        products=cards,
                        reveal=reveal,
                        reveal_seconds=settings.reveal_seconds,
                    ),
                )
            )
        return [
            RoundBundle(
                rounds=[RoundDefinition(id="calories", steps=steps)],
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
