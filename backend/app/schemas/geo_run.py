import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GeoRunCreate(BaseModel):
    merchant_id: uuid.UUID
    run_type: Literal["organic_eval", "diagnostic_eval"] = "organic_eval"
    providers: list[str] = Field(min_length=1)
    prompt_count: int | None = Field(default=None, ge=1, le=500)
    repeat_count: int = Field(default=1, ge=1, le=5)
    modes: list[str] | None = None
    phases: list[str] | None = None


class GeoRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    run_type: str | None = None
    status: str | None = None
    total_jobs: int | None = None
    finished_jobs: int | None = None
    failed_jobs: int | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class GeoRunProgress(BaseModel):
    run_id: uuid.UUID
    status: str | None = None
    total_jobs: int = 0
    finished_jobs: int = 0
    failed_jobs: int = 0
    progress: float = 0.0


class ProviderResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt_id: uuid.UUID | None = None
    provider: str | None = None
    channel: str | None = None
    model: str | None = None
    answer_text: str | None = None
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    status: str | None = None
    created_at: datetime | None = None
