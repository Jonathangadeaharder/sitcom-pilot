from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class NodeMap:
    start_prompt: str = "6"
    end_prompt: str = "12"
    audio: str = "25"
    seed: str = "3"
    env_profile: str = "40"
    char_profiles: list[str] = field(default_factory=lambda: ["41", "42", "43"])

    @classmethod
    def from_dict(cls, data: dict) -> NodeMap:
        return cls(
            start_prompt=data.get("start_prompt", cls.start_prompt),
            end_prompt=data.get("end_prompt", cls.end_prompt),
            audio=data.get("audio", cls.audio),
            seed=data.get("seed", cls.seed),
            env_profile=data.get("env_profile", cls.env_profile),
            char_profiles=data.get("char_profiles", ["41", "42", "43"]),
        )
