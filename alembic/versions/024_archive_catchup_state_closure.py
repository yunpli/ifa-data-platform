"""Strengthen archive catch-up state closure

Revision ID: 024_archive_catchup_state
Revises: 023_unified_runtime_audit
Create Date: 2026-04-15 03:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '024_archive_catchup_state'
down_revision = '023_unified_runtime_audit'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('archive_target_catchup', sa.Column('archive_run_id', sa.String(length=64), nullable=True), schema='ifa2')
    op.add_column('archive_target_catchup', sa.Column('checkpoint_dataset_name', sa.String(length=255), nullable=True), schema='ifa2')
    op.add_column('archive_target_catchup', sa.Column('checkpoint_asset_type', sa.String(length=100), nullable=True), schema='ifa2')
    op.add_column('archive_target_catchup', sa.Column('started_at', sa.DateTime(), nullable=True), schema='ifa2')
    op.add_column('archive_target_catchup', sa.Column('completed_at', sa.DateTime(), nullable=True), schema='ifa2')
    op.add_column('archive_target_catchup', sa.Column('progress_note', sa.Text(), nullable=True), schema='ifa2')

    op.create_index(
        'ix_archive_target_catchup_run_status',
        'archive_target_catchup',
        ['archive_run_id', 'status'],
        unique=False,
        schema='ifa2',
    )
    op.create_index(
        'ix_archive_target_catchup_checkpoint',
        'archive_target_catchup',
        ['checkpoint_dataset_name', 'checkpoint_asset_type'],
        unique=False,
        schema='ifa2',
    )


def downgrade() -> None:
    op.drop_index('ix_archive_target_catchup_checkpoint', table_name='archive_target_catchup', schema='ifa2')
    op.drop_index('ix_archive_target_catchup_run_status', table_name='archive_target_catchup', schema='ifa2')
    op.drop_column('archive_target_catchup', 'progress_note', schema='ifa2')
    op.drop_column('archive_target_catchup', 'completed_at', schema='ifa2')
    op.drop_column('archive_target_catchup', 'started_at', schema='ifa2')
    op.drop_column('archive_target_catchup', 'checkpoint_asset_type', schema='ifa2')
    op.drop_column('archive_target_catchup', 'checkpoint_dataset_name', schema='ifa2')
    op.drop_column('archive_target_catchup', 'archive_run_id', schema='ifa2')
