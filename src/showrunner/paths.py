from __future__ import annotations

import datetime
import re
import uuid
from pathlib import Path

_PATH_COMPONENT_RE = re.compile(r"^[^/\\:.]+$")


def _validate_path_component(value: str, name: str) -> str:
    if not value or not _PATH_COMPONENT_RE.match(value) or ".." in value:
        raise ValueError(
            f"Invalid {name} '{value}': must be a single path component without slashes or '..'"
        )
    return value


class RunPaths:
    """Canonical output directory layout for a single pipeline run.

    Structure::

        <root>/
          <run_id>/
            beats/
              <scene_id>/
                <beat_id>.png      # keyframe image
                <beat_id>.mp4      # video clip
            audio/
              <scene_id>/
                <beat_id>.wav      # TTS or extracted audio
            subtitles/
              <scene_id>/
                <beat_id>.srt
            assembly/
              episode.mp4          # final assembled episode
              episode.srt          # merged subtitle track
            manifest.json          # run manifest (see manifest.py)
            progress.json          # resume checkpoint
    """

    def __init__(self, root: Path, run_id: str = ""):
        self.root = Path(root)
        if run_id:
            self.run_id = _validate_path_component(run_id, "run_id")
        else:
            self.run_id = self._generate_run_id()
        self.run_dir = self.root / self.run_id

    # ------------------------------------------------------------------
    # Sub-directory helpers
    # ------------------------------------------------------------------

    @property
    def beats_dir(self) -> Path:
        return self.run_dir / "beats"

    @property
    def audio_dir(self) -> Path:
        return self.run_dir / "audio"

    @property
    def subtitles_dir(self) -> Path:
        return self.run_dir / "subtitles"

    @property
    def assembly_dir(self) -> Path:
        return self.run_dir / "assembly"

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "manifest.json"

    @property
    def progress_path(self) -> Path:
        return self.run_dir / "progress.json"

    # ------------------------------------------------------------------
    # Per-beat paths
    # ------------------------------------------------------------------

    def beat_image(self, scene_id: str, beat_id: str) -> Path:
        s = _validate_path_component(scene_id, "scene_id")
        b = _validate_path_component(beat_id, "beat_id")
        return self.beats_dir / s / f"{b}.png"

    def beat_video(self, scene_id: str, beat_id: str) -> Path:
        s = _validate_path_component(scene_id, "scene_id")
        b = _validate_path_component(beat_id, "beat_id")
        return self.beats_dir / s / f"{b}.mp4"

    def beat_audio(self, scene_id: str, beat_id: str) -> Path:
        s = _validate_path_component(scene_id, "scene_id")
        b = _validate_path_component(beat_id, "beat_id")
        return self.audio_dir / s / f"{b}.wav"

    def beat_subtitle(self, scene_id: str, beat_id: str) -> Path:
        s = _validate_path_component(scene_id, "scene_id")
        b = _validate_path_component(beat_id, "beat_id")
        return self.subtitles_dir / s / f"{b}.srt"

    # ------------------------------------------------------------------
    # Assembly paths
    # ------------------------------------------------------------------

    @property
    def episode_video(self) -> Path:
        return self.assembly_dir / "episode.mp4"

    @property
    def episode_subtitle(self) -> Path:
        return self.assembly_dir / "episode.srt"

    # ------------------------------------------------------------------
    # Creation helpers
    # ------------------------------------------------------------------

    def ensure_dirs(self) -> None:
        """Create all output directories."""
        for d in (self.beats_dir, self.audio_dir, self.subtitles_dir, self.assembly_dir):
            d.mkdir(parents=True, exist_ok=True)

    def ensure_scene_dirs(self, scene_id: str) -> None:
        _validate_path_component(scene_id, "scene_id")
        dirs = [
            self.beats_dir / scene_id,
            self.audio_dir / scene_id,
            self.subtitles_dir / scene_id,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_run_id() -> str:
        ts = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S")
        short = str(uuid.uuid4())[:8]
        return f"{ts}-{short}"
