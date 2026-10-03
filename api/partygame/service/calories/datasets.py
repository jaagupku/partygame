from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, text

from partygame.db.postgres import AsyncSessionLocal
from partygame.schemas.calorie_game import CalorieGameSettings
from partygame.schemas.game_session import DatasetSnapshot
from partygame.service.calories.generator import (
    GENERATOR_VERSION,
    CalorieGenerator,
    InsufficientCalorieData,
    has_capacity,
    products_from,
)
from partygame.state.calorie_models import CalorieDatasetLease, CalorieDatasetRecord

DATASET_LOCK = 49192741


class CalorieDatasets:
    def __init__(self, sessionmaker=AsyncSessionLocal):
        self.sessionmaker = sessionmaker

    async def latest(self, session):
        record = await session.scalar(
            select(CalorieDatasetRecord).order_by(CalorieDatasetRecord.captured_at.desc()).limit(1)
        )
        return {"openfoodfacts": record} if record else {}

    def snapshot(self, records):
        if not records:
            raise InsufficientCalorieData("No calorie dataset")
        record = records[0]
        return DatasetSnapshot(
            source_id="openfoodfacts",
            dataset_id="calorie_guessing",
            version=record.id,
            captured_at=record.captured_at,
            records=record.products,
        )

    async def prepare(self, settings, seed, session_id):
        async with self.sessionmaker() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": DATASET_LOCK})
            snapshot = self.snapshot(list((await self.latest(session)).values()))
            bundles = CalorieGenerator().generate(settings, seed=seed, dataset=snapshot)
            session.add(CalorieDatasetLease(session_id=session_id, dataset_id=snapshot.version))
            return bundles, [
                {
                    "source_id": "openfoodfacts",
                    "dataset_id": "calorie_guessing",
                    "dataset_version": snapshot.version,
                    "captured_at": snapshot.captured_at,
                    "generator_version": GENERATOR_VERSION,
                    "seed": seed,
                }
            ]

    async def bind_lobby(self, session_id, lobby_id):
        """Retain a continued run's images for the lifetime of its stable lobby."""
        async with self.sessionmaker() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": DATASET_LOCK})
            leases = (
                await session.scalars(
                    select(CalorieDatasetLease).where(CalorieDatasetLease.session_id == session_id)
                )
            ).all()
            for lease in leases:
                if await session.get(CalorieDatasetLease, (lobby_id, lease.dataset_id)) is None:
                    session.add(
                        CalorieDatasetLease(session_id=lobby_id, dataset_id=lease.dataset_id)
                    )

    async def availability(self):
        async with self.sessionmaker() as session:
            records = list((await self.latest(session)).values())
            products = products_from(self.snapshot(records)) if records else []
            return {
                "captured_at": records[0].captured_at if records else None,
                "combinations": [
                    {"mode": mode, "questions": n}
                    for mode in ("guess", "compare", "mixed")
                    for n in (5, 10, 15, 20)
                    if has_capacity(CalorieGameSettings(mode=mode, questions=n), products)
                ],
                "modes": ["guess", "compare", "mixed"],
                "questions": [5, 10, 15, 20],
                "answer_seconds": [15, 30, 45, 60],
                "reveal_seconds": [4, 6, 8, 10, 15],
            }

    async def publish(self, products):
        if len({p.id for p in products}) != len(products):
            raise ValueError("Duplicate barcodes")
        if any(not p.image_asset_id or min(p.image_width, p.image_height) < 256 for p in products):
            raise ValueError("Uncached or undersized images")
        if any(
            not has_capacity(CalorieGameSettings(mode=mode, questions=20), products)
            for mode in ("guess", "compare", "mixed")
        ):
            raise InsufficientCalorieData("Dataset must support 20 questions in every mode")
        record = CalorieDatasetRecord(
            id=uuid4().hex,
            source="openfoodfacts",
            captured_at=datetime.now(UTC),
            products=[p.model_dump(mode="json") for p in products],
        )
        async with self.sessionmaker() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": DATASET_LOCK})
            session.add(record)
        return record.id

    async def download(self):
        async with self.sessionmaker() as session:
            records = list((await self.latest(session)).values())
            if not records:
                raise InsufficientCalorieData("No calorie dataset")
            record = records[0]
            return {
                "source": "Open Food Facts",
                "source_url": "https://world.openfoodfacts.org",
                "license": "https://opendatacommons.org/licenses/odbl/1-0/",
                "contents_license": "https://opendatacommons.org/licenses/dbcl/1-0/",
                "image_license": "https://creativecommons.org/licenses/by-sa/3.0/",
                "version": record.id,
                "captured_at": record.captured_at,
                "products": record.products,
            }

    async def cleanup(self, repo, storage):
        async with self.sessionmaker() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": DATASET_LOCK})
            grace = datetime.now(UTC) - timedelta(hours=2)
            leases = (await session.scalars(select(CalorieDatasetLease))).all()
            for lease in leases:
                if lease.created_at < grace and not await repo.lobby_exists(lease.session_id):
                    await session.delete(lease)
            await session.flush()
            latest_ids = {r.id for r in (await self.latest(session)).values()}
            retained = (
                set(await session.scalars(select(CalorieDatasetLease.dataset_id))) | latest_ids
            )
            records = (await session.scalars(select(CalorieDatasetRecord))).all()
            for record in records:
                if record.id in retained or record.captured_at >= grace:
                    continue
                for product in record.products:
                    # Each version owns its images. Failed deletes leave the record retryable.
                    try:
                        await storage.delete(product["image_asset_id"])
                    except Exception as error:
                        if getattr(error, "status_code", None) != 404:
                            raise
                await session.execute(
                    delete(CalorieDatasetRecord).where(CalorieDatasetRecord.id == record.id)
                )
