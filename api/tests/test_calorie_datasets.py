import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from partygame.db.postgres import Base
from partygame.schemas.calorie_game import CalorieGameSettings, CalorieProduct
from partygame.service.calories import refresh as refresh_module
from partygame.service.calories.datasets import CalorieDatasets
from partygame.state.calorie_models import CalorieDatasetLease, CalorieDatasetRecord
from tests.test_calorie_game import dataset


@pytest_asyncio.fixture()
async def store():
    url = os.environ.get("POSTGRES_TEST_DATABASE_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is not configured")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield CalorieDatasets(async_sessionmaker(engine, expire_on_commit=False))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def products():
    return [
        CalorieProduct.model_validate(p).model_copy(
            update={
                "category": f"category-{i % 3}",
                "image_width": 600,
                "image_height": 600,
                "image_sha256": f"{i:064x}",
            }
        )
        for i, p in enumerate(dataset().records)
    ]


@pytest.mark.asyncio
async def test_empty_availability_and_prepared_versions_survive_refresh(store):
    assert (await store.availability())["combinations"] == []
    original = await store.publish(products())
    bundles, provenance = await store.prepare(CalorieGameSettings(), 123, "session")
    frozen = bundles[0].model_dump(mode="json")
    changed = [p.model_copy(update={"kcal": p.kcal + 1}) for p in products()]
    new = await store.publish(changed)
    assert original != new
    assert bundles[0].model_dump(mode="json") == frozen
    assert provenance[0]["dataset_version"] == original
    availability = await store.availability()
    assert len(availability["combinations"]) == 12
    assert availability["captured_at"] is not None


@pytest.mark.asyncio
async def test_cleanup_retains_active_session_images_then_releases_them(store):
    old = await store.publish(products())
    await store.prepare(CalorieGameSettings(), 1, "session")
    await store.publish(
        [p.model_copy(update={"image_asset_id": "new-" + p.id}) for p in products()]
    )
    async with store.sessionmaker() as session, session.begin():
        record = await session.get(CalorieDatasetRecord, old)
        record.captured_at = datetime.now(UTC) - timedelta(days=8)
        lease = await session.get(CalorieDatasetLease, ("session", old))
        lease.created_at = datetime.now(UTC) - timedelta(days=1)
    repo, storage = AsyncMock(), AsyncMock()
    repo.lobby_exists.return_value = True
    await store.cleanup(repo, storage)
    storage.delete.assert_not_called()
    repo.lobby_exists.return_value = False
    await store.cleanup(repo, storage)
    assert storage.delete.await_count == len(products())
    async with store.sessionmaker() as session:
        assert await session.get(CalorieDatasetRecord, old) is None


@pytest.mark.asyncio
async def test_refresh_failure_retains_previous_dataset_and_cleans_staged_images(
    store, monkeypatch
):
    old = await store.publish(products())
    monkeypatch.setattr(refresh_module, "collect", AsyncMock(return_value=products()[:2]))
    monkeypatch.setattr(refresh_module, "fetch", lambda *args: b"fixture-image")
    monkeypatch.setattr(
        refresh_module,
        "inspect_image",
        lambda _: (
            "png",
            "image/png",
            {"image_width": 600, "image_height": 600, "image_sha256": "a" * 64},
        ),
    )
    monkeypatch.setattr(refresh_module, "get_connection", lambda: AsyncMock())
    storage = AsyncMock()
    storage.save.return_value = SimpleNamespace(id="temporary")
    storage.build_public_url = lambda _: "/api/v1/media/temporary"
    assert await refresh_module.refresh(datasets=store, storage=storage) is False
    assert storage.delete.await_count == 2
    async with store.sessionmaker() as session:
        assert [r.id for r in await session.scalars(select(CalorieDatasetRecord))] == [old]


@pytest.mark.asyncio
async def test_refresh_excludes_concurrent_workers_and_startup_skips_existing(store, monkeypatch):
    collect = AsyncMock()
    monkeypatch.setattr(refresh_module, "collect", collect)
    monkeypatch.setattr(refresh_module, "get_connection", lambda: AsyncMock())
    async with store.sessionmaker() as lock:
        await lock.execute(
            text("SELECT pg_advisory_lock(:key)"), {"key": refresh_module.REFRESH_LOCK}
        )
        try:
            assert await refresh_module.refresh(datasets=store, storage=AsyncMock()) is False
        finally:
            await lock.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": refresh_module.REFRESH_LOCK}
            )
    collect.assert_not_called()
    await store.publish(products())
    assert (
        await refresh_module.refresh(missing_only=True, datasets=store, storage=AsyncMock()) is True
    )
    collect.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_publish_preserves_version_and_download_has_license(store):
    old = await store.publish(products())
    with pytest.raises(ValueError):
        await store.publish(products()[:2])
    exported = await store.download()
    assert exported["version"] == old
    assert "odbl" in exported["license"]
    assert "by-sa" in exported["image_license"]


@pytest.mark.asyncio
async def test_continued_run_pins_stable_lobby(store):
    old = await store.publish(products())
    await store.prepare(CalorieGameSettings(), 1, "new-run")
    await store.bind_lobby("new-run", "stable-lobby")
    async with store.sessionmaker() as session:
        assert await session.get(CalorieDatasetLease, ("stable-lobby", old)) is not None


@pytest.mark.asyncio
async def test_source_outage_retains_published_dataset(store, monkeypatch):
    old = await store.publish(products())
    monkeypatch.setattr(refresh_module, "collect", AsyncMock(side_effect=TimeoutError))
    assert not await refresh_module.refresh(datasets=store, storage=AsyncMock())
    assert (await store.download())["version"] == old
