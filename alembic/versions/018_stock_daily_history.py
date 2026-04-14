"""Add stock_daily_history table for D2 Stock Historical Archive Layer

Revision ID: 018_stock_daily_history
Revises: 017_archive_control
Create Date: 2026-04-13

Tables:
- stock_daily_history: Stock daily OHLCV data from Tushare for historical archive

This is the D2 implementation for stock daily historical data archive.
- Supports backfill from checkpoint
- Stores OHLCV data: open, high, low, close, volume, turnover, pct_change
- Target: active stocks from each sector/board (top 10-30 per board)
- Uses ts_code for unique identification
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "018_stock_daily_history"
down_revision: Union[str, None] = "017_archive_control"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_daily_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("pre_close", sa.Numeric(18, 4)),
        sa.Column("change", sa.Numeric(18, 4)),
        sa.Column("pct_chg", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("adjusted", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("source", sa.String(50), default="tushare"),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_daily_history_ts_date",
        "stock_daily_history",
        ["ts_code", "trade_date"],
        schema="ifa2",
        unique=True,
    )
    op.create_index(
        "ix_stock_daily_history_date",
        "stock_daily_history",
        ["trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "stock_history_checkpoint",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_name", sa.String(255), nullable=False),
        sa.Column("last_completed_date", sa.Date),
        sa.Column("last_ts_code", sa.String(20)),
        sa.Column("batch_no", sa.Integer, default=0),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_stock_history_checkpoint_dataset",
        "stock_history_checkpoint",
        ["dataset_name"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_unique_constraint(
        "uq_stock_history_checkpoint_dataset",
        "stock_history_checkpoint",
        schema="ifa2",
    )
    op.drop_table("stock_history_checkpoint", schema="ifa2")
    op.drop_index("ix_stock_daily_history_date", schema="ifa2")
    op.drop_index("ix_stock_daily_history_ts_date", schema="ifa2")
    op.drop_table("stock_daily_history", schema="ifa2")
