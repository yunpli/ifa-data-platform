"""Add minute archive tables and missing midfreq history/storage tables

Revision ID: 026_collection_prod_closure
Revises: 025_stock_15min_history
Create Date: 2026-04-15 19:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "026_collection_prod_closure"
down_revision: Union[str, None] = "025_stock_15min_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_intraday_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(30), nullable=False),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("oi", sa.Numeric(24, 2), nullable=True),
        sa.Column("freq", sa.String(16), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="tushare"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        f"ix_{name}_ts_time",
        name,
        ["ts_code", "trade_time"],
        unique=True,
        schema="ifa2",
    )
    op.create_index(
        f"ix_{name}_time",
        name,
        ["trade_time"],
        unique=False,
        schema="ifa2",
    )


def upgrade() -> None:
    _create_intraday_table("stock_minute_history")
    _create_intraday_table("futures_15min_history")
    _create_intraday_table("futures_minute_history")
    _create_intraday_table("commodity_15min_history")
    _create_intraday_table("commodity_minute_history")
    _create_intraday_table("precious_metal_15min_history")
    _create_intraday_table("precious_metal_minute_history")

    op.create_table(
        "southbound_flow_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("south_money", sa.Numeric(20, 4)),
        sa.Column("south_bal", sa.Numeric(20, 4)),
        sa.Column("south_buy", sa.Numeric(20, 4)),
        sa.Column("south_sell", sa.Numeric(20, 4)),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_southbound_flow_trade_date",
        "southbound_flow_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_table(
        "southbound_flow_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("south_money", sa.Numeric(20, 4)),
        sa.Column("south_bal", sa.Numeric(20, 4)),
        sa.Column("south_buy", sa.Numeric(20, 4)),
        sa.Column("south_sell", sa.Numeric(20, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "turnover_rate_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("turnover_rate", sa.Numeric(10, 4)),
        sa.Column("turnover_rate_f", sa.Numeric(10, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "limit_up_detail_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("limit", sa.String(32)),
        sa.Column("pre_limit", sa.String(32)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_table("limit_up_detail_history", schema="ifa2")
    op.drop_table("turnover_rate_history", schema="ifa2")
    op.drop_table("southbound_flow_history", schema="ifa2")
    op.drop_table("southbound_flow_current", schema="ifa2")
    for name in [
        "precious_metal_minute_history",
        "precious_metal_15min_history",
        "commodity_minute_history",
        "commodity_15min_history",
        "futures_minute_history",
        "futures_15min_history",
        "stock_minute_history",
    ]:
        op.drop_index(f"ix_{name}_time", table_name=name, schema="ifa2")
        op.drop_index(f"ix_{name}_ts_time", table_name=name, schema="ifa2")
        op.drop_table(name, schema="ifa2")
