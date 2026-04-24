from fastapi import APIRouter, Depends, HTTPException, status

from partygame.schemas import GameDefinition
from partygame.api import deps
from partygame.service.definitions import (
    DefinitionProvider,
    GameDefinitionPayload,
    GameDefinitionResponse,
    DefinitionSummary,
    DefinitionValidationError,
    PostgresDefinitionProvider,
    get_default_definition_provider,
)
from partygame.state.auth_models import UserRecord

router = APIRouter()


def get_definition_provider() -> DefinitionProvider:
    return get_default_definition_provider()


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
