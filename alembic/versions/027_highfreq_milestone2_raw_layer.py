"""Add highfreq working/raw tables for milestone 2

Revision ID: 027_highfreq_raw
Revises: 026_collection_prod_closure
Create Date: 2026-04-16 03:36:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "027_highfreq_raw"
down_revision: Union[str, None] = "026_collection_prod_closure"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "highfreq_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("dataset_name", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watermark", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_runs_run_id", "highfreq_runs", ["run_id"], schema="ifa2")
    op.create_index("ix_highfreq_runs_dataset_name", "highfreq_runs", ["dataset_name"], schema="ifa2")

    op.create_table(
        "highfreq_stock_1m_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("vwap", sa.Numeric(18, 4)),
        sa.Column("amplitude", sa.Numeric(18, 6)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_stock_1m_working_ts_time", "highfreq_stock_1m_working", ["ts_code", "trade_time"], unique=True, schema="ifa2")

    op.create_table(
        "highfreq_open_auction_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("vwap", sa.Numeric(18, 4)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_open_auction_working_ts_date", "highfreq_open_auction_working", ["ts_code", "trade_date"], unique=True, schema="ifa2")

    op.create_table(
        "highfreq_close_auction_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("vwap", sa.Numeric(18, 4)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_close_auction_working_ts_date", "highfreq_close_auction_working", ["ts_code", "trade_date"], unique=True, schema="ifa2")


def downgrade() -> None:
    op.drop_index("ix_highfreq_close_auction_working_ts_date", table_name="highfreq_close_auction_working", schema="ifa2")
    op.drop_table("highfreq_close_auction_working", schema="ifa2")
    op.drop_index("ix_highfreq_open_auction_working_ts_date", table_name="highfreq_open_auction_working", schema="ifa2")
    op.drop_table("highfreq_open_auction_working", schema="ifa2")
    op.drop_index("ix_highfreq_stock_1m_working_ts_time", table_name="highfreq_stock_1m_working", schema="ifa2")
    op.drop_table("highfreq_stock_1m_working", schema="ifa2")
    op.drop_index("ix_highfreq_runs_dataset_name", table_name="highfreq_runs", schema="ifa2")
    op.drop_index("ix_highfreq_runs_run_id", table_name="highfreq_runs", schema="ifa2")
    op.drop_table("highfreq_runs", schema="ifa2")
