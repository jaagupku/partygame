"""Conservative normalization of Open Food Facts as-sold nutrition."""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from urllib.parse import urlparse

from partygame.schemas.calorie_game import CalorieProduct

DRINKS = {"en:beverages", "en:milks", "en:plant-milks"}
SOLIDS = {
    "en:biscuits",
    "en:chocolates",
    "en:cheeses",
    "en:breads",
    "en:breakfast-cereals",
    "en:pastas",
    "en:rices",
    "en:nuts",
    "en:crisps",
    "en:confectioneries",
    "en:yogurts",
    "en:meats",
    "en:fish-and-seafood",
    "en:fruits",
    "en:vegetables",
    "en:spreads",
}
EXCLUDED = {
    "en:dehydrated-foods",
    "en:beverage-preparations",
    "en:powdered-milks",
    "en:food-supplements",
    "en:baby-foods",
}
FIELDS = "code,product_name,product_name_et,product_name_en,quantity,product_quantity_unit,serving_size,categories_tags,countries_tags,nutriments,nutrition_data,nutrition_data_per,image_front_url,data_quality_errors_tags"


def nutrition_basis(record):
    tags = set(record.get("categories_tags") or [])
    if tags & EXCLUDED:
        return None
    units = set()
    for value in (record.get("quantity", ""), record.get("serving_size", "")):
        for unit in re.findall(r"\d\s*(kg|mg|ml|cl|dl|g|l)\b", str(value).lower()):
            units.add("100ml" if unit in {"ml", "cl", "dl", "l"} else "100g")
    unit = record.get("product_quantity_unit")
    if unit in {"g", "kg", "mg"}:
        units.add("100g")
    elif unit in {"ml", "cl", "dl", "l"}:
        units.add("100ml")
    drink = bool(tags & DRINKS)
    solid = bool(tags & SOLIDS)
    if drink == solid or len(units) > 1:
        return None
    expected = "100ml" if drink else "100g"
    return expected if units == {expected} else None


def normalize(record, captured_at):
    basis = nutrition_basis(record)
    code = str(record.get("code", ""))
    title = (
        record.get("product_name_et") or record.get("product_name_en") or record.get("product_name")
    )
    image = record.get("image_front_url", "")
    parsed = urlparse(image)
    if (
        not basis
        or not re.fullmatch(r"\d{8,14}", code)
        or not title
        or record.get("data_quality_errors_tags")
    ):
        return None
    if (
        record.get("nutrition_data") == ""
        or parsed.scheme != "https"
        or parsed.hostname != "images.openfoodfacts.org"
    ):
        return None
    try:
        value = Decimal(str((record.get("nutriments") or {}).get("energy-kcal_100g")))
        if not value.is_finite() or not 0 < value <= 1000:
            return None
        kcal = int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))
        if kcal <= 0:
            return None
    except InvalidOperation, ValueError:
        return None
    tags = set(record.get("categories_tags") or [])
    category = min(tags & (SOLIDS | DRINKS))
    return CalorieProduct(
        id=code,
        title=str(title).strip(),
        detail=str(record.get("quantity") or ""),
        category=category,
        basis=basis,
        kcal=kcal,
        estonia="en:estonia" in (record.get("countries_tags") or []),
        source_url=f"https://world.openfoodfacts.org/product/{code}",
        image_url=image,
        original_image_url=image,
        captured_at=captured_at,
    )
