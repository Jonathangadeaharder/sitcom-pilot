"""Bootstrap voice clones for each character in a cast manifest.

Usage:
    python scripts/build_voices.py --manifest cast/manifest.json --output assets/voices/
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


SAMPLE_TEXT = (
    "Hello, my name is {name}. "
    "I'm testing my voice clone for the sitcom pilot project. "
    "This is a sample recording to establish my vocal characteristics."
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap voice clones")
    parser.add_argument("--manifest", required=True, help="Path to cast manifest JSON")
    parser.add_argument("--output", required=True, help="Output directory for voice samples")
    parser.add_argument("--sample-text", default=None, help="Custom sample text template")
    args = parser.parse_args()

    from sitcom_pilot.aiservices_client import AIServicesClient
    from sitcom_pilot.cast_manifest import CastManifest

    manifest = CastManifest.load(Path(args.manifest))
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    client = AIServicesClient()

    template = args.sample_text or SAMPLE_TEXT

    failed = 0
    for slug, char in manifest.characters.items():
        if not char.voice:
            logger.warning("No voice config for %s, skipping", slug)
            continue
        text = template.format(name=char.name)
        out_path = output_dir / f"{slug}_sample.wav"
        if out_path.exists():
            logger.info("Skipping existing: %s", out_path)
            continue
        logger.info("Generating voice sample for %s", char.name)
        try:
            client.text2speech(
                text,
                out_path,
                voice=char.voice,
            )
            logger.info("Saved: %s", out_path)
        except Exception as _:
            logger.exception("Failed for %s", slug)
            failed += 1

    if failed:
        raise SystemExit(f"{failed} voice samples failed to generate")
    logger.info("Done. Voice samples in %s", output_dir)


if __name__ == "__main__":
    main()
