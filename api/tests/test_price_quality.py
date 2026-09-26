from collections import Counter
from io import BytesIO
from itertools import pairwise

import pytest
from PIL import Image, ImageDraw

from partygame.schemas.price_game import PriceGameSettings
from partygame.service.prices.generator import PriceGenerator
from partygame.service.prices.quality import inspect_image, validate_dataset
from partygame.service.prices.selection import familiar
from partygame.service.prices.sources import money, parse_klick, parse_rimi
from tests.test_price_datasets import products
from tests.test_price_game import CAPTURED, FIXTURES, dataset


def picture(format_="PNG", size=(600, 600), blank=False):
    image = Image.new("RGB", size, "white")
    if not blank:
        ImageDraw.Draw(image).rectangle((20, 20, size[0] - 20, size[1] - 20), fill="navy")
    stream = BytesIO()
    image.save(stream, format=format_)
    return stream.getvalue()


@pytest.mark.parametrize("format_,suffix", [("PNG", "png"), ("JPEG", "jpg"), ("WEBP", "webp")])
def test_images_are_decoded_before_acceptance(format_, suffix):
    extension, mime, details = inspect_image(picture(format_))
    assert extension == suffix
    assert mime.startswith("image/")
    assert details["image_width"] == 600
    assert len(details["image_sha256"]) == 64


@pytest.mark.parametrize(
    "data",
    [
        b"RIFF0000WEBP",
        b"<html>broken</html>",
        picture(size=(80, 80)),
        picture(blank=True),
        picture("JPEG")[:100],
    ],
)
def test_unusable_images_are_rejected(data):
    with pytest.raises(ValueError):
        inspect_image(data)


def test_dataset_quality_gates_and_price_change_review():
    good = products()
    assert validate_dataset("rimi", good)["categories"] == 3
    for bad in [
        good[:5],
        [p.model_copy(update={"category": "one"}) for p in good],
        good + [good[0]],
        [p.model_copy(update={"image_width": 80}) for p in good],
    ]:
        with pytest.raises(ValueError):
            validate_dataset("rimi", bad)
    wrong_url = good.copy()
    wrong_url[-1] = wrong_url[-1].model_copy(update={"source_url": good[0].source_url})
    with pytest.raises(ValueError, match="Duplicate source URLs"):
        validate_dataset("rimi", wrong_url)
    changed = [p.model_copy(update={"price_minor": p.price_minor * 10}) for p in good]
    with pytest.raises(ValueError, match="50%"):
        validate_dataset("rimi", changed, good)
    assert validate_dataset("rimi", changed, good, accept_price_changes=True)[
        "reviewed_price_changes"
    ] == len(good)
    with pytest.raises(ValueError, match="coverage"):
        validate_dataset("rimi", good, good * 3)


def test_dataset_requires_twenty_comparison_questions():
    bad = [p.model_copy(update={"price_minor": 100}) for p in products()]
    with pytest.raises(ValueError, match="comparable"):
        validate_dataset("rimi", bad)


def test_question_selection_balances_categories_and_avoids_adjacent_repeats():
    source = dataset()
    records = [p.model_dump(mode="json") for p in products()]
    source = source.model_copy(update={"records": records})
    categories = {p.source_url: p.category for p in products()}
    for mode in ("guess", "compare", "mixed"):
        for seed in range(10):
            steps = (
                PriceGenerator()
                .generate(
                    PriceGameSettings(mode=mode, product_range="groceries", questions=15),
                    seed=seed,
                    dataset=source,
                )[0]
                .rounds[0]
                .steps
            )
            chosen = [categories[s.price_question.reveal[0].source_url] for s in steps]
            assert set(Counter(chosen).values()) == {5}
            assert all(a != b for a, b in pairwise(chosen))


def test_familiar_products_preferred_within_category():
    entries = products()
    for i, p in enumerate(entries):
        p.title = ("Tere milk " if i < 30 else "Specialty item ") + str(i)
    source = dataset().model_copy(update={"records": [p.model_dump(mode="json") for p in entries]})
    selected = (
        PriceGenerator()
        .generate(
            PriceGameSettings(mode="guess", product_range="groceries", questions=10),
            seed=42,
            dataset=source,
        )[0]
        .rounds[0]
        .steps
    )
    assert all(s.price_question.products[0].title.startswith("Tere") for s in selected)
    assert familiar(entries[0])


def test_klick_categories_use_breadcrumbs_and_fail_closed():
    html = (FIXTURES / "klick.html").read_text()
    result = parse_klick(html, CAPTURED)
    assert result[0].category == "telefonid-ja-lisad/mobiiltelefonid/nutitelefonid"
    assert (
        parse_klick(html.replace('"@type":"BreadcrumbList"', '"@type":"Unknown"'), CAPTURED) == []
    )
    assert parse_klick('<script type="application/ld+json">[null,3,"x"]</script>', CAPTURED) == []


def test_prices_fail_closed_for_ambiguous_or_missing_regular_prices():
    for value in ("alates 10 €", "10 €/kuu", "10 € või 20 €", "-1.00 €"):
        assert money(value) is None
    html = (FIXTURES / "klick.html").read_text()
    assert (
        parse_klick(
            html.replace("Tavahind", "Kuus").replace("price-original", "price-discount"), CAPTURED
        )
        == []
    )
    assert parse_klick(html.replace("265<span", "100<span"), CAPTURED) == []
    rimi = (FIXTURES / "rimi.html").read_text()
    regular = parse_rimi(rimi, CAPTURED)
    without_regular = parse_rimi(rimi.replace("card__old-price", "unknown-price"), CAPTURED)
    assert len(without_regular) < len(regular)


@pytest.mark.parametrize(
    "filename,price,category",
    [
        ("klick-0.html", 26599, "nutitelefonid"),
        ("klick-1.html", 65999, "sulearvutid"),
        ("klick-2.html", 4999, "juhtmevabad-korvaklapid-3"),
        ("klick-3.html", 21999, "monitorid"),
    ],
)
def test_captured_klick_categories_and_regular_prices(filename, price, category):
    html = (FIXTURES / filename).read_text()
    parsed = parse_klick(html, CAPTURED)
    assert len(parsed) == 1
    assert parsed[0].price_minor == price
    assert parsed[0].category.split("/")[-1] == category
    assert parse_klick(html.replace("/InStock", "/OutOfStock"), CAPTURED) == []


def test_captured_rimi_pack_size_and_regular_price():
    parsed = parse_rimi((FIXTURES / "rimi-more.html").read_text(), CAPTURED)
    assert {(p.title, p.price_minor) for p in parsed} == {
        ("Joogivesi karboniseeritud Rimi Smart 1,5L PET", 39),
        ("Juust Forte Classico Valio 180g", 369),
    }
    assert parsed[0].detail == "1,5L"


def test_regular_offer_is_used_when_no_discount_and_installments_are_ignored():
    import json
    import re

    html = (FIXTURES / "klick-1.html").read_text()
    payload = json.loads(re.search(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)[1])
    product = next(p for p in payload["@graph"] if p.get("@type") == "Product")
    product["offers"]["price"] = "1299.99"
    regular = (
        '<script type="application/ld+json">'
        + json.dumps(payload)
        + '</script><div class="installment">Alates 19.99 €/kuu</div>'
    )
    assert parse_klick(regular, CAPTURED)[0].price_minor == 129999
    product["image"] = []
    assert (
        parse_klick(
            '<script type="application/ld+json">' + json.dumps(payload) + "</script>", CAPTURED
        )
        == []
    )


def test_loyalty_discount_without_regular_price_is_excluded():
    html = (FIXTURES / "rimi.html").read_text()
    assert len(
        parse_rimi(
            html.replace("-has-discount", "-has-loyalty").replace(
                "card__old-price", "loyalty-price"
            ),
            CAPTURED,
        )
    ) < len(parse_rimi(html, CAPTURED))


def test_refresh_command_help_and_scheduled_override_guard():
    import subprocess
    import sys

    command = [sys.executable, "-m", "partygame.service.prices.refresh"]
    help_result = subprocess.run([*command, "--help"], capture_output=True, text=True, check=False)
    assert help_result.returncode == 0
    assert "--accept-price-changes" in help_result.stdout
    scheduled = subprocess.run(
        [*command, "--schedule", "--accept-price-changes"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scheduled.returncode == 2
    assert "one-shot" in scheduled.stderr


@pytest.mark.asyncio
async def test_klick_discovery_interleaves_categories_within_product_budget(monkeypatch):
    from partygame.service.prices import refresh

    visited = []
    categories = [f"https://www.klick.ee/{c}" for c in refresh.KLICK_DISCOVERY_CATEGORIES]

    async def page(url):
        if url in categories:
            index = categories.index(url)
            return "".join(
                f'<a data-testid="productLink" href="/item-{index}-{i}"></a>' for i in range(10)
            )
        if url.endswith("sitemap.xml"):
            return '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        if url.endswith("parimad-pakkumised"):
            return ""
        visited.append(url)
        return url

    monkeypatch.setattr(refresh, "page", page)
    monkeypatch.setattr(
        refresh, "parse_klick", lambda html, _: [products()[0].model_copy(update={"id": html})]
    )
    result = await refresh.collect("klick", max_pages=4)
    assert len(result) == 4
    assert visited == [f"https://www.klick.ee/item-{i}-0" for i in range(4)]
