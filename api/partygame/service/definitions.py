import json
from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel
from dataclasses import dataclass

from partygame.schemas import GameDefinition


class DefinitionSummary(BaseModel):
    id: str
    title: str
    description: str | None = None


class DefinitionProvider(ABC):
    @abstractmethod
    async def load(self, definition_id: str) -> GameDefinition: ...

    @abstractmethod
    async def list_definitions(self) -> list[DefinitionSummary]: ...


@dataclass
class _DefinitionCacheEntry:
    mtime_ns: int
    definition: GameDefinition


class FileDefinitionProvider(DefinitionProvider):
    def __init__(self, games_dir: Path | None = None):
        if games_dir is None:
            games_dir = Path(__file__).resolve().parents[2] / "games"
        self.games_dir = games_dir
        self._definitions_cache: dict[str, _DefinitionCacheEntry] = {}

    def _load_from_disk(self, path: Path) -> GameDefinition:
        with path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
        return GameDefinition.model_validate(payload)

    async def load(self, definition_id: str) -> GameDefinition:
        path = self.games_dir / f"{definition_id}.json"
        mtime_ns = path.stat().st_mtime_ns
        cached = self._definitions_cache.get(definition_id)
        if cached is not None and cached.mtime_ns == mtime_ns:
            return cached.definition

        definition = self._load_from_disk(path)
        self._definitions_cache[definition_id] = _DefinitionCacheEntry(
            mtime_ns=mtime_ns,
            definition=definition,
        )
        return definition

    async def list_definitions(self) -> list[DefinitionSummary]:
        definitions: list[DefinitionSummary] = []
        for path in sorted(self.games_dir.glob("*.json")):
            definition = await self.load(path.stem)
            definitions.append(
                DefinitionSummary(
                    id=definition.id,
                    title=definition.title,
                    description=definition.description,
                )
            )
        return definitions
