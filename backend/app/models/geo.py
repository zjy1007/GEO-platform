import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GeoRun(Base):
    __tablename__ = "geo_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), index=True
    )
    run_type: Mapped[str | None] = mapped_column(String(50))  # organic_eval | diagnostic_eval
    status: Mapped[str | None] = mapped_column(String(50), default="created")
    total_jobs: Mapped[int | None] = mapped_column(Integer, default=0)
    finished_jobs: Mapped[int | None] = mapped_column(Integer, default=0)
    failed_jobs: Mapped[int | None] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GeoPrompt(Base):
    __tablename__ = "geo_prompts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), index=True
    )
    scenario_type: Mapped[str | None] = mapped_column(String(100))
    phase: Mapped[str | None] = mapped_column(String(20))  # decision | doubt
    mode: Mapped[str | None] = mapped_column(String(20))  # organic | diagnostic
    prompt_text: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(100))
    intent: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProviderResult(Base):
    __tablename__ = "provider_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geo_runs.id", ondelete="CASCADE"), index=True
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geo_prompts.id", ondelete="CASCADE")
    )
    provider: Mapped[str | None] = mapped_column(String(100))
    channel: Mapped[str | None] = mapped_column(String(20))  # api | web
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    model: Mapped[str | None] = mapped_column(String(100))
    answer_text: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CitationSource(Base):
    """Account-pool (web channel) core output — feeds the citation ranking / source-investment report blocks (P2)."""

    __tablename__ = "citation_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_results.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(String(255), index=True)
    source_name: Mapped[str | None] = mapped_column(String(255))
    snippet: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MentionResult(Base):
    __tablename__ = "mention_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_results.id", ondelete="CASCADE"), index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE")
    )
    is_mentioned: Mapped[bool | None] = mapped_column(Boolean)
    mention_text: Mapped[str | None] = mapped_column(Text)
    rank_position: Mapped[int | None] = mapped_column(Integer)
    # All brands (target + competitors) with their order, for competitor visibility comparison.
    mentioned_brands: Mapped[dict | None] = mapped_column(JSONB)
    sentiment: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float | None] = mapped_column(Float)


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_results.id", ondelete="CASCADE"), index=True
    )
    claim_text: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str | None] = mapped_column(String(50))
    evidence_source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    confidence: Mapped[float | None] = mapped_column(Float)
    explanation: Mapped[str | None] = mapped_column(Text)


class GeoReport(Base):
    __tablename__ = "geo_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geo_runs.id", ondelete="CASCADE"), index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE")
    )
    geo_score: Mapped[float | None] = mapped_column(Float)
    mention_rate: Mapped[float | None] = mapped_column(Float)
    evidence_rate: Mapped[float | None] = mapped_column(Float)
    positive_rate: Mapped[float | None] = mapped_column(Float)
    rank_score: Mapped[float | None] = mapped_column(Float)
    report_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
