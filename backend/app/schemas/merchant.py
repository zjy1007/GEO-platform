import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MerchantBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    city: str | None = None
    district: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    business_hours: str | None = None
    price_range: str | None = None
    services: list[str] | None = None
    target_keywords: list[str] | None = None
    official_sources: list[str] | None = None
    competitors: list[str] | None = None


class MerchantCreate(MerchantBase):
    pass


class MerchantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = None
    city: str | None = None
    district: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    business_hours: str | None = None
    price_range: str | None = None
    services: list[str] | None = None
    target_keywords: list[str] | None = None
    official_sources: list[str] | None = None
    competitors: list[str] | None = None


class MerchantOut(MerchantBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AliasOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alias: str
    alias_type: str | None = None
    confidence: float | None = None


class CompletenessResult(BaseModel):
    score: int = Field(ge=0, le=100)
    filled_fields: list[str]
    missing_fields: list[str]
    suggestions: list[str]


class NapCheckResult(BaseModel):
    consistent: bool
    issues: list[str]
