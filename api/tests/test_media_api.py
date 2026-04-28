from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from partygame.core.config import settings
from partygame.schemas import MediaKind
from partygame.service.media import LocalFilesystemMediaStorage
from partygame.api.api_v1.endpoints import media as media_endpoints


def _request_with_body(body: bytes) -> Request:
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/media",
        "headers": [],
    }
    return Request(scope, receive)


@pytest.mark.asyncio
async def test_media_upload_and_fetch(tmp_path):
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")

    upload_response = await media_endpoints.upload_media(
        request=_request_with_body(b"<svg>hello</svg>"),
        kind=MediaKind.IMAGE,
        filename="Tallinn skyline.svg",
        content_type="image/svg+xml",
        storage=storage,
    )
    assert upload_response.kind == "image"
    assert upload_response.original_filename == "Tallinn skyline.svg"
    assert upload_response.public_url.startswith("/api/v1/media/")

    asset_id = upload_response.id
    meta_response = await media_endpoints.get_media_meta(asset_id=asset_id, storage=storage)
    assert meta_response.id == asset_id

    file_response = await media_endpoints.get_media_file(asset_id=asset_id, storage=storage)
    assert file_response.media_type == "image/svg+xml"
    assert Path(file_response.path).read_bytes() == b"<svg>hello</svg>"


@pytest.mark.asyncio
async def test_media_upload_limit_comes_from_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_MAX_UPLOAD_MB", 1)
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")

    upload_response = await media_endpoints.upload_media(
        request=_request_with_body(b"x" * (1024 * 1024)),
        kind=MediaKind.VIDEO,
        filename="clip.mp4",
        content_type="video/mp4",
        storage=storage,
    )
    assert upload_response.size_bytes == 1024 * 1024

    with pytest.raises(HTTPException) as error:
        await media_endpoints.upload_media(
            request=_request_with_body(b"x" * (1024 * 1024 + 1)),
            kind=MediaKind.VIDEO,
            filename="clip-too-large.mp4",
            content_type="video/mp4",
            storage=storage,
        )

    assert getattr(error.value, "status_code") == 413


@pytest.mark.asyncio
async def test_seed_media_fetch(tmp_path):
    storage = LocalFilesystemMediaStorage(root=tmp_path / "media", public_base="/api/v1/media")

    source = Path(__file__).resolve().parents[1] / "media_seed" / "city-skyline.svg"
    target = storage.seed_dir / "city-skyline.svg"
    target.write_bytes(source.read_bytes())
    storage.ensure_seed_asset(
        asset_id="demo-city-skyline",
        kind=MediaKind.IMAGE,
        filename="city-skyline.svg",
        content_type="image/svg+xml",
        seed_relative_path="city-skyline.svg",
    )

    asset = await media_endpoints.get_media_meta(asset_id="demo-city-skyline", storage=storage)
    response = await media_endpoints.get_media_file(asset_id="demo-city-skyline", storage=storage)

    assert asset.public_url == "/api/v1/media/demo-city-skyline"
    assert response.media_type == "image/svg+xml"
