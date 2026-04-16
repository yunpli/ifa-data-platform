"""Add highfreq index/proxy working tables

Revision ID: 029_hf_proxy_idx
Revises: 028_hf_evt_stream
Create Date: 2026-04-16 03:46:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "029_hf_proxy_idx"
down_revision: Union[str, None] = "028_hf_evt_stream"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "highfreq_index_1m_working",
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
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_index_1m_working_ts_time", "highfreq_index_1m_working", ["ts_code", "trade_time"], unique=True, schema="ifa2")

    op.create_table(
        "highfreq_proxy_1m_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("proxy_code", sa.String(32), nullable=False),
        sa.Column("proxy_type", sa.String(32), nullable=False),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_proxy_1m_working_code_time", "highfreq_proxy_1m_working", ["proxy_code", "trade_time"], unique=True, schema="ifa2")


def downgrade() -> None:
    op.drop_index("ix_highfreq_proxy_1m_working_code_time", table_name="highfreq_proxy_1m_working", schema="ifa2")
    op.drop_table("highfreq_proxy_1m_working", schema="ifa2")
    op.drop_index("ix_highfreq_index_1m_working_ts_time", table_name="highfreq_index_1m_working", schema="ifa2")
    op.drop_table("highfreq_index_1m_working", schema="ifa2")
