"""Add Job 10A2 asset batch tables - forecast, margin, north_south_flow

Revision ID: 013_lowfreq_asset_batch2
Revises: 012_lowfreq_asset_batch1
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "013_lowfreq_asset_batch2"
down_revision: Union[str, None] = "012_lowfreq_asset_batch1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_fund_forecast_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("type", sa.String(50)),
        sa.Column("eps", sa.Float),
        sa.Column("eps_yoy", sa.Float),
        sa.Column("net_profit", sa.Float),
        sa.Column("net_profit_yoy", sa.Float),
        sa.Column("gross_profit_margin", sa.Float),
        sa.Column("net_profit_margin", sa.Float),
        sa.Column("roe", sa.Float),
        sa.Column("earnings_weight", sa.Float),
        sa.Column("conference_type", sa.String(100)),
        sa.Column("org_type", sa.String(50)),
        sa.Column("org_sname", sa.String(100)),
        sa.Column("analyst_name", sa.String(100)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_fund_forecast_current_ts_code",
        "stock_fund_forecast_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_fund_forecast_current_end_date",
        "stock_fund_forecast_current",
        ["end_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_stock_fund_forecast_current_key",
        "stock_fund_forecast_current",
        ["ts_code", "end_date", "type"],
        schema="ifa2",
    )

    op.create_table(
        "margin_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("rzye", sa.Float),
        sa.Column("rzmre", sa.Float),
        sa.Column("rzche", sa.Float),
        sa.Column("rzche_ratio", sa.Float),
        sa.Column("rqye", sa.Float),
        sa.Column("rqmcl", sa.Float),
        sa.Column("rqchl", sa.Float),
        sa.Column("rqchl_ratio", sa.Float),
        sa.Column("total_market", sa.Float),
        sa.Column("total_margin", sa.Float),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_margin_current_trade_date", "margin_current", ["trade_date"], schema="ifa2"
    )
    op.create_index(
        "ix_margin_current_ts_code", "margin_current", ["ts_code"], schema="ifa2"
    )
    op.create_unique_constraint(
        "uq_margin_current_key",
        "margin_current",
        ["trade_date", "ts_code"],
        schema="ifa2",
    )

    op.create_table(
        "north_south_flow_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("north_money", sa.Float),
        sa.Column("south_money", sa.Float),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_north_south_flow_current_trade_date",
        "north_south_flow_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_north_south_flow_current_ts_code",
        "north_south_flow_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_north_south_flow_current_key",
        "north_south_flow_current",
        ["trade_date", "ts_code"],
        schema="ifa2",
    )

    op.create_table(
        "stock_fund_forecast_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("type", sa.String(50)),
        sa.Column("eps", sa.Float),
        sa.Column("eps_yoy", sa.Float),
        sa.Column("net_profit", sa.Float),
        sa.Column("net_profit_yoy", sa.Float),
        sa.Column("gross_profit_margin", sa.Float),
        sa.Column("net_profit_margin", sa.Float),
        sa.Column("roe", sa.Float),
        sa.Column("earnings_weight", sa.Float),
        sa.Column("conference_type", sa.String(100)),
        sa.Column("org_type", sa.String(50)),
        sa.Column("org_sname", sa.String(100)),
        sa.Column("analyst_name", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_fund_forecast_history_version_id",
        "stock_fund_forecast_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "margin_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("rzye", sa.Float),
        sa.Column("rzmre", sa.Float),
        sa.Column("rzche", sa.Float),
        sa.Column("rzche_ratio", sa.Float),
        sa.Column("rqye", sa.Float),
        sa.Column("rqmcl", sa.Float),
        sa.Column("rqchl", sa.Float),
        sa.Column("rqchl_ratio", sa.Float),
        sa.Column("total_market", sa.Float),
        sa.Column("total_margin", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_margin_history_version_id", "margin_history", ["version_id"], schema="ifa2"
    )

    op.create_table(
        "north_south_flow_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("north_money", sa.Float),
        sa.Column("south_money", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_north_south_flow_history_version_id",
        "north_south_flow_history",
        ["version_id"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_north_south_flow_history_version_id", schema="ifa2")
    op.drop_table("north_south_flow_history", schema="ifa2")
    op.drop_index("ix_margin_history_version_id", schema="ifa2")
    op.drop_table("margin_history", schema="ifa2")
    op.drop_index("ix_stock_fund_forecast_history_version_id", schema="ifa2")
    op.drop_table("stock_fund_forecast_history", schema="ifa2")

    op.drop_index("ix_north_south_flow_current_ts_code", schema="ifa2")
    op.drop_index("ix_north_south_flow_current_trade_date", schema="ifa2")
    op.drop_constraint(
        "uq_north_south_flow_current_key", "north_south_flow_current", schema="ifa2"
    )
    op.drop_table("north_south_flow_current", schema="ifa2")

    op.drop_index("ix_margin_current_ts_code", schema="ifa2")
    op.drop_index("ix_margin_current_trade_date", schema="ifa2")
    op.drop_constraint("uq_margin_current_key", "margin_current", schema="ifa2")
    op.drop_table("margin_current", schema="ifa2")

    op.drop_index("ix_stock_fund_forecast_current_end_date", schema="ifa2")
    op.drop_index("ix_stock_fund_forecast_current_ts_code", schema="ifa2")
    op.drop_constraint(
        "uq_stock_fund_forecast_current_key",
        "stock_fund_forecast_current",
        schema="ifa2",
    )
    op.drop_table("stock_fund_forecast_current", schema="ifa2")
