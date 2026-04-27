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
from partygame.state.auth_models import UserRecord, UserRole
from partygame.state.definition_models import DefinitionVisibility, GameDefinitionRecord


class DefinitionSummary(BaseModel):
    id: str
    title: str
    description: str | None = None
    visibility: DefinitionVisibility = DefinitionVisibility.PUBLIC
    owner_user_id: str | None = None
    owner_display_name: str | None = None
    can_edit: bool = False


class GameDefinitionPayload(GameDefinition):
    id: str = ""
    visibility: DefinitionVisibility = DefinitionVisibility.PRIVATE


class GameDefinitionResponse(GameDefinition):
    visibility: DefinitionVisibility = DefinitionVisibility.PUBLIC
    owner_user_id: str | None = None
    owner_display_name: str | None = None
    can_edit: bool = False


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
    size: int
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
        stat = path.stat()
        mtime_ns = stat.st_mtime_ns
        cached = self._definitions_cache.get(definition_id)
        if cached is not None and cached.mtime_ns == mtime_ns and cached.size == stat.st_size:
            return cached.definition

        definition = self._load_from_disk(path)
        self._definitions_cache[definition_id] = _DefinitionCacheEntry(
            mtime_ns=mtime_ns,
            size=stat.st_size,
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

    def _can_edit(self, record: GameDefinitionRecord, user: UserRecord | None) -> bool:
        if user is None:
            return False
        return user.role == UserRole.ADMIN.value or record.owner_user_id == user.id

    def _can_play(self, record: GameDefinitionRecord, user: UserRecord | None) -> bool:
        if record.visibility == DefinitionVisibility.PUBLIC.value:
            return True
        if user is None:
            return False
        if record.visibility == DefinitionVisibility.LOGIN_REQUIRED.value:
            return True
        return self._can_edit(record, user)

    def _can_view_for_management(
        self, record: GameDefinitionRecord, user: UserRecord | None
    ) -> bool:
        if self._can_play(record, user):
            return True
        return self._can_edit(record, user)

    def _response(
        self,
        record: GameDefinitionRecord,
        user: UserRecord | None,
        owner_display_name: str | None = None,
    ) -> GameDefinitionResponse:
        definition = self._definition_from_payload(record.payload)
        return GameDefinitionResponse(
            **definition.model_dump(),
            visibility=DefinitionVisibility(record.visibility),
            owner_user_id=record.owner_user_id,
            owner_display_name=owner_display_name,
            can_edit=self._can_edit(record, user),
        )

    async def load_for_user(
        self,
        definition_id: str,
        user: UserRecord | None,
    ) -> GameDefinitionResponse:
        async with self.sessionmaker() as session:
            record = await session.get(GameDefinitionRecord, definition_id)
            if record is None:
                raise FileNotFoundError(f"Definition '{definition_id}' was not found")
            owner_name = None
            if record.owner_user_id is not None:
                owner_name = await session.scalar(
                    select(UserRecord.display_name).where(UserRecord.id == record.owner_user_id)
                )
        if not self._can_view_for_management(record, user):
            raise PermissionError(f"Definition '{definition_id}' is not available")
        return self._response(record, user, owner_name)

    async def require_playable(
        self,
        definition_id: str,
        user: UserRecord | None,
    ) -> GameDefinition:
        async with self.sessionmaker() as session:
            record = await session.get(GameDefinitionRecord, definition_id)
        if record is None:
            raise FileNotFoundError(f"Definition '{definition_id}' was not found")
        if not self._can_play(record, user):
            raise PermissionError(f"Definition '{definition_id}' is not available")
        return self._definition_from_payload(record.payload)

    async def load(self, definition_id: str) -> GameDefinition:
        async with self.sessionmaker() as session:
            payload = await session.scalar(
                select(GameDefinitionRecord.payload).where(GameDefinitionRecord.id == definition_id)
            )
        if payload is None:
            raise FileNotFoundError(f"Definition '{definition_id}' was not found")
        return self._definition_from_payload(payload)

    async def list_definitions_for_user(self, user: UserRecord | None) -> list[DefinitionSummary]:
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(
                    GameDefinitionRecord,
                    UserRecord.display_name,
                )
                .outerjoin(UserRecord, UserRecord.id == GameDefinitionRecord.owner_user_id)
                .order_by(GameDefinitionRecord.title, GameDefinitionRecord.id)
            )
        definitions: list[DefinitionSummary] = []
        for record, owner_display_name in result:
            if not self._can_view_for_management(record, user):
                continue
            definitions.append(
                DefinitionSummary(
                    id=record.id,
                    title=record.title,
                    description=record.description,
                    visibility=DefinitionVisibility(record.visibility),
                    owner_user_id=record.owner_user_id,
                    owner_display_name=owner_display_name,
                    can_edit=self._can_edit(record, user),
                )
            )
        return definitions

    async def list_definitions(self) -> list[DefinitionSummary]:
        return await self.list_definitions_for_user(None)

    async def create_for_user(
        self,
        definition: GameDefinition,
        user: UserRecord,
        visibility: DefinitionVisibility = DefinitionVisibility.PRIVATE,
    ) -> GameDefinitionResponse:
        validate_definition(definition)
        async with self.sessionmaker() as session:
            session.add(
                GameDefinitionRecord(
                    id=definition.id,
                    title=definition.title,
                    description=definition.description,
                    owner_user_id=user.id,
                    visibility=visibility.value,
                    payload=self._payload(definition),
                )
            )
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise FileExistsError(f"Definition '{definition.id}' already exists") from error
        return await self.load_for_user(definition.id, user)

    async def create(self, definition: GameDefinition) -> GameDefinition:
        validate_definition(definition)
        async with self.sessionmaker() as session:
            session.add(
                GameDefinitionRecord(
                    id=definition.id,
                    title=definition.title,
                    description=definition.description,
                    visibility=DefinitionVisibility.PUBLIC.value,
                    payload=self._payload(definition),
                )
            )
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise FileExistsError(f"Definition '{definition.id}' already exists") from error
        return await self.load(definition.id)

    async def update_for_user(
        self,
        definition_id: str,
        definition: GameDefinition,
        user: UserRecord,
        visibility: DefinitionVisibility,
    ) -> GameDefinitionResponse:
        validate_definition(definition)
        async with self.sessionmaker() as session:
            record = await session.get(GameDefinitionRecord, definition_id)
            if record is None:
                raise FileNotFoundError(f"Definition '{definition_id}' was not found")
            if not self._can_edit(record, user):
                raise PermissionError(f"Definition '{definition_id}' cannot be edited")
            result = await session.execute(
                update(GameDefinitionRecord)
                .where(GameDefinitionRecord.id == definition_id)
                .values(
                    title=definition.title,
                    description=definition.description,
                    payload=self._payload(definition),
                    visibility=visibility.value,
                    updated_at=func.now(),
                )
            )
            if result.rowcount == 0:
                await session.rollback()
                raise FileNotFoundError(f"Definition '{definition_id}' was not found")
            await session.commit()
        return await self.load_for_user(definition.id, user)

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

    async def delete_for_user(self, definition_id: str, user: UserRecord) -> None:
        async with self.sessionmaker() as session:
            record = await session.get(GameDefinitionRecord, definition_id)
            if record is None:
                raise FileNotFoundError(f"Definition '{definition_id}' was not found")
            if not self._can_edit(record, user):
                raise PermissionError(f"Definition '{definition_id}' cannot be deleted")
            await session.delete(record)
            await session.commit()


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
