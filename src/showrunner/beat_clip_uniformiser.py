from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from showrunner.paths import RunPaths
from showrunner.schemas.episode import Beat

logger = logging.getLogger(__name__)


class _RunError(RuntimeError):
    pass


@dataclass(frozen=True)
class UniformiserConfig:
    width: int = 1280
    height: int = 720
    fps: int = 16
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_sample_rate: int = 44100
    pix_fmt: str = "yuv420p"
    video_bitrate: str = ""
    audio_bitrate: str = "128k"


class BeatClipUniformiser:
    def __init__(self, config: UniformiserConfig | None = None) -> None:
        self._config = config or UniformiserConfig()

    @property
    def config(self) -> UniformiserConfig:
        return self._config

    def uniformise(self, input_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = self._build_cmd(input_path, output_path)
        _run(cmd)
        return output_path

    def uniformise_beat(
        self,
        video_path: Path,
        paths: RunPaths,
        scene_id: str,
        beat_id: str,
    ) -> Path | None:
        if not video_path.exists():
            logger.warning("Beat video not found: %s", video_path)
            return None
        output = paths.beats_dir / scene_id / f"{beat_id}.uniformised.mp4"
        return self.uniformise(video_path, output)

    def uniformise_beats(
        self,
        beats: list[Beat],
        paths: RunPaths,
        scene_id: str,
    ) -> list[Path]:
        results: list[Path] = []
        for beat in beats:
            video_path = paths.beat_video(scene_id, beat.beat_id)
            result = self.uniformise_beat(video_path, paths, scene_id, beat.beat_id)
            if result is not None:
                results.append(result)
        return results

    def _build_cmd(self, input_path: Path, output_path: Path) -> list[str]:
        cfg = self._config
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-s",
            f"{cfg.width}x{cfg.height}",
            "-r",
            str(cfg.fps),
            "-c:v",
            cfg.video_codec,
        ]
        if cfg.video_bitrate:
            cmd.extend(["-b:v", cfg.video_bitrate])
        if cfg.pix_fmt:
            cmd.extend(["-pix_fmt", cfg.pix_fmt])
        cmd.extend(["-c:a", cfg.audio_codec])
        if cfg.audio_bitrate:
            cmd.extend(["-b:a", cfg.audio_bitrate])
        cmd.extend(["-ar", str(cfg.audio_sample_rate)])
        cmd.append(str(output_path))
        return cmd


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    logger.debug("ffmpeg: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        error_msg = f"ffmpeg failed (rc={result.returncode}): {' '.join(cmd)}\n"
        if result.stdout:
            error_msg += f"stdout: {result.stdout[-1000:]}\n"
        if result.stderr:
            error_msg += f"stderr: {result.stderr[-1000:]}"
        raise _RunError(error_msg)
    return result
