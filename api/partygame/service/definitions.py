import json
from tempfile import NamedTemporaryFile
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


class DefinitionValidationError(ValueError):
    pass


@dataclass
class _DefinitionCacheEntry:
    mtime_ns: int
    definition: GameDefinition


class FileDefinitionProvider(DefinitionProvider):
    def __init__(self, games_dir: Path | None = None):
        if games_dir is None:
            games_dir = Path(__file__).resolve().parents[2] / "games"
        self.games_dir = games_dir
        self.games_dir.mkdir(parents=True, exist_ok=True)
        self._definitions_cache: dict[str, _DefinitionCacheEntry] = {}

    def _load_from_disk(self, path: Path) -> GameDefinition:
        with path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
        return GameDefinition.model_validate(payload)

    def _validate_definition(self, definition: GameDefinition):
        round_ids: set[str] = set()
        for round_definition in definition.rounds:
            if round_definition.id in round_ids:
                raise DefinitionValidationError(
                    f"Duplicate round id '{round_definition.id}' in definition '{definition.id}'"
                )
            round_ids.add(round_definition.id)

            step_ids: set[str] = set()
            for step in round_definition.steps:
                if step.id in step_ids:
                    raise DefinitionValidationError(
                        "Duplicate step id "
                        f"'{step.id}' in round '{round_definition.id}' of definition '{definition.id}'"
                    )
                step_ids.add(step.id)

    def _write_to_disk(self, path: Path, definition: GameDefinition):
        payload = definition.model_dump(mode="json")
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.games_dir,
            prefix=f"{path.stem}-",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            json.dump(payload, temp_file, indent=2)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        temp_path.replace(path)

    async def create(self, definition: GameDefinition) -> GameDefinition:
        self._validate_definition(definition)
        path = self.games_dir / f"{definition.id}.json"
        if path.exists():
            raise FileExistsError(f"Definition '{definition.id}' already exists")
        self._write_to_disk(path, definition)
        self._definitions_cache.pop(definition.id, None)
        return await self.load(definition.id)

    async def update(self, definition_id: str, definition: GameDefinition) -> GameDefinition:
        self._validate_definition(definition)
        path = self.games_dir / f"{definition_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Definition '{definition_id}' was not found")
        self._write_to_disk(path, definition)
        self._definitions_cache.pop(definition_id, None)
        if definition.id != definition_id:
            self._definitions_cache.pop(definition.id, None)
        return await self.load(definition.id)

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
