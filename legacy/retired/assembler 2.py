from __future__ import annotations

"""
V2 Assembly — mixes Fish-Speech dialogue audio onto LTX video per scene,
then concatenates all scenes into the final pilot episode.

Pipeline: scene_video + scene_audio → scene_mixed → concat → pilot.mp4
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from script import SCENES

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def has_videotoolbox() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"], capture_output=True, text=True, check=True
        )
        return "h264_videotoolbox" in result.stdout
    except Exception:
        return False


VIDEO_CODEC = "h264_videotoolbox" if has_videotoolbox() else "libx264"


def get_video_duration(path: Path) -> float:
    """Get duration of a video/audio file in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def create_title_card(output_path: Path, duration: float = 4.0,
                      width: int = 768, height: int = 512) -> bool:
    """Generate a title card video using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=black:s={width}x{height}:d={duration}:r=24",
        "-vf", (
            "drawtext=text='BUFFERING':fontsize=56:fontcolor=white:"
            "x=(w-text_w)/2:y=(h-text_h)/2-30:font=Helvetica,"
            "drawtext=text='Season 1 \\- Episode 1':fontsize=24:fontcolor=gray:"
            "x=(w-text_w)/2:y=(h-text_h)/2+30:font=Helvetica,"
            "drawtext=text='The Deployment':fontsize=22:fontcolor=lightgray:"
            "x=(w-text_w)/2:y=(h-text_h)/2+65:font=Helvetica"
        ),
        "-c:v", VIDEO_CODEC, "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def create_credits(output_path: Path, duration: float = 6.0,
                   width: int = 768, height: int = 512) -> bool:
    """Generate end credits video."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=black:s={width}x{height}:d={duration}:r=24",
        "-vf", (
            "drawtext=text='BUFFERING':fontsize=40:fontcolor=white:"
            "x=(w-text_w)/2:y=60:font=Helvetica,"
            "drawtext=text='Created with AI':fontsize=20:fontcolor=gray:"
            "x=(w-text_w)/2:y=140:font=Helvetica,"
            "drawtext=text='Flux2 + LTX-2.3 + Fish-Speech':fontsize=16:fontcolor=gray:"
            "x=(w-text_w)/2:y=170:font=Helvetica,"
            "drawtext=text='Maya Chen  •  Derek Thompson':fontsize=18:fontcolor=lightgray:"
            "x=(w-text_w)/2:y=250:font=Helvetica,"
            "drawtext=text='Priya Sharma  •  Finn O\\'Brien':fontsize=18:fontcolor=lightgray:"
            "x=(w-text_w)/2:y=280:font=Helvetica"
        ),
        "-c:v", VIDEO_CODEC, "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def normalize_clip(input_path: Path, output_path: Path,
                   target_w: int = 768, target_h: int = 512) -> bool:
    """Normalize a clip to consistent resolution and codec (no audio)."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
               f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", VIDEO_CODEC, "-pix_fmt", "yuv420p",
        "-an",
        "-r", "24",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def mix_scene_audio(video_path: Path, audio_path: Path,
                    output_path: Path) -> bool:
    """Mix a scene's dialogue audio WAV onto its video.

    The video is used as-is; the audio is mixed in as the sole audio track.
    If audio is longer than video, video is padded/looped.
    If video is longer than audio, remaining video plays silent.
    """
    video_dur = get_video_duration(video_path)
    audio_dur = get_video_duration(audio_path)

    if audio_dur <= 0:
        # No valid audio, just copy video
        import shutil
        shutil.copy2(video_path, output_path)
        return True

    # If audio is longer than video, extend video to match audio duration
    # by looping the last frame
    if audio_dur > video_dur + 0.5:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex",
            f"[0:v]tpad=stop_mode=clone:stop_duration={audio_dur - video_dur}[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", VIDEO_CODEC, "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(output_path),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(output_path),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0 and output_path.exists()


def assemble_pilot() -> Path | None:
    """Assemble all scenes into the final pilot episode."""
    print("╔══════════════════════════════════════════╗")
    print("║  V2 Assembly — Buffering S01E01           ║")
    print("║  Fish-Speech Audio + LTX-2.3 Video        ║")
    print("╚══════════════════════════════════════════╝")

    if not check_ffmpeg():
        print("✗ ffmpeg not found. Install with: brew install ffmpeg")
        return None

    final_dir = OUTPUT_DIR / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    norm_dir = final_dir / "normalized"
    norm_dir.mkdir(exist_ok=True)

    # Step 1: Title card
    print("\n─── Creating Title Card ───")
    title_path = final_dir / "title.mp4"
    if create_title_card(title_path):
        print("  ✓ Title card created")

    # Step 2: Process each scene — normalize video, mix audio
    print("\n─── Processing Scenes ───")
    clip_paths = []

    if title_path.exists():
        clip_paths.append(title_path)

    for scene in SCENES:
        sid = scene["id"]
        print(f"\n  Scene {sid}: {scene['title']}")

        # Find scene video (from LTX generator)
        scene_video = OUTPUT_DIR / "videos" / f"scene_{sid}_full.mp4"
        if not scene_video.exists():
            # Try single segment
            scene_video = OUTPUT_DIR / "videos" / f"scene_{sid}" / "seg_000.mp4"
        if not scene_video.exists():
            # Try V1 clip location
            scene_video = OUTPUT_DIR / "clips" / f"scene_{sid}.mp4"

        if not scene_video.exists():
            print(f"    ⚠ No video found for scene {sid}")
            continue

        # Normalize video resolution
        norm_clip = norm_dir / f"scene_{sid}_norm.mp4"
        print("    Normalizing video...")
        if not normalize_clip(scene_video, norm_clip):
            print("    ✗ Normalization failed")
            continue

        # Find scene audio (from Fish-Speech)
        scene_audio = OUTPUT_DIR / "voices" / f"scene_{sid}" / f"scene_{sid}_full.wav"

        if scene_audio.exists():
            audio_dur = get_video_duration(scene_audio)
            video_dur = get_video_duration(norm_clip)
            print(f"    Mixing audio ({audio_dur:.1f}s) onto video ({video_dur:.1f}s)...")

            mixed_clip = norm_dir / f"scene_{sid}_mixed.mp4"
            if mix_scene_audio(norm_clip, scene_audio, mixed_clip):
                final_dur = get_video_duration(mixed_clip)
                print(f"    ✓ Mixed clip: {final_dur:.1f}s")
                clip_paths.append(mixed_clip)
            else:
                print("    ⚠ Mix failed, using video-only")
                clip_paths.append(norm_clip)
        else:
            print("    No dialogue audio, using video-only")
            clip_paths.append(norm_clip)

    # Step 3: Credits
    print("\n─── Creating Credits ───")
    credits_path = final_dir / "credits.mp4"
    if create_credits(credits_path):
        print("  ✓ Credits created")
        clip_paths.append(credits_path)

    if len(clip_paths) < 2:
        print("✗ Not enough clips to assemble")
        return None

    # Step 4: Concatenate everything
    print(f"\n─── Concatenating {len(clip_paths)} clips ───")
    concat_list = final_dir / "concat.txt"
    with open(concat_list, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve()}'\n")

    final_output = final_dir / "buffering_s01e01_v2.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", VIDEO_CODEC, "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(final_output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0 and final_output.exists():
        duration = get_video_duration(final_output)
        size_mb = final_output.stat().st_size / (1024 * 1024)
        print("\n╔══════════════════════════════════════════╗")
        print("║  ✓ V2 PILOT ASSEMBLED SUCCESSFULLY       ║")
        print("╠══════════════════════════════════════════╣")
        print(f"║  Output: {final_output.name:<30} ║")
        print(f"║  Duration: {duration:.1f}s ({duration/60:.1f} min){' '*(17-len(f'{duration:.1f}s ({duration/60:.1f} min)'))} ║")
        print(f"║  Size: {size_mb:.1f} MB{' '*(26-len(f'{size_mb:.1f} MB'))} ║")
        print(f"║  Clips: {len(clip_paths)}{' '*(30-len(str(len(clip_paths))))} ║")
        print("╚══════════════════════════════════════════╝")
        return final_output
    else:
        print(f"✗ Assembly failed: {result.stderr[:300]}")
        return None


if __name__ == "__main__":
    assemble_pilot()
