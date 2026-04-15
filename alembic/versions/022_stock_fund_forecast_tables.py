"""Add stock_fund_forecast current/history tables

Revision ID: 022_stock_fund_forecast
Revises: 021tb_runtime
Create Date: 2026-04-15 01:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '022_stock_fund_forecast'
down_revision = '021tb_runtime'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'stock_fund_forecast_current',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('dataset_name', sa.String(length=64), nullable=False),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ts_code', sa.String(length=32), nullable=False),
        sa.Column('ann_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('report_type', sa.String(length=64), nullable=True),
        sa.Column('net_profit_min', sa.Numeric(), nullable=True),
        sa.Column('net_profit_max', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        schema='ifa2',
    )
    op.create_index('ix_stock_fund_forecast_current_ts_code', 'stock_fund_forecast_current', ['ts_code'], unique=False, schema='ifa2')

    op.create_table(
        'stock_fund_forecast_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('dataset_name', sa.String(length=64), nullable=False),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ts_code', sa.String(length=32), nullable=False),
        sa.Column('ann_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('report_type', sa.String(length=64), nullable=True),
        sa.Column('net_profit_min', sa.Numeric(), nullable=True),
        sa.Column('net_profit_max', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        schema='ifa2',
    )
    op.create_index('ix_stock_fund_forecast_history_ts_code', 'stock_fund_forecast_history', ['ts_code'], unique=False, schema='ifa2')


def downgrade() -> None:
    op.drop_index('ix_stock_fund_forecast_history_ts_code', table_name='stock_fund_forecast_history', schema='ifa2')
    op.drop_table('stock_fund_forecast_history', schema='ifa2')
    op.drop_index('ix_stock_fund_forecast_current_ts_code', table_name='stock_fund_forecast_current', schema='ifa2')
    op.drop_table('stock_fund_forecast_current', schema='ifa2')
