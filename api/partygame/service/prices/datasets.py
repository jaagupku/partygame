from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, text

from partygame.db.postgres import AsyncSessionLocal
from partygame.schemas.game_session import DatasetSnapshot
from partygame.schemas.price_game import PriceGameSettings, PriceProduct
from partygame.service.prices.generator import InsufficientPriceData, PriceGenerator
from partygame.service.prices.quality import validate_dataset
from partygame.service.prices.selection import GENERATOR_VERSION
from partygame.state.price_models import PriceDatasetLease, PriceDatasetRecord

DATASET_LOCK = 49192731


class PriceDatasets:
    def __init__(self, sessionmaker=AsyncSessionLocal):
        self.sessionmaker = sessionmaker

    async def latest(self, session):
        records = (
            await session.scalars(
                select(PriceDatasetRecord).order_by(PriceDatasetRecord.captured_at.desc())
            )
        ).all()
        latest = {}
        for record in records:
            latest.setdefault(record.source, record)
        return latest

    def snapshot(self, records):
        if not records:
            raise InsufficientPriceData("No product dataset")
        return DatasetSnapshot(
            source_id="estonian-prices",
            dataset_id="price_guessing",
            version="+".join(sorted(r.id for r in records)),
            captured_at=min(r.captured_at for r in records),
            records=[p for r in records for p in r.products],
        )

    async def prepare(self, settings: PriceGameSettings, seed: int, session_id: str):
        async with self.sessionmaker() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": DATASET_LOCK})
            latest = await self.latest(session)
            sources = {"groceries": ["rimi"], "electronics": ["klick"], "both": ["rimi", "klick"]}[
                settings.product_range
            ]
            if any(source not in latest for source in sources):
                raise InsufficientPriceData("Missing product range")
            records = [latest[source] for source in sources]
            snapshot = self.snapshot(records)
            bundles = PriceGenerator().generate(settings, seed=seed, dataset=snapshot)
            for record in records:
                session.add(PriceDatasetLease(session_id=session_id, dataset_id=record.id))
            return bundles, [
                {
                    "source_id": r.source,
                    "dataset_id": "price_guessing",
                    "dataset_version": r.id,
                    "captured_at": r.captured_at,
                    "generator_version": GENERATOR_VERSION,
                    "seed": seed,
                }
                for r in records
            ]

    async def availability(self):
        async with self.sessionmaker() as session:
            latest = await self.latest(session)
            result = []
            for product_range, source in [("groceries", "rimi"), ("electronics", "klick")]:
                record = latest.get(source)
                result.append(
                    {
                        "product_range": product_range,
                        "available": bool(record),
                        "captured_at": record.captured_at if record else None,
                    }
                )
            combinations = []
            for product_range in ["groceries", "electronics", "both"]:
                sources = {
                    "groceries": ["rimi"],
                    "electronics": ["klick"],
                    "both": ["rimi", "klick"],
                }[product_range]
                if any(source not in latest for source in sources):
                    continue
                snapshot = self.snapshot([latest[source] for source in sources])
                for mode in ["guess", "compare", "mixed"]:
                    for count in [5, 10, 15, 20]:
                        config = PriceGameSettings(
                            mode=mode, product_range=product_range, questions=count
                        )
                        try:
                            PriceGenerator().generate(config, seed=0, dataset=snapshot)
                            combinations.append(
                                {"mode": mode, "product_range": product_range, "questions": count}
                            )
                        except InsufficientPriceData:
                            pass
            return {
                "ranges": result,
                "combinations": combinations,
                "modes": ["guess", "compare", "mixed"],
                "questions": [5, 10, 15, 20],
                "answer_seconds": [15, 30, 45, 60],
            }

    async def publish(
        self, source: str, products: list[PriceProduct], *, accept_price_changes=False
    ):
        record = PriceDatasetRecord(
            id=uuid4().hex,
            source=source,
            captured_at=datetime.now(UTC),
            products=[p.model_dump(mode="json") for p in products],
        )
        async with self.sessionmaker() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": DATASET_LOCK})
            latest = (await self.latest(session)).get(source)
            previous = [PriceProduct.model_validate(p) for p in latest.products] if latest else []
            validate_dataset(source, products, previous, accept_price_changes=accept_price_changes)
            session.add(record)
        return record.id

    async def cleanup(self, repo, storage):
        async with self.sessionmaker() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": DATASET_LOCK})
            grace = datetime.now(UTC) - timedelta(hours=2)
            leases = (await session.scalars(select(PriceDatasetLease))).all()
            for lease in leases:
                if lease.created_at < grace and not await repo.lobby_exists(lease.session_id):
                    await session.delete(lease)
            await session.flush()
            latest_ids = {r.id for r in (await self.latest(session)).values()}
            retained = set(await session.scalars(select(PriceDatasetLease.dataset_id))) | latest_ids
            records = (await session.scalars(select(PriceDatasetRecord))).all()
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
                    delete(PriceDatasetRecord).where(PriceDatasetRecord.id == record.id)
                )
