from __future__ import annotations

from pydantic import BaseModel, Field


class BeatPlan(BaseModel):
    beat_number: int = Field(ge=1)
    type: str  # "silent" | "speech" | "transition"
    description: str
    duration_seconds: float = Field(gt=0)
    estimated_cost: float = Field(ge=0)
    rendering_strategy: str
