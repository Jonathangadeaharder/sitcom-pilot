from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from showrunner.cast_manifest import CastManifest
from showrunner.loader import EpisodeData

# ---------------------------------------------------------------------------
# SeedStrategy — deterministic seed derivation per beat / scene / episode
# ---------------------------------------------------------------------------


class SeedStrategy:
    """Deterministic seed derivation strategy.

    Given an episode identifier and an optional override namespace, produces
    reproducible seeds for every (scene, beat) coordinate in the episode.
    Supports pluggable base seeds so callers can shift the entire random
    space without changing individual beat seeds in the episode JSON.
    """

    def __init__(self, episode_id: str, base_seed: int = 0) -> None:
        if not episode_id:
            raise ValueError("episode_id must be non-empty")
        self._episode_id = episode_id
        self._base_seed = base_seed

    @property
    def episode_id(self) -> str:
        return self._episode_id

    @property
    def base_seed(self) -> int:
        return self._base_seed

    def for_beat(
        self,
        scene_id: str,
        beat_id: str,
        beat_seed: int = 0,
    ) -> int:
        """Derive a deterministic seed for a single beat.

        The returned seed incorporates the episode, scene, beat, and the
        base seed so that flipping *either* the episode base *or* the
        individual beat seed produces a different final value.
        """
        combined_base = _mix_seeds(self._base_seed, beat_seed)
        return resolve_seed(self._episode_id, scene_id, beat_id, combined_base)

    def for_scene(self, scene_id: str) -> int:
        """Derive a deterministic seed for broad scene‑level operations."""
        return resolve_seed(self._episode_id, scene_id, "__scene__", self._base_seed)

    def for_episode(self) -> int:
        """Derive a single seed representing the whole episode."""
        return resolve_seed(self._episode_id, "__episode__", "__episode__", self._base_seed)

    def with_base_seed(self, base_seed: int) -> SeedStrategy:
        """Return a new strategy with a different base seed (immutable style)."""
        return SeedStrategy(self._episode_id, base_seed)


def _mix_seeds(a: int, b: int) -> int:
    """Combine two seeds into one deterministic value."""
    digest = hashlib.sha256(f"{a}:{b}".encode()).hexdigest()
    return int(digest[:8], 16)


# ---------------------------------------------------------------------------
# resolve_seed — low‑level deterministic seed
# ---------------------------------------------------------------------------


def resolve_seed(
    episode_id: str,
    scene_id: str,
    beat_id: str,
    base_seed: int = 0,
) -> int:
    """Deterministic pseudo‑random seed for any (episode, scene, beat) tuple.

    The same inputs always yield the same integer in ``[1, 2**32)``.
    """
    components = f"{episode_id}:{scene_id}:{beat_id}:{base_seed}"
    digest = hashlib.sha256(components.encode()).hexdigest()
    return int(digest[:8], 16)


# ---------------------------------------------------------------------------
# DeterminismConfig — top-level determinism settings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeterminismConfig:
    """Global determinism settings for a render run."""

    seed: int
    deterministic: bool = False


# ---------------------------------------------------------------------------
# derive_seed — convert hash to int seed
# ---------------------------------------------------------------------------


def derive_seed(manifest_hash: str) -> int:
    """First 8 hex characters (4 bytes) of SHA-256 hex string as a positive int."""
    return int(manifest_hash[:8], 16)


# ---------------------------------------------------------------------------
# compute_manifest_hash (dict overload) — quick hash from raw JSON
# ---------------------------------------------------------------------------


def compute_manifest_hash_from_dict(episode_json: dict) -> str:
    """SHA-256 of canonical JSON representation of an episode dict."""
    payload = json.dumps(episode_json, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Manifest hashing — full render-graph hash
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# DeterminismConfig — top-level determinism settings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeterminismConfig:
    """Global determinism settings for a render run."""

    seed: int
    deterministic: bool = False


# ---------------------------------------------------------------------------
# derive_seed — convert hash to int seed
# ---------------------------------------------------------------------------


def derive_seed(manifest_hash: str) -> int:
    """First 8 bytes of SHA-256 hex string as a positive int."""
    return int(manifest_hash[:8], 16)


# ---------------------------------------------------------------------------
# compute_manifest_hash (dict overload) — quick hash from raw JSON
# ---------------------------------------------------------------------------


def compute_manifest_hash_from_dict(episode_json: dict) -> str:
    """SHA-256 of canonical JSON representation of an episode dict."""
    payload = json.dumps(episode_json, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Manifest hashing — full render-graph hash
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestInput:
    """All inputs that contribute to a render's reproducibility."""

    episode: EpisodeData
    manifest: CastManifest
    render_config: dict[str, Any] = field(default_factory=dict)
    episode_path: str = ""
    episode_file_hash: str = ""


def compute_manifest_hash(
    episode: EpisodeData,
    manifest: CastManifest,
    *,
    render_config: dict[str, Any] | None = None,
    episode_path: str = "",
) -> str:
    """SHA‑256 hash of every input that affects the rendered output.

    Includes episode metadata, cast manifest, render config, and an
    optional episode file hash (read from disk when ``episode_path`` is
    provided).
    """
    m = ManifestInput(
        episode=episode,
        manifest=manifest,
        render_config=render_config or {},
        episode_path=episode_path,
        episode_file_hash=_file_hash(episode_path) if episode_path else "",
    )
    return _hash_manifest_input(m)


def _hash_manifest_input(m: ManifestInput) -> str:
    payload = json.dumps(
        {
            "show": m.episode.show,
            "season": m.episode.season,
            "episode_number": m.episode.episode_number,
            "title": m.episode.title,
            "schema_version": m.episode.schema_version,
            "render_config": m.render_config,
            "manifest": m.manifest.to_dict(),
            "episode_path": m.episode_path,
            "episode_file_hash": m.episode_file_hash,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _file_hash(path: str) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Run fingerprint — hash of file artefacts generated by a run
# ---------------------------------------------------------------------------


def compute_run_fingerprint(run_paths: list[Path]) -> str:
    """SHA‑256 fingerprint of a set of file paths (content + metadata).

    Paths are sorted internally so the result is order‑independent.
    Non‑existent paths are silently skipped.
    """
    h = hashlib.sha256()
    for path in sorted(run_paths):
        p = Path(path)
        if not p.exists():
            continue
        h.update(str(p.resolve()).encode())
        h.update(str(p.stat().st_size).encode())
        h.update(hashlib.sha256(p.read_bytes()).hexdigest().encode())
    return h.hexdigest()
