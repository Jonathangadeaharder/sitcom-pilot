#!/usr/bin/env python3
import argparse
import json
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from sitcom_pilot.loader import EpisodeLoader
from sitcom_pilot.prompts import PromptBuilder
from sitcom_pilot.comfyui_client import ComfyUIClient
from sitcom_pilot.renderer import ShotRenderer
from sitcom_pilot.assembler import concat_clips
from sitcom_pilot.node_map import NodeMap
from sitcom_pilot.progress import ProgressTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="AI Showrunner Orchestrator")
    parser.add_argument("episode", help="Path to episode JSON cut-sheet")
    parser.add_argument("--workflow", default="workflow_api.json", help="ComfyUI workflow template")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--output-dir", default="output/rendered")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without rendering")
    parser.add_argument("--cooldown", type=float, default=0.0, help="Cooldown seconds between shots")
    parser.add_argument("--crash-recovery", action="store_true", help="Enable crash recovery")
    parser.add_argument("--server-cmd", nargs="+", default=None, help="Command to start ComfyUI server")
    parser.add_argument("--server-cwd", default=None, help="Working directory for ComfyUI server")
    parser.add_argument("--node-map", default=None, help="Path to node map JSON")
    parser.add_argument("--resume", default=None, help="Path to progress state file for resuming")
    parser.add_argument("--assemble-only", action="store_true", help="Only assemble from existing outputs")
    args = parser.parse_args()

    episode = EpisodeLoader().load(Path(args.episode))

    with open(args.workflow) as f:
        template = json.load(f)

    node_map = NodeMap()
    if args.node_map:
        with open(args.node_map) as f:
            node_map = NodeMap.from_dict(json.load(f))

    if args.dry_run:
        builder = PromptBuilder()
        for scene in episode.scenes:
            for shot in scene.shots:
                start = builder.build_start_prompt(shot, scene, episode)
                end = builder.build_end_prompt(shot, scene, episode)
                print(f"\n[{shot.shot_id}]")
                print(f"  START: {start}")
                print(f"  END:   {end}")
        return

    client = ComfyUIClient(base_url=args.comfy_url)

    if not args.crash_recovery:
        if not client.is_server_running():
            print("ComfyUI is not running. Start it first.")
            sys.exit(1)

    renderer = ShotRenderer(
        client=client,
        builder=PromptBuilder(),
        node_map=node_map,
        cooldown_seconds=args.cooldown,
        crash_recovery=args.crash_recovery,
        server_cmd=args.server_cmd,
        server_cwd=args.server_cwd,
    )

    tracker = None
    if args.resume:
        tracker = ProgressTracker(Path(args.resume))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_outputs: list[str] = []
    for scene in episode.scenes:
        for shot in scene.shots:
            if tracker and tracker.is_done(shot.shot_id):
                logging.info(f"Skipping {shot.shot_id} (already done)")
                continue
            result = renderer.render_shot(shot, scene, episode, template)
            if result.success:
                paths = client.get_output_paths(result.prompt_id)
                all_outputs.extend(paths)
                if tracker:
                    tracker.mark_done(shot.shot_id)
                logging.info(f"Rendered {shot.shot_id} -> {paths}")
            else:
                logging.warning(f"Failed to render {shot.shot_id}")

    if all_outputs:
        clip_paths = [Path(p) for p in all_outputs]
        output_path = output_dir / f"{episode.title.replace(' ', '_')}.mp4"
        try:
            concat_clips(clip_paths, output_path)
            print(f"\nAssembled episode to {output_path}")
        except Exception:
            print("\nAssembly failed.")
            sys.exit(1)
    else:
        print("\nNo outputs to assemble.")

    print(f"\nRendering complete. {len(all_outputs)} clips processed.")


if __name__ == "__main__":
    main()
