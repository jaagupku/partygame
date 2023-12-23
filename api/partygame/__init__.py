import logging

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from partygame.api.api_v1.api import api_router
from partygame.core.config import settings

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(name)s - %(levelname)s: %(message)s"
)

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

router = APIRouter()
@router.get("/api/health")
async def get_health():
    return {"status": "ok"}

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(router)
