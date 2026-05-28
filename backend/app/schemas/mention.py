import uuid

from pydantic import BaseModel, ConfigDict


class MentionResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_result_id: uuid.UUID
    merchant_id: uuid.UUID
    is_mentioned: bool | None = None
    mention_text: str | None = None
    rank_position: int | None = None
    mentioned_brands: list[dict] | None = None
    sentiment: str | None = None
    confidence: float | None = None


class ExtractResponse(BaseModel):
    enqueued: int


class VerificationResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_result_id: uuid.UUID
    claim_text: str | None = None
    verification_status: str | None = None
    evidence_source_id: uuid.UUID | None = None
    confidence: float | None = None
    explanation: str | None = None
