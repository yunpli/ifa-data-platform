"""Add stock_15min_history table and intraday archive checkpoint watermark

Revision ID: 025_stock_15min_history
Revises: 024_archive_catchup_state
Create Date: 2026-04-15 08:55:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "025_stock_15min_history"
down_revision: Union[str, None] = "024_archive_catchup_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "archive_checkpoints",
        sa.Column("last_completed_at", sa.DateTime(), nullable=True),
        schema="ifa2",
    )

    op.create_table(
        "stock_15min_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("freq", sa.String(16), nullable=False, server_default="15min"),
        sa.Column("source", sa.String(50), nullable=False, server_default="tushare"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_15min_history_ts_time",
        "stock_15min_history",
        ["ts_code", "trade_time"],
        unique=True,
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_15min_history_time",
        "stock_15min_history",
        ["trade_time"],
        unique=False,
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_stock_15min_history_time", table_name="stock_15min_history", schema="ifa2")
    op.drop_index("ix_stock_15min_history_ts_time", table_name="stock_15min_history", schema="ifa2")
    op.drop_table("stock_15min_history", schema="ifa2")
    op.drop_column("archive_checkpoints", "last_completed_at", schema="ifa2")
