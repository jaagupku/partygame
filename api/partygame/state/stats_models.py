from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from partygame.db.postgres import Base


class GameStatSummaryRecord(Base):
    __tablename__ = "game_stat_summaries"

    game_id: Mapped[str] = mapped_column(Text, primary_key=True)
    join_code: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    definition_id: Mapped[str | None] = mapped_column(Text, index=True)
    definition_title: Mapped[str | None] = mapped_column(Text)
    host_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    round_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
