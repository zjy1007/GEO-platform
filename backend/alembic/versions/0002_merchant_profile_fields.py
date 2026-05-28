"""merchant profile fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONB = postgresql.JSONB


def upgrade() -> None:
    op.add_column("merchants", sa.Column("business_hours", sa.String(100)))
    op.add_column("merchants", sa.Column("price_range", sa.String(100)))
    op.add_column("merchants", sa.Column("services", JSONB))
    op.add_column("merchants", sa.Column("target_keywords", JSONB))
    op.add_column("merchants", sa.Column("official_sources", JSONB))
    op.add_column("merchants", sa.Column("competitors", JSONB))


def downgrade() -> None:
    for col in ["competitors", "official_sources", "target_keywords", "services", "price_range", "business_hours"]:
        op.drop_column("merchants", col)
