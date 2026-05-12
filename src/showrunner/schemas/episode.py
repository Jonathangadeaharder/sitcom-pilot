from __future__ import annotations

from typing import Literal

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
    resolution: tuple[int, int] = (1280, 720)


class Beat(BaseModel):
    beat_id: str = Field(min_length=1)
    kind: Literal["speech", "silent"]
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
    schema_version: Literal["2.0"]
    dialogue_status: Literal["present", "missing", "partial"] = "present"
    dialogue_recovery_note: str = ""
    render: RenderConfig | None = None
    cast: dict[str, Character]
    environments: dict[str, Environment]
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self):
        cast_keys = set(self.cast.keys())
        env_keys = set(self.environments.keys())
        beat_ids = set()
        for scene in self.scenes:
            if scene.environment not in env_keys:
                raise ValueError(
                    f"Scene '{scene.scene_id}' references unknown environment '{scene.environment}'"
                )
            for char in scene.characters_present:
                if char not in cast_keys:
                    raise ValueError(
                        f"Scene '{scene.scene_id}' references unknown character '{char}'"
                    )
            for beat in scene.beats:
                if beat.beat_id in beat_ids:
                    raise ValueError(f"Duplicate beat_id: '{beat.beat_id}'")
                beat_ids.add(beat.beat_id)
        return self
