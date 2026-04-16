"""Add highfreq schedule/daemon state tables

Revision ID: 031_hf_sched_state
Revises: 030_hf_fut_min
Create Date: 2026-04-16 03:58:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "031_hf_sched_state"
down_revision: Union[str, None] = "030_hf_fut_min"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "highfreq_daemon_state",
        sa.Column("daemon_name", sa.String(64), primary_key=True),
        sa.Column("latest_loop_at", sa.DateTime(), nullable=True),
        sa.Column("latest_status", sa.String(32), nullable=True),
        sa.Column("last_window_type", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "highfreq_window_state",
        sa.Column("window_type", sa.String(64), primary_key=True),
        sa.Column("group_name", sa.String(64), nullable=False),
        sa.Column("succeeded_today", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_status", sa.String(32), nullable=True),
        sa.Column("last_run_time", sa.DateTime(), nullable=True),
        sa.Column("sla_status", sa.String(32), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "highfreq_execution_summary",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_name", sa.String(64), nullable=False),
        sa.Column("window_type", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("total_datasets", sa.Integer(), nullable=False),
        sa.Column("succeeded_datasets", sa.Integer(), nullable=False),
        sa.Column("failed_datasets", sa.Integer(), nullable=False),
        sa.Column("sla_status", sa.String(32), nullable=True),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_table("highfreq_execution_summary", schema="ifa2")
    op.drop_table("highfreq_window_state", schema="ifa2")
    op.drop_table("highfreq_daemon_state", schema="ifa2")
