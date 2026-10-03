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


@router.get("/calorie_guessing/availability")
async def calorie_availability():
    from partygame.service.calories.datasets import CalorieDatasets

    return await CalorieDatasets().availability()


@router.get("/calorie_guessing/dataset")
async def calorie_dataset():
    from fastapi import HTTPException
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import JSONResponse

    from partygame.service.calories.datasets import CalorieDatasets
    from partygame.service.calories.generator import InsufficientCalorieData

    try:
        data = await CalorieDatasets().download()
    except InsufficientCalorieData as error:
        raise HTTPException(status_code=404, detail="calorie_content_unavailable") from error
    return JSONResponse(
        jsonable_encoder(data),
        headers={"Content-Disposition": 'attachment; filename="calorie-dataset.json"'},
    )
