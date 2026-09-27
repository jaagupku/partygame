"""Supported price categories and their public data sources."""

from typing import Literal, get_args

ProductRange = Literal["groceries", "electronics", "furniture", "antiques"]
PriceRetailer = Literal["rimi", "klick", "tootemaailm", "eantiik"]
PRODUCT_RANGES = get_args(ProductRange)
SOURCE_RANGES: dict[str, ProductRange] = {
    "rimi": "groceries",
    "klick": "electronics",
    "tootemaailm": "furniture",
    "eantiik": "antiques",
}


def sources_for(ranges):
    return [source for source, product_range in SOURCE_RANGES.items() if product_range in ranges]
