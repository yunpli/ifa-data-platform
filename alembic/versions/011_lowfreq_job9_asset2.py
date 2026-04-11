"""Add Job 9 asset extension tables - stk_managers, new_share, name_change

Revision ID: 011_lowfreq_job9_asset2
Revises: 010_lowfreq_asset
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "011_lowfreq_job9_asset2"
down_revision: Union[str, None] = "010_lowfreq_asset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stk_managers_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("title", sa.String(100)),
        sa.Column("gender", sa.String(10)),
        sa.Column("edu", sa.String(50)),
        sa.Column("nationality", sa.String(50)),
        sa.Column("birthday", sa.String(20)),
        sa.Column("begin_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stk_managers_current_ts_code",
        "stk_managers_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_stk_managers_current_key",
        "stk_managers_current",
        ["ts_code", "name", "begin_date"],
        schema="ifa2",
    )

    op.create_table(
        "new_share_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("ipo_date", sa.Date),
        sa.Column("issue_date", sa.Date),
        sa.Column("issue_price", sa.Float),
        sa.Column("amount", sa.Float),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_new_share_current_ts_code",
        "new_share_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_new_share_current_key",
        "new_share_current",
        ["ts_code"],
        schema="ifa2",
    )

    op.create_table(
        "name_change_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_name_change_current_ts_code",
        "name_change_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_name_change_current_start_date",
        "name_change_current",
        ["start_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_name_change_current_key",
        "name_change_current",
        ["ts_code", "start_date"],
        schema="ifa2",
    )

    op.create_table(
        "stk_managers_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("title", sa.String(100)),
        sa.Column("gender", sa.String(10)),
        sa.Column("edu", sa.String(50)),
        sa.Column("nationality", sa.String(50)),
        sa.Column("birthday", sa.String(20)),
        sa.Column("begin_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_stk_managers_history_version_id",
        "stk_managers_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "new_share_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("ipo_date", sa.Date),
        sa.Column("issue_date", sa.Date),
        sa.Column("issue_price", sa.Float),
        sa.Column("amount", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_new_share_history_version_id",
        "new_share_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "name_change_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_name_change_history_version_id",
        "name_change_history",
        ["version_id"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_name_change_history_version_id", schema="ifa2")
    op.drop_table("name_change_history", schema="ifa2")
    op.drop_index("ix_new_share_history_version_id", schema="ifa2")
    op.drop_table("new_share_history", schema="ifa2")
    op.drop_index("ix_stk_managers_history_version_id", schema="ifa2")
    op.drop_table("stk_managers_history", schema="ifa2")

    op.drop_constraint(
        "uq_name_change_current_key",
        "name_change_current",
        schema="ifa2",
    )
    op.drop_index("ix_name_change_current_start_date", schema="ifa2")
    op.drop_index("ix_name_change_current_ts_code", schema="ifa2")
    op.drop_table("name_change_current", schema="ifa2")

    op.drop_constraint(
        "uq_new_share_current_key",
        "new_share_current",
        schema="ifa2",
    )
    op.drop_index("ix_new_share_current_ts_code", schema="ifa2")
    op.drop_table("new_share_current", schema="ifa2")

    op.drop_constraint(
        "uq_stk_managers_current_key",
        "stk_managers_current",
        schema="ifa2",
    )
    op.drop_index("ix_stk_managers_current_ts_code", schema="ifa2")
    op.drop_table("stk_managers_current", schema="ifa2")
