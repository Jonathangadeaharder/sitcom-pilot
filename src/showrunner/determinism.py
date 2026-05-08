from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sitcom_pilot.cast_manifest import CastManifest
from sitcom_pilot.loader import EpisodeData


def compute_manifest_hash(episode: EpisodeData, manifest: CastManifest) -> str:
    payload = json.dumps(
        {
            "show": episode.show,
            "season": episode.season,
            "episode_number": episode.episode_number,
            "title": episode.title,
            "manifest": manifest.to_dict(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def resolve_seed(
    episode_id: str,
    scene_id: str,
    beat_id: str,
    base_seed: int = 0,
) -> int:
    components = f"{episode_id}:{scene_id}:{beat_id}:{base_seed}"
    digest = hashlib.sha256(components.encode()).hexdigest()
    return int(digest[:8], 16)


def compute_run_fingerprint(run_paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in sorted(run_paths):
        p = Path(path)
        if not p.exists():
            continue
        h.update(str(p.resolve()).encode())
        h.update(str(p.stat().st_size).encode())
        h.update(hashlib.sha256(p.read_bytes()).hexdigest().encode())
    return h.hexdigest()
