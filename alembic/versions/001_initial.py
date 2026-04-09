"""Initial ifa2 schema and core tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ifa2")

    op.create_table(
        "source_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_name", sa.String(255), nullable=False, unique=True),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("base_url", sa.String(500)),
        sa.Column("credentials_secret", sa.String(255)),
        sa.Column("config_json", sa.Text),
        sa.Column("is_active", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("error_message", sa.Text),
        sa.Column("records_processed", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "raw_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_hash", sa.String(64), nullable=False),
        sa.Column("raw_json", sa.Text, nullable=False),
        sa.Column("ingested_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("processed_at", sa.DateTime),
        schema="ifa2",
    )

    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_type", sa.String(100), nullable=False),
        sa.Column("cik", sa.String(20)),
        sa.Column("entity_name", sa.String(255)),
        sa.Column("data_json", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "official_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_date", sa.DateTime, nullable=False),
        sa.Column("cik", sa.String(20)),
        sa.Column("entity_name", sa.String(255)),
        sa.Column("details_json", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "market_bars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("bar_date", sa.DateTime, nullable=False),
        sa.Column("open", sa.Numeric(18, 6)),
        sa.Column("high", sa.Numeric(18, 6)),
        sa.Column("low", sa.Numeric(18, 6)),
        sa.Column("close", sa.Numeric(18, 6)),
        sa.Column("volume", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_market_bars_symbol_date",
        "market_bars",
        ["symbol", "bar_date"],
        schema="ifa2",
    )

    op.create_table(
        "filings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cik", sa.String(20), nullable=False),
        sa.Column("entity_name", sa.String(255)),
        sa.Column("form_type", sa.String(20), nullable=False),
        sa.Column("filing_date", sa.DateTime, nullable=False),
        sa.Column("period_of_report", sa.DateTime),
        sa.Column("filed_at", sa.DateTime),
        sa.Column("html_content", sa.Text),
        sa.Column("accession_number", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.String(256), nullable=False),
        sa.Column("value", sa.Text),
        sa.Column("unit", sa.String(20)),
        sa.Column("context", sa.String(256)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index(
        "ix_facts_filing_id_tag", "facts", ["filing_id", "tag"], schema="ifa2"
    )

    op.create_table(
        "fact_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_name", sa.String(255), nullable=False, unique=True),
        sa.Column("entity_name", sa.String(255)),
        sa.Column("fact_tags", sa.Text),
        sa.Column("is_active", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )

    op.create_table(
        "slot_materializations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slot_name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("data_json", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime),
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_table("slot_materializations", schema="ifa2")
    op.drop_table("fact_sources", schema="ifa2")
    op.drop_index("ix_facts_filing_id_tag", schema="ifa2")
    op.drop_table("facts", schema="ifa2")
    op.drop_table("filings", schema="ifa2")
    op.drop_index("ix_market_bars_symbol_date", schema="ifa2")
    op.drop_table("market_bars", schema="ifa2")
    op.drop_table("official_events", schema="ifa2")
    op.drop_table("items", schema="ifa2")
    op.drop_table("raw_records", schema="ifa2")
    op.drop_table("job_runs", schema="ifa2")
    op.drop_table("source_registry", schema="ifa2")
    op.execute("DROP SCHEMA ifa2")
