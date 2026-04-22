"""Add slot replay evidence storage

Revision ID: 038_slot_replay_evidence
Revises: 037_trade_calendar_sync_state
Create Date: 2026-04-21 20:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '038_slot_replay_evidence'
down_revision = '037_trade_calendar_sync_state'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'slot_replay_evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('slot_key', sa.String(length=32), nullable=False),
        sa.Column('perspective', sa.String(length=32), nullable=False),
        sa.Column('capture_reason', sa.String(length=64), nullable=False),
        sa.Column('slot_label', sa.Text(), nullable=False),
        sa.Column('slot_cutoff_beijing', sa.String(length=5), nullable=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('primary_manifest_snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('primary_manifest_hash', sa.String(length=64), nullable=True),
        sa.Column('selection_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('manifest_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('trigger_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('worker_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('dataset_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('snapshot_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('artifact_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['primary_manifest_snapshot_id'], ['ifa2.target_manifest_snapshots.id'], ondelete='SET NULL'),
        schema='ifa2',
    )
    op.create_index('ix_slot_replay_evidence_lookup', 'slot_replay_evidence', ['trade_date', 'slot_key', 'perspective', 'captured_at'], unique=False, schema='ifa2')

    op.create_table(
        'slot_replay_evidence_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('evidence_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lane', sa.String(length=32), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='source_run'),
        sa.Column('selection_rank', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['evidence_id'], ['ifa2.slot_replay_evidence.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['ifa2.unified_runtime_runs.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('evidence_id', 'run_id', name='uq_slot_replay_evidence_runs_pair'),
        schema='ifa2',
    )
    op.create_index('ix_slot_replay_evidence_runs_evidence', 'slot_replay_evidence_runs', ['evidence_id', 'selection_rank'], unique=False, schema='ifa2')


def downgrade() -> None:
    op.drop_index('ix_slot_replay_evidence_runs_evidence', table_name='slot_replay_evidence_runs', schema='ifa2')
    op.drop_table('slot_replay_evidence_runs', schema='ifa2')
    op.drop_index('ix_slot_replay_evidence_lookup', table_name='slot_replay_evidence', schema='ifa2')
    op.drop_table('slot_replay_evidence', schema='ifa2')
