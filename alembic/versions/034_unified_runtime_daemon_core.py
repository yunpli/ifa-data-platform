"""Add unified runtime daemon governance tables

Revision ID: 034_unified_runtime_daemon
Revises: 033_highfreq_scope_management
Create Date: 2026-04-16 06:55:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '034_unified_runtime_daemon'
down_revision = '033_hf_scope_mgmt'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'runtime_worker_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('worker_type', sa.String(length=32), nullable=False),
        sa.Column('schedule_key', sa.String(length=128), nullable=False),
        sa.Column('group_name', sa.String(length=128), nullable=True),
        sa.Column('trigger_type', sa.String(length=32), nullable=False, server_default='daily_time'),
        sa.Column('timezone', sa.String(length=64), nullable=False, server_default='Asia/Shanghai'),
        sa.Column('beijing_time_hm', sa.String(length=5), nullable=True),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('cadence_minutes', sa.Integer(), nullable=True),
        sa.Column('runtime_budget_sec', sa.Integer(), nullable=False, server_default='1800'),
        sa.Column('overlap_policy', sa.String(length=32), nullable=False, server_default='skip'),
        sa.Column('retry_policy', sa.String(length=32), nullable=False, server_default='degrade'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('schedule_source', sa.String(length=32), nullable=False, server_default='seeded_from_code'),
        sa.Column('schedule_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('worker_type', 'schedule_key', name='uq_runtime_worker_schedules_worker_key'),
        schema='ifa2',
    )
    op.create_index('ix_runtime_worker_schedules_enabled', 'runtime_worker_schedules', ['enabled', 'worker_type'], unique=False, schema='ifa2')
    op.create_index('ix_runtime_worker_schedules_due', 'runtime_worker_schedules', ['worker_type', 'beijing_time_hm', 'day_of_week'], unique=False, schema='ifa2')

    op.create_table(
        'runtime_worker_state',
        sa.Column('worker_type', sa.String(length=32), primary_key=True, nullable=False),
        sa.Column('last_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('last_schedule_key', sa.String(length=128), nullable=True),
        sa.Column('last_trigger_mode', sa.String(length=32), nullable=True),
        sa.Column('last_started_at', sa.DateTime(), nullable=True),
        sa.Column('last_completed_at', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.String(length=32), nullable=True),
        sa.Column('active_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('active_schedule_key', sa.String(length=128), nullable=True),
        sa.Column('active_started_at', sa.DateTime(), nullable=True),
        sa.Column('last_heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_due_at_utc', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        schema='ifa2',
    )

    op.add_column('unified_runtime_runs', sa.Column('schedule_key', sa.String(length=128), nullable=True), schema='ifa2')
    op.add_column('unified_runtime_runs', sa.Column('triggered_for_beijing_time', sa.String(length=16), nullable=True), schema='ifa2')
    op.add_column('unified_runtime_runs', sa.Column('runtime_budget_sec', sa.Integer(), nullable=True), schema='ifa2')
    op.add_column('unified_runtime_runs', sa.Column('duration_ms', sa.Integer(), nullable=True), schema='ifa2')
    op.add_column('unified_runtime_runs', sa.Column('tables_updated', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='ifa2')
    op.add_column('unified_runtime_runs', sa.Column('tasks_executed', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='ifa2')
    op.add_column('unified_runtime_runs', sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'), schema='ifa2')
    op.add_column('unified_runtime_runs', sa.Column('governance_state', sa.String(length=32), nullable=True), schema='ifa2')

    op.create_index('ix_unified_runtime_runs_schedule_key', 'unified_runtime_runs', ['lane', 'schedule_key', 'started_at'], unique=False, schema='ifa2')
    op.create_index('ix_unified_runtime_runs_governance_state', 'unified_runtime_runs', ['governance_state', 'status'], unique=False, schema='ifa2')


def downgrade() -> None:
    op.drop_index('ix_unified_runtime_runs_governance_state', table_name='unified_runtime_runs', schema='ifa2')
    op.drop_index('ix_unified_runtime_runs_schedule_key', table_name='unified_runtime_runs', schema='ifa2')
    op.drop_column('unified_runtime_runs', 'governance_state', schema='ifa2')
    op.drop_column('unified_runtime_runs', 'error_count', schema='ifa2')
    op.drop_column('unified_runtime_runs', 'tasks_executed', schema='ifa2')
    op.drop_column('unified_runtime_runs', 'tables_updated', schema='ifa2')
    op.drop_column('unified_runtime_runs', 'duration_ms', schema='ifa2')
    op.drop_column('unified_runtime_runs', 'runtime_budget_sec', schema='ifa2')
    op.drop_column('unified_runtime_runs', 'triggered_for_beijing_time', schema='ifa2')
    op.drop_column('unified_runtime_runs', 'schedule_key', schema='ifa2')
    op.drop_table('runtime_worker_state', schema='ifa2')
    op.drop_index('ix_runtime_worker_schedules_due', table_name='runtime_worker_schedules', schema='ifa2')
    op.drop_index('ix_runtime_worker_schedules_enabled', table_name='runtime_worker_schedules', schema='ifa2')
    op.drop_table('runtime_worker_schedules', schema='ifa2')
