"""Add Job 9 asset extension tables - index_weight, etf_daily_basic, share_float, company_basic

Revision ID: 010_lowfreq_asset
Revises: 009_lowfreq_job8b
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "010_lowfreq_asset"
down_revision: Union[str, None] = "009_lowfreq_job8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "index_weight_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("index_code", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("con_code", sa.String(20), nullable=False),
        sa.Column("weight", sa.Float, nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_index_weight_current_index_code",
        "index_weight_current",
        ["index_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_index_weight_current_trade_date",
        "index_weight_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_index_weight_current_key",
        "index_weight_current",
        ["index_code", "trade_date", "con_code"],
        schema="ifa2",
    )

    op.create_table(
        "etf_daily_basic_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("unit_nav", sa.Float),
        sa.Column("unit_total", sa.Float),
        sa.Column("total_mv", sa.Float),
        sa.Column("nav_mv", sa.Float),
        sa.Column("share", sa.Float),
        sa.Column("adj_factor", sa.Float),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_etf_daily_basic_current_ts_code",
        "etf_daily_basic_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_etf_daily_basic_current_trade_date",
        "etf_daily_basic_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_etf_daily_basic_current_key",
        "etf_daily_basic_current",
        ["ts_code", "trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "share_float_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("float_date", sa.Date, nullable=False),
        sa.Column("float_share", sa.Float),
        sa.Column("total_share", sa.Float),
        sa.Column("free_share", sa.Float),
        sa.Column("float_mv", sa.Float),
        sa.Column("total_mv", sa.Float),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_share_float_current_ts_code",
        "share_float_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_share_float_current_trade_date",
        "share_float_current",
        ["float_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_share_float_current_key",
        "share_float_current",
        ["ts_code", "float_date"],
        schema="ifa2",
    )

    op.create_table(
        "company_basic_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(20)),
        sa.Column("chairman", sa.String(100)),
        sa.Column("manager", sa.String(100)),
        sa.Column("secretary", sa.String(100)),
        sa.Column("registered_capital", sa.Float),
        sa.Column("paid_in_capital", sa.Float),
        sa.Column("setup_date", sa.Date),
        sa.Column("province", sa.String(50)),
        sa.Column("city", sa.String(50)),
        sa.Column("introduction", sa.Text),
        sa.Column("website", sa.String(255)),
        sa.Column("email", sa.String(100)),
        sa.Column("office", sa.String(200)),
        sa.Column("employees", sa.Integer),
        sa.Column("main_business", sa.Text),
        sa.Column("business_scope", sa.Text),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_company_basic_current_ts_code",
        "company_basic_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_company_basic_current_key",
        "company_basic_current",
        ["ts_code"],
        schema="ifa2",
    )

    op.create_table(
        "stk_holdernumber_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("holder_num", sa.Integer),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stk_holdernumber_current_ts_code",
        "stk_holdernumber_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_stk_holdernumber_current_key",
        "stk_holdernumber_current",
        ["ts_code", "end_date"],
        schema="ifa2",
    )

    op.create_table(
        "index_weight_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("index_code", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("con_code", sa.String(20), nullable=False),
        sa.Column("weight", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_index_weight_history_version_id",
        "index_weight_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "etf_daily_basic_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("unit_nav", sa.Float),
        sa.Column("unit_total", sa.Float),
        sa.Column("total_mv", sa.Float),
        sa.Column("nav_mv", sa.Float),
        sa.Column("share", sa.Float),
        sa.Column("adj_factor", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_etf_daily_basic_history_version_id",
        "etf_daily_basic_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "share_float_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("float_date", sa.Date, nullable=False),
        sa.Column("float_share", sa.Float),
        sa.Column("total_share", sa.Float),
        sa.Column("free_share", sa.Float),
        sa.Column("float_mv", sa.Float),
        sa.Column("total_mv", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_share_float_history_version_id",
        "share_float_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "company_basic_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(20)),
        sa.Column("chairman", sa.String(100)),
        sa.Column("manager", sa.String(100)),
        sa.Column("secretary", sa.String(100)),
        sa.Column("registered_capital", sa.Float),
        sa.Column("paid_in_capital", sa.Float),
        sa.Column("setup_date", sa.Date),
        sa.Column("province", sa.String(50)),
        sa.Column("city", sa.String(50)),
        sa.Column("introduction", sa.Text),
        sa.Column("website", sa.String(255)),
        sa.Column("email", sa.String(100)),
        sa.Column("office", sa.String(200)),
        sa.Column("employees", sa.Integer),
        sa.Column("main_business", sa.Text),
        sa.Column("business_scope", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_company_basic_history_version_id",
        "company_basic_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "stk_holdernumber_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("holder_num", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stk_holdernumber_history_version_id",
        "stk_holdernumber_history",
        ["version_id"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_stk_holdernumber_history_version_id", schema="ifa2")
    op.drop_table("stk_holdernumber_history", schema="ifa2")
    op.drop_index("ix_company_basic_history_version_id", schema="ifa2")
    op.drop_table("company_basic_history", schema="ifa2")
    op.drop_index("ix_share_float_history_version_id", schema="ifa2")
    op.drop_table("share_float_history", schema="ifa2")
    op.drop_index("ix_etf_daily_basic_history_version_id", schema="ifa2")
    op.drop_table("etf_daily_basic_history", schema="ifa2")
    op.drop_index("ix_index_weight_history_version_id", schema="ifa2")
    op.drop_table("index_weight_history", schema="ifa2")

    op.drop_index("ix_stk_holdernumber_current_ts_code", schema="ifa2")
    op.drop_constraint(
        "uq_stk_holdernumber_current_key",
        "stk_holdernumber_current",
        schema="ifa2",
    )
    op.drop_table("stk_holdernumber_current", schema="ifa2")
    op.drop_index("ix_company_basic_current_ts_code", schema="ifa2")
    op.drop_constraint(
        "uq_company_basic_current_key",
        "company_basic_current",
        schema="ifa2",
    )
    op.drop_table("company_basic_current", schema="ifa2")
    op.drop_index("ix_share_float_current_ts_code", schema="ifa2")
    op.drop_index("ix_share_float_current_trade_date", schema="ifa2")
    op.drop_constraint(
        "uq_share_float_current_key",
        "share_float_current",
        schema="ifa2",
    )
    op.drop_table("share_float_current", schema="ifa2")
    op.drop_index("ix_etf_daily_basic_current_ts_code", schema="ifa2")
    op.drop_index("ix_etf_daily_basic_current_trade_date", schema="ifa2")
    op.drop_constraint(
        "uq_etf_daily_basic_current_key",
        "etf_daily_basic_current",
        schema="ifa2",
    )
    op.drop_table("etf_daily_basic_current", schema="ifa2")
    op.drop_index("ix_index_weight_current_index_code", schema="ifa2")
    op.drop_index("ix_index_weight_current_trade_date", schema="ifa2")
    op.drop_constraint(
        "uq_index_weight_current_key",
        "index_weight_current",
        schema="ifa2",
    )
    op.drop_table("index_weight_current", schema="ifa2")
