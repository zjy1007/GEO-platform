import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GeoReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    merchant_id: uuid.UUID
    geo_score: float | None = None
    mention_rate: float | None = None
    evidence_rate: float | None = None
    positive_rate: float | None = None
    rank_score: float | None = None
    report_json: dict | None = None
    created_at: datetime | None = None
