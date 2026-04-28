from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class EpisodeAssembler:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._video_codec = "h264_videotoolbox" if self._detect_videotoolbox() else "libx264"

    @staticmethod
    def _detect_videotoolbox() -> bool:
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders"], capture_output=True, text=True, check=True
            )
            return "h264_videotoolbox" in result.stdout
        except Exception:
            return False

    def _write_concat_list(self, clips: list[Path]) -> Path:
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, "w") as f:
            for clip in clips:
                f.write(f"file '{clip.resolve()}'\n")
        return concat_file

    def concatenate(self, clips: list[Path], output_path: Path) -> bool:
        if not clips:
            return False
        concat_file = self._write_concat_list(clips)
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c:v", self._video_codec, "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Concatenation failed: {e}")
            return False
