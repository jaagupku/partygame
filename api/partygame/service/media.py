from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from partygame.core.config import settings
from partygame.schemas import MediaAsset, MediaKind


class MediaStorage(ABC):
    @abstractmethod
    async def save(
        self,
        *,
        content: bytes,
        kind: MediaKind,
        filename: str,
        content_type: str,
    ) -> MediaAsset: ...

    @abstractmethod
    async def get(self, asset_id: str) -> MediaAsset: ...

    @abstractmethod
    async def open(self, asset: MediaAsset) -> Path: ...

    @abstractmethod
    async def delete(self, asset_id: str): ...

    @abstractmethod
    def build_public_url(self, asset_id: str) -> str: ...


class LocalFilesystemMediaStorage(MediaStorage):
    def __init__(self, root: Path | None = None, public_base: str | None = None):
        self.root = Path(root or settings.MEDIA_ROOT)
        self.public_base = (public_base or settings.MEDIA_PUBLIC_BASE).rstrip("/")
        self.assets_dir = self.root / "assets"
        self.metadata_dir = self.root / "metadata"
        self.seed_dir = self.root / "seed"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.seed_dir.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        *,
        content: bytes,
        kind: MediaKind,
        filename: str,
        content_type: str,
    ) -> MediaAsset:
        asset_id = uuid4().hex
        suffix = Path(filename).suffix.lower()
        storage_name = f"{asset_id}{suffix}"
        storage_path = self.assets_dir / storage_name

        size_bytes = len(content)
        max_bytes = settings.MEDIA_MAX_UPLOAD_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise HTTPException(status_code=413, detail="Uploaded file exceeds media size limit")

        storage_path.write_bytes(content)
        asset = MediaAsset(
            id=asset_id,
            kind=kind,
            storage_path=str(Path("assets") / storage_name),
            original_filename=filename or storage_name,
            content_type=content_type or self._default_content_type(kind),
            size_bytes=size_bytes,
            public_url=self.build_public_url(asset_id),
        )
        self._write_metadata(asset)
        return asset

    async def get(self, asset_id: str) -> MediaAsset:
        path = self.metadata_dir / f"{asset_id}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Media asset not found")
        return MediaAsset.model_validate(json.loads(path.read_text(encoding="utf-8")))

    async def open(self, asset: MediaAsset) -> Path:
        path = self.root / asset.storage_path
        if not path.exists():
            raise HTTPException(status_code=404, detail="Media file not found")
        return path

    async def delete(self, asset_id: str):
        asset = await self.get(asset_id)
        file_path = self.root / asset.storage_path
        file_path.unlink(missing_ok=True)
        (self.metadata_dir / f"{asset_id}.json").unlink(missing_ok=True)

    def build_public_url(self, asset_id: str) -> str:
        return f"{self.public_base}/{asset_id}"

    def ensure_seed_asset(
        self,
        *,
        asset_id: str,
        kind: MediaKind,
        filename: str,
        content_type: str,
        seed_relative_path: str,
    ) -> MediaAsset:
        asset = MediaAsset(
            id=asset_id,
            kind=kind,
            storage_path=str(Path("seed") / seed_relative_path),
            original_filename=filename,
            content_type=content_type,
            size_bytes=(self.root / "seed" / seed_relative_path).stat().st_size,
            public_url=self.build_public_url(asset_id),
        )
        self._write_metadata(asset)
        return asset

    def _write_metadata(self, asset: MediaAsset):
        (self.metadata_dir / f"{asset.id}.json").write_text(
            asset.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def _default_content_type(self, kind: MediaKind) -> str:
        if kind == MediaKind.IMAGE:
            return "image/svg+xml"
        if kind == MediaKind.AUDIO:
            return "audio/mpeg"
        return "video/mp4"


def get_media_storage() -> LocalFilesystemMediaStorage:
    return LocalFilesystemMediaStorage()
