"""Add runtime schedule policy day-type governance

Revision ID: 035_runtime_schedule_policy
Revises: 034_unified_runtime_daemon
Create Date: 2026-04-16 07:28:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '035_runtime_schedule_policy'
down_revision = '034_unified_runtime_daemon'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('runtime_worker_schedules', sa.Column('day_type', sa.String(length=32), nullable=True), schema='ifa2')
    op.add_column('runtime_worker_schedules', sa.Column('purpose', sa.Text(), nullable=True), schema='ifa2')
    op.execute("UPDATE ifa2.runtime_worker_schedules SET day_type = 'legacy_seeded', purpose = 'legacy seeded schedule before policy redesign' WHERE day_type IS NULL")
    op.alter_column('runtime_worker_schedules', 'day_type', nullable=False, schema='ifa2')
    op.create_index('ix_runtime_worker_schedules_day_type', 'runtime_worker_schedules', ['day_type', 'worker_type', 'enabled'], unique=False, schema='ifa2')


def downgrade() -> None:
    op.drop_index('ix_runtime_worker_schedules_day_type', table_name='runtime_worker_schedules', schema='ifa2')
    op.drop_column('runtime_worker_schedules', 'purpose', schema='ifa2')
    op.drop_column('runtime_worker_schedules', 'day_type', schema='ifa2')
