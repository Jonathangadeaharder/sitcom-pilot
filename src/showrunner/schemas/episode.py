from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class VoiceConfig(BaseModel):
    provider: str = "text2speech"
    voice_id: str = ""
    clone_from: str = ""
    seed: int | None = None
    temperature: float | None = None
    language: str = "en"


class Character(BaseModel):
    name: str = Field(min_length=1)
    role: str = ""
    visual: str = ""
    reference_images: list[str] = []
    lora: str | None = None
    voice: VoiceConfig | None = None


class Environment(BaseModel):
    trigger_word: str = Field(min_length=1)
    reference_image: str = ""
    style: str = ""


class RenderConfig(BaseModel):
    fps: int = Field(default=24, ge=1)
    resolution: list[int] = Field(default=[1280, 720], min_length=2, max_length=2)


class Beat(BaseModel):
    beat_id: str = Field(min_length=1)
    kind: str = Field(pattern=r"^(speech|silent)$")
    camera: str = ""
    action: str = ""
    seed: int | None = None
    speaker: str | None = None
    text: str | None = None
    audio_path: str = ""

    @model_validator(mode="after")
    def check_speech_beat(self):
        if self.kind == "speech":
            if not self.speaker:
                raise ValueError(f"speech beat '{self.beat_id}' requires a speaker")
            if not self.text:
                raise ValueError(f"speech beat '{self.beat_id}' requires text")
        return self


class Scene(BaseModel):
    scene_id: str = Field(min_length=1)
    title: str = ""
    environment: str = Field(min_length=1)
    characters_present: list[str] = Field(min_length=1)
    mood: str = ""
    beats: list[Beat] = Field(min_length=1)


class Episode(BaseModel):
    show: str = Field(min_length=1)
    season: int = Field(ge=1)
    episode: int = Field(ge=1)
    title: str = Field(min_length=1)
    schema_version: str = Field(pattern=r"^2\.0$")
    dialogue_status: str = Field(default="present", pattern=r"^(present|missing|partial)$")
    dialogue_recovery_note: str = ""
    render: RenderConfig | None = None
    cast: dict[str, Character]
    environments: dict[str, Environment]
    scenes: list[Scene] = Field(min_length=1)
