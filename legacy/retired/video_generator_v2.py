from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from showrunner.loader import EpisodeLoader
from showrunner.prompts import PromptBuilder

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "s01e02"

LTX_ROOT = Path(os.environ.get("LTX_ROOT", "/Users/jonathangadeaharder/Documents/projects/LTX-2"))
LTX_PYTHON = str(LTX_ROOT / ".venv" / "bin" / "python")

DISTILLED_CKPT = LTX_ROOT / "checkpoints" / "ltx-2.3-22b-distilled-1.1.safetensors"
GEMMA_ROOT = LTX_ROOT / "checkpoints" / "gemma-3-12b-it"
SPATIAL_UPSAMPLER = LTX_ROOT / "checkpoints" / "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"

NUM_FRAMES = 161
FRAME_RATE = 24
WIDTH = 768
HEIGHT = 512


def generate_clip(
    prompt: str,
    output_path: Path,
    seed: int = 42,
    image_path: Path | None = None,
    num_frames: int = NUM_FRAMES,
) -> bool:
    if output_path.exists():
        print(f"  [SKIP] {output_path.name} already exists")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{LTX_ROOT / 'packages' / 'ltx-core' / 'src'}:"
        f"{LTX_ROOT / 'packages' / 'ltx-pipelines' / 'src'}:"
        f"{env.get('PYTHONPATH', '')}"
    )

    cmd = [
        LTX_PYTHON, "-m", "ltx_pipelines.distilled",
        "--distilled-checkpoint-path", str(DISTILLED_CKPT),
        "--gemma-root", str(GEMMA_ROOT),
        "--spatial-upsampler-path", str(SPATIAL_UPSAMPLER),
        "--prompt", prompt,
        "--output-path", str(output_path),
        "--seed", str(seed),
        "--num-frames", str(num_frames),
        "--frame-rate", str(FRAME_RATE),
        "--height", str(HEIGHT),
        "--width", str(WIDTH),
    ]

    if image_path and image_path.exists():
        cmd.extend(["--image", str(image_path), "0", "0.95"])

    dur = num_frames / FRAME_RATE
    print(
        f"  [LTX] Generating {output_path.name} "
        f"({num_frames} frames, {dur:.1f}s)..."
    )
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  [LTX] OK {output_path.name} ({size_mb:.1f} MB)")
            return True
        else:
            stderr = result.stderr[-500:] if result.stderr else "(no stderr)"
            print(f"  [LTX] FAIL: {stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("  [LTX] TIMEOUT (900s)")
        return False
    except Exception as e:
        print(f"  [LTX] ERROR: {e}")
        return False


def extract_last_frame(video_path: Path, output_path: Path) -> bool:
    cmd = [
        "ffmpeg", "-y", "-sseof", "-0.042",
        "-i", str(video_path), "-frames:v", "1", "-q:v", "2", str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0 and output_path.exists()
    except Exception:
        return False


def get_audio_duration(audio_path: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-hide_banner", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(audio_path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip())
    except Exception:
        return NUM_FRAMES / FRAME_RATE


def calc_frames_for_duration(duration_sec: float) -> int:
    target = int(duration_sec * FRAME_RATE)
    base = 8 * ((target - 1) // 8) + 1
    if base < target:
        base += 8
    return max(17, min(base, 161))


def generate_video_for_episode(episode_path: Path, output_dir: Path) -> dict[str, Path]:
    episode = EpisodeLoader().load(episode_path)
    builder = PromptBuilder()
    results: dict[str, Path] = {}

    video_dir = output_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = output_dir / "audio"

    for scene in episode.scenes:
        prev_video: Path | None = None
        for shot in scene.shots:
            audio_path = audio_dir / f"{shot.shot_id}.wav"
            if audio_path.exists():
                duration = get_audio_duration(audio_path)
                num_frames = calc_frames_for_duration(duration)
            else:
                num_frames = NUM_FRAMES

            output_path = video_dir / f"{shot.shot_id}.mp4"
            start_prompt = builder.build_start_prompt(shot, scene, episode)
            end_prompt = builder.build_end_prompt(shot, scene, episode)
            prompt = f"{start_prompt} transitioning to {end_prompt}"

            if prev_video and prev_video.exists():
                last_frame = video_dir / f"{shot.shot_id}_lastframe.png"
                if extract_last_frame(prev_video, last_frame):
                    success = generate_clip(
                        prompt=prompt, output_path=output_path,
                        seed=shot.seed, image_path=last_frame,
                        num_frames=num_frames,
                    )
                else:
                    success = generate_clip(
                        prompt=prompt, output_path=output_path,
                        seed=shot.seed, num_frames=num_frames,
                    )
            else:
                success = generate_clip(
                    prompt=prompt, output_path=output_path,
                    seed=shot.seed, num_frames=num_frames,
                )

            if success:
                results[shot.shot_id] = output_path
                prev_video = output_path
            else:
                prev_video = None

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LTX Video Gen for S01E02")
    parser.add_argument("episode", help="Path to episode JSON")
    parser.add_argument("--output-dir", default="output/s01e02")
    args = parser.parse_args()

    print("=== LTX-2.3 Video Generation for S01E02 ===")
    results = generate_video_for_episode(Path(args.episode), Path(args.output_dir))
    print(f"\nGenerated {len(results)} video clips")
    for sid, path in sorted(results.items()):
        size = path.stat().st_size / (1024 * 1024) if path.exists() else 0
        print(f"  {sid}: {path.name} ({size:.1f} MB)")


if __name__ == "__main__":
    main()
