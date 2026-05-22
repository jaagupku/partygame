"""add game stat summaries

Revision ID: 20260522_0004
Revises: 20260427_0003
Create Date: 2026-05-22

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260522_0004"
down_revision: str | None = "20260427_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_stat_summaries",
        sa.Column("game_id", sa.Text(), nullable=False),
        sa.Column("join_code", sa.Text(), nullable=False),
        sa.Column("definition_id", sa.Text(), nullable=True),
        sa.Column("definition_title", sa.Text(), nullable=True),
        sa.Column("host_enabled", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("player_count", sa.Integer(), nullable=False),
        sa.Column("round_count", sa.Integer(), nullable=False),
        sa.Column("step_count", sa.Integer(), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("game_id"),
    )
    op.create_index(op.f("ix_game_stat_summaries_join_code"), "game_stat_summaries", ["join_code"])
    op.create_index(
        op.f("ix_game_stat_summaries_definition_id"),
        "game_stat_summaries",
        ["definition_id"],
    )
    op.create_index(
        op.f("ix_game_stat_summaries_started_at"),
        "game_stat_summaries",
        ["started_at"],
    )
    op.create_index(
        op.f("ix_game_stat_summaries_finished_at"),
        "game_stat_summaries",
        ["finished_at"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_game_stat_summaries_finished_at"), table_name="game_stat_summaries")
    op.drop_index(op.f("ix_game_stat_summaries_started_at"), table_name="game_stat_summaries")
    op.drop_index(op.f("ix_game_stat_summaries_definition_id"), table_name="game_stat_summaries")
    op.drop_index(op.f("ix_game_stat_summaries_join_code"), table_name="game_stat_summaries")
    op.drop_table("game_stat_summaries")
