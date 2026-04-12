"""Add B4 midfreq batch 1 tables

Revision ID: 015_midfreq_batch1
Revises: 014_symbol_universe
Create Date: 2026-04-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "015_midfreq_batch1"
down_revision: Union[str, None] = "014_symbol_universe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "equity_daily_bar_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("open", sa.Numeric(20, 4)),
        sa.Column("high", sa.Numeric(20, 4)),
        sa.Column("low", sa.Numeric(20, 4)),
        sa.Column("close", sa.Numeric(20, 4)),
        sa.Column("vol", sa.Numeric(20, 4)),
        sa.Column("amount", sa.Numeric(20, 4)),
        sa.Column("pre_close", sa.Numeric(20, 4)),
        sa.Column("change", sa.Numeric(20, 4)),
        sa.Column("pct_chg", sa.Numeric(10, 4)),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_equity_daily_bar_ts_trade",
        "equity_daily_bar_current",
        ["ts_code", "trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "equity_daily_bar_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("open", sa.Numeric(20, 4)),
        sa.Column("high", sa.Numeric(20, 4)),
        sa.Column("low", sa.Numeric(20, 4)),
        sa.Column("close", sa.Numeric(20, 4)),
        sa.Column("vol", sa.Numeric(20, 4)),
        sa.Column("amount", sa.Numeric(20, 4)),
        sa.Column("pre_close", sa.Numeric(20, 4)),
        sa.Column("change", sa.Numeric(20, 4)),
        sa.Column("pct_chg", sa.Numeric(10, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "index_daily_bar_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("open", sa.Numeric(20, 4)),
        sa.Column("high", sa.Numeric(20, 4)),
        sa.Column("low", sa.Numeric(20, 4)),
        sa.Column("close", sa.Numeric(20, 4)),
        sa.Column("vol", sa.Numeric(20, 4)),
        sa.Column("amount", sa.Numeric(20, 4)),
        sa.Column("pre_close", sa.Numeric(20, 4)),
        sa.Column("change", sa.Numeric(20, 4)),
        sa.Column("pct_chg", sa.Numeric(10, 4)),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_index_daily_bar_ts_trade",
        "index_daily_bar_current",
        ["ts_code", "trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "index_daily_bar_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("open", sa.Numeric(20, 4)),
        sa.Column("high", sa.Numeric(20, 4)),
        sa.Column("low", sa.Numeric(20, 4)),
        sa.Column("close", sa.Numeric(20, 4)),
        sa.Column("vol", sa.Numeric(20, 4)),
        sa.Column("amount", sa.Numeric(20, 4)),
        sa.Column("pre_close", sa.Numeric(20, 4)),
        sa.Column("change", sa.Numeric(20, 4)),
        sa.Column("pct_chg", sa.Numeric(10, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "etf_daily_bar_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("open", sa.Numeric(20, 4)),
        sa.Column("high", sa.Numeric(20, 4)),
        sa.Column("low", sa.Numeric(20, 4)),
        sa.Column("close", sa.Numeric(20, 4)),
        sa.Column("vol", sa.Numeric(20, 4)),
        sa.Column("amount", sa.Numeric(20, 4)),
        sa.Column("pre_close", sa.Numeric(20, 4)),
        sa.Column("change", sa.Numeric(20, 4)),
        sa.Column("pct_chg", sa.Numeric(10, 4)),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_etf_daily_bar_ts_trade",
        "etf_daily_bar_current",
        ["ts_code", "trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "etf_daily_bar_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("open", sa.Numeric(20, 4)),
        sa.Column("high", sa.Numeric(20, 4)),
        sa.Column("low", sa.Numeric(20, 4)),
        sa.Column("close", sa.Numeric(20, 4)),
        sa.Column("vol", sa.Numeric(20, 4)),
        sa.Column("amount", sa.Numeric(20, 4)),
        sa.Column("pre_close", sa.Numeric(20, 4)),
        sa.Column("change", sa.Numeric(20, 4)),
        sa.Column("pct_chg", sa.Numeric(10, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "northbound_flow_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("north_money", sa.Numeric(20, 4)),
        sa.Column("north_bal", sa.Numeric(20, 4)),
        sa.Column("north_buy", sa.Numeric(20, 4)),
        sa.Column("north_sell", sa.Numeric(20, 4)),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_northbound_flow_date",
        "northbound_flow_current",
        ["trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "northbound_flow_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("north_money", sa.Numeric(20, 4)),
        sa.Column("north_bal", sa.Numeric(20, 4)),
        sa.Column("north_buy", sa.Numeric(20, 4)),
        sa.Column("north_sell", sa.Numeric(20, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "limit_up_down_status_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("limit_up_count", sa.Integer),
        sa.Column("limit_down_count", sa.Integer),
        sa.Column("limit_up_streak_high", sa.Integer),
        sa.Column("limit_down_streak_high", sa.Integer),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_limit_up_down_date",
        "limit_up_down_status_current",
        ["trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "limit_up_down_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("limit_up_count", sa.Integer),
        sa.Column("limit_down_count", sa.Integer),
        sa.Column("limit_up_streak_high", sa.Integer),
        sa.Column("limit_down_streak_high", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "midfreq_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_name", sa.String(64), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("source_name", sa.String(32), nullable=False),
        sa.Column("job_type", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("true")),
        sa.Column("timezone_semantics", sa.String(32), server_default="china_shanghai"),
        sa.Column("runner_type", sa.String(32), server_default="generic"),
        sa.Column("watermark_strategy", sa.String(32), server_default="date_based"),
        sa.Column("budget_records_max", sa.Integer),
        sa.Column("budget_seconds_max", sa.Integer),
        sa.Column("metadata", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_midfreq_datasets_name",
        "midfreq_datasets",
        ["dataset_name"],
        schema="ifa2",
    )

    op.create_table(
        "midfreq_daemon_state",
        sa.Column("daemon_name", sa.String(64), primary_key=True),
        sa.Column("latest_loop_at", sa.DateTime),
        sa.Column("latest_status", sa.String(32)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "midfreq_window_state",
        sa.Column("window_type", sa.String(64), primary_key=True),
        sa.Column("group_name", sa.String(64)),
        sa.Column("succeeded_today", sa.Boolean, server_default=sa.text("false")),
        sa.Column("retry_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("last_status", sa.String(32)),
        sa.Column("last_run_time", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_index(
        "ix_equity_daily_bar_ts_code",
        "equity_daily_bar_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_equity_daily_bar_date",
        "equity_daily_bar_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_index_daily_bar_ts_code",
        "index_daily_bar_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_index_daily_bar_date",
        "index_daily_bar_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_etf_daily_bar_ts_code", "etf_daily_bar_current", ["ts_code"], schema="ifa2"
    )
    op.create_index(
        "ix_etf_daily_bar_date", "etf_daily_bar_current", ["trade_date"], schema="ifa2"
    )
    op.create_index(
        "ix_northbound_flow_date",
        "northbound_flow_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_limit_up_down_date",
        "limit_up_down_status_current",
        ["trade_date"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_limit_up_down_date", schema="ifa2")
    op.drop_index("ix_northbound_flow_date", schema="ifa2")
    op.drop_index("ix_etf_daily_bar_date", schema="ifa2")
    op.drop_index("ix_etf_daily_bar_ts_code", schema="ifa2")
    op.drop_index("ix_index_daily_bar_date", schema="ifa2")
    op.drop_index("ix_index_daily_bar_ts_code", schema="ifa2")
    op.drop_index("ix_equity_daily_bar_date", schema="ifa2")
    op.drop_index("ix_equity_daily_bar_ts_code", schema="ifa2")

    op.drop_table("midfreq_window_state", schema="ifa2")
    op.drop_table("midfreq_daemon_state", schema="ifa2")
    op.drop_table("midfreq_datasets", schema="ifa2")
    op.drop_table("limit_up_down_status_history", schema="ifa2")
    op.drop_table("limit_up_down_status_current", schema="ifa2")
    op.drop_table("northbound_flow_history", schema="ifa2")
    op.drop_table("northbound_flow_current", schema="ifa2")
    op.drop_table("etf_daily_bar_history", schema="ifa2")
    op.drop_table("etf_daily_bar_current", schema="ifa2")
    op.drop_table("index_daily_bar_history", schema="ifa2")
    op.drop_table("index_daily_bar_current", schema="ifa2")
    op.drop_table("equity_daily_bar_history", schema="ifa2")
    op.drop_table("equity_daily_bar_current", schema="ifa2")
