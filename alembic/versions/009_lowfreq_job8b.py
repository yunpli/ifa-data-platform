"""Add announcements, news, research_reports, investor_qa current and history tables

Revision ID: 009_lowfreq_job8b
Revises: 008_lowfreq_job9
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "009_lowfreq_job8b"
down_revision: Union[str, None] = "008_lowfreq_job9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "announcements_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ann_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("title", sa.Text),
        sa.Column("url", sa.String(500)),
        sa.Column("rec_time", sa.DateTime),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_announcements_current_ts_code",
        "announcements_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_announcements_current_ann_date",
        "announcements_current",
        ["ann_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_announcements_current_key",
        "announcements_current",
        ["ts_code", "ann_date", "title"],
        schema="ifa2",
    )

    op.create_table(
        "news_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("datetime", sa.DateTime, nullable=False),
        sa.Column("classify", sa.String(50)),
        sa.Column("title", sa.String(500)),
        sa.Column("source", sa.String(100)),
        sa.Column("url", sa.String(500)),
        sa.Column("content", sa.Text),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_news_current_datetime",
        "news_current",
        ["datetime"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_news_current_key",
        "news_current",
        ["datetime", "title"],
        schema="ifa2",
    )

    op.create_table(
        "research_reports_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("title", sa.String(500)),
        sa.Column("report_type", sa.String(50)),
        sa.Column("author", sa.String(255)),
        sa.Column("inst_csname", sa.String(255)),
        sa.Column("ind_name", sa.String(100)),
        sa.Column("url", sa.String(500)),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_research_reports_current_ts_code",
        "research_reports_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_research_reports_current_trade_date",
        "research_reports_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_research_reports_current_key",
        "research_reports_current",
        ["ts_code", "trade_date", "title"],
        schema="ifa2",
    )

    op.create_table(
        "investor_qa_current",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("q", sa.Text, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("a", sa.Text),
        sa.Column("pub_time", sa.DateTime),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_investor_qa_current_ts_code",
        "investor_qa_current",
        ["ts_code"],
        schema="ifa2",
    )
    op.create_index(
        "ix_investor_qa_current_trade_date",
        "investor_qa_current",
        ["trade_date"],
        schema="ifa2",
    )
    op.create_unique_constraint(
        "uq_investor_qa_current_key",
        "investor_qa_current",
        ["ts_code", "trade_date", "q"],
        schema="ifa2",
    )

    op.create_table(
        "announcements_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ann_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("title", sa.Text),
        sa.Column("url", sa.String(500)),
        sa.Column("rec_time", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_announcements_history_version_id",
        "announcements_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "news_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("datetime", sa.DateTime, nullable=False),
        sa.Column("classify", sa.String(50)),
        sa.Column("title", sa.String(500)),
        sa.Column("source", sa.String(100)),
        sa.Column("url", sa.String(500)),
        sa.Column("content", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_news_history_version_id",
        "news_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "research_reports_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("title", sa.String(500)),
        sa.Column("report_type", sa.String(50)),
        sa.Column("author", sa.String(255)),
        sa.Column("inst_csname", sa.String(255)),
        sa.Column("ind_name", sa.String(100)),
        sa.Column("url", sa.String(500)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_research_reports_history_version_id",
        "research_reports_history",
        ["version_id"],
        schema="ifa2",
    )

    op.create_table(
        "investor_qa_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("q", sa.Text, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("a", sa.Text),
        sa.Column("pub_time", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_investor_qa_history_version_id",
        "investor_qa_history",
        ["version_id"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_investor_qa_history_version_id", schema="ifa2")
    op.drop_table("investor_qa_history", schema="ifa2")
    op.drop_index("ix_research_reports_history_version_id", schema="ifa2")
    op.drop_table("research_reports_history", schema="ifa2")
    op.drop_index("ix_news_history_version_id", schema="ifa2")
    op.drop_table("news_history", schema="ifa2")
    op.drop_index("ix_announcements_history_version_id", schema="ifa2")
    op.drop_table("announcements_history", schema="ifa2")
    op.drop_constraint(
        "uq_investor_qa_current_key", "investor_qa_current", schema="ifa2"
    )
    op.drop_index("ix_investor_qa_current_trade_date", schema="ifa2")
    op.drop_index("ix_investor_qa_current_ts_code", schema="ifa2")
    op.drop_table("investor_qa_current", schema="ifa2")
    op.drop_constraint(
        "uq_research_reports_current_key", "research_reports_current", schema="ifa2"
    )
    op.drop_index("ix_research_reports_current_trade_date", schema="ifa2")
    op.drop_index("ix_research_reports_current_ts_code", schema="ifa2")
    op.drop_table("research_reports_current", schema="ifa2")
    op.drop_constraint("uq_news_current_key", "news_current", schema="ifa2")
    op.drop_index("ix_news_current_datetime", schema="ifa2")
    op.drop_table("news_current", schema="ifa2")
    op.drop_constraint(
        "uq_announcements_current_key", "announcements_current", schema="ifa2"
    )
    op.drop_index("ix_announcements_current_ann_date", schema="ifa2")
    op.drop_index("ix_announcements_current_ts_code", schema="ifa2")
    op.drop_table("announcements_current", schema="ifa2")
