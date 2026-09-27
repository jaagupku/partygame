"""Supported price categories and their public data sources."""

from typing import Literal, get_args

ProductRange = Literal["groceries", "electronics", "furniture", "antiques", "clothing"]
PriceRetailer = Literal["rimi", "klick", "tootemaailm", "eantiik", "arvutitark", "reserved"]
PRODUCT_RANGES = get_args(ProductRange)
SOURCE_RANGES: dict[str, ProductRange] = {
    "rimi": "groceries",
    "klick": "electronics",
    "tootemaailm": "furniture",
    "eantiik": "antiques",
    "arvutitark": "electronics",
    "reserved": "clothing",
}


def sources_for(ranges):
    return [source for source, product_range in SOURCE_RANGES.items() if product_range in ranges]
