import logging
from pathlib import Path

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from partygame.api.api_v1.api import api_router
from partygame.core.config import settings
from partygame.db.postgres import AsyncSessionLocal
from partygame.schemas import MediaKind
from partygame.service.auth import seed_admin_user
from partygame.service.definitions import get_default_definition_provider, seed_missing_definitions
from partygame.service.media import get_media_storage

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(name)s - %(levelname)s: %(message)s"
)

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")


@app.on_event("startup")
async def seed_builtin_game_definitions():
    async with AsyncSessionLocal() as session:
        await seed_admin_user(session)
    imported = await seed_missing_definitions(get_default_definition_provider())
    if imported:
        logging.getLogger(__name__).info("Seeded %s built-in game definitions", imported)


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

media_storage = get_media_storage()
seed_dir = Path(__file__).resolve().parents[1] / "media_seed"
for asset_id, kind, filename, content_type in (
    ("demo-city-skyline", MediaKind.IMAGE, "city-skyline.svg", "image/svg+xml"),
    ("demo-animal-closeup", MediaKind.IMAGE, "animal-closeup.svg", "image/svg+xml"),
    ("demo-movie-poster", MediaKind.IMAGE, "movie-poster.svg", "image/svg+xml"),
    ("demo-landmark-detail", MediaKind.IMAGE, "landmark-detail.svg", "image/svg+xml"),
    ("demo-jellybeans-jar", MediaKind.IMAGE, "jellybeans-jar.svg", "image/svg+xml"),
    ("demo-theme-song", MediaKind.AUDIO, "theme-song.mp3", "audio/mpeg"),
    ("demo-mystery-sound", MediaKind.AUDIO, "mystery-sound.mp3", "audio/mpeg"),
    ("demo-rating-clip", MediaKind.AUDIO, "rating-clip.mp3", "audio/mpeg"),
    ("demo-finale-sting", MediaKind.AUDIO, "finale-sting.mp3", "audio/mpeg"),
    ("demo-looping-clip", MediaKind.VIDEO, "looping-clip.mp4", "video/mp4"),
    ("demo-one-shot-clip", MediaKind.VIDEO, "one-shot-clip.mp4", "video/mp4"),
):
    source = seed_dir / filename
    if source.exists():
        target = media_storage.seed_dir / filename
        if not target.exists():
            target.write_bytes(source.read_bytes())
        media_storage.ensure_seed_asset(
            asset_id=asset_id,
            kind=kind,
            filename=filename,
            content_type=content_type,
            seed_relative_path=filename,
        )


@router.get("/api/health")
async def get_health():
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(router)
