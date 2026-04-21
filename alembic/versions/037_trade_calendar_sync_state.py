"""Add trade calendar sync state table

Revision ID: 037_trade_calendar_sync_state
Revises: 036_archive_60m_and_structured_outputs
Create Date: 2026-04-21 06:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '037_trade_calendar_sync_state'
down_revision = '036_archive_60m_and_structured'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trade_calendar_sync_state',
        sa.Column('exchange', sa.String(length=16), primary_key=True, nullable=False),
        sa.Column('last_successful_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_successful_run_id', sa.String(length=64), nullable=True),
        sa.Column('last_successful_version_id', sa.String(length=64), nullable=True),
        sa.Column('last_successful_start_date', sa.Date(), nullable=True),
        sa.Column('last_successful_end_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        schema='ifa2',
    )


def downgrade() -> None:
    op.drop_table('trade_calendar_sync_state', schema='ifa2')
