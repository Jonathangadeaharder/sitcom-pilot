from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ShotData:
    shot_id: str
    camera_angle: str
    action_start: str
    action_end: str
    audio_path: str
    seed: int


@dataclass(frozen=True)
class CharacterData:
    profile: str
    trigger_word: str


@dataclass(frozen=True)
class EnvironmentData:
    profile: str
    trigger_word: str


@dataclass(frozen=True)
class SceneData:
    scene_id: str
    environment: str
    characters_present: list[str]
    shots: list[ShotData]


@dataclass(frozen=True)
class EpisodeData:
    title: str
    cast: dict[str, CharacterData]
    environments: dict[str, EnvironmentData]
    scenes: list[SceneData]


class EpisodeLoader:
    def load(self, path: Path) -> EpisodeData:
        with open(path) as f:
            raw = json.load(f)
        cast = {
            name: CharacterData(profile=v["profile"], trigger_word=v["trigger_word"])
            for name, v in raw["cast"].items()
        }
        environments = {
            name: EnvironmentData(profile=v["profile"], trigger_word=v["trigger_word"])
            for name, v in raw["environments"].items()
        }
        scenes = []
        for s in raw["scenes"]:
            shots = [
                ShotData(
                    shot_id=sh["shot_id"], camera_angle=sh["camera_angle"],
                    action_start=sh["action_start"], action_end=sh["action_end"],
                    audio_path=sh["audio_path"], seed=sh["seed"],
                )
                for sh in s.get("shots", [])
            ]
            scenes.append(SceneData(
                scene_id=s["scene_id"], environment=s["environment"],
                characters_present=s["characters_present"], shots=shots,
            ))
        return EpisodeData(
            title=raw["episode_title"], cast=cast,
            environments=environments, scenes=scenes,
        )
