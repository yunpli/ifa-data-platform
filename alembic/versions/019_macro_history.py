"""Add macro_history table for D3 Macro Historical Archive

Revision ID: 019_macro_history
Revises: 018_stock_daily_history
Create Date: 2026-04-13

Tables:
- macro_history: Macro economic indicators from Tushare for historical archive

This is the D3 implementation for macro historical data archive.
- Key macro variables: interest rates, CPI, PPI, PMI, GDP, industrial production, social financing, M2
- Supports backfill from checkpoint
- Uses macro_series + date for unique identification
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "019_macro_history"
down_revision: Union[str, None] = "018_stock_daily_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "macro_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("macro_series", sa.String(100), nullable=False),
        sa.Column("indicator_name", sa.String(255), nullable=False),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("value", sa.Numeric(24, 6)),
        sa.Column("unit", sa.String(50)),
        sa.Column("source", sa.String(50), default="tushare"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_macro_history_series_date",
        "macro_history",
        ["macro_series", "report_date"],
        schema="ifa2",
        unique=True,
    )
    op.create_index(
        "ix_macro_history_date",
        "macro_history",
        ["report_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_macro_history_series",
        "macro_history",
        ["macro_series"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_macro_history_series", schema="ifa2")
    op.drop_index("ix_macro_history_date", schema="ifa2")
    op.drop_index("ix_macro_history_series_date", schema="ifa2")
    op.drop_table("macro_history", schema="ifa2")
