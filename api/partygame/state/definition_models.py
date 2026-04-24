from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from partygame.db.postgres import Base


class DefinitionVisibility(StrEnum):
    PRIVATE = "private"
    LOGIN_REQUIRED = "login_required"
    PUBLIC = "public"


class GameDefinitionRecord(Base):
    __tablename__ = "game_definitions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        Text,
        default=DefinitionVisibility.PUBLIC.value,
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
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
