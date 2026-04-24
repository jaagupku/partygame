"""add users and definition access

Revision ID: 20260424_0002
Revises: 20260424_0001
Create Date: 2026-04-24

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260424_0002"
down_revision: str | None = "20260424_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)
    op.add_column("game_definitions", sa.Column("owner_user_id", sa.Text(), nullable=True))
    op.add_column(
        "game_definitions",
        sa.Column(
            "visibility",
            sa.Text(),
            server_default="public",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_game_definitions_owner_user_id"),
        "game_definitions",
        ["owner_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_game_definitions_owner_user_id_users",
        "game_definitions",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_game_definitions_owner_user_id_users",
        "game_definitions",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_game_definitions_owner_user_id"), table_name="game_definitions")
    op.drop_column("game_definitions", "visibility")
    op.drop_column("game_definitions", "owner_user_id")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
