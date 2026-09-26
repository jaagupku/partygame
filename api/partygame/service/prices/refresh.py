"""Run with python -m partygame.service.prices.refresh [--schedule]."""

import argparse
import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from itertools import zip_longest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

from sqlalchemy import text

from partygame.db.redis import get_connection
from partygame.schemas import MediaKind
from partygame.service.media import get_media_storage
from partygame.service.prices.datasets import PriceDatasets
from partygame.service.prices.quality import inspect_image
from partygame.service.prices.sources import klick_links, parse_klick, parse_rimi
from partygame.state import GameStateRepository

log = logging.getLogger(__name__)
REFRESH_LOCK = 49192732
KLICK_DISCOVERY_CATEGORIES = (
    "telefonid-ja-lisad/mobiiltelefonid/nutitelefonid",
    "arvutid-ja-lisad/arvutid/sulearvutid",
    "heli-ja-pilt/korvaklapid-2/juhtmevabad-korvaklapid-3",
    "arvutid-ja-lisad/monitorid-ja-lisad/monitorid",
)
ALLOWED_HOSTS = {"www.rimi.ee", "www.klick.ee", "rimibaltic-res.cloudinary.com", "vsf-api.klick.ee"}


def validate_url(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Unexpected retailer URL")


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, limit=8_000_000):
    validate_url(url)
    for attempt in range(3):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Manguohtu-Price-Dataset/1.0",
                    "Accept": "text/html,image/*,*/*",
                },
            )
            with build_opener(SafeRedirect()).open(request, timeout=20) as response:
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise ValueError("Retailer response too large")
                return data
        except HTTPError, URLError, TimeoutError:
            if attempt == 2:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Fetch failed")


async def page(url):
    await asyncio.sleep(1)
    return (await asyncio.to_thread(fetch, url)).decode("utf-8")


def image_format(data):
    suffix, mime, _ = inspect_image(data)
    return suffix, mime


def next_refresh(now: datetime) -> datetime:
    candidate = now.astimezone(UTC).replace(hour=4, minute=0, second=0, microsecond=0)
    candidate += timedelta(days=(0 - candidate.weekday()) % 7)
    return candidate if candidate > now else candidate + timedelta(days=7)


async def collect(source, max_pages=80):
    captured = datetime.now(UTC)
    if source == "rimi":
        products = []
        for number in range(1, min(max_pages, 10) + 1):
            products.extend(
                parse_rimi(
                    await page(f"https://www.rimi.ee/epood/ee/otsing?currentPage={number}"),
                    captured,
                )
            )
        return list({p.id: p for p in products}.values())
    category_links = []
    for category in KLICK_DISCOVERY_CATEGORIES:
        try:
            category_links.append(klick_links(await page(f"https://www.klick.ee/{category}")))
        except ValueError, URLError, TimeoutError:
            log.warning("Skipping inaccessible Klick category %s", category)
    # Interleave curated categories so one listing cannot consume the page budget.
    links = [url for group in zip_longest(*category_links) for url in group if url]
    listing = await page("https://www.klick.ee/parimad-pakkumised")
    links.extend(klick_links(listing))
    # Supplement campaign listings with product URLs from the public sitemap.
    sitemap = await page("https://www.klick.ee/sitemap.xml")
    root = ElementTree.fromstring(sitemap)
    urls = [n.text for n in root.iter() if n.tag.endswith("}loc") and n.text]
    if root.tag.endswith("sitemapindex"):
        for url in urls[:2]:
            xml = ElementTree.fromstring(await page(url))
            links.extend(
                n.text
                for n in xml.iter()
                if n.tag.endswith("}loc") and n.text and urlparse(n.text).path.count("/") == 1
            )
    else:
        links.extend(url for url in urls if urlparse(url).path.count("/") == 1)
    products = []
    for url in list(dict.fromkeys(links))[:max_pages]:
        try:
            products.extend(parse_klick(await page(url), captured))
        except ValueError, URLError, TimeoutError:
            log.warning("Skipping inaccessible Klick product %s", url)
    return list({p.id: p for p in products}.values())


async def refresh(
    *,
    missing_only=False,
    max_pages=80,
    sources=("rimi", "klick"),
    datasets=None,
    storage=None,
    accept_price_changes=False,
):
    datasets = datasets or PriceDatasets()
    storage = storage or get_media_storage()
    async with datasets.sessionmaker() as lock_session:
        locked = await lock_session.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": REFRESH_LOCK}
        )
        if not locked:
            log.info("Price refresh already running")
            return False
        try:
            succeeded = True
            latest = await datasets.latest(lock_session)
            for source in sources:
                if missing_only and source in latest:
                    continue
                saved = []
                try:
                    products = await collect(source, max_pages=max_pages)
                    ready = []
                    for product in products:
                        try:
                            data = await asyncio.to_thread(fetch, product.image_url, 5_000_000)
                            suffix, content_type, image_details = await asyncio.to_thread(
                                inspect_image, data
                            )
                            asset = await storage.save(
                                content=data,
                                kind=MediaKind.IMAGE,
                                filename=f"product.{suffix}",
                                content_type=content_type,
                            )
                            saved.append(asset.id)
                            ready.append(
                                product.model_copy(
                                    update={
                                        "image_url": storage.build_public_url(asset.id),
                                        "image_asset_id": asset.id,
                                        **image_details,
                                    }
                                )
                            )
                        except ValueError, HTTPError, URLError, TimeoutError:
                            log.warning("Skipping unusable image for %s:%s", source, product.id)
                    version = await datasets.publish(
                        source, ready, accept_price_changes=accept_price_changes
                    )
                    saved.clear()
                    log.info(
                        "Published %s version=%s accepted=%d rejected_images=%d",
                        source,
                        version,
                        len(ready),
                        len(products) - len(ready),
                    )
                except Exception:
                    succeeded = False
                    log.exception("Price refresh failed for %s; retaining previous dataset", source)
                finally:
                    for asset_id in saved:
                        await storage.delete(asset_id)
            redis = get_connection()
            try:
                await datasets.cleanup(GameStateRepository(redis), storage)
            finally:
                await redis.aclose()
            return succeeded
        finally:
            await lock_session.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": REFRESH_LOCK}
            )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true")
    parser.add_argument(
        "--accept-price-changes",
        action="store_true",
        help="Publish independently verified price changes over 50%% (one-shot only)",
    )
    parser.add_argument("--max-pages", type=int, default=80)
    parser.add_argument("--source", choices=["rimi", "klick"])
    args = parser.parse_args()
    if not 1 <= args.max_pages <= 200:
        parser.error("--max-pages must be between 1 and 200")
    if args.schedule and args.accept_price_changes:
        parser.error("--accept-price-changes is only allowed for a reviewed one-shot refresh")
    if args.accept_price_changes:
        log.warning("Operator accepted large regular-price changes for this refresh")
    sources = (args.source,) if args.source else ("rimi", "klick")
    succeeded = await refresh(
        missing_only=args.schedule,
        max_pages=args.max_pages,
        sources=sources,
        accept_price_changes=args.accept_price_changes,
    )
    if not args.schedule and not succeeded:
        raise SystemExit(1)
    while args.schedule:
        due = next_refresh(datetime.now(UTC))
        log.info("Next price refresh: %s", due.isoformat())
        await asyncio.sleep((due - datetime.now(UTC)).total_seconds())
        await refresh(max_pages=args.max_pages, sources=sources)


if __name__ == "__main__":
    asyncio.run(main())
