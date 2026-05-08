from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from sitcom_pilot.loader import BeatData

logger = logging.getLogger(__name__)

TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
TARGET_FPS = 16
TARGET_CODEC = "libx264"


def uniformize_clip(
    input_path: Path,
    output_path: Path,
    *,
    width: int = TARGET_WIDTH,
    height: int = TARGET_HEIGHT,
    fps: int = TARGET_FPS,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-r",
        str(fps),
        "-c:v",
        TARGET_CODEC,
        "-preset",
        "fast",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def concat_clips(
    clip_paths: list[Path],
    output_path: Path,
) -> Path:
    if not clip_paths:
        raise ValueError("No clips to concatenate")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in clip_paths:
            escaped = str(p).replace("\\", "\\\\").replace("'", r"\'")
            f.write(f"file '{escaped}'\n")
        list_path = f.name
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_path,
            "-c",
            "copy",
            str(output_path),
        ]
        _run(cmd)
    finally:
        Path(list_path).unlink(missing_ok=True)
    return output_path


def mux_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def extract_thumbnail(
    video_path: Path,
    output_path: Path,
    *,
    timestamp: float = 0.0,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-ss",
        str(timestamp),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def generate_srt(
    beats: list[tuple[BeatData, float]],
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    idx = 1
    current_time = 0.0
    for beat, duration in beats:
        if beat.kind == "speech" and beat.text:
            start = _fmt_srt_time(current_time)
            end = _fmt_srt_time(current_time + duration)
            lines.append(str(idx))
            lines.append(f"{start} --> {end}")
            speaker = f"{beat.speaker}: " if beat.speaker else ""
            sanitized_text = beat.text.replace("\n", " ").replace("\r", " ")
            lines.append(f"{speaker}{sanitized_text}")
            lines.append("")
            idx += 1
        current_time += duration
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def burn_in_captions(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    srt_escaped = str(srt_path).replace("\\", "/").replace("'", r"\'").replace(":", r"\:")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"subtitles='{srt_escaped}'",
        "-c:a",
        "copy",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def mix_music_bed(
    video_path: Path,
    music_path: Path,
    output_path: Path,
    *,
    music_volume: float = 0.15,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(music_path),
        "-filter_complex",
        f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def mix_beat_audio(
    video_path: Path,
    voice_path: Path,
    music_path: Path | None = None,
    output_path: Path | None = None,
    *,
    music_volume: float = 0.1,
) -> Path:
    if output_path is None:
        suffix = video_path.suffix
        output_path = video_path.with_suffix(f".mixed{suffix}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if music_path and music_path.exists():
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(voice_path),
            "-i",
            str(music_path),
            "-filter_complex",
            f"[2:a]volume={music_volume}[bg];[1:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(voice_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            str(output_path),
        ]
    _run(cmd)
    return output_path


def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    logger.debug("ffmpeg: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        error_msg = f"ffmpeg failed (rc={result.returncode}): {' '.join(cmd)}\n"
        if result.stdout:
            error_msg += f"stdout: {result.stdout[-1000:]}\n"
        if result.stderr:
            error_msg += f"stderr: {result.stderr[-1000:]}"
        raise RuntimeError(error_msg)
    return result
