from collections import Counter
from itertools import combinations
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from partygame.schemas.price_catalog import PRODUCT_RANGES, SOURCE_RANGES
from partygame.schemas.price_game import PriceGameSettings, PriceProduct
from partygame.service.prices.datasets import PriceDatasets
from partygame.service.prices.generator import (
    InsufficientPriceData,
    PriceGenerator,
    comparable,
    comparison_graph,
    select_pairs,
)
from partygame.service.prices.home_sources import parse_eantiik, parse_tootemaailm, product_links
from tests.test_price_game import CAPTURED, FIXTURES, dataset

SELECTIONS = [
    list(group)
    for size in range(1, len(PRODUCT_RANGES) + 1)
    for group in combinations(PRODUCT_RANGES, size)
]


def all_categories():
    source = dataset()
    originals = source.records[:40]
    source.records = [
        dict(
            p,
            retailer=retailer,
            product_range=product_range,
            id=str(i),
            category=f"category-{i % 3}",
            source_url=f"https://{retailer}.ee/{i}",
        )
        for retailer, product_range in SOURCE_RANGES.items()
        for i, p in enumerate(originals)
    ]
    return source


@pytest.mark.parametrize("ranges", SELECTIONS)
@pytest.mark.parametrize("mode", ["guess", "compare", "mixed"])
@pytest.mark.parametrize("count", [5, 10, 15, 20])
def test_all_category_selections_generate_unique_deterministic_games(ranges, mode, count):
    source = all_categories()
    settings = PriceGameSettings(mode=mode, product_ranges=ranges, questions=count)
    generator = PriceGenerator()
    for seed in (0, 7):
        result = generator.generate(settings, seed=seed, dataset=source)
        assert result == generator.generate(settings, seed=seed, dataset=source)
        steps = result[0].rounds[0].steps
        assert len(steps) == count
        reveals = [p for step in steps for p in step.price_question.reveal]
        assert len({p.source_url for p in reveals}) == len(reveals)
        assert {SOURCE_RANGES[p.retailer] for p in reveals} == set(ranges)
        comparisons = [step for step in steps if step.price_question.mode == "compare"]
        assert len(comparisons) == (
            count // 2 if mode == "mixed" else count if mode == "compare" else 0
        )
        if comparisons and len(ranges) > 1:
            assert any(
                s.price_question.reveal[0].retailer != s.price_question.reveal[1].retailer
                for s in comparisons
            )
        for step in comparisons:
            left, right = step.price_question.reveal
            low, high = sorted((left.price_minor, right.price_minor))
            assert 11 * low <= 10 * high <= 30 * low
            assert step.evaluation.answer == str(int(right.price_minor > left.price_minor))


@pytest.mark.parametrize("value", [[], ["unknown"], ["furniture", "furniture"], "furniture"])
def test_category_settings_reject_invalid_selection(value):
    with pytest.raises(ValidationError):
        PriceGameSettings(product_ranges=value)


def test_settings_normalize_legacy_requests_and_reject_conflicts():
    assert PriceGameSettings(product_range="both").product_ranges == ["groceries", "electronics"]
    assert PriceGameSettings(product_range="groceries").product_ranges == ["groceries"]
    assert PriceGameSettings(product_ranges=["antiques", "furniture"]).product_ranges == [
        "furniture",
        "antiques",
    ]
    with pytest.raises(ValidationError):
        PriceGameSettings(product_range="both", product_ranges=["furniture"])
    with pytest.raises(ValidationError):
        PriceGameSettings(product_range="furniture")


def test_pair_identity_and_price_boundaries():
    a = PriceProduct.model_validate(all_categories().records[0])
    a.price_minor = 100
    for price, expected in [(100, False), (109, False), (110, True), (300, True), (301, False)]:
        b = a.model_copy(
            update={"retailer": "klick", "product_range": "electronics", "price_minor": price}
        )
        assert comparable(a, b) is expected
    assert not comparable(a, a.model_copy(update={"price_minor": 110}))


def test_cross_category_preference_never_destroys_matching_capacity():
    base = PriceProduct.model_validate(all_categories().records[0])
    # Choosing the tempting cross-category 12/31 pair strands 10 and 35.
    products = [
        base.model_copy(
            update={
                "id": str(i),
                "price_minor": price,
                "product_range": "furniture" if i < 2 else "electronics",
            }
        )
        for i, price in enumerate((1000, 1200, 3100, 3500))
    ]
    pairs = select_pairs(products, comparison_graph(products), 2, Counter())
    assert {frozenset(p.price_minor for p in pair) for pair in pairs} == {
        frozenset((1000, 1200)),
        frozenset((3100, 3500)),
    }


@pytest.mark.asyncio
async def test_availability_matches_creation_for_all_selections_and_seeds():
    source = all_categories()
    records = {
        retailer: SimpleNamespace(
            id=retailer,
            source=retailer,
            captured_at=CAPTURED,
            products=[p for p in source.records if p["retailer"] == retailer],
        )
        for retailer in SOURCE_RANGES
    }
    session = AsyncMock()
    session.__aenter__.return_value = session
    store = PriceDatasets(sessionmaker=lambda: session)
    store.latest = AsyncMock(return_value=records)
    available = await store.availability()
    assert len(available["ranges"]) == len(PRODUCT_RANGES)
    assert len(available["combinations"]) == 12 * (2 ** len(PRODUCT_RANGES) - 1)
    for config in available["combinations"]:
        for seed in (0, 19):
            PriceGenerator().generate(PriceGameSettings(**config), seed=seed, dataset=source)
    store.latest = AsyncMock(return_value={"klick": records["klick"]})
    available = await store.availability()
    assert all(c["product_ranges"] == ["electronics"] for c in available["combinations"])
    # A missing source must fail before generation or lease creation.
    session.begin = lambda: AsyncMock()
    with pytest.raises(InsufficientPriceData):
        await store.prepare(PriceGameSettings(product_ranges=["furniture"]), 0, "missing")


def test_captured_furniture_regular_price_and_fail_closed_variants():
    html = (FIXTURES / "tootemaailm.html").read_text()
    product = parse_tootemaailm(html, CAPTURED)[0]
    assert product.price_minor == 29553
    assert product.category == "Diivanilauad"
    assert product.image_url.startswith("https://media.tootemaailm.ee/")
    for old, new in [
        ("product-type-simple", "product-type-variable"),
        ("/InStock", "/OutOfStock"),
        ('"EUR"', '"USD"'),
        ("<del", "<unknown"),
        ("295.53", "alates 295.53"),
    ]:
        assert parse_tootemaailm(html.replace(old, new), CAPTURED) == []


def test_captured_antique_and_vintage_classification_and_details():
    antique = (FIXTURES / "eantiik-antique.html").read_text()
    vintage = (FIXTURES / "eantiik-vintage.html").read_text()
    product = parse_eantiik(antique, CAPTURED)[0]
    assert (product.category, product.price_minor) == ("clocks", 34500)
    assert "1920" in product.detail and "kullatud puit" in product.detail
    assert parse_eantiik(vintage, CAPTURED)[0].category == "furniture"
    assert parse_eantiik(vintage.replace("2000", "2025"), CAPTURED) == []
    assert parse_eantiik(antique.replace("list_price", "unknown_price"), CAPTURED) == []
    assert parse_eantiik(antique.replace("Antiik", "Uus"), CAPTURED) == []
    assert parse_eantiik(antique.replace('id="add_to_cart"', 'id="sold"'), CAPTURED) == []
    assert (
        parse_eantiik(
            antique.replace('id="add_to_cart"', 'disabled="disabled" id="add_to_cart"'), CAPTURED
        )
        == []
    )
    assert parse_eantiik(antique.replace("Seinakell", "Seinakell müüdud"), CAPTURED) == []


@pytest.mark.asyncio
async def test_home_discovery_interleaves_and_respects_total_page_budget(monkeypatch):
    from partygame.service.prices import refresh

    visited = []

    async def page(url):
        visited.append(url)
        if url in refresh.ANTIQUE_LISTINGS:
            index = refresh.ANTIQUE_LISTINGS.index(url)
            return (
                '<form class="oe_product_cart">'
                + "".join(f'<a href="/shop/product/{index}-{i}">Item</a>' for i in range(5))
                + "</form>"
            )
        return ""

    monkeypatch.setattr(refresh, "page", page)
    await refresh.collect("eantiik", max_pages=10)
    assert len(visited) == 10
    assert visited[6:] == [f"https://www.e-antiik.ee/shop/product/{i}-0" for i in range(4)]
    assert product_links('<a href="/shop/product/unrelated">x</a>', "eantiik") == []


def test_low_price_category_is_not_crowded_out_by_cross_category_pairs():
    source = all_categories()
    for p in source.records:
        if p["product_range"] != "groceries":
            p["price_minor"] *= 100
    steps = (
        PriceGenerator()
        .generate(
            PriceGameSettings(mode="compare", product_ranges=list(PRODUCT_RANGES), questions=20),
            seed=3,
            dataset=source,
        )[0]
        .rounds[0]
        .steps
    )
    appearances = Counter(
        SOURCE_RANGES[p.retailer] for step in steps for p in step.price_question.reveal
    )
    assert set(appearances) == set(PRODUCT_RANGES)
    assert max(appearances.values()) - min(appearances.values()) <= 2
    assert any(
        step.price_question.reveal[0].retailer != step.price_question.reveal[1].retailer
        for step in steps
    )
