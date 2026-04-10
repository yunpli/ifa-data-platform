"""Add daemon state tables for Job 6 closure.

Revision ID: 005_lowfreq_daemon_state
Revises: 004_lowfreq_version_history
Create Date: 2026-04-10

"""

from __future__ import annotations

from alembic import op

revision = "005_lowfreq_daemon_state"
down_revision = "004_lowfreq_version_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ifa2.lowfreq_daemon_state (
            daemon_name VARCHAR(100) PRIMARY KEY,
            last_loop_at_utc TIMESTAMP WITH TIME ZONE,
            last_run_group VARCHAR(100),
            last_run_status VARCHAR(50),
            last_success_at_utc TIMESTAMP WITH TIME ZONE,
            updated_at_utc TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ifa2.lowfreq_group_state (
            id SERIAL PRIMARY KEY,
            group_name VARCHAR(100) NOT NULL UNIQUE,
            last_run_at_utc TIMESTAMP WITH TIME ZONE,
            last_success_at_utc TIMESTAMP WITH TIME ZONE,
            last_status VARCHAR(50),
            retry_count INTEGER DEFAULT 0,
            is_degraded BOOLEAN DEFAULT FALSE,
            in_fallback BOOLEAN DEFAULT FALSE,
            created_at_utc TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at_utc TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ifa2.lowfreq_group_state")
    op.execute("DROP TABLE IF EXISTS ifa2.lowfreq_daemon_state")
