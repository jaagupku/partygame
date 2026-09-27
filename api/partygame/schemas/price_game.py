from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from partygame.schemas.price_catalog import PRODUCT_RANGES, PriceRetailer, ProductRange


class PriceGameSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["guess", "compare", "mixed"] = "mixed"
    product_ranges: list[ProductRange] = Field(
        default_factory=lambda: ["groceries", "electronics"], min_length=1, max_length=4
    )
    questions: Literal[5, 10, 15, 20] = 10
    answer_seconds: Literal[15, 30, 45, 60] = 30
    reveal_seconds: Literal[4, 6, 8, 10, 15] = 4

    @model_validator(mode="before")
    @classmethod
    def legacy_range(cls, value):
        if isinstance(value, dict) and "product_range" in value:
            value = dict(value)
            if "product_ranges" in value:
                raise ValueError("Use product_ranges or product_range, not both")
            legacy = value.pop("product_range")
            if legacy not in ("groceries", "electronics", "both"):
                raise ValueError("Unknown legacy product range")
            value["product_ranges"] = ["groceries", "electronics"] if legacy == "both" else [legacy]
        return value

    @field_validator("product_ranges")
    @classmethod
    def canonical_ranges(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Product categories must be unique")
        return [product_range for product_range in PRODUCT_RANGES if product_range in value]


class PriceProduct(BaseModel):
    id: str
    retailer: PriceRetailer
    product_range: ProductRange
    category: str
    title: str
    detail: str
    price_minor: int = Field(gt=0)
    source_url: str
    image_url: str
    image_asset_id: str = ""
    image_width: int = 0
    image_height: int = 0
    image_sha256: str = ""
    captured_at: datetime


class PriceCard(BaseModel):
    id: str
    title: str
    detail: str
    image_url: str


class PriceReveal(BaseModel):
    id: str
    price_minor: int = Field(gt=0)
    retailer: str
    source_url: str
    captured_at: datetime


class PriceQuestion(BaseModel):
    mode: Literal["guess", "compare"]
    products: list[PriceCard]
    reveal_seconds: Literal[4, 6, 8, 10, 15] = 4
    # Private definition metadata, projected only after answer reveal.
    reveal: list[PriceReveal]


class PriceResult(BaseModel):
    player_id: str
    player_name: str
    answer: Any = None
    points: int = 0
