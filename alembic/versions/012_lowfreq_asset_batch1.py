"""Add Job 10A1 asset batch tables - top10_holders, top10_floatholders, pledge_stat

Revision ID: 012_lowfreq_asset_batch1
Revises: 011_lowfreq_job9_asset2
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "012_lowfreq_asset_batch1"
down_revision: Union[str, None] = "011_lowfreq_job9_asset2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "top10_holders_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("ann_date", sa.Date),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("holder_name", sa.String(255), nullable=False),
        sa.Column("hold_amount", sa.Float),
        sa.Column("hold_ratio", sa.Float),
        sa.Column("hold_float_ratio", sa.Float),
        sa.Column("hold_change", sa.Float),
        sa.Column("holder_type", sa.String(100)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_top10_holders_current_ts_code", "top10_holders_current", ["ts_code"], schema="ifa2")
    op.create_index("ix_top10_holders_current_end_date", "top10_holders_current", ["end_date"], schema="ifa2")
    op.create_unique_constraint(
        "uq_top10_holders_current_key",
        "top10_holders_current",
        ["ts_code", "end_date", "holder_name"],
        schema="ifa2",
    )

    op.create_table(
        "top10_floatholders_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("ann_date", sa.Date),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("holder_name", sa.String(255), nullable=False),
        sa.Column("hold_amount", sa.Float),
        sa.Column("hold_ratio", sa.Float),
        sa.Column("hold_float_ratio", sa.Float),
        sa.Column("hold_change", sa.Float),
        sa.Column("holder_type", sa.String(100)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_top10_floatholders_current_ts_code", "top10_floatholders_current", ["ts_code"], schema="ifa2")
    op.create_index("ix_top10_floatholders_current_end_date", "top10_floatholders_current", ["end_date"], schema="ifa2")
    op.create_unique_constraint(
        "uq_top10_floatholders_current_key",
        "top10_floatholders_current",
        ["ts_code", "end_date", "holder_name"],
        schema="ifa2",
    )

    op.create_table(
        "pledge_stat_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("pledge_count", sa.Integer),
        sa.Column("unrest_pledge", sa.Float),
        sa.Column("rest_pledge", sa.Float),
        sa.Column("total_share", sa.Float),
        sa.Column("pledge_ratio", sa.Float),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_pledge_stat_current_ts_code", "pledge_stat_current", ["ts_code"], schema="ifa2")
    op.create_index("ix_pledge_stat_current_end_date", "pledge_stat_current", ["end_date"], schema="ifa2")
    op.create_unique_constraint(
        "uq_pledge_stat_current_key",
        "pledge_stat_current",
        ["ts_code", "end_date"],
        schema="ifa2",
    )

    op.create_table(
        "top10_holders_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("ann_date", sa.Date),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("holder_name", sa.String(255), nullable=False),
        sa.Column("hold_amount", sa.Float),
        sa.Column("hold_ratio", sa.Float),
        sa.Column("hold_float_ratio", sa.Float),
        sa.Column("hold_change", sa.Float),
        sa.Column("holder_type", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_top10_holders_history_version_id", "top10_holders_history", ["version_id"], schema="ifa2")

    op.create_table(
        "top10_floatholders_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("ann_date", sa.Date),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("holder_name", sa.String(255), nullable=False),
        sa.Column("hold_amount", sa.Float),
        sa.Column("hold_ratio", sa.Float),
        sa.Column("hold_float_ratio", sa.Float),
        sa.Column("hold_change", sa.Float),
        sa.Column("holder_type", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_top10_floatholders_history_version_id", "top10_floatholders_history", ["version_id"], schema="ifa2")

    op.create_table(
        "pledge_stat_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("pledge_count", sa.Integer),
        sa.Column("unrest_pledge", sa.Float),
        sa.Column("rest_pledge", sa.Float),
        sa.Column("total_share", sa.Float),
        sa.Column("pledge_ratio", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_pledge_stat_history_version_id", "pledge_stat_history", ["version_id"], schema="ifa2")


def downgrade() -> None:
    op.drop_index("ix_pledge_stat_history_version_id", schema="ifa2")
    op.drop_table("pledge_stat_history", schema="ifa2")
    op.drop_index("ix_top10_floatholders_history_version_id", schema="ifa2")
    op.drop_table("top10_floatholders_history", schema="ifa2")
    op.drop_index("ix_top10_holders_history_version_id", schema="ifa2")
    op.drop_table("top10_holders_history", schema="ifa2")

    op.drop_index("ix_pledge_stat_current_ts_code", schema="ifa2")
    op.drop_index("ix_pledge_stat_current_end_date", schema="ifa2")
    op.drop_constraint("uq_pledge_stat_current_key", "pledge_stat_current", schema="ifa2")
    op.drop_table("pledge_stat_current", schema="ifa2")

    op.drop_index("ix_top10_floatholders_current_ts_code", schema="ifa2")
    op.drop_index("ix_top10_floatholders_current_end_date", schema="ifa2")
    op.drop_constraint("uq_top10_floatholders_current_key", "top10_floatholders_current", schema="ifa2")
    op.drop_table("top10_floatholders_current", schema="ifa2")

    op.drop_index("ix_top10_holders_current_ts_code", schema="ifa2")
    op.drop_index("ix_top10_holders_current_end_date", schema="ifa2")
    op.drop_constraint("uq_top10_holders_current_key", "top10_holders_current", schema="ifa2")
    op.drop_table("top10_holders_current", schema="ifa2")
