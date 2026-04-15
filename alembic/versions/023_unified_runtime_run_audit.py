"""Add unified runtime run audit table

Revision ID: 023_unified_runtime_audit
Revises: 022_stock_fund_forecast
Create Date: 2026-04-15 03:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '023_unified_runtime_audit'
down_revision = '022_stock_fund_forecast'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'unified_runtime_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('lane', sa.String(length=32), nullable=False),
        sa.Column('worker_type', sa.String(length=128), nullable=False),
        sa.Column('trigger_mode', sa.String(length=64), nullable=False),
        sa.Column('manifest_snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('manifest_id', sa.String(length=64), nullable=False),
        sa.Column('manifest_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('records_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['manifest_snapshot_id'], ['ifa2.target_manifest_snapshots.id'], ondelete='SET NULL'),
        schema='ifa2',
    )
    op.create_index(
        'ix_unified_runtime_runs_lane_started',
        'unified_runtime_runs',
        ['lane', 'started_at'],
        unique=False,
        schema='ifa2',
    )
    op.create_index(
        'ix_unified_runtime_runs_manifest_hash',
        'unified_runtime_runs',
        ['manifest_hash'],
        unique=False,
        schema='ifa2',
    )
    op.create_index(
        'ix_unified_runtime_runs_status',
        'unified_runtime_runs',
        ['status', 'lane'],
        unique=False,
        schema='ifa2',
    )


def downgrade() -> None:
    op.drop_index('ix_unified_runtime_runs_status', table_name='unified_runtime_runs', schema='ifa2')
    op.drop_index('ix_unified_runtime_runs_manifest_hash', table_name='unified_runtime_runs', schema='ifa2')
    op.drop_index('ix_unified_runtime_runs_lane_started', table_name='unified_runtime_runs', schema='ifa2')
    op.drop_table('unified_runtime_runs', schema='ifa2')
