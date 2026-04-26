import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from partygame.core.config import settings
from partygame.schemas import GameDefinition
from partygame.api import deps
from partygame.service.definition_archive import (
    build_definition_export_zip,
    create_imported_definition,
    parse_definition_import_zip,
)
from partygame.service.definitions import (
    DefinitionProvider,
    GameDefinitionPayload,
    GameDefinitionResponse,
    DefinitionSummary,
    DefinitionValidationError,
    PostgresDefinitionProvider,
    get_default_definition_provider,
)
from partygame.service.media import LocalFilesystemMediaStorage, get_media_storage
from partygame.state.auth_models import UserRecord

router = APIRouter()


def get_definition_provider() -> DefinitionProvider:
    return get_default_definition_provider()


async def read_limited_request_body(request: Request, max_bytes: int) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_bytes:
            raise HTTPException(status_code=413, detail="Definition archive exceeds size limit")
    return bytes(body)


@router.get("", response_model=list[DefinitionSummary])
async def list_definitions(
    definition_provider: DefinitionProvider = Depends(get_definition_provider),
    current_user: UserRecord | None = Depends(deps.get_current_user_optional),
):
    if isinstance(definition_provider, PostgresDefinitionProvider):
        return await definition_provider.list_definitions_for_user(current_user)
    return await definition_provider.list_definitions()


@router.post("", response_model=GameDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_definition(
    definition: GameDefinitionPayload,
    definition_provider: DefinitionProvider = Depends(get_definition_provider),
    current_user: UserRecord = Depends(deps.get_current_user_required),
):
    try:
        game_definition = GameDefinition.model_validate(definition.model_dump())
        if isinstance(definition_provider, PostgresDefinitionProvider):
            return await definition_provider.create_for_user(
                game_definition,
                current_user,
                definition.visibility,
            )
        return await definition_provider.create(definition)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DefinitionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/import", response_model=GameDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def import_definition(
    request: Request,
    definition_provider: DefinitionProvider = Depends(get_definition_provider),
    media_storage: LocalFilesystemMediaStorage = Depends(get_media_storage),
    current_user: UserRecord = Depends(deps.get_current_user_required),
):
    content = await read_limited_request_body(
        request,
        settings.DEFINITION_ARCHIVE_MAX_UPLOAD_MB * 1024 * 1024,
    )
    imported = await parse_definition_import_zip(
        content=content,
        definition_provider=definition_provider,
        media_storage=media_storage,
    )
    try:
        return await create_imported_definition(
            imported=imported,
            definition_provider=definition_provider,
            media_storage=media_storage,
            current_user=current_user,
        )
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DefinitionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{definition_id}", response_model=GameDefinitionResponse)
async def update_definition(
    definition_id: str,
    definition: GameDefinitionPayload,
    definition_provider: DefinitionProvider = Depends(get_definition_provider),
    current_user: UserRecord = Depends(deps.get_current_user_required),
):
    if definition.id != definition_id:
        raise HTTPException(
            status_code=400,
            detail="Definition id in payload must match the requested definition id",
        )
    try:
        game_definition = GameDefinition.model_validate(definition.model_dump())
        if isinstance(definition_provider, PostgresDefinitionProvider):
            return await definition_provider.update_for_user(
                definition_id,
                game_definition,
                current_user,
                definition.visibility,
            )
        return await definition_provider.update(definition_id, game_definition)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except DefinitionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{definition_id}/export")
async def export_definition(
    definition_id: str,
    definition_provider: DefinitionProvider = Depends(get_definition_provider),
    media_storage: LocalFilesystemMediaStorage = Depends(get_media_storage),
    current_user: UserRecord | None = Depends(deps.get_current_user_optional),
):
    try:
        if isinstance(definition_provider, PostgresDefinitionProvider):
            loaded = await definition_provider.load_for_user(definition_id, current_user)
        else:
            loaded = await definition_provider.load(definition_id)
        definition = GameDefinition.model_validate(loaded.model_dump())
        archive = await build_definition_export_zip(
            definition=definition,
            media_storage=media_storage,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error

    filename = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{definition.id}.zip")
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{definition_id}", response_model=GameDefinitionResponse)
async def get_definition(
    definition_id: str,
    definition_provider: DefinitionProvider = Depends(get_definition_provider),
    current_user: UserRecord | None = Depends(deps.get_current_user_optional),
):
    try:
        if isinstance(definition_provider, PostgresDefinitionProvider):
            return await definition_provider.load_for_user(definition_id, current_user)
        return await definition_provider.load(definition_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.delete("/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_definition(
    definition_id: str,
    definition_provider: DefinitionProvider = Depends(get_definition_provider),
    current_user: UserRecord = Depends(deps.get_current_user_required),
):
    if not isinstance(definition_provider, PostgresDefinitionProvider):
        raise HTTPException(status_code=405, detail="Delete is not supported by this provider")
    try:
        await definition_provider.delete_for_user(definition_id, current_user)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
