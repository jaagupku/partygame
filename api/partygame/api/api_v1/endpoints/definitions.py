from fastapi import APIRouter, Depends, HTTPException, status

from partygame.schemas import GameDefinition
from partygame.service.definitions import (
    DefinitionSummary,
    DefinitionValidationError,
    FileDefinitionProvider,
)

router = APIRouter()
provider = FileDefinitionProvider()


def get_definition_provider() -> FileDefinitionProvider:
    return provider


@router.get("", response_model=list[DefinitionSummary])
async def list_definitions(
    definition_provider: FileDefinitionProvider = Depends(get_definition_provider),
):
    return await definition_provider.list_definitions()


@router.post("", response_model=GameDefinition, status_code=status.HTTP_201_CREATED)
async def create_definition(
    definition: GameDefinition,
    definition_provider: FileDefinitionProvider = Depends(get_definition_provider),
):
    try:
        return await definition_provider.create(definition)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DefinitionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{definition_id}", response_model=GameDefinition)
async def update_definition(
    definition_id: str,
    definition: GameDefinition,
    definition_provider: FileDefinitionProvider = Depends(get_definition_provider),
):
    if definition.id != definition_id:
        raise HTTPException(
            status_code=400,
            detail="Definition id in payload must match the requested definition id",
        )
    try:
        return await definition_provider.update(definition_id, definition)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DefinitionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{definition_id}", response_model=GameDefinition)
async def get_definition(
    definition_id: str,
    definition_provider: FileDefinitionProvider = Depends(get_definition_provider),
):
    return await definition_provider.load(definition_id)
