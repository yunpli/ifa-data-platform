"""Add highfreq futures-family minute working table

Revision ID: 030_hf_fut_min
Revises: 029_hf_proxy_idx
Create Date: 2026-04-16 03:52:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "030_hf_fut_min"
down_revision: Union[str, None] = "029_hf_proxy_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "highfreq_futures_minute_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("ts_code", sa.String(32), nullable=False),
        sa.Column("bucket", sa.String(32), nullable=False),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4)),
        sa.Column("high", sa.Numeric(18, 4)),
        sa.Column("low", sa.Numeric(18, 4)),
        sa.Column("close", sa.Numeric(18, 4)),
        sa.Column("vol", sa.Numeric(24, 2)),
        sa.Column("amount", sa.Numeric(24, 2)),
        sa.Column("oi", sa.Numeric(24, 2)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_futures_minute_working_key", "highfreq_futures_minute_working", ["ts_code", "trade_time"], unique=True, schema="ifa2")


def downgrade() -> None:
    op.drop_index("ix_highfreq_futures_minute_working_key", table_name="highfreq_futures_minute_working", schema="ifa2")
    op.drop_table("highfreq_futures_minute_working", schema="ifa2")
