from fastapi import APIRouter

from partygame.service.game_catalog import GAME_TYPES, GameType

router = APIRouter()


@router.get("", response_model=list[GameType])
async def list_game_types():
    return list(GAME_TYPES)


@router.get("/price_guessing/availability")
async def price_availability():
    from partygame.service.prices.datasets import PriceDatasets

    return await PriceDatasets().availability()
