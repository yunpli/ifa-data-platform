"""Add B6 midfreq batch 2 tables

Revision ID: 016_midfreq_batch2
Revises: 015_midfreq_batch1
Create Date: 2026-04-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "016_midfreq_batch2"
down_revision: Union[str, None] = "015_midfreq_batch1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "main_force_flow_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("main_force", sa.Numeric(20, 4)),
        sa.Column("main_force_pct", sa.Numeric(10, 4)),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_main_force_flow_ts_trade",
        "main_force_flow_current",
        ["ts_code", "trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "main_force_flow_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("main_force", sa.Numeric(20, 4)),
        sa.Column("main_force_pct", sa.Numeric(10, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "sector_performance_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sector_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("sector_name", sa.String(128)),
        sa.Column("close", sa.Numeric(20, 4)),
        sa.Column("pct_chg", sa.Numeric(10, 4)),
        sa.Column("turnover_rate", sa.Numeric(10, 4)),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_sector_performance_code_date",
        "sector_performance_current",
        ["sector_code", "trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "sector_performance_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("sector_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("sector_name", sa.String(128)),
        sa.Column("close", sa.Numeric(20, 4)),
        sa.Column("pct_chg", sa.Numeric(10, 4)),
        sa.Column("turnover_rate", sa.Numeric(10, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "dragon_tiger_list_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("buy_amount", sa.Numeric(20, 4)),
        sa.Column("sell_amount", sa.Numeric(20, 4)),
        sa.Column("net_amount", sa.Numeric(20, 4)),
        sa.Column("version_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_dragon_tiger_list_ts_trade",
        "dragon_tiger_list_current",
        ["ts_code", "trade_date"],
        schema="ifa2",
    )

    op.create_table(
        "dragon_tiger_list_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("buy_amount", sa.Numeric(20, 4)),
        sa.Column("sell_amount", sa.Numeric(20, 4)),
        sa.Column("net_amount", sa.Numeric(20, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_index(
        "ix_main_force_flow_ts_code",
        "main_force_flow_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_main_force_flow_date",
        "main_force_flow_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_sector_performance_code",
        "sector_performance_current",
        ["sector_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_sector_performance_date",
        "sector_performance_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_index(
        "ix_dragon_tiger_list_ts_code",
        "dragon_tiger_list_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_dragon_tiger_list_date",
        "dragon_tiger_list_current",
        ["trade_date"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_dragon_tiger_list_date", schema="ifa2")
    op.drop_index("ix_dragon_tiger_list_ts_code", schema="ifa2")
    op.drop_index("ix_sector_performance_date", schema="ifa2")
    op.drop_index("ix_sector_performance_code", schema="ifa2")
    op.drop_index("ix_main_force_flow_date", schema="ifa2")
    op.drop_index("ix_main_force_flow_ts_code", schema="ifa2")

    op.drop_table("dragon_tiger_list_history", schema="ifa2")
    op.drop_table("dragon_tiger_list_current", schema="ifa2")
    op.drop_table("sector_performance_history", schema="ifa2")
    op.drop_table("sector_performance_current", schema="ifa2")
    op.drop_table("main_force_flow_history", schema="ifa2")
    op.drop_table("main_force_flow_current", schema="ifa2")
