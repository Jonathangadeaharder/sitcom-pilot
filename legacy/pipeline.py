from __future__ import annotations

import json
import logging
import subprocess
import sys

from dataclasses import replace
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from sitcom_pilot.loader import EpisodeData, EpisodeLoader  # noqa: E402
from sitcom_pilot.audio_builder import build_shot_audio  # noqa: E402
from sitcom_pilot.prompts import PromptBuilder  # noqa: E402
from sitcom_pilot.comfyui_client import ComfyUIClient  # noqa: E402
from sitcom_pilot.renderer import ShotRenderer  # noqa: E402
from sitcom_pilot.assembler import EpisodeAssembler  # noqa: E402
from sitcom_pilot.node_map import NodeMap  # noqa: E402
from sitcom_pilot.progress import ProgressTracker  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def generate_audio_for_episode(
    episode: EpisodeData, output_dir: Path, cast: dict
) -> dict[str, Path]:
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    shot_audio_map: dict[str, Path] = {}

    for scene in episode.scenes:
        for shot in scene.shots:
            if not shot.dialogue:
                continue
            first_speaker = shot.dialogue[0].get("speaker", "")
            char = cast.get(first_speaker, {})
            out_path = audio_dir / f"{shot.shot_id}.wav"
            success = build_shot_audio(
                dialogue=shot.dialogue,
                character_id=first_speaker,
                output_path=out_path,
                voice_seed=char.get("voice_seed", 42),
                voice_temp=char.get("voice_temp", 0.8),
            )
            if success and out_path.exists():
                shot_audio_map[shot.shot_id] = out_path
                logger.info(f"Audio generated: {shot.shot_id} -> {out_path}")
            else:
                logger.warning(f"Audio failed for {shot.shot_id}")

    return shot_audio_map


def inject_audio_paths(episode: EpisodeData, audio_map: dict[str, Path]) -> EpisodeData:
    new_scenes = []
    for scene in episode.scenes:
        new_shots = []
        for shot in scene.shots:
            p = audio_map.get(shot.shot_id)
            audio_path = str(p) if p else ""
            new_shots.append(replace(shot, audio_path=audio_path))
        new_scenes.append(replace(scene, shots=new_shots))
    return replace(episode, scenes=new_scenes)


def merge_audio_video(video_path: Path, audio_path: Path, output_path: Path) -> bool:
    if not video_path.exists() or not audio_path.exists():
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and output_path.exists()
    except Exception as e:
        logger.error(f"Merge failed for {video_path}: {e}")
        return False


def run_pipeline(
    episode_path: Path,
    output_dir: Path,
    workflow_path: Path = Path("workflow_api.json"),
    comfy_url: str = "http://127.0.0.1:8188",
    audio_only: bool = False,
    video_only: bool = False,
    skip_audio: bool = False,
    dry_run: bool = False,
    crash_recovery: bool = False,
    cooldown: float = 0.0,
    server_cmd: list[str] | None = None,
    server_cwd: str | None = None,
    node_map: NodeMap | None = None,
    progress_file: Path | None = None,
) -> Path:
    logger.info(f"=== Pipeline: {episode_path.name} ===")

    raw = json.loads(episode_path.read_text())
    cast = raw.get("cast", {})
    episode = EpisodeLoader().load(episode_path)
    if episode.schema_version == "2.0":
        raise SystemExit(
            "This legacy pipeline only supports v1 (shot-based) episode files. "
            "For v2 beat-based episodes, use the src/sitcom_pilot pipeline."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_map: dict[str, Path] = {}
    if not video_only and not skip_audio:
        logger.info("Phase 1: Generating audio from dialogue...")
        audio_map = generate_audio_for_episode(episode, output_dir, cast)
        total = sum(len(s.shots) for s in episode.scenes)
        logger.info(
            f"Audio generated for {len(audio_map)}/{total} shots"
        )

    if audio_only:
        logger.info("Audio-only mode, skipping video")
        return output_dir

    episode = inject_audio_paths(episode, audio_map)

    if dry_run:
        builder = PromptBuilder()
        for scene in episode.scenes:
            for shot in scene.shots:
                start = builder.build_start_prompt(shot, scene, episode)
                end = builder.build_end_prompt(shot, scene, episode)
                audio_info = f"audio={shot.audio_path}" if shot.audio_path else "no audio"
                print(f"[{shot.shot_id}] {audio_info}")
                print(f"  START: {start[:100]}...")
                print(f"  END:   {end[:100]}...")
        return output_dir

    template = json.loads(workflow_path.read_text())

    client = ComfyUIClient(base_url=comfy_url)
    if not crash_recovery and not client.is_server_running():
        logger.error("ComfyUI is not running")
        raise RuntimeError("ComfyUI server not available")

    renderer = ShotRenderer(
        client=client,
        builder=PromptBuilder(),
        node_map=node_map,
        cooldown_seconds=cooldown,
        crash_recovery=crash_recovery,
        server_cmd=server_cmd,
        server_cwd=server_cwd,
    )

    tracker = None
    if progress_file:
        tracker = ProgressTracker(progress_file)

    rendered_dir = output_dir / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)

    video_outputs: dict[str, Path] = {}
    logger.info("Phase 2: Rendering video via ComfyUI...")
    for scene in episode.scenes:
        for shot in scene.shots:
            if tracker and tracker.is_done(shot.shot_id):
                logger.info(f"Skipping {shot.shot_id} (already done)")
                continue
            result = renderer.render_shot(shot, scene, episode, template)
            if result.success:
                paths = client.get_output_paths(result.prompt_id)
                if paths:
                    video_outputs[shot.shot_id] = Path(paths[0])
                if tracker:
                    tracker.mark_done(shot.shot_id)
                logger.info(f"Rendered {shot.shot_id}")
            else:
                logger.warning(f"Failed to render {shot.shot_id}")

    logger.info("Phase 3: Merging audio + video per shot...")
    merged_dir = output_dir / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)

    merged_clips: list[Path] = []
    for scene in episode.scenes:
        for shot in scene.shots:
            video_path = video_outputs.get(shot.shot_id)
            audio_path = audio_map.get(shot.shot_id)
            merged_path = merged_dir / f"{shot.shot_id}.mp4"

            if video_path and video_path.exists():
                if audio_path and audio_path.exists():
                    if merge_audio_video(video_path, audio_path, merged_path):
                        merged_clips.append(merged_path)
                    else:
                        merged_clips.append(video_path)
                else:
                    merged_clips.append(video_path)

    if not merged_clips:
        logger.error("No clips to assemble")
        raise RuntimeError("No video clips produced")

    logger.info("Phase 4: Assembling final episode...")
    final_path = output_dir / "final" / f"{episode.title.replace(' ', '_')}.mp4"
    assembler = EpisodeAssembler(output_dir=output_dir / "final")
    ok = assembler.concatenate(merged_clips, final_path)

    if ok:
        size_mb = final_path.stat().st_size / (1024 * 1024)
        logger.info(f"Episode assembled: {final_path} ({size_mb:.1f} MB)")
    else:
        logger.error("Assembly failed")

    return final_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Buffering S01E02 Unified Pipeline")
    parser.add_argument("episode", help="Path to episode JSON")
    parser.add_argument("--output-dir", default="output/s01e02")
    parser.add_argument("--workflow", default="workflow_api.json")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--audio-only", action="store_true")
    parser.add_argument("--video-only", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--crash-recovery", action="store_true")
    parser.add_argument("--cooldown", type=float, default=0.0)
    parser.add_argument("--server-cmd", nargs="+", default=None)
    parser.add_argument("--server-cwd", default=None)
    parser.add_argument("--progress", default=None)
    args = parser.parse_args()

    run_pipeline(
        episode_path=Path(args.episode),
        output_dir=Path(args.output_dir),
        workflow_path=Path(args.workflow),
        comfy_url=args.comfy_url,
        audio_only=args.audio_only,
        video_only=args.video_only,
        skip_audio=args.skip_audio,
        dry_run=args.dry_run,
        crash_recovery=args.crash_recovery,
        cooldown=args.cooldown,
        server_cmd=args.server_cmd,
        server_cwd=args.server_cwd,
        progress_file=Path(args.progress) if args.progress else None,
    )


if __name__ == "__main__":
    main()
