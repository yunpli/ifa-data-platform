"""Add symbol_universe table for database-driven universe management

Revision ID: 014_symbol_universe
Revises: 013_lowfreq_asset_batch2
Create Date: 2026-04-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "014_symbol_universe"
down_revision: Union[str, None] = "013_lowfreq_asset_batch2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symbol_universe",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("universe_type", sa.String(1), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        schema="ifa2",
    )
    op.create_index("ix_symbol_universe_symbol", "symbol_universe", ["symbol"], schema="ifa2")
    op.create_index("ix_symbol_universe_universe_type", "symbol_universe", ["universe_type"], schema="ifa2")
    op.create_unique_constraint(
        "uq_symbol_universe_symbol_type",
        "symbol_universe",
        ["symbol", "universe_type"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_index("ix_symbol_universe_universe_type", schema="ifa2")
    op.drop_index("ix_symbol_universe_symbol", schema="ifa2")
    op.drop_constraint("uq_symbol_universe_symbol_type", "symbol_universe", schema="ifa2")
    op.drop_table("symbol_universe", schema="ifa2")
