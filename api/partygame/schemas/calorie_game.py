from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from partygame.schemas.price_game import PriceCard, PriceResult

CalorieBasis = Literal["100g", "100ml"]


class CalorieGameSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["guess", "compare", "mixed"] = "mixed"
    questions: Literal[5, 10, 15, 20] = 10
    answer_seconds: Literal[15, 30, 45, 60] = 30
    reveal_seconds: Literal[4, 6, 8, 10, 15] = 4


class CalorieProduct(BaseModel):
    id: str
    title: str
    detail: str = ""
    category: str
    basis: CalorieBasis
    kcal: int = Field(gt=0, le=1000)
    estonia: bool = False
    source_url: str
    image_url: str
    original_image_url: str = ""
    image_asset_id: str = ""
    image_width: int = 0
    image_height: int = 0
    image_sha256: str = ""
    captured_at: datetime


class CalorieCard(PriceCard):
    basis: CalorieBasis


class CalorieReveal(BaseModel):
    id: str
    kcal: int = Field(gt=0, le=1000)
    basis: CalorieBasis
    source_url: str
    captured_at: datetime


class CalorieQuestion(BaseModel):
    mode: Literal["guess", "compare"]
    products: list[CalorieCard]
    reveal_seconds: Literal[4, 6, 8, 10, 15] = 4
    reveal: list[CalorieReveal]


class CalorieResult(PriceResult):
    pass
