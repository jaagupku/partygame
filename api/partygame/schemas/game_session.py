"""Private preparation records; never send these models to game clients."""

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from partygame.schemas.game_definition import DefinitionTheme, GameDefinition, RoundDefinition


class SourceMetadata(BaseModel):
    source_id: str
    dataset_id: str | None = None
    dataset_version: str | None = None
    captured_at: datetime | None = None
    generator_version: str | None = None
    seed: int | None = None


class RoundBundle(BaseModel):
    rounds: list[RoundDefinition]
    source: SourceMetadata
    theme: DefinitionTheme | None = None


class RoundOrigin(BaseModel):
    runtime_round_id: str
    source_round_id: str
    # Runtime step ID -> original step ID (IDs may repeat across bundles).
    step_ids: dict[str, str]
    source: SourceMetadata


class PreparedSession(BaseModel):
    version: Literal[1] = 1
    session_id: str | None = None
    datasets: list[SourceMetadata] = Field(default_factory=list)
    definition: GameDefinition
    origins: list[RoundOrigin] = Field(default_factory=list)


class DatasetSnapshot(BaseModel):
    source_id: str
    dataset_id: str
    version: str
    captured_at: datetime
    records: list[dict[str, Any]]


class RoundGenerator[Settings](Protocol):
    """Generate locally from a fixed dataset; implementations own typed settings."""

    def generate(
        self, settings: Settings, *, seed: int, dataset: DatasetSnapshot
    ) -> list[RoundBundle]: ...
