"""Low-frequency data raw mirror and canonical current tables

Revision ID: 003_lowfreq_raw_canonical
Revises: 002_lowfreq
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_lowfreq_raw_canonical"
down_revision: Union[str, None] = "002_lowfreq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lowfreq_raw_fetch",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("dataset_name", sa.String(255), nullable=False),
        sa.Column("request_params_json", sa.Text),
        sa.Column("fetched_at_utc", sa.DateTime, nullable=False),
        sa.Column("raw_payload_json", sa.Text, nullable=False),
        sa.Column("record_count", sa.Integer, default=0),
        sa.Column("watermark", sa.String(255)),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_lowfreq_raw_fetch_run_id",
        "lowfreq_raw_fetch",
        ["run_id"],
        schema="ifa2",
    )
    op.create_index(
        "ix_lowfreq_raw_fetch_dataset_name",
        "lowfreq_raw_fetch",
        ["dataset_name"],
        schema="ifa2",
    )
    op.create_index(
        "ix_lowfreq_raw_fetch_fetched_at",
        "lowfreq_raw_fetch",
        ["fetched_at_utc"],
        schema="ifa2",
    )

    op.create_table(
        "trade_cal_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cal_date", sa.Date, nullable=False),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("is_open", sa.Integer, nullable=False),
        sa.Column("pretrade_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_trade_cal_current_exchange_date",
        "trade_cal_current",
        ["exchange", "cal_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_trade_cal_current_cal_date",
        "trade_cal_current",
        ["cal_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_trade_cal_current_exchange_date",
        "trade_cal_current",
        ["exchange", "cal_date"],
        schema="ifa2",
    )

    op.create_table(
        "stock_basic_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("symbol", sa.String(20)),
        sa.Column("name", sa.String(255)),
        sa.Column("area", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("market", sa.String(50)),
        sa.Column("list_status", sa.String(10)),
        sa.Column("list_date", sa.Date),
        sa.Column("delist_date", sa.Date),
        sa.Column("is_hs", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_basic_current_ts_code",
        "stock_basic_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_stock_basic_current_ts_code",
        "stock_basic_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_basic_current_symbol",
        "stock_basic_current",
        ["symbol"],
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_basic_current_market",
        "stock_basic_current",
        ["market"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_stock_basic_current_market", schema="ifa2")
    op.drop_index("ix_stock_basic_current_symbol", schema="ifa2")
    op.drop_index("ix_stock_basic_current_ts_code", schema="ifa2")
    op.drop_table("stock_basic_current", schema="ifa2")
    op.drop_index("ix_trade_cal_current_cal_date", schema="ifa2")
    op.drop_index("ix_trade_cal_current_exchange_date", schema="ifa2")
    op.drop_table("trade_cal_current", schema="ifa2")
    op.drop_index("ix_lowfreq_raw_fetch_fetched_at", schema="ifa2")
    op.drop_index("ix_lowfreq_raw_fetch_dataset_name", schema="ifa2")
    op.drop_index("ix_lowfreq_raw_fetch_run_id", schema="ifa2")
    op.drop_table("lowfreq_raw_fetch", schema="ifa2")
