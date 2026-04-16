"""Add archive 60m and structured output tables

Revision ID: 036_archive_60m_and_structured
Revises: 035_runtime_schedule_policy
Create Date: 2026-04-16 10:38:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '036_archive_60m_and_structured'
down_revision = '035_runtime_schedule_policy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in [
        'stock_60min_history',
        'futures_60min_history',
        'commodity_60min_history',
        'precious_metal_60min_history',
    ]:
        op.create_table(
            table,
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column('ts_code', sa.String(length=64), nullable=False),
            sa.Column('trade_time', sa.DateTime(), nullable=False),
            sa.Column('open', sa.Numeric(), nullable=True),
            sa.Column('high', sa.Numeric(), nullable=True),
            sa.Column('low', sa.Numeric(), nullable=True),
            sa.Column('close', sa.Numeric(), nullable=True),
            sa.Column('vol', sa.Numeric(), nullable=True),
            sa.Column('amount', sa.Numeric(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.UniqueConstraint('ts_code', 'trade_time', name=f'uq_{table}_code_time'),
            schema='ifa2',
        )
    op.create_table(
        'daily_structured_output_archive',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('source_table', sa.String(length=128), nullable=False),
        sa.Column('business_date', sa.Date(), nullable=False),
        sa.Column('row_key', sa.String(length=256), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('source_table', 'business_date', 'row_key', name='uq_daily_structured_output_archive_key'),
        schema='ifa2',
    )


def downgrade() -> None:
    op.drop_table('daily_structured_output_archive', schema='ifa2')
    op.drop_table('precious_metal_60min_history', schema='ifa2')
    op.drop_table('commodity_60min_history', schema='ifa2')
    op.drop_table('futures_60min_history', schema='ifa2')
    op.drop_table('stock_60min_history', schema='ifa2')
