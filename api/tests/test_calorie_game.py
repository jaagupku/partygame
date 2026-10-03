from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from partygame import schemas
from partygame.schemas.calorie_game import CalorieGameSettings, CalorieProduct
from partygame.schemas.game_session import DatasetSnapshot
from partygame.service.calories.generator import CalorieGenerator, InsufficientCalorieData
from partygame.service.calories.scoring import calorie_points, parse_calories
from partygame.service.calories.sources import normalize
from partygame.service.game import GameRuntimeService
from partygame.service.game_sessions import SESSION_COMPONENT_ID, compose_rounds
from partygame.service.player import public_runtime_snapshot
from partygame.service.runtime.price_reveal import (
    price_reveal_speed,
    remaining_price_reveal_seconds,
)
from partygame.service.runtime.scheduler import RuntimeTransitionScheduler
from tests.test_game_runtime import FakeRepo

CAPTURED = datetime(2026, 9, 27, tzinfo=UTC)


def dataset():
    return DatasetSnapshot(
        source_id="openfoodfacts",
        dataset_id="calorie_guessing",
        version="v1",
        captured_at=CAPTURED,
        records=[
            CalorieProduct(
                id=str(1000000000000 + i),
                title=f"Product {i}",
                category=f"category-{i % 4}",
                basis="100g" if i % 2 else "100ml",
                kcal=10 + i * 10,
                estonia=i < 48,
                source_url=f"https://world.openfoodfacts.org/product/{1000000000000+i}",
                image_url=f"/api/v1/media/{i}",
                image_asset_id=str(i),
                image_width=600,
                image_height=600,
                captured_at=CAPTURED,
            ).model_dump(mode="json")
            for i in range(64)
        ],
    )


@pytest.mark.parametrize(
    "value,points", [(100, 1000), (90, 900), (110, 900), (0, 0), (200, 0), (500, 0), (None, 0)]
)
def test_scoring(value, points):
    assert calorie_points(value, 100) == points
    assert calorie_points(value, 0) == 0


@pytest.mark.parametrize("value", [-1, "1.1", "NaN", "Infinity", True, {}, "", 1000001])
def test_invalid_input(value):
    assert parse_calories(value) is None


def test_half_up():
    assert calorie_points(1, 16) == 63


def raw():
    return {
        "code": "1234567890123",
        "product_name": "Chocolate",
        "quantity": "100 g",
        "categories_tags": ["en:chocolates"],
        "countries_tags": ["en:estonia"],
        "nutriments": {"energy-kcal_100g": 123.5},
        "image_front_url": "https://images.openfoodfacts.org/front.jpg",
    }


def test_nutrition_normalization_and_basis():
    product = normalize(raw(), CAPTURED)
    assert (product.kcal, product.basis, product.estonia) == (124, "100g", True)
    drink = {**raw(), "quantity": "1 l", "categories_tags": ["en:beverages"]}
    assert normalize(drink, CAPTURED).basis == "100ml"
    assert normalize({**drink, "quantity": "100 g"}, CAPTURED) is None
    assert normalize({**raw(), "serving_size": "100 ml"}, CAPTURED) is None


@pytest.mark.parametrize(
    "change",
    [
        {"quantity": ""},
        {"categories_tags": []},
        {"nutriments": {"energy-kcal_prepared_100g": 100}},
        {"nutriments": {"energy-kcal_100g": 0.1}},
        {"nutriments": {"energy-kcal_100g": 1001}},
        {"nutriments": {"energy-kcal_100g": "NaN"}},
        {"image_front_url": "https://evil.example/p.jpg"},
        {"data_quality_errors_tags": ["bad"]},
        {"categories_tags": ["en:beverages", "en:beverage-preparations"]},
    ],
)
def test_rejected_records(change):
    assert normalize({**raw(), **change}, CAPTURED) is None


@pytest.mark.parametrize("mode", ["guess", "compare", "mixed"])
def test_generation(mode):
    settings = CalorieGameSettings(mode=mode, questions=20)
    first = CalorieGenerator().generate(settings, seed=12, dataset=dataset())
    assert first == CalorieGenerator().generate(settings, seed=12, dataset=dataset())
    steps = first[0].rounds[0].steps
    assert len(steps) == 20
    assert (
        sum(s.calorie_question.mode == "compare" for s in steps)
        == {"guess": 0, "compare": 20, "mixed": 10}[mode]
    )
    urls = [p.source_url for s in steps for p in s.calorie_question.reveal]
    assert len(urls) == len(set(urls))
    assert all(int(url.rsplit("/", 1)[1]) < 1000000000048 for url in urls)
    for step in steps:
        assert len({p.basis for p in step.calorie_question.products}) == 1
        if step.calorie_question.mode == "compare":
            assert len({p.kcal for p in step.calorie_question.reveal}) == 2


def test_international_supplement_and_insufficient_pairs():
    source = dataset()
    for i, p in enumerate(source.records):
        p["estonia"] = i < 3
    steps = (
        CalorieGenerator()
        .generate(CalorieGameSettings(mode="guess", questions=5), seed=1, dataset=source)[0]
        .rounds[0]
        .steps
    )
    assert (
        sum(
            int(s.calorie_question.reveal[0].source_url.rsplit("/", 1)[1]) < 1000000000003
            for s in steps
        )
        == 3
    )
    for p in source.records:
        p["kcal"] = 100
    with pytest.raises(InsufficientCalorieData):
        CalorieGenerator().generate(CalorieGameSettings(mode="compare"), seed=1, dataset=source)


@pytest.mark.asyncio
@pytest.mark.parametrize("host_enabled", [True, False])
@pytest.mark.parametrize("mode", ["guess", "compare"])
async def test_runtime_calorie_privacy_reconnect_and_idempotent_scoring(mode, host_enabled):
    bundles = CalorieGenerator().generate(
        CalorieGameSettings(mode=mode, questions=5), seed=1, dataset=dataset()
    )
    prepared = compose_rounds(bundles, definition_id="calorie_guessing", title="Calories")
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
        game_type="calorie_guessing",
        host_enabled=host_enabled,
    )
    await runtime.start_game(lobby)
    before = public_runtime_snapshot(await runtime.build_snapshot(lobby))
    assert before.active_step.calorie_products
    assert before.active_step.calorie_reveal == []
    assert before.active_step.calorie_results == []
    assert "source_url" not in before.model_dump_json()
    step = await runtime.get_current_step(lobby)
    invalid = "1.1" if mode == "guess" else "bad-id"
    assert (await runtime.submit_player_input(lobby, "p1", invalid))[1] is False
    answer = str(step.evaluation.answer) if mode == "guess" else step.evaluation.answer
    first_answer = (
        "1.00"
        if mode == "guess"
        else next(option for option in step.player_input.options if option != answer)
    )
    assert (await runtime.submit_player_input(lobby, "p1", first_answer))[1] is True
    assert (await runtime.submit_player_input(lobby, "p1", answer))[1] is True
    assert (await runtime.get_step_state(lobby.id))["answers"]["p1"] == answer
    await runtime.close_step(lobby)
    assert (await runtime.submit_player_input(lobby, "p1", first_answer))[1] is False
    await runtime.close_step(lobby)
    assert await repo.get_player_score("g1", "p1") == 1000
    assert await runtime.reset_current_step(lobby) == []
    await runtime.close_step(lobby)
    assert await repo.get_player_score("g1", "p1") == 1000
    reconnected = GameRuntimeService(repo, provider, archive_game_stats=False)
    snapshot = public_runtime_snapshot(await reconnected.build_snapshot(lobby))
    assert snapshot.active_step.calorie_reveal
    results = {item.player_id: item for item in snapshot.active_step.calorie_results}
    assert results["p1"].points == 1000
    assert results["p2"].points == 0
    provider.load.assert_not_called()


@pytest.mark.asyncio
async def test_price_ready_changes_only_future_countdown_speed(monkeypatch):
    bundles = CalorieGenerator().generate(
        CalorieGameSettings(questions=5, reveal_seconds=8), seed=1, dataset=dataset()
    )
    prepared = compose_rounds(bundles, definition_id="calorie_guessing", title="Prices")
    repo = FakeRepo()
    await repo.set_component_state(
        "g1", SESSION_COMPONENT_ID, {"snapshot": prepared.model_dump(mode="json")}
    )
    runtime = GameRuntimeService(repo, AsyncMock(), archive_game_stats=False)
    lobby = schemas.Lobby(
        id="g1",
        join_code="ABCDE",
        session_version=1,
        game_type="calorie_guessing",
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


def test_captured_openfoodfacts_responses():
    import json
    from pathlib import Path

    records = json.loads(
        (Path(__file__).parent / "fixtures/calories/openfoodfacts.json").read_text()
    )
    products = [normalize(record, CAPTURED) for record in records]
    assert all(products)
    assert [p.basis for p in products] == ["100g", "100ml"]
    assert all(p.estonia for p in products)
