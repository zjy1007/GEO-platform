import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.prompt_generation_service import VALID_MODES, VALID_PHASES


class PromptGenerateRequest(BaseModel):
    tier: Literal["basic", "standard", "professional"] = "basic"
    count: int | None = Field(default=None, ge=1, le=500)  # overrides tier when set
    modes: list[str] = ["organic"]
    phases: list[str] = ["decision", "doubt"]
    provider: str = "deepseek"

    @field_validator("modes")
    @classmethod
    def _check_modes(cls, v: list[str]) -> list[str]:
        bad = set(v) - VALID_MODES
        if bad or not v:
            raise ValueError(f"invalid modes {bad or 'empty'}; allowed: {sorted(VALID_MODES)}")
        return v

    @field_validator("phases")
    @classmethod
    def _check_phases(cls, v: list[str]) -> list[str]:
        bad = set(v) - VALID_PHASES
        if bad or not v:
            raise ValueError(f"invalid phases {bad or 'empty'}; allowed: {sorted(VALID_PHASES)}")
        return v


class GeoPromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_type: str | None = None
    phase: str | None = None
    mode: str | None = None
    prompt_text: str | None = None
    city: str | None = None
    category: str | None = None
    intent: str | None = None
    created_at: datetime | None = None


class PromptGenerateResponse(BaseModel):
    total: int
    prompts: list[GeoPromptOut]
