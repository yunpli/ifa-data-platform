"""Low-frequency framework schema

Revision ID: 002_lowfreq
Revises: 001_initial
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_lowfreq"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lowfreq_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_name", sa.String(255), nullable=False, unique=True),
        sa.Column("market", sa.String(50), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Integer, default=1),
        sa.Column("timezone_semantics", sa.String(50), nullable=False),
        sa.Column("runner_type", sa.String(50), nullable=False),
        sa.Column("watermark_strategy", sa.String(50), nullable=False),
        sa.Column("budget_records_max", sa.Integer),
        sa.Column("budget_seconds_max", sa.Integer),
        sa.Column("metadata", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "lowfreq_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("records_processed", sa.Integer, default=0),
        sa.Column("watermark", sa.String(255)),
        sa.Column("error_message", sa.Text),
        sa.Column("run_type", sa.String(50)),
        sa.Column("dry_run", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_lowfreq_runs_dataset_name",
        "lowfreq_runs",
        ["dataset_name"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_lowfreq_runs_dataset_name", schema="ifa2")
    op.drop_table("lowfreq_runs", schema="ifa2")
    op.drop_table("lowfreq_datasets", schema="ifa2")
