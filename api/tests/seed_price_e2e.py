"""Synthetic data only for the isolated browser-test database, never a fallback."""

import asyncio
from datetime import UTC, datetime
from io import BytesIO

from PIL import Image, ImageDraw
from sqlalchemy import text

from partygame.schemas import MediaKind
from partygame.schemas.price_game import PriceProduct
from partygame.service.media import get_media_storage
from partygame.service.prices.datasets import PriceDatasets
from partygame.service.prices.quality import inspect_image


async def main():
    datasets = PriceDatasets()
    async with datasets.sessionmaker() as session:
        if await session.scalar(text("SELECT current_database()")) != "partygame_price_e2e":
            raise RuntimeError("Browser fixtures require the isolated partygame_price_e2e database")
    storage = get_media_storage()
    for source, product_range in [("rimi", "groceries"), ("klick", "electronics")]:
        products = []
        for index in range(48):
            image = Image.new("RGB", (600, 600), "white")
            ImageDraw.Draw(image).rectangle((150, 80, 450, 520), fill=(30 + index * 3, 90, 160))
            stream = BytesIO()
            image.save(stream, format="PNG")
            data = stream.getvalue()
            _, _, details = inspect_image(data)
            asset = await storage.save(
                content=data, kind=MediaKind.IMAGE, filename="fixture.png", content_type="image/png"
            )
            products.append(
                PriceProduct(
                    id=f"fixture-{source}-{index}",
                    retailer=source,
                    product_range=product_range,
                    category=f"fixture-category-{index % 3}",
                    title=f"E2E {product_range} {index}",
                    detail="500g" if source == "rimi" else "Test model",
                    price_minor=100 + index * 25,
                    source_url=f"https://www.{source}.ee/fixture/{index}",
                    image_url=asset.public_url,
                    image_asset_id=asset.id,
                    captured_at=datetime.now(UTC),
                    **details,
                )
            )
        await datasets.publish(source, products)


if __name__ == "__main__":
    asyncio.run(main())
