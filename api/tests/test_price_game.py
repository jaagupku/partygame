from datetime import UTC, datetime, timedelta
from pathlib import Path
from random import Random
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from partygame import schemas
from partygame.schemas.game_session import DatasetSnapshot
from partygame.schemas.price_game import PriceGameSettings, PriceProduct
from partygame.service.game import GameRuntimeService
from partygame.service.game_sessions import SESSION_COMPONENT_ID, compose_rounds
from partygame.service.player import public_runtime_snapshot
from partygame.service.prices.generator import InsufficientPriceData, PriceGenerator
from partygame.service.prices.matching import maximum_pairs
from partygame.service.prices.refresh import image_format, next_refresh, validate_url
from partygame.service.prices.scoring import parse_euros, price_points
from partygame.service.prices.sources import money, parse_klick, parse_rimi
from partygame.service.runtime.price_reveal import (
    price_reveal_speed,
    remaining_price_reveal_seconds,
)
from partygame.service.runtime.scheduler import RuntimeTransitionScheduler
from tests.test_game_runtime import FakeRepo

FIXTURES = Path(__file__).parent / "fixtures" / "prices"
CAPTURED = datetime(2026, 9, 19, tzinfo=UTC)


def dataset():
    products = []
    for retailer, product_range in [("rimi", "groceries"), ("klick", "electronics")]:
        for index in range(60):
            products.append(
                PriceProduct(
                    id=f"{retailer}-{index}",
                    retailer=retailer,
                    product_range=product_range,
                    category="category",
                    title=f"Product {index}",
                    detail="500g",
                    price_minor=100 + index * 20,
                    source_url=f"https://www.{retailer}.ee/product/{index}",
                    image_url=f"/api/v1/media/{retailer}-{index}",
                    image_asset_id=f"{retailer}-{index}",
                    captured_at=CAPTURED,
                ).model_dump(mode="json")
            )
    return DatasetSnapshot(
        source_id="fixture",
        dataset_id="prices",
        version="v1",
        captured_at=CAPTURED,
        records=products,
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (10, 1000),
        (9, 900),
        (11, 900),
        (5, 500),
        (15, 500),
        (0, 0),
        (20, 0),
        (100, 0),
        ("10.01", 999),
        ("9.99", 999),
    ],
)
def test_closeness(value, expected):
    assert price_points(value, 1000) == expected


def test_half_up_rounding():
    assert price_points("0.01", 16) == 63


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        -1,
        "-0.01",
        "NaN",
        "Infinity",
        float("inf"),
        True,
        {},
        "1.001",
        "1.000",
        "not a price",
    ],
)
def test_invalid_price(value):
    assert parse_euros(value) is None
    assert price_points(value, 1000) == 0


@pytest.mark.parametrize("mode", ["guess", "compare", "mixed"])
@pytest.mark.parametrize("product_range", ["groceries", "electronics", "both"])
@pytest.mark.parametrize("count", [5, 10, 15, 20])
def test_generator_balances_unique_questions(mode, product_range, count):
    settings = PriceGameSettings(mode=mode, product_range=product_range, questions=count)
    generator = PriceGenerator()
    bundles = generator.generate(settings, seed=42, dataset=dataset())
    assert bundles == generator.generate(settings, seed=42, dataset=dataset())
    steps = bundles[0].rounds[0].steps
    assert len(steps) == count
    urls = [p.source_url for step in steps for p in step.price_question.reveal]
    assert len(urls) == len(set(urls))
    if mode == "mixed":
        assert sum(step.price_question.mode == "guess" for step in steps) == (count + 1) // 2
    if product_range == "both":
        appearances = [p.retailer for step in steps for p in step.price_question.reveal]
        assert abs(appearances.count("rimi") - appearances.count("klick")) <= 1
    for step in steps:
        if step.price_question.mode == "compare":
            left, right = step.price_question.reveal
            low, high = sorted([left.price_minor, right.price_minor])
            assert 11 * low <= 10 * high <= 30 * low
            assert step.evaluation.answer == str(0 if left.price_minor > right.price_minor else 1)


def test_generator_varies_seed_and_rejects_insufficient_pool():
    settings = PriceGameSettings()
    assert PriceGenerator().generate(
        settings, seed=1, dataset=dataset()
    ) != PriceGenerator().generate(settings, seed=2, dataset=dataset())
    empty = dataset().model_copy(update={"records": []})
    with pytest.raises(InsufficientPriceData):
        PriceGenerator().generate(settings, seed=0, dataset=empty)
    winners = set()
    for seed in range(5):
        for step in (
            PriceGenerator()
            .generate(PriceGameSettings(mode="compare"), seed=seed, dataset=dataset())[0]
            .rounds[0]
            .steps
        ):
            winners.add(step.evaluation.answer)
    assert winners == {"0", "1"}


def test_maximum_matching_against_exhaustive_small_graphs():
    def optimum(graph, remaining):
        if not remaining:
            return 0
        left, *tail = remaining
        return max(
            [optimum(graph, tail)]
            + [
                1 + optimum(graph, [v for v in tail if v != right])
                for right in tail
                if right in graph[left]
            ]
        )

    rng = Random(11)
    for _ in range(100):
        prices = sorted(rng.sample(range(10, 80), 8))
        graph = [
            [
                j
                for j, right in enumerate(prices)
                if i != j
                and 11 * min(left, right) <= 10 * max(left, right) <= 30 * min(left, right)
            ]
            for i, left in enumerate(prices)
        ]
        pairs = maximum_pairs(graph)
        assert len(pairs) == optimum(graph, list(range(len(graph))))
        assert len({v for pair in pairs for v in pair}) == 2 * len(pairs)


def test_rimi_regular_price_and_variable_weight():
    products = parse_rimi((FIXTURES / "rimi.html").read_text(), CAPTURED)
    assert {p.id: p.price_minor for p in products} == {"205757": 149, products[0].id: 239}
    assert all(not p.title.endswith("kg") for p in products)
    html = (FIXTURES / "rimi.html").read_text().replace("Lisa ostukorvi", "Unavailable")
    assert parse_rimi(html, CAPTURED) == []


def test_rimi_caches_loaded_product_image_instead_of_blurred_placeholder():
    products = parse_rimi((FIXTURES / "rimi.html").read_text(), CAPTURED)
    assert products
    assert all("q_1," not in p.image_url and "w_600" in p.image_url for p in products)


def test_klick_regular_price_not_sale_or_installments():
    html = (FIXTURES / "klick.html").read_text()
    products = parse_klick(html, CAPTURED)
    assert len(products) == 1
    assert products[0].price_minor == 26599
    assert parse_klick(html.replace("/InStock", "/OutOfStock"), CAPTURED) == []
    assert parse_klick(html.replace("/NewCondition", "/UsedCondition"), CAPTURED) == []
    assert parse_klick(html.replace('"@type":"Offer"', '"@type":"AggregateOffer"'), CAPTURED) == []


def test_image_and_url_validation():
    with pytest.raises(ValueError):
        image_format(b"RIFF0000WEBPdata")
    with pytest.raises(ValueError):
        image_format(b"<html>error</html>")
    for url in ["http://127.0.0.1", "https://example.org/image", "https://www.rimi.ee:999/image"]:
        with pytest.raises(ValueError):
            validate_url(url)


def test_weekly_refresh_utc():
    monday = datetime(2026, 9, 21, 4, tzinfo=UTC)
    assert next_refresh(monday - timedelta(seconds=1)) == monday
    assert next_refresh(monday) == monday + timedelta(days=7)
    assert next_refresh(CAPTURED) == monday


@pytest.mark.asyncio
@pytest.mark.parametrize("host_enabled", [True, False])
@pytest.mark.parametrize("mode", ["guess", "compare"])
async def test_runtime_price_privacy_reconnect_and_idempotent_scoring(mode, host_enabled):
    bundles = PriceGenerator().generate(
        PriceGameSettings(mode=mode, questions=5), seed=1, dataset=dataset()
    )
    prepared = compose_rounds(bundles, definition_id="price_guessing", title="Prices")
    repo = FakeRepo()
    await repo.set_component_state(
        "g1", SESSION_COMPONENT_ID, {"snapshot": prepared.model_dump(mode="json")}
    )
    provider = AsyncMock()
    runtime = GameRuntimeService(repo, provider, archive_game_stats=False)
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        session_version=1,
        game_type="price_guessing",
        host_enabled=host_enabled,
    )
    await runtime.start_game(lobby)
    before = public_runtime_snapshot(await runtime.build_snapshot(lobby))
    assert before.active_step.price_products
    assert before.active_step.price_reveal == []
    assert before.active_step.price_results == []
    assert "source_url" not in before.model_dump_json()
    step = await runtime.get_current_step(lobby)
    invalid = "1.001" if mode == "guess" else "bad-id"
    assert (await runtime.submit_player_input(lobby, "p1", invalid))[1] is False
    answer = str(step.evaluation.answer / 100) if mode == "guess" else step.evaluation.answer
    assert (await runtime.submit_player_input(lobby, "p1", answer))[1] is True
    await runtime.close_step(lobby)
    await runtime.close_step(lobby)
    assert await repo.get_player_score("g1", "p1") == 1000
    assert await runtime.reset_current_step(lobby) == []
    await runtime.close_step(lobby)
    assert await repo.get_player_score("g1", "p1") == 1000
    reconnected = GameRuntimeService(repo, provider, archive_game_stats=False)
    snapshot = public_runtime_snapshot(await reconnected.build_snapshot(lobby))
    assert snapshot.active_step.price_reveal
    results = {item.player_id: item for item in snapshot.active_step.price_results}
    assert results["p1"].points == 1000
    assert results["p2"].points == 0
    provider.load.assert_not_called()


def test_balanced_generation_uses_feasible_mode_allocation_for_every_seed():
    source = dataset()
    groceries = [p for p in source.records if p["retailer"] == "rimi"][:3]
    electronics = [p for p in source.records if p["retailer"] == "klick"][:4]
    # Groceries can supply three guesses but no pair; electronics supply two pairs.
    for p in groceries:
        p["price_minor"] = 100
    source = source.model_copy(update={"records": groceries + electronics})
    for seed in range(20):
        steps = (
            PriceGenerator()
            .generate(PriceGameSettings(questions=5), seed=seed, dataset=source)[0]
            .rounds[0]
            .steps
        )
        assert len(steps) == 5
        assert sum(step.price_question.mode == "compare" for step in steps) == 2


@pytest.mark.parametrize("value", ["1 299,99 €", "1\u00a0299.99 €", "1299.99 €"])
def test_retailer_price_grouping(value):
    assert money(value) == 129999


def test_price_creation_defaults_keep_trivia_compatible():
    assert schemas.CreateGame().host_enabled is True
    price = schemas.CreateGame(game_type="price_guessing")
    assert price.host_enabled is False
    assert price.price_settings == PriceGameSettings()


@pytest.mark.asyncio
async def test_price_builder_rejects_missing_content_without_loading_quiz(monkeypatch):
    from fastapi import HTTPException

    from partygame.service.game_sessions import prepare_session
    from partygame.service.prices.datasets import PriceDatasets

    monkeypatch.setattr(
        PriceDatasets, "prepare", AsyncMock(side_effect=InsufficientPriceData("empty"))
    )
    provider = AsyncMock()
    with pytest.raises(HTTPException) as raised:
        await prepare_session(schemas.CreateGame(game_type="price_guessing"), None, provider)
    assert raised.value.status_code == 409
    assert raised.value.detail == "price_content_unavailable"
    provider.load.assert_not_called()


def test_reveal_duration_settings_and_generated_steps():
    assert PriceGameSettings().reveal_seconds == 4
    with pytest.raises(ValidationError):
        PriceGameSettings(reveal_seconds=5)
    with pytest.raises(ValidationError):
        schemas.CreateGame(game_type="price_guessing", price_settings={"reveal_seconds": 5})
    steps = (
        PriceGenerator()
        .generate(PriceGameSettings(questions=5, reveal_seconds=15), seed=1, dataset=dataset())[0]
        .rounds[0]
        .steps
    )
    assert all(step.price_question.reveal_seconds == 15 for step in steps)


@pytest.mark.asyncio
async def test_price_ready_changes_only_future_countdown_speed(monkeypatch):
    bundles = PriceGenerator().generate(
        PriceGameSettings(questions=5, reveal_seconds=8), seed=1, dataset=dataset()
    )
    prepared = compose_rounds(bundles, definition_id="price_guessing", title="Prices")
    repo = FakeRepo()
    await repo.set_component_state(
        "g1", SESSION_COMPONENT_ID, {"snapshot": prepared.model_dump(mode="json")}
    )
    runtime = GameRuntimeService(repo, AsyncMock(), archive_game_stats=False)
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        session_version=1,
        game_type="price_guessing",
        host_enabled=False,
    )
    clock = [1000.0]
    monkeypatch.setattr("partygame.service.game.time", lambda: clock[0])
    monkeypatch.setattr("partygame.service.runtime.price_reveal.time", lambda: clock[0])
    monkeypatch.setattr("partygame.service.runtime.snapshots.time", lambda: clock[0])
    await runtime.start_game(lobby)
    step = await runtime.get_current_step(lobby)
    assert await runtime.set_price_reveal_ready(lobby, "p1", step.id, True) is False
    await runtime.close_step(lobby)
    assert repo.steps["g1"]["price_ready_player_ids"] == []
    assert await runtime.set_price_reveal_ready(lobby, "p1", "old-step", True) is False
    assert await runtime.set_price_reveal_ready(lobby, "stranger", step.id, True) is False
    clock[0] += 2
    assert await runtime.set_price_reveal_ready(lobby, "p1", step.id, True)
    state = await runtime.get_step_state(lobby.id)
    assert remaining_price_reveal_seconds(state, 8, now=clock[0]) == 6
    assert price_reveal_speed(state) == pytest.approx(1.15)
    snapshot = await runtime.build_snapshot(lobby)
    assert snapshot.price_ready_player_ids == ["p1"]
    assert snapshot.price_reveal_remaining_seconds == 6
    transition = await RuntimeTransitionScheduler().next_transition(
        lobby=lobby, snapshot=snapshot, runtime=runtime
    )
    assert transition.delay_seconds == pytest.approx(6 / 1.15)
    clock[0] += 1
    assert await runtime.set_price_reveal_ready(lobby, "p2", step.id, True)
    state = await runtime.get_step_state(lobby.id)
    assert remaining_price_reveal_seconds(state, 8, now=clock[0]) == pytest.approx(4.85)
    assert price_reveal_speed(state) == pytest.approx(1.3)
    clock[0] += 1
    assert await runtime.set_price_reveal_ready(lobby, "p1", step.id, False)
    state = await runtime.get_step_state(lobby.id)
    assert remaining_price_reveal_seconds(state, 8, now=clock[0]) == pytest.approx(3.55)
    assert price_reveal_speed(state) == pytest.approx(1.15)
    assert state["price_ready_player_ids"] == ["p2"]
    clock[0] += 0.5
    reconnected = GameRuntimeService(repo, AsyncMock(), archive_game_stats=False)
    reconnected_snapshot = await reconnected.build_snapshot(lobby)
    assert reconnected_snapshot.price_ready_player_ids == ["p2"]
    assert reconnected_snapshot.price_reveal_remaining_seconds == pytest.approx(2.975)
    transition = await RuntimeTransitionScheduler().next_transition(
        lobby=lobby, snapshot=reconnected_snapshot, runtime=reconnected
    )
    assert transition.delay_seconds == pytest.approx(2.975 / 1.15)
    await runtime.close_step(lobby)
    assert (await runtime.get_step_state(lobby.id))["price_reveal_updated_at"] == 1004.0
    await runtime.advance_step(lobby)
    assert (await runtime.get_step_state(lobby.id))["price_ready_player_ids"] == []
