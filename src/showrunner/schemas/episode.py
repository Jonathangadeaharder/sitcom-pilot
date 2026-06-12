from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class VoiceConfig(BaseModel):
    provider: str = ""
    voice_id: str = ""
    clone_from: str = ""
    seed: int = 0
    temperature: float = 0.8
    language: str = "en"


class Character(BaseModel):
    name: str = ""
    role: str = ""
    visual: str = ""
    reference_images: list[str] = []
    lora: str | None = None
    voice: VoiceConfig | None = None
    profile: str = ""
    trigger_word: str = ""


class Environment(BaseModel):
    trigger_word: str = ""
    reference_image: str = ""
    style: str = ""
    profile: str = ""


class RenderConfig(BaseModel):
    fps: int = Field(default=24, ge=1)
    resolution: list[int] = Field(default=[1280, 720], min_length=2, max_length=2)


class Beat(BaseModel):
    beat_id: str = ""
    kind: str = ""
    camera: str = ""
    action: str = ""
    duration_sec: float = 3.0
    seed: int = 0
    speaker: str = ""
    text: str = ""
    audio_path: str = ""

    model_config = {"extra": "ignore"}


class Shot(BaseModel):
    shot_id: str = ""
    camera_angle: str = ""
    action_start: str = ""
    action_end: str = ""
    seed: int = 0
    audio_path: str = ""
    dialogue: list[dict] = []

    @field_validator("dialogue", mode="before")
    @classmethod
    def coerce_none_dialogue(cls, v: object) -> list:
        if v is None:
            return []
        return v  # type: ignore[return-value]


class Scene(BaseModel):
    scene_id: str = ""
    title: str = ""
    environment: str = ""
    characters_present: list[str] = []
    mood: str = ""
    beats: list[Beat] = []
    shots: list[Shot] = []
    target_duration_sec: int = 60


class EpisodeData(BaseModel):
    title: str = ""
    cast: dict[str, Character] = {}
    environments: dict[str, Environment] = {}
    scenes: list[Scene] = []
    schema_version: str = "1.0"
    show: str = ""
    season: int = 0
    episode_number: int = 0
    render_config: dict[str, Any] = {}


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

    @model_validator(mode="after")
    def validate_references(self):
        valid_kinds = {"speech", "silent"}
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
                if beat.kind not in valid_kinds:
                    raise ValueError(
                        f"Beat '{beat.beat_id}' has invalid kind '{beat.kind}', must be one of {valid_kinds}"
                    )
                if beat.beat_id in beat_ids:
                    raise ValueError(f"Duplicate beat_id: '{beat.beat_id}'")
                beat_ids.add(beat.beat_id)
                if beat.kind == "speech":
                    if not beat.speaker:
                        raise ValueError(
                            f"Beat '{beat.beat_id}' is a speech beat but has no speaker"
                        )
                    if not beat.text:
                        raise ValueError(
                            f"Beat '{beat.beat_id}' is a speech beat but has no text"
                        )
                    if beat.speaker not in cast_keys:
                        raise ValueError(
                            f"Beat '{beat.beat_id}' in scene '{scene.scene_id}' "
                            f"references unknown speaker '{beat.speaker}'"
                        )
        return self
