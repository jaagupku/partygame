"""Publication gates. A failed candidate never replaces the last good version."""

from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO

from PIL import Image, ImageStat

from partygame.schemas.game_session import DatasetSnapshot
from partygame.schemas.price_game import PriceGameSettings, PriceProduct
from partygame.service.prices.generator import PriceGenerator

MIN_PRODUCTS = 40
MIN_CATEGORIES = 3
MIN_CATEGORY_PRODUCTS = 4
MIN_IMAGE_SIDE = 256
MAX_IMAGE_PIXELS = 16_000_000


def inspect_image(data: bytes):
    try:
        with Image.open(BytesIO(data), formats=("JPEG", "PNG", "WEBP")) as image:
            width, height = image.size
            if min(width, height) < MIN_IMAGE_SIDE or width * height > MAX_IMAGE_PIXELS:
                raise ValueError("Product image resolution outside accepted bounds")
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Animated product image")
            format_ = image.format
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image.load()  # Header verification alone does not detect truncated pixel data.
            if max(ImageStat.Stat(image.convert("RGB")).stddev) < 2:
                raise ValueError("Blank product image")
    except (OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError("Unreadable product image") from error
    suffix, mime = {
        "JPEG": ("jpg", "image/jpeg"),
        "PNG": ("png", "image/png"),
        "WEBP": ("webp", "image/webp"),
    }[format_]
    return (
        suffix,
        mime,
        {"image_width": width, "image_height": height, "image_sha256": sha256(data).hexdigest()},
    )


def validate_dataset(
    source: str, products: list[PriceProduct], previous=(), *, accept_price_changes=False
):
    expected_range = {"rimi": "groceries", "klick": "electronics"}.get(source)
    if expected_range is None or len(products) < MIN_PRODUCTS:
        raise ValueError(
            f"Dataset requires at least {MIN_PRODUCTS} products from a supported source"
        )
    if any(p.retailer != source or p.product_range != expected_range for p in products):
        raise ValueError("Dataset contains products from the wrong source or range")
    for label, values in {
        "product IDs": [p.id for p in products],
        "source URLs": [p.source_url for p in products],
        "product descriptions": [
            (p.title.casefold().strip(), p.detail.casefold().strip()) for p in products
        ],
    }.items():
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate {label}")
    if any(
        not p.id.strip()
        or not p.title.strip()
        or not p.category.strip()
        or not p.image_asset_id
        or min(p.image_width, p.image_height) < MIN_IMAGE_SIDE
        or len(p.image_sha256) != 64
        for p in products
    ):
        raise ValueError("Incomplete product or unverified image")
    categories = Counter(p.category for p in products)
    if sum(count >= MIN_CATEGORY_PRODUCTS for count in categories.values()) < MIN_CATEGORIES:
        raise ValueError("Dataset needs at least three categories with four products each")
    if previous and len(products) * 2 < len(previous):
        raise ValueError("Dataset lost more than half its product coverage")
    old = {p.id: p for p in previous}
    changed = [
        p.id
        for p in products
        if p.id in old and abs(p.price_minor - old[p.id].price_minor) * 2 > old[p.id].price_minor
    ]
    if changed and not accept_price_changes:
        raise ValueError(
            f"Regular prices changed by over 50%; review before publication: {changed}"
        )
    snapshot = DatasetSnapshot(
        source_id=source,
        dataset_id="validation",
        version="candidate",
        captured_at=datetime.now(UTC),
        records=[p.model_dump(mode="json") for p in products],
    )
    for mode in ("guess", "compare", "mixed"):
        PriceGenerator().generate(
            PriceGameSettings(mode=mode, product_range=expected_range, questions=20),
            seed=0,
            dataset=snapshot,
        )
    return {
        "products": len(products),
        "categories": len(categories),
        "reviewed_price_changes": len(changed),
    }
