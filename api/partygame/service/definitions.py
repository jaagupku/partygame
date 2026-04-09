import json
from abc import ABC, abstractmethod
from pathlib import Path

from partygame.schemas import GameDefinition


class DefinitionProvider(ABC):
    @abstractmethod
    async def load(self, definition_id: str) -> GameDefinition: ...


class FileDefinitionProvider(DefinitionProvider):
    def __init__(self, games_dir: Path | None = None):
        if games_dir is None:
            games_dir = Path(__file__).resolve().parents[2] / "games"
        self.games_dir = games_dir

    async def load(self, definition_id: str) -> GameDefinition:
        path = self.games_dir / f"{definition_id}.json"
        with path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
        return GameDefinition.model_validate(payload)
