from pathlib import Path
from typing import List, Union

from pydantic import field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SERVER_NAME: str = "partygame"
    SERVER_HOST: AnyHttpUrl = "http://localhost"
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000", \
    # "http://localhost:8080", "http://local.dockertoolbox.tiangolo.com"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5123",
        "http://127.0.0.1:5123",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "partygame"
    MEDIA_ROOT: Path = Path(__file__).resolve().parents[2] / "media"
    MEDIA_PUBLIC_BASE: str = "/api/v1/media"
    MEDIA_MAX_UPLOAD_MB: int = 25
    GAME_IDLE_TTL_SECONDS: int = 3600
    GAME_FINISHED_TTL_SECONDS: int = 900

    model_config = SettingsConfigDict(case_sensitive=True)


settings = Settings()
