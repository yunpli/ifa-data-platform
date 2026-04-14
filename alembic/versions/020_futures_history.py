"""Add futures_history table for D4 Commodity/Futures/Precious Metals Historical Archive

Revision ID: 020_futures_history
Revises: 019_macro_history
Create Date: 2026-04-13

Tables:
- futures_history: Futures and precious metals daily data from Tushare for historical archive

This is the D4 implementation for commodity/futures/precious metals historical data archive.
- Focus on key futures contracts: precious metals (AU, AG), base metals (CU, AL, ZN), energy (SC, RB)
- Supports backfill from checkpoint
- Uses ts_code + trade_date for unique identification
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "020_futures_history"
down_revision: Union[str, None] = "019_macro_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "futures_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(30), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("pre_close", sa.Numeric(18, 4)),
        sa.Column("pre_settle", sa.Numeric(18, 4)),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("settle", sa.Numeric(18, 4)),
        sa.Column("change1", sa.Numeric(18, 4)),
        sa.Column("change2", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("oi", sa.Numeric(24, 2)),
        sa.Column("oi_chg", sa.Numeric(24, 2)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("source", sa.String(50), default="tushare"),
        schema="ifa2",
    )
    op.create_index(
        "ix_futures_history_ts_date",
        "futures_history",
        ["ts_code", "trade_date"],
        schema="ifa2",
        unique=True,
    )
    op.create_index(
        "ix_futures_history_date",
        "futures_history",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_futures_history_ts",
        "futures_history",
        ["ts_code"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_futures_history_ts", schema="ifa2")
    op.drop_index("ix_futures_history_date", schema="ifa2")
    op.drop_index("ix_futures_history_ts_date", schema="ifa2")
    op.drop_table("futures_history", schema="ifa2")
