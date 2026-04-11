"""Add unique constraint to sw_industry_mapping_current

Revision ID: 007_add_sw_constraint
Revises: 006_lowfreq_job8a
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_add_sw_constraint"
down_revision: Union[str, None] = "006_lowfreq_job8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_sw_industry_mapping_current_key",
        "sw_industry_mapping_current",
        ["index_code", "member_ts_code", "in_date"],
        schema="ifa2",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_sw_industry_mapping_current_key",
        "sw_industry_mapping_current",
        schema="ifa2",
    )
