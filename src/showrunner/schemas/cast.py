from __future__ import annotations

from pydantic import BaseModel, Field


class VisualReference(BaseModel):
    front: str = ""
    three_quarter: str = ""
    profile: str = ""
    extra: list[str] = []


class VoiceProfile(BaseModel):
    voice_id: str
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class WardrobeEntry(BaseModel):
    episode: str = ""
    description: str = ""
    notes: str = ""


class CastCharacter(BaseModel):
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    description: str = ""
    age: str = ""
    gender: str = ""
    ethnicity: str = ""
    visual: str = ""
    role: str = ""
    visual_refs: VisualReference = Field(default_factory=VisualReference)
    voice: VoiceProfile | None = None
    lora: str | None = None
    wardrobe: list[WardrobeEntry] = Field(default_factory=list)
    consistency_notes: str = ""


class CastManifest(BaseModel):
    version: str = "1.0"
    characters: dict[str, CastCharacter] = Field(default_factory=dict)
