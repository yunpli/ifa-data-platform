"""Low-frequency dataset version registry and history tables

Revision ID: 004_lowfreq_version_history
Revises: 003_lowfreq_raw_canonical
Create Date: 2026-04-10

Adds:
- dataset_versions: Version registry with promote/active semantics
- version_id column to canonical current tables
- trade_cal_history and stock_basic_history: Historical records per version
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_lowfreq_version_history"
down_revision: Union[str, None] = "003_lowfreq_raw_canonical"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_name", sa.String(255), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at_utc", sa.DateTime, nullable=False),
        sa.Column("promoted_at_utc", sa.DateTime),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Integer, default=0),
        sa.Column("supersedes_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("watermark", sa.String(255)),
        sa.Column("metadata", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_dataset_versions_dataset_name",
        "dataset_versions",
        ["dataset_name"],
        schema="ifa2",
    )
    op.create_index(
        "ix_dataset_versions_is_active",
        "dataset_versions",
        ["is_active"],
        schema="ifa2",
    )
    op.create_index(
        "ix_dataset_versions_promoted_at",
        "dataset_versions",
        ["promoted_at_utc"],
        schema="ifa2",
    )

    op.execute(
        """
        COMMENT ON TABLE ifa2.dataset_versions IS 'Dataset version registry with promote/active semantics'
        """
    )

    op.add_column(
        "trade_cal_current",
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            server_default=None,
        ),
        schema="ifa2",
    )
    op.add_column(
        "stock_basic_current",
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            server_default=None,
        ),
        schema="ifa2",
    )

    op.create_table(
        "trade_cal_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cal_date", sa.Date, nullable=False),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("is_open", sa.Integer, nullable=False),
        sa.Column("pretrade_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_trade_cal_history_version_id",
        "trade_cal_history",
        ["version_id"],
        schema="ifa2",
    )
    op.create_index(
        "ix_trade_cal_history_cal_date",
        "trade_cal_history",
        ["cal_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_trade_cal_history_version_date",
        "trade_cal_history",
        ["version_id", "cal_date"],
        schema="ifa2",
    )

    op.create_table(
        "stock_basic_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_basic_history_version_id",
        "stock_basic_history",
        ["version_id"],
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_basic_history_ts_code",
        "stock_basic_history",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_stock_basic_history_version_ts_code",
        "stock_basic_history",
        ["version_id", "ts_code"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_stock_basic_history_version_ts_code", schema="ifa2")
    op.drop_index("ix_stock_basic_history_ts_code", schema="ifa2")
    op.drop_index("ix_stock_basic_history_version_id", schema="ifa2")
    op.drop_table("stock_basic_history", schema="ifa2")
    op.drop_index("ix_trade_cal_history_version_date", schema="ifa2")
    op.drop_index("ix_trade_cal_history_cal_date", schema="ifa2")
    op.drop_index("ix_trade_cal_history_version_id", schema="ifa2")
    op.drop_table("trade_cal_history", schema="ifa2")

    op.drop_column("stock_basic_current", "version_id", schema="ifa2")
    op.drop_column("trade_cal_current", "version_id", schema="ifa2")

    op.drop_index("ix_dataset_versions_promoted_at", schema="ifa2")
    op.drop_index("ix_dataset_versions_is_active", schema="ifa2")
    op.drop_index("ix_dataset_versions_dataset_name", schema="ifa2")
    op.drop_table("dataset_versions", schema="ifa2")
