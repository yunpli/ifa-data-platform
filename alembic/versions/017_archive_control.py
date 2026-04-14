"""Add archive control tables for D1 Archive Layer Framework

Revision ID: 017_archive_control
Revises: 016_midfreq_batch2
Create Date: 2026-04-13

Tables:
- archive_jobs: Define archive jobs (job_name, asset_type, dataset_name, pool_name, scope_name)
- archive_runs: Track individual archive runs
- archive_checkpoints: Persist checkpoint for resume capability
- archive_summary_daily: Daily summary for reporting
- archive_daemon_state: Daemon state persistence
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "017_archive_control"
down_revision: Union[str, None] = "016_midfreq_batch2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "archive_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_name", sa.String(255), nullable=False, unique=True),
        sa.Column("dataset_name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(100), nullable=False),
        sa.Column("pool_name", sa.String(255), default=""),
        sa.Column("scope_name", sa.String(255), default=""),
        sa.Column("is_enabled", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_jobs_job_name",
        "archive_jobs",
        ["job_name"],
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_jobs_dataset",
        "archive_jobs",
        ["dataset_name"],
        schema="ifa2",
    )

    op.create_table(
        "archive_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False, unique=True),
        sa.Column("job_name", sa.String(255), nullable=False),
        sa.Column("dataset_name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(100), nullable=False),
        sa.Column("window_name", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("records_processed", sa.Integer, default=0),
        sa.Column("error_summary", sa.Text),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_runs_run_id",
        "archive_runs",
        ["run_id"],
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_runs_job",
        "archive_runs",
        ["job_name"],
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_runs_status",
        "archive_runs",
        ["status"],
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_runs_started",
        "archive_runs",
        ["started_at"],
        schema="ifa2",
    )

    op.create_table(
        "archive_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(100), nullable=False),
        sa.Column("backfill_start", sa.Date),
        sa.Column("backfill_end", sa.Date),
        sa.Column("last_completed_date", sa.Date),
        sa.Column("shard_id", sa.String(100)),
        sa.Column("batch_no", sa.Integer),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_archive_checkpoint_dataset",
        "archive_checkpoints",
        ["dataset_name", "asset_type"],
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_checkpoints_dataset",
        "archive_checkpoints",
        ["dataset_name", "asset_type"],
        schema="ifa2",
    )

    op.create_table(
        "archive_summary_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("window_name", sa.String(100), nullable=False),
        sa.Column("total_jobs", sa.Integer, default=0),
        sa.Column("succeeded_jobs", sa.Integer, default=0),
        sa.Column("failed_jobs", sa.Integer, default=0),
        sa.Column("total_records", sa.Integer, default=0),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_archive_summary_date_window",
        "archive_summary_daily",
        ["date", "window_name"],
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_summary_date",
        "archive_summary_daily",
        ["date"],
        schema="ifa2",
    )

    op.create_table(
        "archive_daemon_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("daemon_name", sa.String(100), nullable=False, unique=True),
        sa.Column("last_loop_at_utc", sa.DateTime),
        sa.Column("last_run_job", sa.String(255)),
        sa.Column("last_run_status", sa.String(50)),
        sa.Column("last_success_at_utc", sa.DateTime),
        sa.Column("is_running", sa.Boolean, default=False),
        sa.Column("updated_at_utc", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_archive_daemon_state_name",
        "archive_daemon_state",
        ["daemon_name"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_archive_daemon_state_name", schema="ifa2")
    op.drop_table("archive_daemon_state", schema="ifa2")
    op.drop_index("ix_archive_summary_date", schema="ifa2")
    op.drop_unique_constraint(
        "uq_archive_summary_date_window",
        "archive_summary_daily",
        schema="ifa2",
    )
    op.drop_table("archive_summary_daily", schema="ifa2")
    op.drop_index(
        "ix_archive_checkpoints_dataset",
        schema="ifa2",
    )
    op.drop_unique_constraint(
        "uq_archive_checkpoint_dataset",
        "archive_checkpoints",
        schema="ifa2",
    )
    op.drop_table("archive_checkpoints", schema="ifa2")
    op.drop_index("ix_archive_runs_started", schema="ifa2")
    op.drop_index("ix_archive_runs_status", schema="ifa2")
    op.drop_index("ix_archive_runs_job", schema="ifa2")
    op.drop_index("ix_archive_runs_run_id", schema="ifa2")
    op.drop_table("archive_runs", schema="ifa2")
    op.drop_index("ix_archive_jobs_dataset", schema="ifa2")
    op.drop_index("ix_archive_jobs_job_name", schema="ifa2")
    op.drop_table("archive_jobs", schema="ifa2")
