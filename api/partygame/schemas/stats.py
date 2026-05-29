from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GameStatSummary(BaseModel):
    game_id: str
    join_code: str
    definition_id: str | None = None
    definition_title: str | None = None
    host_enabled: bool
    started_at: datetime | None = None
    finished_at: datetime
    player_count: int
    round_count: int
    step_count: int
    summary: dict[str, Any] = Field(default_factory=dict)


class GameStatSummaryList(BaseModel):
    items: list[GameStatSummary]
    total: int
    limit: int
    offset: int
