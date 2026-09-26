from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PriceGameSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["guess", "compare", "mixed"] = "mixed"
    product_range: Literal["groceries", "electronics", "both"] = "both"
    questions: Literal[5, 10, 15, 20] = 10
    answer_seconds: Literal[15, 30, 45, 60] = 30


class PriceProduct(BaseModel):
    id: str
    retailer: Literal["rimi", "klick"]
    product_range: Literal["groceries", "electronics"]
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
    # Private definition metadata, projected only after answer reveal.
    reveal: list[PriceReveal]


class PriceResult(BaseModel):
    player_id: str
    player_name: str
    answer: Any = None
    points: int = 0
