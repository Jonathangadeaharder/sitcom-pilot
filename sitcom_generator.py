#!/usr/bin/env python3
"""
Sitcom Pilot Generator V2 — Main Orchestrator
══════════════════════════════════════════════

Audio-first pipeline for "Buffering" S01E01.

Phases:
  1. Images   — Flux2 (ComfyUI) character portraits + scene shots
  2. Audio    — Fish-Speech TTS with character reference voices
  3. Video    — LTX-2.3 distilled with image conditioning + extension chains
  4. Assembly — FFmpeg: mix Fish audio onto video, concat scenes

Usage:
  python sitcom_generator.py              # Run full pipeline
  python sitcom_generator.py --phase 1    # Images only
  python sitcom_generator.py --phase 2    # Audio only
  python sitcom_generator.py --phase 3    # Video only
  python sitcom_generator.py --phase 4    # Assembly only
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def phase_1_images():
    """Phase 1: Generate all images via Flux2/ComfyUI."""
    from flux2_generator import run_all
    return run_all()


def phase_2_audio():
    """Phase 2: Generate dialogue audio via Fish-Speech with character references."""
    from voice_generator import generate_all_voices
    return generate_all_voices()


def phase_3_videos():
    """Phase 3: Generate video clips via LTX-2.3 with image conditioning + extension."""
    from ltx_video_generator import generate_all_videos
    return generate_all_videos()


def phase_4_assembly():
    """Phase 4: Assemble final pilot episode — mix audio onto video, concat scenes."""
    from assembler import assemble_pilot
    return assemble_pilot()


def main():
    parser = argparse.ArgumentParser(description="AI Sitcom Pilot Generator")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4],
                        help="Run a specific phase only (1=images, 2=video, 3=voices, 4=assembly)")
    args = parser.parse_args()

    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ██████╗ ██╗   ██╗███████╗███████╗███████╗██████╗        ║
    ║   ██╔══██╗██║   ██║██╔════╝██╔════╝██╔════╝██╔══██╗       ║
    ║   ██████╔╝██║   ██║█████╗  █████╗  █████╗  ██████╔╝       ║
    ║   ██╔══██╗██║   ██║██╔══╝  ██╔══╝  ██╔══╝  ██╔══██╗       ║
    ║   ██████╔╝╚██████╔╝██║     ██║     ███████╗██║  ██║       ║
    ║   ╚═════╝  ╚═════╝ ╚═╝     ╚═╝     ╚══════╝╚═╝  ╚═╝       ║
    ║                                                           ║
    ║   Season 1, Episode 1: "The Deployment"                   ║
    ║   AI Sitcom Pilot Generator                               ║
    ║   Flux2 + LTX-2.3 + Fish-Speech                          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

    start_time = time.time()

    if args.phase:
        if args.phase == 1:
            phase_1_images()
        elif args.phase == 2:
            phase_2_audio()
        elif args.phase == 3:
            phase_3_videos()
        elif args.phase == 4:
            phase_4_assembly()
    else:
        # Full pipeline (audio-first order)
        print("Running full V2 pipeline...\n")

        print("=" * 60)
        print("PHASE 1: Image Generation (Flux2)")
        print("=" * 60)
        phase_1_images()

        print("\n" + "=" * 60)
        print("PHASE 2: Audio Generation (Fish-Speech)")
        print("=" * 60)
        phase_2_audio()

        print("\n" + "=" * 60)
        print("PHASE 3: Video Generation (LTX-2.3)")
        print("=" * 60)
        phase_3_videos()

        print("\n" + "=" * 60)
        print("PHASE 4: Final Assembly")
        print("=" * 60)
        result = phase_4_assembly()

        elapsed = time.time() - start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        print(f"\nTotal pipeline time: {hours}h {minutes}m")

        if result:
            print(f"\n🎬 Your pilot episode is ready: {result}")
        else:
            print("\n⚠ Pipeline completed with some missing components.")
            print("  Run individual phases to fill gaps:")
            print("    python sitcom_generator.py --phase 1  # Images")
            print("    python sitcom_generator.py --phase 2  # Audio")
            print("    python sitcom_generator.py --phase 3  # Videos")
            print("    python sitcom_generator.py --phase 4  # Assembly")


if __name__ == "__main__":
    main()
