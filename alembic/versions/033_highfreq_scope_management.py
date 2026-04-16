"""Add highfreq scope management tables

Revision ID: 033_hf_scope_mgmt
Revises: 032_hf_derived
Create Date: 2026-04-16 06:15:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "033_hf_scope_mgmt"
down_revision: Union[str, None] = "032_hf_derived"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "highfreq_active_scope",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("asset_category", sa.String(32), nullable=False),
        sa.Column("source_list_type", sa.String(32), nullable=False),
        sa.Column("source_list_name", sa.String(128), nullable=False),
        sa.Column("scope_priority", sa.Integer(), nullable=False),
        sa.Column("scope_tier", sa.String(32), nullable=False),
        sa.Column("scope_status", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_active_scope_symbol", "highfreq_active_scope", ["symbol"], schema="ifa2")

    op.create_table(
        "highfreq_dynamic_candidate",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("candidate_type", sa.String(32), nullable=False),
        sa.Column("trigger_reason", sa.String(128), nullable=False),
        sa.Column("priority_score", sa.Numeric(18, 6), nullable=False),
        sa.Column("upgrade_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_highfreq_dynamic_candidate_symbol", "highfreq_dynamic_candidate", ["symbol"], schema="ifa2")


def downgrade() -> None:
    op.drop_index("ix_highfreq_dynamic_candidate_symbol", table_name="highfreq_dynamic_candidate", schema="ifa2")
    op.drop_table("highfreq_dynamic_candidate", schema="ifa2")
    op.drop_index("ix_highfreq_active_scope_symbol", table_name="highfreq_active_scope", schema="ifa2")
    op.drop_table("highfreq_active_scope", schema="ifa2")
