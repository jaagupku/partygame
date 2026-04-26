from __future__ import annotations

import copy
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError

from partygame.core.config import settings
from partygame.schemas import GameDefinition, MediaAsset, MediaKind
from partygame.service.definitions import (
    DefinitionProvider,
    DefinitionValidationError,
    PostgresDefinitionProvider,
    validate_definition,
)
from partygame.service.media import LocalFilesystemMediaStorage
from partygame.state.auth_models import UserRecord
from partygame.state.definition_models import DefinitionVisibility

ARCHIVE_VERSION = 1
DEFINITION_FILE = "definition.json"
MANIFEST_FILE = "manifest.json"


@dataclass
class ImportedDefinition:
    definition: GameDefinition
    visibility: DefinitionVisibility
    media_asset_ids: list[str]


def _media_public_base_pattern() -> re.Pattern[str]:
    public_base = settings.MEDIA_PUBLIC_BASE.rstrip("/")
    return re.compile(rf"^{re.escape(public_base)}/([^/?#]+)$")


def _asset_id_from_src(src: str) -> str | None:
    match = _media_public_base_pattern().match(src)
    if not match:
        return None
    return match.group(1)


def _iter_media(definition: GameDefinition):
    for round_definition in definition.rounds:
        for step in round_definition.steps:
            if step.media is not None and step.media.src:
                yield step.media


def _archive_media_path(asset: MediaAsset) -> str:
    suffix = Path(asset.original_filename or asset.storage_path).suffix.lower()
    return f"media/{asset.id}{suffix}"


async def build_definition_export_zip(
    *,
    definition: GameDefinition,
    media_storage: LocalFilesystemMediaStorage,
) -> bytes:
    payload = definition.model_dump(mode="json")
    media_entries: list[dict[str, Any]] = []
    bundled_asset_ids: set[str] = set()
    output = io.BytesIO()

    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(DEFINITION_FILE, json.dumps(payload, indent=2) + "\n")

        for media in _iter_media(definition):
            asset_id = _asset_id_from_src(media.src)
            if asset_id is None or asset_id in bundled_asset_ids:
                continue

            asset = await media_storage.get(asset_id)
            media_path = _archive_media_path(asset)
            file_path = await media_storage.open(asset)
            archive.write(file_path, media_path)
            bundled_asset_ids.add(asset_id)
            media_entries.append(
                {
                    "src": media.src,
                    "archive_path": media_path,
                    "asset_id": asset.id,
                    "kind": asset.kind.value,
                    "filename": asset.original_filename,
                    "content_type": asset.content_type,
                    "size_bytes": asset.size_bytes,
                }
            )

        manifest = {
            "version": ARCHIVE_VERSION,
            "definition_id": definition.id,
            "media": media_entries,
        }
        archive.writestr(MANIFEST_FILE, json.dumps(manifest, indent=2) + "\n")

    return output.getvalue()


def _read_archive_json(archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
    try:
        with archive.open(name) as file_handle:
            payload = file_handle.read()
    except KeyError as error:
        raise HTTPException(status_code=422, detail=f"Archive is missing {name}") from error
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=422, detail=f"{name} is not valid JSON") from error
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail=f"{name} must contain a JSON object")
    return parsed


def _validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("version") != ARCHIVE_VERSION:
        raise HTTPException(status_code=422, detail="Unsupported definition archive version")
    media_entries = manifest.get("media", [])
    if not isinstance(media_entries, list):
        raise HTTPException(status_code=422, detail="Archive manifest media must be a list")
    for entry in media_entries:
        if not isinstance(entry, dict):
            raise HTTPException(
                status_code=422, detail="Archive manifest media entries must be objects"
            )
        if not isinstance(entry.get("src"), str) or not isinstance(entry.get("archive_path"), str):
            raise HTTPException(
                status_code=422, detail="Archive manifest media entry is incomplete"
            )
        archive_path = entry["archive_path"]
        if archive_path.startswith("/") or ".." in Path(archive_path).parts:
            raise HTTPException(status_code=422, detail="Archive manifest media path is invalid")
    return media_entries


async def _next_copy_definition_id(
    *,
    base_id: str,
    definition_provider: DefinitionProvider,
) -> str:
    candidates = [
        base_id,
        f"{base_id}_copy",
        *[f"{base_id}_copy_{index}" for index in range(2, 10_000)],
    ]
    for candidate in candidates:
        try:
            await definition_provider.load(candidate)
        except FileNotFoundError:
            return candidate
    raise HTTPException(
        status_code=409, detail="Could not allocate a copy id for imported definition"
    )


async def parse_definition_import_zip(
    *,
    content: bytes,
    definition_provider: DefinitionProvider,
    media_storage: LocalFilesystemMediaStorage,
) -> ImportedDefinition:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise HTTPException(
            status_code=422, detail="Uploaded file is not a valid zip archive"
        ) from error

    saved_asset_ids: list[str] = []
    try:
        with archive:
            definition_payload = _read_archive_json(archive, DEFINITION_FILE)
            manifest = _read_archive_json(archive, MANIFEST_FILE)
            media_entries = _validate_manifest(manifest)
            try:
                definition = GameDefinition.model_validate(definition_payload)
                validate_definition(definition)
            except (ValidationError, DefinitionValidationError, ValueError) as error:
                raise HTTPException(
                    status_code=422, detail=f"Definition is invalid: {error}"
                ) from error

            source_rewrites: dict[str, str] = {}
            for entry in media_entries:
                archive_path = entry["archive_path"]
                try:
                    media_bytes = archive.read(archive_path)
                except KeyError as error:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Archive is missing media file {archive_path}",
                    ) from error
                try:
                    kind = MediaKind(entry.get("kind", "image"))
                except ValueError as error:
                    raise HTTPException(
                        status_code=422, detail="Archive manifest media kind is invalid"
                    ) from error
                asset = await media_storage.save(
                    content=media_bytes,
                    kind=kind,
                    filename=entry.get("filename") or Path(archive_path).name,
                    content_type=entry.get("content_type") or "",
                )
                saved_asset_ids.append(asset.id)
                source_rewrites[entry["src"]] = asset.public_url
    except Exception:
        for asset_id in saved_asset_ids:
            try:
                await media_storage.delete(asset_id)
            except Exception:
                pass
        raise

    imported_definition = copy.deepcopy(definition)
    for media in _iter_media(imported_definition):
        if media.src in source_rewrites:
            media.src = source_rewrites[media.src]

    imported_definition.id = await _next_copy_definition_id(
        base_id=imported_definition.id,
        definition_provider=definition_provider,
    )
    return ImportedDefinition(
        definition=imported_definition,
        visibility=DefinitionVisibility.PRIVATE,
        media_asset_ids=saved_asset_ids,
    )


async def create_imported_definition(
    *,
    imported: ImportedDefinition,
    definition_provider: DefinitionProvider,
    media_storage: LocalFilesystemMediaStorage,
    current_user: UserRecord,
):
    try:
        if isinstance(definition_provider, PostgresDefinitionProvider):
            return await definition_provider.create_for_user(
                imported.definition,
                current_user,
                imported.visibility,
            )
        return await definition_provider.create(imported.definition)
    except Exception:
        for asset_id in imported.media_asset_ids:
            try:
                await media_storage.delete(asset_id)
            except Exception:
                pass
        raise
