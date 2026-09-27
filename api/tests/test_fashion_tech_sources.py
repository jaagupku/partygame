from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from partygame.schemas.price_game import PriceGameSettings
from partygame.service.prices import refresh
from partygame.service.prices.datasets import PriceDatasets
from partygame.service.prices.fashion_tech_sources import LISTINGS, PARSERS, product_links
from tests.test_price_categories import all_categories
from tests.test_price_game import CAPTURED, FIXTURES


@pytest.mark.parametrize(
    "source,price,category",
    [
        ("arvutitark", 29990, "Protsessorid (CPU)"),
        ("reserved", 1999, "T-shirts"),
    ],
)
def test_captured_retailer_products(source, price, category):
    products = PARSERS[source]((FIXTURES / f"{source}.html").read_text(), CAPTURED, "T-shirts")
    assert len(products) == 1
    product = products[0]
    assert (product.price_minor, product.category, product.retailer) == (price, category, source)
    assert product.image_url.startswith("https://")
    assert product.captured_at == CAPTURED


@pytest.mark.parametrize(
    "source,old,new",
    [
        ("arvutitark", '"original_price": 299.9', '"original_price": 399.9'),
        ("reserved", '"regularPrice": 19.99', '"regularPrice": 29.99'),
    ],
)
def test_regular_prices_win_over_discount_prices(source, old, new):
    html = (FIXTURES / f"{source}.html").read_text().replace(old, new)
    if source == "reserved":
        html = html.replace('content="19.99"', 'content="29.99"')
    product = PARSERS[source](html, CAPTURED, "T-shirts")[0]
    assert product.price_minor == (39990 if source == "arvutitark" else 2999)


@pytest.mark.parametrize(
    "source,old,new",
    [
        ("arvutitark", '"active": true', '"active": false'),
        ("arvutitark", '"original_price": 299.9', '"original_price": null'),
        ("arvutitark", '"original_price": 299.9', '"original_price": 100'),
        ("arvutitark", '"can_be_sold": true', '"can_be_sold": false'),
        ("arvutitark", "/InStock", "/OutOfStock"),
        ("reserved", '"isSaleable": true', '"isSaleable": false'),
        ("reserved", '"isInStock": true', '"isInStock": false'),
        ("reserved", '"isBlocked": false', '"isBlocked": true'),
        ("reserved", '"regularPrice": 19.99', '"regularPrice": null'),
        ("reserved", '"regularPrice": 19.99', '"regularPrice": 9.99'),
    ],
)
def test_rejects_ambiguous_prices_and_unavailable_or_unrelated_products(source, old, new):
    html = (FIXTURES / f"{source}.html").read_text()
    assert old in html
    assert PARSERS[source](html.replace(old, new), CAPTURED, "T-shirts") == []


@pytest.mark.parametrize("source", PARSERS)
def test_rejects_wrong_currency_and_foreign_images(source):
    html = (FIXTURES / f"{source}.html").read_text()
    assert PARSERS[source](html.replace("EUR", "USD"), CAPTURED, "T-shirts") == []
    for host in ("media.arvutitark.ee", "static.reserved.com"):
        if host in html:
            assert (
                PARSERS[source](html.replace(host, "unknown.example"), CAPTURED, "T-shirts") == []
            )


@pytest.mark.parametrize("source", PARSERS)
@pytest.mark.asyncio
async def test_discovery_interleaves_and_counts_listing_pages(monkeypatch, source):
    visited = []

    def link(index, item):
        if source == "arvutitark":
            return f"https://arvutitark.ee/category/item-{index}-{item}"
        if source == "reserved":
            return f"https://www.reserved.com/ee/et/item-{index}{item}abc-01x"

    async def page(url):
        visited.append(url)
        for i, (listing, _) in enumerate(LISTINGS[source]):
            if url == listing:
                return "".join(
                    f'<a class="catalogue-product-link" href="{link(i, j)}">Item</a>'
                    for j in range(4)
                )
        return ""

    monkeypatch.setattr(refresh, "page", page)
    count = len(LISTINGS[source])
    assert await refresh.collect(source, max_pages=count + 2) == []
    assert len(visited) == count + 2
    assert visited[-2:] == [link(0, 0), link(1, 0)]
    assert (
        product_links(
            '<a class="catalogue-product-link" href="https://unknown.example/item">x</a>', source
        )
        == []
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sources", [("klick",), ("arvutitark",), ("reserved",), ("klick", "arvutitark")]
)
async def test_partial_source_availability_and_prepare_agree(sources):
    records = all_categories().records
    latest = {
        s: SimpleNamespace(
            id=s,
            source=s,
            captured_at=CAPTURED + timedelta(days=i),
            products=[p for p in records if p["retailer"] == s],
        )
        for i, s in enumerate(sources)
    }
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.begin = lambda: AsyncMock()
    session.add = lambda _: None
    store = PriceDatasets(sessionmaker=lambda: session)
    store.latest = AsyncMock(return_value=latest)
    availability = await store.availability()
    assert len(availability["ranges"]) == 5
    active = [r for r in availability["ranges"] if r["available"]]
    assert len(active) == 1
    assert active[0]["captured_at"] == CAPTURED
    assert len(availability["combinations"]) == 12
    for mode in ["guess", "compare", "mixed"]:
        _, provenance = await store.prepare(
            PriceGameSettings(mode=mode, product_ranges=[active[0]["product_range"]]), 0, "partial"
        )
        assert {p["source_id"] for p in provenance} == set(sources)
