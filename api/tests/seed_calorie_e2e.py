"""Synthetic data only for the isolated browser-test database, never a fallback."""

import asyncio
from io import BytesIO

from PIL import Image, ImageDraw
from sqlalchemy import text

from partygame.schemas import MediaKind
from partygame.service.media import get_media_storage
from partygame.service.prices.datasets import PriceDatasets
from partygame.service.prices.quality import inspect_image


async def main():
    datasets = PriceDatasets()
    async with datasets.sessionmaker() as session:
        if await session.scalar(text("SELECT current_database()")) != "partygame_price_e2e":
            raise RuntimeError("Browser fixtures require the isolated partygame_price_e2e database")
    storage = get_media_storage()
    from partygame.schemas.calorie_game import CalorieProduct
    from partygame.service.calories.datasets import CalorieDatasets
    from tests.test_calorie_game import dataset

    products = []
    for index, record in enumerate(dataset().records):
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
            CalorieProduct.model_validate(
                {**record, "image_url": asset.public_url, "image_asset_id": asset.id, **details}
            )
        )
    await CalorieDatasets().publish(products)


if __name__ == "__main__":
    asyncio.run(main())
