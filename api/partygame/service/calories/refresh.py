"""Bounded Open Food Facts ingestion: python -m partygame.service.calories.refresh."""

import argparse
import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from sqlalchemy import text

from partygame.db.redis import get_connection
from partygame.schemas import MediaKind
from partygame.service.calories.datasets import CalorieDatasets
from partygame.service.calories.sources import FIELDS, normalize
from partygame.service.media import get_media_storage
from partygame.service.prices.quality import inspect_image
from partygame.service.prices.refresh import next_refresh
from partygame.state import GameStateRepository

log = logging.getLogger(__name__)
REFRESH_LOCK = 49192742


def validate_url(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"world.openfoodfacts.org", "images.openfoodfacts.org"}
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Unexpected Open Food Facts URL")


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, limit=8_000_000):
    validate_url(url)
    for attempt in range(3):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Manguohtu-Calorie-Dataset/1.0 (https://game.theority.ee)",
                    "Accept": "application/json,image/*",
                },
            )
            with build_opener(SafeRedirect()).open(request, timeout=30) as response:
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise ValueError("Open Food Facts response too large")
                return data
        except (HTTPError, URLError, TimeoutError) as error:
            if attempt == 2:
                raise
            retry = error.headers.get("Retry-After", "") if isinstance(error, HTTPError) else ""
            time.sleep(max(7 * 2**attempt, min(int(retry), 120) if retry.isdigit() else 0))
    raise RuntimeError("Fetch failed")


async def collect(max_pages=4):
    captured = datetime.now(UTC)
    products = {}
    rejected = 0
    for region in ("en:estonia", None):
        for page in range(1, max_pages // 2 + 1):
            params = {
                "fields": FIELDS,
                "page_size": 100,
                "page": page,
                "sort_by": "unique_scans_n",
                "json": 1,
            }
            if region:
                params["countries_tags"] = region
            await asyncio.sleep(7)
            body = json.loads(
                await asyncio.to_thread(
                    fetch, "https://world.openfoodfacts.org/api/v2/search?" + urlencode(params)
                )
            )
            if not isinstance(body.get("products"), list):
                raise TypeError("Missing product list")
            for raw in body["products"]:
                product = normalize(raw, captured)
                if product:
                    products.setdefault(product.id, product)
                else:
                    rejected += 1
            if len(body["products"]) < 100:
                break
    log.info("Open Food Facts accepted_records=%d rejected_records=%d", len(products), rejected)
    return list(products.values())


async def refresh(*, missing_only=False, max_pages=4, datasets=None, storage=None):
    datasets = datasets or CalorieDatasets()
    storage = storage or get_media_storage()
    async with datasets.sessionmaker() as lock_session:
        locked = await lock_session.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": REFRESH_LOCK}
        )
        if not locked:
            return False
        saved = []
        try:
            if missing_only and await datasets.latest(lock_session):
                return True
            products = await collect(max_pages)
            ready = []
            for product in products:
                try:
                    await asyncio.sleep(0.25)
                    data = await asyncio.to_thread(fetch, product.image_url, 5_000_000)
                    suffix, mime, details = await asyncio.to_thread(inspect_image, data)
                    asset = await storage.save(
                        content=data,
                        kind=MediaKind.IMAGE,
                        filename=f"product.{suffix}",
                        content_type=mime,
                    )
                    saved.append(asset.id)
                    ready.append(
                        product.model_copy(
                            update={
                                "image_url": storage.build_public_url(asset.id),
                                "image_asset_id": asset.id,
                                **details,
                            }
                        )
                    )
                except ValueError, HTTPError, URLError, TimeoutError:
                    log.warning("Rejected front image for %s", product.id)
            version = await datasets.publish(ready)
            saved.clear()
            log.info(
                "Published calorie dataset version=%s accepted=%d rejected_images=%d",
                version,
                len(ready),
                len(products) - len(ready),
            )
            redis = get_connection()
            try:
                await datasets.cleanup(GameStateRepository(redis), storage)
            finally:
                await redis.aclose()
            return True
        except Exception:
            log.exception("Calorie refresh failed; retaining previous dataset")
            return False
        finally:
            for asset_id in saved:
                await storage.delete(asset_id)
            await lock_session.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": REFRESH_LOCK}
            )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true")
    parser.add_argument("--max-pages", type=int, default=4)
    args = parser.parse_args()
    if args.max_pages not in (2, 4, 6):
        parser.error("--max-pages must be 2, 4 or 6 (at most 600 candidates)")
    success = await refresh(missing_only=args.schedule, max_pages=args.max_pages)
    if not args.schedule and not success:
        raise SystemExit(1)
    while args.schedule:
        due = next_refresh(datetime.now(UTC))
        log.info("Next calorie refresh: %s", due)
        await asyncio.sleep((due - datetime.now(UTC)).total_seconds())
        await refresh(max_pages=args.max_pages)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
