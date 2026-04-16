"""Add highfreq event stream working table

Revision ID: 028_hf_evt_stream
Revises: 027_highfreq_raw
Create Date: 2026-04-16 03:42:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "028_hf_evt_stream"
down_revision: Union[str, None] = "027_highfreq_raw"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "highfreq_event_stream_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=True),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_event_stream_working_time", "highfreq_event_stream_working", ["event_time"], schema="ifa2")
    op.create_index("ix_highfreq_event_stream_working_type", "highfreq_event_stream_working", ["event_type"], schema="ifa2")


def downgrade() -> None:
    op.drop_index("ix_highfreq_event_stream_working_type", table_name="highfreq_event_stream_working", schema="ifa2")
    op.drop_index("ix_highfreq_event_stream_working_time", table_name="highfreq_event_stream_working", schema="ifa2")
    op.drop_table("highfreq_event_stream_working", schema="ifa2")
