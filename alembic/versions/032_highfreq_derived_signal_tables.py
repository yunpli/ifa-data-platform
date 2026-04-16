"""Add highfreq derived signal tables

Revision ID: 032_hf_derived
Revises: 031_hf_sched_state
Create Date: 2026-04-16 04:07:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "032_hf_derived"
down_revision: Union[str, None] = "031_hf_sched_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "highfreq_sector_breadth_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("sector_code", sa.String(32), nullable=False),
        sa.Column("up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("down_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("strong_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spread_ratio", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "highfreq_sector_heat_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("sector_code", sa.String(32), nullable=False),
        sa.Column("heat_score", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "highfreq_leader_candidate_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("candidate_score", sa.Numeric(18, 6), nullable=False),
        sa.Column("confirmation_state", sa.String(32), nullable=False),
        sa.Column("continuation_health", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "highfreq_limit_event_stream_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "highfreq_intraday_signal_state_working",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("scope_key", sa.String(64), nullable=False),
        sa.Column("emotion_stage", sa.String(32), nullable=False),
        sa.Column("validation_state", sa.String(32), nullable=False),
        sa.Column("risk_opportunity_state", sa.String(32), nullable=False),
        sa.Column("turnover_progress", sa.Numeric(18, 6), nullable=False),
        sa.Column("amount_progress", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_table("highfreq_intraday_signal_state_working", schema="ifa2")
    op.drop_table("highfreq_limit_event_stream_working", schema="ifa2")
    op.drop_table("highfreq_leader_candidate_working", schema="ifa2")
    op.drop_table("highfreq_sector_heat_working", schema="ifa2")
    op.drop_table("highfreq_sector_breadth_working", schema="ifa2")
