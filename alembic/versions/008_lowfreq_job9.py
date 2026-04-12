"""Add Job 9 event metadata and slow variable tables

Revision ID: 008_lowfreq_job9
Revises: 006_lowfreq_job8a
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008_lowfreq_job9"
down_revision: Union[str, None] = "007_add_sw_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "news_basic_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("datetime", sa.DateTime),
        sa.Column("source", sa.String(255)),
        sa.Column("url", sa.String(512)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_news_basic_current_ts_code",
        "news_basic_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_news_basic_current_key",
        "news_basic_current",
        ["ts_code", "datetime"],
        schema="ifa2",
    )

    op.create_table(
        "stock_repurchase_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("ann_date", sa.Date, nullable=False),
        sa.Column("holder_name", sa.String(255)),
        sa.Column("holder_type", sa.String(50)),
        sa.Column("repur_amount", sa.Float),
        sa.Column("repur_price", sa.Float),
        sa.Column("volume", sa.Float),
        sa.Column("progress", sa.String(100)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_repurchase_current_ts_code",
        "stock_repurchase_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_stock_repurchase_current_key",
        "stock_repurchase_current",
        ["ts_code", "ann_date"],
        schema="ifa2",
    )

    op.create_table(
        "stock_dividend_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("divi_date", sa.Date, nullable=False),
        sa.Column("divi_cash", sa.Float),
        sa.Column("divi_stock", sa.Float),
        sa.Column("record_date", sa.Date),
        sa.Column("ex_date", sa.Date),
        sa.Column("pay_date", sa.Date),
        sa.Column("ann_date", sa.Date),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_dividend_current_ts_code",
        "stock_dividend_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_stock_dividend_current_key",
        "stock_dividend_current",
        ["ts_code", "divi_date"],
        schema="ifa2",
    )

    op.create_table(
        "name_change_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_name_change_current_ts_code",
        "name_change_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_name_change_current_key",
        "name_change_current",
        ["ts_code", "start_date"],
        schema="ifa2",
    )

    op.create_table(
        "new_stock_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ipo_date", sa.Date),
        sa.Column("issue_date", sa.Date),
        sa.Column("offer_price", sa.Float),
        sa.Column("total_share", sa.Float),
        sa.Column("net_assets", sa.Float),
        sa.Column("pe", sa.Float),
        sa.Column("venue", sa.String(50)),
        sa.Column("status", sa.String(50)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_new_stock_current_ts_code",
        "new_stock_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_new_stock_current_ts_code",
        "new_stock_current",
        ["ts_code"],
        schema="ifa2",
    )

    op.create_table(
        "management_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("gender", sa.String(10)),
        sa.Column("title", sa.String(100)),
        sa.Column("edu", sa.String(50)),
        sa.Column("nationality", sa.String(50)),
        sa.Column("birthday", sa.String(20)),
        sa.Column("begin_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("resume", sa.Text),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_management_current_ts_code",
        "management_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_management_current_key",
        "management_current",
        ["ts_code", "name", "begin_date"],
        schema="ifa2",
    )

    op.create_table(
        "stock_equity_change_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("ann_date", sa.Date, nullable=False),
        sa.Column("change_type", sa.String(50)),
        sa.Column("change_vol", sa.Float),
        sa.Column("change_pct", sa.Float),
        sa.Column("after_share", sa.Float),
        sa.Column("after_capital", sa.Float),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_equity_change_current_ts_code",
        "stock_equity_change_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_stock_equity_change_current_key",
        "stock_equity_change_current",
        ["ts_code", "ann_date"],
        schema="ifa2",
    )

    op.create_table(
        "news_basic_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("datetime", sa.DateTime),
        sa.Column("source", sa.String(255)),
        sa.Column("url", sa.String(512)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_news_basic_history_version_id",
        "news_basic_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "stock_repurchase_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("ann_date", sa.Date, nullable=False),
        sa.Column("holder_name", sa.String(255)),
        sa.Column("holder_type", sa.String(50)),
        sa.Column("repur_amount", sa.Float),
        sa.Column("repur_price", sa.Float),
        sa.Column("volume", sa.Float),
        sa.Column("progress", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_repurchase_history_version_id",
        "stock_repurchase_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "stock_dividend_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("divi_date", sa.Date, nullable=False),
        sa.Column("divi_cash", sa.Float),
        sa.Column("divi_stock", sa.Float),
        sa.Column("record_date", sa.Date),
        sa.Column("ex_date", sa.Date),
        sa.Column("pay_date", sa.Date),
        sa.Column("ann_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_dividend_history_version_id",
        "stock_dividend_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "name_change_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_name_change_history_version_id",
        "name_change_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "new_stock_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ipo_date", sa.Date),
        sa.Column("issue_date", sa.Date),
        sa.Column("offer_price", sa.Float),
        sa.Column("total_share", sa.Float),
        sa.Column("net_assets", sa.Float),
        sa.Column("pe", sa.Float),
        sa.Column("venue", sa.String(50)),
        sa.Column("status", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_new_stock_history_version_id",
        "new_stock_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "management_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("gender", sa.String(10)),
        sa.Column("title", sa.String(100)),
        sa.Column("edu", sa.String(50)),
        sa.Column("nationality", sa.String(50)),
        sa.Column("birthday", sa.String(20)),
        sa.Column("begin_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("resume", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_management_history_version_id",
        "management_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "stock_equity_change_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("ann_date", sa.Date, nullable=False),
        sa.Column("change_type", sa.String(50)),
        sa.Column("change_vol", sa.Float),
        sa.Column("change_pct", sa.Float),
        sa.Column("after_share", sa.Float),
        sa.Column("after_capital", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_equity_change_history_version_id",
        "stock_equity_change_history",
        ["version_id"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_stock_equity_change_history_version_id", schema="ifa2")
    op.drop_table("stock_equity_change_history", schema="ifa2")
    op.drop_index("ix_management_history_version_id", schema="ifa2")
    op.drop_table("management_history", schema="ifa2")
    op.drop_index("ix_new_stock_history_version_id", schema="ifa2")
    op.drop_table("new_stock_history", schema="ifa2")
    op.drop_index("ix_name_change_history_version_id", schema="ifa2")
    op.drop_table("name_change_history", schema="ifa2")
    op.drop_index("ix_stock_dividend_history_version_id", schema="ifa2")
    op.drop_table("stock_dividend_history", schema="ifa2")
    op.drop_index("ix_stock_repurchase_history_version_id", schema="ifa2")
    op.drop_table("stock_repurchase_history", schema="ifa2")
    op.drop_index("ix_news_basic_history_version_id", schema="ifa2")
    op.drop_table("news_basic_history", schema="ifa2")

    op.drop_index("ix_stock_equity_change_current_ts_code", schema="ifa2")
    op.drop_constraint(
        "uq_stock_equity_change_current_key",
        "stock_equity_change_current",
        schema="ifa2",
    )
    op.drop_table("stock_equity_change_current", schema="ifa2")
    op.drop_index("ix_management_current_ts_code", schema="ifa2")
    op.drop_constraint("uq_management_current_key", "management_current", schema="ifa2")
    op.drop_table("management_current", schema="ifa2")
    op.drop_index("ix_new_stock_current_ts_code", schema="ifa2")
    op.drop_constraint(
        "uq_new_stock_current_ts_code", "new_stock_current", schema="ifa2"
    )
    op.drop_table("new_stock_current", schema="ifa2")
    op.drop_index("ix_name_change_current_ts_code", schema="ifa2")
    op.drop_constraint(
        "uq_name_change_current_key", "name_change_current", schema="ifa2"
    )
    op.drop_table("name_change_current", schema="ifa2")
    op.drop_index("ix_stock_dividend_current_ts_code", schema="ifa2")
    op.drop_constraint(
        "uq_stock_dividend_current_key", "stock_dividend_current", schema="ifa2"
    )
    op.drop_table("stock_dividend_current", schema="ifa2")
    op.drop_index("ix_stock_repurchase_current_ts_code", schema="ifa2")
    op.drop_constraint(
        "uq_stock_repurchase_current_key", "stock_repurchase_current", schema="ifa2"
    )
    op.drop_table("stock_repurchase_current", schema="ifa2")
    op.drop_index("ix_news_basic_current_ts_code", schema="ifa2")
    op.drop_constraint("uq_news_basic_current_key", "news_basic_current", schema="ifa2")
    op.drop_table("news_basic_current", schema="ifa2")
