"""Add immutable product datasets and active-session leases."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260919_0005"
down_revision = "20260522_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "price_datasets",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("products", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_price_datasets_source", "price_datasets", ["source"])
    op.create_index("ix_price_datasets_captured_at", "price_datasets", ["captured_at"])
    op.create_table(
        "price_dataset_leases",
        sa.Column("session_id", sa.Text(), primary_key=True),
        sa.Column("dataset_id", sa.Text(), sa.ForeignKey("price_datasets.id"), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    op.drop_table("price_dataset_leases")
    op.drop_table("price_datasets")
