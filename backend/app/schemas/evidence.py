import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

SourceType = Literal["official_website", "user_upload", "map", "review", "news", "social", "other"]


class EvidenceSourceIn(BaseModel):
    source_type: SourceType = "other"
    url: str | None = None
    title: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def _need_url_or_text(self) -> "EvidenceSourceIn":
        if not self.url and not (self.text and self.text.strip()):
            raise ValueError("must provide either url or text")
        return self


class EvidenceSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    source_type: str | None = None
    url: str | None = None
    title: str | None = None
    content_text: str | None = None
    trust_level: float | None = None
    retrieved_at: datetime | None = None
    content_hash: str | None = None
