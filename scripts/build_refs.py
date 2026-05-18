"""Generate reference images for each character in a cast manifest.

Usage:
    python scripts/build_refs.py --manifest cast/manifest.json --output assets/cast/
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def build_ref_prompt(character, view: str) -> str:
    base = character.visual
    view_map = {
        "front": "front-facing portrait photo",
        "three_quarter": "three-quarter view portrait photo",
        "profile": "side profile portrait photo",
    }
    view_desc = view_map.get(view, view)
    extras = "neutral expression, plain background, studio lighting"
    return f"{view_desc} of {base}, {extras}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build character reference images")
    parser.add_argument("--manifest", required=True, help="Path to cast manifest JSON")
    parser.add_argument("--output", required=True, help="Output directory for reference images")
    parser.add_argument("--seed-base", type=int, default=1000, help="Base seed for generation")
    args = parser.parse_args()

    from showrunner.aiservices_client import AIServicesClient
    from showrunner.cast_manifest import CastManifest

    manifest = CastManifest.load(Path(args.manifest))
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    client = AIServicesClient()

    failed = 0
    for i, (slug, char) in enumerate(sorted(manifest.characters.items())):
        views = ["front", "three_quarter", "profile"]
        for j, view in enumerate(views):
            seed = args.seed_base + i * 10 + j
            filename = f"{slug}_ref_{view}.png"
            out_path = output_dir / filename
            if out_path.exists():
                logger.info("Skipping existing: %s", out_path)
                continue
            prompt = build_ref_prompt(char, view)
            logger.info("Generating %s %s: %s", char.name, view, prompt[:60])
            try:
                client.text2image(
                    prompt,
                    out_path,
                    seed=seed,
                    width=768,
                    height=1024,
                )
                logger.info("Saved: %s", out_path)
            except Exception as _:
                logger.exception("Failed for %s %s", slug, view)
                failed += 1

    if failed:
        raise SystemExit(f"{failed} reference images failed to generate")
    logger.info("Done. Reference images in %s", output_dir)


if __name__ == "__main__":
    main()
