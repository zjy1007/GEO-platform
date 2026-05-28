"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "merchants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("address", sa.Text),
        sa.Column("phone", sa.String(100)),
        sa.Column("website", sa.Text),
        sa.Column("status", sa.String(50)),
        sa.Column("created_at", TS, server_default=sa.func.now()),
        sa.Column("updated_at", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_merchants_tenant_id", "merchants", ["tenant_id"])

    op.create_table(
        "merchant_aliases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE")),
        sa.Column("alias", sa.String(255)),
        sa.Column("alias_type", sa.String(50)),
        sa.Column("confidence", sa.Float),
    )
    op.create_index("ix_merchant_aliases_merchant_id", "merchant_aliases", ["merchant_id"])

    op.create_table(
        "evidence_sources",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE")),
        sa.Column("source_type", sa.String(100)),
        sa.Column("url", sa.Text),
        sa.Column("title", sa.Text),
        sa.Column("content_text", sa.Text),
        sa.Column("trust_level", sa.Float),
        sa.Column("retrieved_at", TS),
        sa.Column("content_hash", sa.String(255)),
    )
    op.create_index("ix_evidence_sources_merchant_id", "evidence_sources", ["merchant_id"])

    op.create_table(
        "geo_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE")),
        sa.Column("run_type", sa.String(50)),
        sa.Column("status", sa.String(50)),
        sa.Column("total_jobs", sa.Integer),
        sa.Column("finished_jobs", sa.Integer),
        sa.Column("failed_jobs", sa.Integer),
        sa.Column("started_at", TS),
        sa.Column("finished_at", TS),
        sa.Column("created_at", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_geo_runs_merchant_id", "geo_runs", ["merchant_id"])

    op.create_table(
        "geo_prompts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE")),
        sa.Column("scenario_type", sa.String(100)),
        sa.Column("phase", sa.String(20)),
        sa.Column("mode", sa.String(20)),
        sa.Column("prompt_text", sa.Text),
        sa.Column("city", sa.String(100)),
        sa.Column("category", sa.String(100)),
        sa.Column("intent", sa.String(100)),
        sa.Column("created_at", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_geo_prompts_merchant_id", "geo_prompts", ["merchant_id"])

    op.create_table(
        "provider_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("run_id", UUID, sa.ForeignKey("geo_runs.id", ondelete="CASCADE")),
        sa.Column("prompt_id", UUID, sa.ForeignKey("geo_prompts.id", ondelete="CASCADE")),
        sa.Column("provider", sa.String(100)),
        sa.Column("channel", sa.String(20)),
        sa.Column("account_id", UUID),
        sa.Column("model", sa.String(100)),
        sa.Column("answer_text", sa.Text),
        sa.Column("raw_response", JSONB),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("prompt_tokens", sa.Integer),
        sa.Column("completion_tokens", sa.Integer),
        sa.Column("status", sa.String(50)),
        sa.Column("created_at", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_provider_results_run_id", "provider_results", ["run_id"])

    op.create_table(
        "citation_sources",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "provider_result_id", UUID, sa.ForeignKey("provider_results.id", ondelete="CASCADE")
        ),
        sa.Column("idx", sa.Integer),
        sa.Column("title", sa.Text),
        sa.Column("url", sa.Text),
        sa.Column("domain", sa.String(255)),
        sa.Column("source_name", sa.String(255)),
        sa.Column("snippet", sa.Text),
        sa.Column("created_at", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_citation_sources_pr_id", "citation_sources", ["provider_result_id"])
    op.create_index("ix_citation_sources_domain", "citation_sources", ["domain"])

    op.create_table(
        "mention_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "provider_result_id", UUID, sa.ForeignKey("provider_results.id", ondelete="CASCADE")
        ),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE")),
        sa.Column("is_mentioned", sa.Boolean),
        sa.Column("mention_text", sa.Text),
        sa.Column("rank_position", sa.Integer),
        sa.Column("mentioned_brands", JSONB),
        sa.Column("sentiment", sa.String(50)),
        sa.Column("confidence", sa.Float),
    )
    op.create_index("ix_mention_results_pr_id", "mention_results", ["provider_result_id"])

    op.create_table(
        "verification_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "provider_result_id", UUID, sa.ForeignKey("provider_results.id", ondelete="CASCADE")
        ),
        sa.Column("claim_text", sa.Text),
        sa.Column("verification_status", sa.String(50)),
        sa.Column("evidence_source_id", UUID),
        sa.Column("confidence", sa.Float),
        sa.Column("explanation", sa.Text),
    )
    op.create_index("ix_verification_results_pr_id", "verification_results", ["provider_result_id"])

    op.create_table(
        "geo_reports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("run_id", UUID, sa.ForeignKey("geo_runs.id", ondelete="CASCADE")),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE")),
        sa.Column("geo_score", sa.Float),
        sa.Column("mention_rate", sa.Float),
        sa.Column("evidence_rate", sa.Float),
        sa.Column("positive_rate", sa.Float),
        sa.Column("rank_score", sa.Float),
        sa.Column("report_json", JSONB),
        sa.Column("created_at", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_geo_reports_run_id", "geo_reports", ["run_id"])


def downgrade() -> None:
    for table in [
        "geo_reports",
        "verification_results",
        "mention_results",
        "citation_sources",
        "provider_results",
        "geo_prompts",
        "geo_runs",
        "evidence_sources",
        "merchant_aliases",
        "merchants",
    ]:
        op.drop_table(table)
