from __future__ import annotations

import logging
from pathlib import Path

from showrunner.aiservices_client import AIServicesClient
from showrunner.beat_prompts import build_beat_prompt
from showrunner.cast_manifest import CastManifest
from showrunner.loader import BeatData, EpisodeData, SceneData
from showrunner.paths import RunPaths

logger = logging.getLogger(__name__)


def render_silent_beat(
    beat: BeatData,
    scene: SceneData,
    episode: EpisodeData,
    manifest: CastManifest,
    client: AIServicesClient,
    output_dir: str | Path = "output",
    run_id: str = "",
    episode_id: str = "",
) -> str:
    prompt = build_beat_prompt(beat, scene, episode, manifest, episode_id=episode_id)
    run_paths = RunPaths(Path(output_dir), run_id=run_id)
    run_paths.ensure_scene_dirs(scene.scene_id)
    output_path = run_paths.beat_image(scene.scene_id, beat.beat_id)
    result = client.text2image(prompt, output_path, seed=beat.seed)
    logger.info("Rendered silent beat %s -> %s", beat.beat_id, result)
    return str(result)
