from fastapi import APIRouter

from partygame.service.definitions import FileDefinitionProvider, DefinitionSummary
from partygame.schemas import GameDefinition

router = APIRouter()
provider = FileDefinitionProvider()


@router.get("", response_model=list[DefinitionSummary])
async def list_definitions():
    return await provider.list_definitions()


@router.get("/{definition_id}", response_model=GameDefinition)
async def get_definition(definition_id: str):
    return await provider.load(definition_id)
