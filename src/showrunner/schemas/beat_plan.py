from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class BeatPlan(BaseModel):
    beat_number: int = Field(ge=1)
    type: Literal["silent", "speech", "transition"]
    description: str
    duration_seconds: float = Field(gt=0)
    estimated_cost: float = Field(ge=0)
    rendering_strategy: Literal["text2image", "voice_clone+video", "video_transition"]
