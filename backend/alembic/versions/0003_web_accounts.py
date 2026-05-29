"""web accounts table (account pool for web channel P2)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "web_accounts",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        # Status: active | paused | need_relogin | disabled
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        # Path to Playwright storage_state JSON — NEVER store raw cookies
        sa.Column("storage_state_ref", sa.String(500), nullable=True),
        sa.Column("daily_quota", sa.Integer, nullable=False, server_default="40"),
        sa.Column("used_today", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quota_reset_at", TS, nullable=True),
        sa.Column("last_used_at", TS, nullable=True),
        sa.Column("paused_reason", sa.String(500), nullable=True),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_web_accounts_provider", "web_accounts", ["provider"])
    op.create_index("ix_web_accounts_status", "web_accounts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_web_accounts_status", table_name="web_accounts")
    op.drop_index("ix_web_accounts_provider", table_name="web_accounts")
    op.drop_table("web_accounts")
