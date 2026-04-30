from __future__ import annotations

"""
LTX-2.3 Video Generator V2 — generates video clips from scene images + prompts.
Uses the distilled pipeline for MPS compatibility (no block streaming required).

V2 generates ~20s clips using image conditioning, with support for
last-frame conditioning to enable video extension chains.
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from script import SCENES, get_video_prompt

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
LTX_ROOT = Path("/Users/jonathangadeaharder/Documents/projects/LTX-2")
LTX_PYTHON = str(LTX_ROOT / ".venv" / "bin" / "python")  # LTX-2 venv with torch+MPS

# Model paths
DISTILLED_CKPT = LTX_ROOT / "checkpoints" / "ltx-2.3-22b-distilled-1.1.safetensors"
GEMMA_ROOT = LTX_ROOT / "checkpoints" / "gemma-3-12b-it"
SPATIAL_UPSAMPLER = LTX_ROOT / "checkpoints" / "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"

# Generation parameters optimized for MPS 64GB
# 161 frames @ 24fps = ~6.7s per segment (safe for MPS memory)
# 81 frames @ 24fps = ~3.4s (proved stable in V1)
# Trying 161 frames for V2 as a balance
NUM_FRAMES = 161  # ~6.7s at 24fps
FRAME_RATE = 24
WIDTH = 768   # Stage 2 output (Stage 1 runs at 384)
HEIGHT = 512  # Stage 2 output (Stage 1 runs at 256)
SEED_BASE = 1000


def generate_clip(
    prompt: str,
    output_path: Path,
    seed: int = 42,
    image_path: Path | None = None,
    image_frame_idx: int = 0,
    image_strength: float = 0.95,
    num_frames: int = NUM_FRAMES,
) -> bool:
    """Generate a single video clip using LTX-2.3 distilled pipeline."""
    if output_path.exists():
        print(f"  [SKIP] {output_path.name} already exists")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    # Add image conditioning if provided
    if image_path and image_path.exists():
        cmd.extend([
            "--image", str(image_path), str(image_frame_idx),
            str(image_strength),
        ])

    print(f"  [LTX] Generating {output_path.name} ({num_frames} frames, {num_frames/FRAME_RATE:.1f}s)...")
    if image_path:
        print(f"         Image: {image_path.name} @ frame {image_frame_idx}")

    try:
        result = subprocess.run(
            cmd, env=env,
            capture_output=True, text=True,
            timeout=900,  # 15 min max per clip
        )
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  [LTX] ✓ {output_path.name} ({size_mb:.1f} MB)")
            return True
        else:
            stderr = result.stderr[-500:] if result.stderr else "(no stderr)"
            print(f"  [LTX] ✗ Failed: {stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("  [LTX] ✗ Timeout (900s)")
        return False
    except Exception as e:
        print(f"  [LTX] ✗ Error: {e}")
        return False


def extract_last_frame(video_path: Path, output_path: Path) -> bool:
    """Extract the last frame from a video clip for extension chaining."""
    cmd = [
        "ffmpeg", "-y",
        "-sseof", "-0.042",  # Seek to ~1 frame before end
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0 and output_path.exists()
    except Exception:
        return False


def generate_scene_video(
    scene: dict,
    scene_image_path: Path | None = None,
    max_segments: int = 3,
) -> list[Path]:
    """Generate video segments for a scene, using extension chaining.

    Args:
        scene: Scene dict from script.py
        scene_image_path: Initial scene image for first segment conditioning
        max_segments: Max number of segments to generate per scene

    Returns:
        List of video segment paths
    """
    sid = scene["id"]
    target_sec = scene.get("target_duration_sec", 60)
    seg_duration = NUM_FRAMES / FRAME_RATE
    needed_segments = min(max_segments, max(1, int(target_sec / seg_duration) + 1))

    video_dir = OUTPUT_DIR / "videos" / f"scene_{sid}"
    video_dir.mkdir(parents=True, exist_ok=True)

    prompt = get_video_prompt(scene)
    segments = []

    for seg_idx in range(needed_segments):
        seg_file = video_dir / f"seg_{seg_idx:03d}.mp4"
        seed = SEED_BASE + int(sid) * 100 + seg_idx

        if seg_idx == 0:
            # First segment: use scene image conditioning
            success = generate_clip(
                prompt=prompt,
                output_path=seg_file,
                seed=seed,
                image_path=scene_image_path,
                image_frame_idx=0,
                image_strength=0.95,
            )
        else:
            # Extension: extract last frame from previous segment
            prev_seg = segments[-1]
            last_frame = video_dir / f"seg_{seg_idx:03d}_lastframe.png"
            if extract_last_frame(prev_seg, last_frame):
                print(f"  [EXT] Extracted last frame from {prev_seg.name}")
                success = generate_clip(
                    prompt=prompt,
                    output_path=seg_file,
                    seed=seed,
                    image_path=last_frame,
                    image_frame_idx=0,
                    image_strength=0.95,
                )
            else:
                print("  [EXT] ✗ Failed to extract last frame, generating without conditioning")
                success = generate_clip(
                    prompt=prompt,
                    output_path=seg_file,
                    seed=seed,
                )

        if success:
            segments.append(seg_file)
        else:
            print(f"  [WARN] Segment {seg_idx} failed, stopping extension chain")
            break

    return segments


def concatenate_segments(segments: list[Path], output_path: Path) -> bool:
    """Concatenate video segments into a single scene video."""
    if not segments:
        return False
    if len(segments) == 1:
        import shutil
        shutil.copy2(segments[0], output_path)
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create concat file
    concat_file = output_path.parent / "concat_list.txt"
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        concat_file.unlink(missing_ok=True)
        return result.returncode == 0 and output_path.exists()
    except Exception:
        return False


def generate_all_videos() -> dict[str, Path]:
    """Generate video for all scenes."""
    print("╔══════════════════════════════════════════════╗")
    print("║  LTX-2.3 Video Gen V2 — Buffering S01        ║")
    print("║  With image conditioning + extension chains   ║")
    print("╚══════════════════════════════════════════════╝")

    results = {}

    for scene in SCENES:
        sid = scene["id"]
        target = scene.get("target_duration_sec", 60)
        print(f"\n─── Scene {sid}: {scene['title']} (target {target}s) ───")

        # Look for existing scene image
        scene_img = OUTPUT_DIR / "scenes" / f"scene_{sid}.png"
        if not scene_img.exists():
            # Try alternative names
            for ext in [".jpg", ".png", ".webp"]:
                alt = OUTPUT_DIR / "scenes" / f"scene_{sid}{ext}"
                if alt.exists():
                    scene_img = alt
                    break

        if scene_img.exists():
            print(f"  Using scene image: {scene_img.name}")
        else:
            print("  No scene image found, generating without conditioning")
            scene_img = None

        segments = generate_scene_video(scene, scene_img)

        if segments:
            scene_video = OUTPUT_DIR / "videos" / f"scene_{sid}_full.mp4"
            if concatenate_segments(segments, scene_video):
                results[sid] = scene_video
                print(f"  [✓] Scene {sid}: {len(segments)} segments → {scene_video.name}")
            else:
                results[sid] = segments[0]
                print("  [WARN] Concat failed, using first segment")
        else:
            print(f"  [✗] No segments generated for scene {sid}")

    print("\n═══ Video Generation Summary ═══")
    for sid, path in results.items():
        if path.exists():
            size = path.stat().st_size / (1024 * 1024)
            print(f"  Scene {sid}: {path.name} ({size:.1f} MB)")

    return results


if __name__ == "__main__":
    generate_all_videos()
