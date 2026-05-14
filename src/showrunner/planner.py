from __future__ import annotations

from typing import Literal

from showrunner.schemas.beat_plan import BeatPlan

_COST_PER_SECOND: dict[str, float] = {
    "silent": 0.01,
    "speech": 0.05,
    "transition": 0.02,
}

_STRATEGY: dict[str, Literal["text2image", "voice_clone+video", "video_transition"]] = {
    "silent": "text2image",
    "speech": "voice_clone+video",
    "transition": "video_transition",
}

_SUPPORTED_KINDS = frozenset(_STRATEGY)

def plan_episode(episode_json: dict) -> list[BeatPlan]:
    beats: list[BeatPlan] = []
    beat_number = 0
    scenes = episode_json.get("scenes", [])

    for scene in scenes:
        scene_beats = scene.get("beats", [])
        beat_count = len(scene_beats)
        target_duration = scene.get("target_duration_sec", scene.get("target_seconds", 60))
        budget_per_beat = max(target_duration / beat_count, 0.1) if beat_count > 0 else 3.0

        for b in scene_beats:
            kind = b.get("kind", "silent")
            if kind not in _SUPPORTED_KINDS:
                beat_id = b.get(
                    "beat_id",
                    f"scene#{scene.get('scene_id', '?')}:beat#{beat_number + 1}",
                )
                raise ValueError(f"Unsupported beat kind '{kind}' for beat {beat_id}")
            beat_number += 1
            duration = b.get("duration_sec") or budget_per_beat
            description = _build_description(kind, b)

            beats.append(
                BeatPlan(
                    beat_number=beat_number,
                    type=kind,
                    description=description,
                    duration_seconds=duration,
                    estimated_cost=_COST_PER_SECOND[kind] * duration,
                    rendering_strategy=_STRATEGY[kind],
                )
            )

    return beats


def _build_description(kind: str, beat: dict) -> str:
    if kind == "speech":
        speaker = beat.get("speaker", "")
        text = beat.get("text", "")
        prefix = f"[{speaker}] " if speaker else ""
        return f"{prefix}{text}" if text else beat.get("action", "")
    if kind == "silent":
        return beat.get("action", "")
    if kind == "transition":
        return beat.get("description", beat.get("camera", ""))
    return beat.get("action", "")
