from __future__ import annotations

import logging
from pathlib import Path

from sitcom_pilot.aiservices_client import AIServicesClient
from sitcom_pilot.beat_prompts import build_beat_prompt, build_scene_prompt
from sitcom_pilot.cast_manifest import CastManifest
from sitcom_pilot.loader import BeatData, EpisodeData, SceneData

logger = logging.getLogger(__name__)


def generate_scene_plate(
    scene: SceneData,
    episode: EpisodeData,
    manifest: CastManifest,
    client: AIServicesClient,
    output_path: Path,
    *,
    seed: int | None = None,
    episode_id: str = "",
) -> Path:
    prompt = build_scene_prompt(scene, episode, manifest, episode_id=episode_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Generating scene plate for %s: %s", scene.scene_id, prompt[:80])
    return client.text2image(
        prompt,
        output_path,
        seed=seed,
        width=1024,
        height=720,
    )


def generate_beat_plate(
    beat: BeatData,
    scene: SceneData,
    episode: EpisodeData,
    manifest: CastManifest,
    client: AIServicesClient,
    scene_plate_path: Path,
    output_path: Path,
    *,
    seed: int | None = None,
    strength: float = 0.5,
    episode_id: str = "",
) -> Path:
    prompt = build_beat_prompt(beat, scene, episode, manifest, episode_id=episode_id)
    if not 0.0 <= strength <= 1.0:
        raise ValueError("strength must be between 0.0 and 1.0")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Generating beat plate for %s: %s", beat.beat_id, prompt[:80])
    return client.image2image(
        scene_plate_path,
        prompt,
        output_path,
        seed=seed,
        strength=strength,
    )
