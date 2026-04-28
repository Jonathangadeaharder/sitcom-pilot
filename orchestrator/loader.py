from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Beat-based v2.0 data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VoiceConfig:
    provider: str = ""
    voice_id: str = ""
    clone_from: str = ""
    seed: int = 0
    temperature: float = 0.8
    language: str = "en"


@dataclass(frozen=True)
class CharacterData:
    """Supports both v1 (profile/trigger_word) and v2 (name/visual/lora/voice)."""
    # v2 fields
    name: str = ""
    visual: str = ""
    lora: Optional[str] = None
    voice: Optional[VoiceConfig] = None
    reference_images: tuple[str, ...] = field(default_factory=tuple)
    # v1 legacy fields (kept for backward compat with existing tests/templates)
    profile: str = ""
    trigger_word: str = ""


@dataclass(frozen=True)
class EnvironmentData:
    """Supports both v1 (profile/trigger_word) and v2 (trigger_word/style)."""
    trigger_word: str = ""
    style: str = ""
    reference_image: str = ""
    # v1 legacy
    profile: str = ""


@dataclass(frozen=True)
class BeatData:
    beat_id: str
    kind: str  # "speech" | "silent"
    camera: str = ""
    action: str = ""
    duration_sec: float = 3.0
    seed: int = 0
    # speech-only
    speaker: str = ""
    text: str = ""
    audio_path: str = ""


@dataclass(frozen=True)
class ShotData:
    """Legacy v1 shot model — kept for backward compat with existing tests."""
    shot_id: str
    camera_angle: str
    action_start: str
    action_end: str
    seed: int
    audio_path: str = ""
    dialogue: Optional[list[dict]] = None

    def __post_init__(self):
        if self.dialogue is None:
            object.__setattr__(self, "dialogue", [])


@dataclass(frozen=True)
class SceneData:
    scene_id: str
    environment: str
    characters_present: list[str]
    # v2: beats (may be empty for legacy scenes)
    beats: list[BeatData] = field(default_factory=list)
    # v1 legacy: shots (may be empty for v2 scenes)
    shots: list[ShotData] = field(default_factory=list)
    target_duration_sec: int = 60
    title: str = ""
    mood: str = ""


@dataclass(frozen=True)
class EpisodeData:
    title: str
    cast: dict[str, CharacterData]
    environments: dict[str, EnvironmentData]
    scenes: list[SceneData]
    schema_version: str = "1.0"
    show: str = ""
    season: int = 0
    episode_number: int = 0
    render_config: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class EpisodeLoader:
    """Load an episode JSON file into EpisodeData.

    Supports:
    - Schema v2.0: beat-based scenes (beats[]), rich cast (name/visual/voice/lora)
    - Schema v1 (legacy): shot-based scenes (shots[]), simple cast (profile/trigger_word)
    """

    def load(self, path: Path) -> EpisodeData:
        with open(path) as f:
            raw = json.load(f)

        schema_version = raw.get("schema_version", "1.0")
        is_v2 = schema_version == "2.0"

        cast = self._load_cast(raw.get("cast", {}), is_v2)
        environments = self._load_environments(raw.get("environments", {}), is_v2)
        scenes = self._load_scenes(raw.get("scenes", []), is_v2)

        title = raw.get("title") or raw.get("episode_title", "")
        return EpisodeData(
            title=title,
            cast=cast,
            environments=environments,
            scenes=scenes,
            schema_version=schema_version,
            show=raw.get("show", ""),
            season=raw.get("season", 0),
            episode_number=raw.get("episode", 0),
            render_config=raw.get("render", {}),
        )

    # ------------------------------------------------------------------
    # Cast
    # ------------------------------------------------------------------

    def _load_cast(self, raw_cast: dict, is_v2: bool) -> dict[str, CharacterData]:
        result = {}
        for name, v in raw_cast.items():
            if is_v2:
                voice_raw = v.get("voice") or {}
                voice = VoiceConfig(
                    provider=voice_raw.get("provider", ""),
                    voice_id=voice_raw.get("voice_id", ""),
                    clone_from=voice_raw.get("clone_from", ""),
                    seed=voice_raw.get("seed", 0),
                    temperature=voice_raw.get("temperature", 0.8),
                    language=voice_raw.get("language", "en"),
                ) if voice_raw else None
                result[name] = CharacterData(
                    name=v.get("name", name),
                    visual=v.get("visual", ""),
                    lora=v.get("lora"),
                    voice=voice,
                    reference_images=tuple(v.get("reference_images", [])),
                    # v2 uses visual as trigger_word for backward compat with renderer
                    trigger_word=v.get("visual", ""),
                    profile=v.get("lora") or name,
                )
            else:
                result[name] = CharacterData(
                    profile=v["profile"],
                    trigger_word=v["trigger_word"],
                    name=name,
                )
        return result

    # ------------------------------------------------------------------
    # Environments
    # ------------------------------------------------------------------

    def _load_environments(self, raw_envs: dict, is_v2: bool) -> dict[str, EnvironmentData]:
        result = {}
        for name, v in raw_envs.items():
            if is_v2:
                result[name] = EnvironmentData(
                    trigger_word=v.get("trigger_word", ""),
                    style=v.get("style", ""),
                    reference_image=v.get("reference_image", ""),
                    # v2: use name as profile for backward compat
                    profile=name,
                )
            else:
                result[name] = EnvironmentData(
                    profile=v["profile"],
                    trigger_word=v["trigger_word"],
                )
        return result

    # ------------------------------------------------------------------
    # Scenes
    # ------------------------------------------------------------------

    def _load_scenes(self, raw_scenes: list, is_v2: bool) -> list[SceneData]:
        scenes = []
        for s in raw_scenes:
            beats: list[BeatData] = []
            shots: list[ShotData] = []

            if is_v2:
                beats = [
                    BeatData(
                        beat_id=b["beat_id"],
                        kind=b["kind"],
                        camera=b.get("camera", ""),
                        action=b.get("action", ""),
                        duration_sec=b.get("duration_sec", 3.0),
                        seed=b.get("seed", 0),
                        speaker=b.get("speaker", ""),
                        text=b.get("text", ""),
                        audio_path=b.get("audio_path", ""),
                    )
                    for b in s.get("beats", [])
                ]
            else:
                shots = [
                    ShotData(
                        shot_id=sh["shot_id"],
                        camera_angle=sh["camera_angle"],
                        action_start=sh["action_start"],
                        action_end=sh["action_end"],
                        audio_path=sh.get("audio_path", ""),
                        seed=sh["seed"],
                        dialogue=sh.get("dialogue", []),
                    )
                    for sh in s.get("shots", [])
                ]

            scenes.append(SceneData(
                scene_id=s["scene_id"],
                environment=s["environment"],
                characters_present=s["characters_present"],
                beats=beats,
                shots=shots,
                target_duration_sec=s.get("target_duration_sec", s.get("target_seconds", 60)),
                title=s.get("title", ""),
                mood=s.get("mood", ""),
            ))
        return scenes
