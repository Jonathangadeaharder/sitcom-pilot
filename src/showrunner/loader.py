from __future__ import annotations

import json
from pathlib import Path

from showrunner.schemas.episode import (
    Beat,
    Character,
    Environment,
    EpisodeData,
    Scene,
    Shot,
    VoiceConfig,
)


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
        if schema_version not in ("1.0", "2.0"):
            raise ValueError(
                f"Unsupported schema_version '{schema_version}'; expected '1.0' or '2.0'"
            )
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

    def _load_cast(self, raw_cast: dict, is_v2: bool) -> dict[str, Character]:
        result = {}
        for name, v in raw_cast.items():
            if is_v2:
                voice_raw = v.get("voice") or {}
                voice = (
                    VoiceConfig(
                        provider=voice_raw.get("provider", ""),
                        voice_id=voice_raw.get("voice_id", ""),
                        clone_from=voice_raw.get("clone_from", ""),
                        seed=voice_raw.get("seed", 0),
                        temperature=voice_raw.get("temperature", 0.8),
                        language=voice_raw.get("language", "en"),
                    )
                    if voice_raw
                    else None
                )
                result[name] = Character(
                    name=v.get("name", name),
                    visual=v.get("visual", ""),
                    lora=v.get("lora"),
                    voice=voice,
                    reference_images=v.get("reference_images", []),
                    trigger_word=v.get("visual", ""),
                    profile=v.get("lora") or name,
                )
            else:
                result[name] = Character(
                    profile=v["profile"],
                    trigger_word=v["trigger_word"],
                    name=name,
                )
        return result

    def _load_environments(self, raw_envs: dict, is_v2: bool) -> dict[str, Environment]:
        result = {}
        for name, v in raw_envs.items():
            if is_v2:
                result[name] = Environment(
                    trigger_word=v.get("trigger_word", ""),
                    style=v.get("style", ""),
                    reference_image=v.get("reference_image", ""),
                    profile=name,
                )
            else:
                result[name] = Environment(
                    profile=v["profile"],
                    trigger_word=v["trigger_word"],
                )
        return result

    def _load_scenes(self, raw_scenes: list, is_v2: bool) -> list[Scene]:
        scenes = []
        for s in raw_scenes:
            beats: list[Beat] = []
            shots: list[Shot] = []

            if is_v2:
                beats = [
                    Beat(
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
                    Shot(
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

            scenes.append(
                Scene(
                    scene_id=s["scene_id"],
                    environment=s["environment"],
                    characters_present=s["characters_present"],
                    beats=beats,
                    shots=shots,
                    target_duration_sec=s.get("target_duration_sec", s.get("target_seconds", 60)),
                    title=s.get("title", ""),
                    mood=s.get("mood", ""),
                )
            )
        return scenes
