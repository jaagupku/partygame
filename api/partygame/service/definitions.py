import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from partygame.db.postgres import AsyncSessionLocal
from partygame.schemas import GameDefinition
from partygame.state.definition_models import GameDefinitionRecord


class DefinitionSummary(BaseModel):
    id: str
    title: str
    description: str | None = None


class DefinitionProvider(ABC):
    @abstractmethod
    async def load(self, definition_id: str) -> GameDefinition: ...

    @abstractmethod
    async def list_definitions(self) -> list[DefinitionSummary]: ...

    @abstractmethod
    async def create(self, definition: GameDefinition) -> GameDefinition: ...

    @abstractmethod
    async def update(self, definition_id: str, definition: GameDefinition) -> GameDefinition: ...


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
        validate_definition(definition)

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
        if not path.exists():
            raise FileNotFoundError(f"Definition '{definition_id}' was not found")
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


def validate_definition(definition: GameDefinition):
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


class PostgresDefinitionProvider(DefinitionProvider):
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
    ):
        self.sessionmaker = sessionmaker

    def _payload(self, definition: GameDefinition) -> dict[str, Any]:
        return definition.model_dump(mode="json")

    def _definition_from_payload(self, payload: dict[str, Any]) -> GameDefinition:
        return GameDefinition.model_validate(payload)

    async def load(self, definition_id: str) -> GameDefinition:
        async with self.sessionmaker() as session:
            payload = await session.scalar(
                select(GameDefinitionRecord.payload).where(GameDefinitionRecord.id == definition_id)
            )
        if payload is None:
            raise FileNotFoundError(f"Definition '{definition_id}' was not found")
        return self._definition_from_payload(payload)

    async def list_definitions(self) -> list[DefinitionSummary]:
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(
                    GameDefinitionRecord.id,
                    GameDefinitionRecord.title,
                    GameDefinitionRecord.description,
                ).order_by(GameDefinitionRecord.title, GameDefinitionRecord.id)
            )
        return [
            DefinitionSummary(id=row.id, title=row.title, description=row.description)
            for row in result
        ]

    async def create(self, definition: GameDefinition) -> GameDefinition:
        validate_definition(definition)
        async with self.sessionmaker() as session:
            session.add(
                GameDefinitionRecord(
                    id=definition.id,
                    title=definition.title,
                    description=definition.description,
                    payload=self._payload(definition),
                )
            )
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise FileExistsError(f"Definition '{definition.id}' already exists") from error
        return await self.load(definition.id)

    async def update(self, definition_id: str, definition: GameDefinition) -> GameDefinition:
        validate_definition(definition)
        async with self.sessionmaker() as session:
            result = await session.execute(
                update(GameDefinitionRecord)
                .where(GameDefinitionRecord.id == definition_id)
                .values(
                    title=definition.title,
                    description=definition.description,
                    payload=self._payload(definition),
                    updated_at=func.now(),
                )
            )
            if result.rowcount == 0:
                await session.rollback()
                raise FileNotFoundError(f"Definition '{definition_id}' was not found")
            await session.commit()
        return await self.load(definition.id)


_default_definition_provider: DefinitionProvider | None = None


def get_default_definition_provider() -> DefinitionProvider:
    global _default_definition_provider
    if _default_definition_provider is None:
        _default_definition_provider = PostgresDefinitionProvider()
    return _default_definition_provider


async def seed_missing_definitions(
    provider: DefinitionProvider,
    games_dir: Path | None = None,
) -> int:
    file_provider = FileDefinitionProvider(games_dir=games_dir)
    imported = 0
    for summary in await file_provider.list_definitions():
        try:
            await provider.load(summary.id)
            continue
        except FileNotFoundError:
            pass
        await provider.create(await file_provider.load(summary.id))
        imported += 1
    return imported
