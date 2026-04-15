"""Trailblazer runtime artifacts

Revision ID: 021tb_runtime
Revises: 020_futures_history
Create Date: 2026-04-14 23:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '021tb_runtime'
down_revision = '020_futures_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'target_manifest_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('manifest_hash', sa.String(length=64), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('owner_type', sa.String(length=64), nullable=False),
        sa.Column('owner_id', sa.String(length=128), nullable=False),
        sa.Column('selector_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('item_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        schema='ifa2',
    )
    op.create_index(
        'ix_target_manifest_snapshots_manifest_hash',
        'target_manifest_snapshots',
        ['manifest_hash'],
        unique=True,
        schema='ifa2',
    )
    op.create_index(
        'ix_target_manifest_snapshots_owner',
        'target_manifest_snapshots',
        ['owner_type', 'owner_id', 'generated_at'],
        unique=False,
        schema='ifa2',
    )

    op.create_table(
        'archive_target_catchup',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('manifest_snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('change_type', sa.String(length=32), nullable=False),
        sa.Column('dedupe_key', sa.String(length=512), nullable=False),
        sa.Column('symbol_or_series_id', sa.String(length=128), nullable=False),
        sa.Column('asset_category', sa.String(length=64), nullable=False),
        sa.Column('granularity', sa.String(length=32), nullable=False),
        sa.Column('source_list_name', sa.String(length=128), nullable=False),
        sa.Column('suggested_backfill_start', sa.Date(), nullable=True),
        sa.Column('suggested_backfill_end', sa.Date(), nullable=True),
        sa.Column('backlog_priority', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['manifest_snapshot_id'], ['ifa2.target_manifest_snapshots.id'], ondelete='SET NULL'),
        schema='ifa2',
    )
    op.create_index(
        'ix_archive_target_catchup_status',
        'archive_target_catchup',
        ['status', 'granularity', 'backlog_priority'],
        unique=False,
        schema='ifa2',
    )
    op.create_index(
        'ix_archive_target_catchup_dedupe',
        'archive_target_catchup',
        ['dedupe_key'],
        unique=False,
        schema='ifa2',
    )


def downgrade() -> None:
    op.drop_index('ix_archive_target_catchup_dedupe', table_name='archive_target_catchup', schema='ifa2')
    op.drop_index('ix_archive_target_catchup_status', table_name='archive_target_catchup', schema='ifa2')
    op.drop_table('archive_target_catchup', schema='ifa2')
    op.drop_index('ix_target_manifest_snapshots_owner', table_name='target_manifest_snapshots', schema='ifa2')
    op.drop_index('ix_target_manifest_snapshots_manifest_hash', table_name='target_manifest_snapshots', schema='ifa2')
    op.drop_table('target_manifest_snapshots', schema='ifa2')
