"""Add index_basic, fund_basic_etf, sw_industry_mapping current and history tables

Revision ID: 006_lowfreq_job8a
Revises: 004_lowfreq_version_history
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006_lowfreq_job8a"
down_revision: Union[str, None] = "005_lowfreq_daemon_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "index_basic_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("market", sa.String(50)),
        sa.Column("publisher", sa.String(255)),
        sa.Column("category", sa.String(50)),
        sa.Column("base_date", sa.Date),
        sa.Column("base_point", sa.Float),
        sa.Column("list_date", sa.Date),
        sa.Column("weight_rule", sa.String(255)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_index_basic_current_ts_code",
        "index_basic_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_index_basic_current_ts_code",
        "index_basic_current",
        ["ts_code"],
        schema="ifa2",
    )

    op.create_table(
        "fund_basic_etf_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("market", sa.String(50)),
        sa.Column("fund_type", sa.String(50)),
        sa.Column("management", sa.String(255)),
        sa.Column("custodian", sa.String(255)),
        sa.Column("list_date", sa.Date),
        sa.Column("due_date", sa.Date),
        sa.Column("issue_date", sa.Date),
        sa.Column("delist_date", sa.Date),
        sa.Column("invest_type", sa.String(50)),
        sa.Column("benchmark", sa.String(255)),
        sa.Column("status", sa.String(20)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_fund_basic_etf_current_ts_code",
        "fund_basic_etf_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_fund_basic_etf_current_ts_code",
        "fund_basic_etf_current",
        ["ts_code"],
        schema="ifa2",
    )

    op.create_table(
        "sw_industry_mapping_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("index_code", sa.String(50), nullable=False),
        sa.Column("industry_name", sa.String(255)),
        sa.Column("level", sa.Integer),
        sa.Column("parent_code", sa.String(50)),
        sa.Column("src", sa.String(20)),
        sa.Column("member_ts_code", sa.String(20)),
        sa.Column("member_name", sa.String(255)),
        sa.Column("in_date", sa.Date),
        sa.Column("out_date", sa.Date),
        sa.Column("is_active", sa.Integer, nullable=False, default=1),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_sw_industry_mapping_current_index_code",
        "sw_industry_mapping_current",
        ["index_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_sw_industry_mapping_current_member_ts_code",
        "sw_industry_mapping_current",
        ["member_ts_code"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_sw_industry_mapping_current_key",
        "sw_industry_mapping_current",
        ["index_code", "member_ts_code", "in_date"],
        schema="ifa2",
    )

    op.create_table(
        "index_basic_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("market", sa.String(50)),
        sa.Column("publisher", sa.String(255)),
        sa.Column("category", sa.String(50)),
        sa.Column("base_date", sa.Date),
        sa.Column("base_point", sa.Float),
        sa.Column("list_date", sa.Date),
        sa.Column("weight_rule", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_index_basic_history_version_id",
        "index_basic_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "fund_basic_etf_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("market", sa.String(50)),
        sa.Column("fund_type", sa.String(50)),
        sa.Column("management", sa.String(255)),
        sa.Column("custodian", sa.String(255)),
        sa.Column("list_date", sa.Date),
        sa.Column("due_date", sa.Date),
        sa.Column("issue_date", sa.Date),
        sa.Column("delist_date", sa.Date),
        sa.Column("invest_type", sa.String(50)),
        sa.Column("benchmark", sa.String(255)),
        sa.Column("status", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_fund_basic_etf_history_version_id",
        "fund_basic_etf_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "sw_industry_mapping_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("index_code", sa.String(50), nullable=False),
        sa.Column("industry_name", sa.String(255)),
        sa.Column("level", sa.Integer),
        sa.Column("parent_code", sa.String(50)),
        sa.Column("src", sa.String(20)),
        sa.Column("member_ts_code", sa.String(20)),
        sa.Column("member_name", sa.String(255)),
        sa.Column("in_date", sa.Date),
        sa.Column("out_date", sa.Date),
        sa.Column("is_active", sa.Integer, nullable=False, default=1),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_sw_industry_mapping_history_version_id",
        "sw_industry_mapping_history",
        ["version_id"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_sw_industry_mapping_history_version_id", schema="ifa2")
    op.drop_table("sw_industry_mapping_history", schema="ifa2")
    op.drop_index("ix_fund_basic_etf_history_version_id", schema="ifa2")
    op.drop_table("fund_basic_etf_history", schema="ifa2")
    op.drop_index("ix_index_basic_history_version_id", schema="ifa2")
    op.drop_table("index_basic_history", schema="ifa2")
    op.drop_index("ix_sw_industry_mapping_current_member_ts_code", schema="ifa2")
    op.drop_index("ix_sw_industry_mapping_current_index_code", schema="ifa2")
    op.drop_table("sw_industry_mapping_current", schema="ifa2")
    op.drop_index("ix_fund_basic_etf_current_ts_code", schema="ifa2")
    op.drop_table("fund_basic_etf_current", schema="ifa2")
    op.drop_index("ix_index_basic_current_ts_code", schema="ifa2")
    op.drop_table("index_basic_current", schema="ifa2")
