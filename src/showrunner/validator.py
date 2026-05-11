from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Optional jsonschema support
try:
    import jsonschema

    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False


_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "episode_v2.schema.json"


class ValidationError(Exception):
    """Raised when an episode file fails structural validation."""


class EpisodeValidator:
    """Validate an episode JSON file against the v2.0 schema and structural rules."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_file(self, path: Path, strict: bool = False) -> list[str]:
        """Return a list of error strings. Empty list means valid."""
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return [f"Cannot parse JSON: {exc}"]
        if not isinstance(data, dict):
            return [f"Expected a JSON object at top level, got {type(data).__name__}"]
        return self.validate(data, strict=strict)

    def validate(self, data: dict[str, Any], strict: bool = False) -> list[str]:
        errors: list[str] = []

        schema_version = data.get("schema_version")
        if schema_version != "2.0":
            errors.append(f"schema_version must be '2.0', got {schema_version!r}")
            return errors

        if _JSONSCHEMA_AVAILABLE:
            errors.extend(self._jsonschema_validate(data))
        else:
            errors.extend(self._structural_validate(data))

        if errors:
            return errors

        errors.extend(self._check_scene_environment_refs(data))
        errors.extend(self._check_scene_character_refs(data))
        errors.extend(self._check_beat_ids_unique(data))
        if strict:
            errors.extend(self._check_beat_speaker_refs(data))
            errors.extend(self._check_speech_beats_have_text(data))

        return errors

    # ------------------------------------------------------------------
    # JSON Schema validation
    # ------------------------------------------------------------------

    def _jsonschema_validate(self, data: dict[str, Any]) -> list[str]:
        if not _SCHEMA_PATH.exists():
            return [f"Schema file not found: {_SCHEMA_PATH}"]
        try:
            with open(_SCHEMA_PATH) as f:
                schema = json.load(f)
            validator = jsonschema.Draft202012Validator(schema)  # pyright: ignore[reportPossiblyUnboundVariable]
            return [str(e.message) for e in validator.iter_errors(data)]
        except Exception as exc:
            return [f"JSON Schema validation error: {exc}"]

    # ------------------------------------------------------------------
    # Lightweight structural validation (no jsonschema dep)
    # ------------------------------------------------------------------

    def _structural_validate(self, data: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for key in ("show", "title", "cast", "environments", "scenes"):
            if key not in data:
                errors.append(f"Missing required top-level field: '{key}'")

        if not isinstance(data.get("scenes"), list):
            errors.append("'scenes' must be a list")
            return errors
        if not isinstance(data.get("cast"), dict):
            errors.append("'cast' must be an object")
        if not isinstance(data.get("environments"), dict):
            errors.append("'environments' must be an object")

        for scene_idx, scene in enumerate(data.get("scenes", [])):
            if not isinstance(scene, dict):
                errors.append(f"Scene[{scene_idx}] must be an object")
                continue
            for key in ("scene_id", "environment", "characters_present", "beats"):
                if key not in scene:
                    errors.append(f"Scene[{scene_idx}] missing required field: '{key}'")
            if not isinstance(scene.get("beats"), list):
                errors.append(f"Scene[{scene_idx}] 'beats' must be a list")
                continue
            for beat_idx, beat in enumerate(scene.get("beats", [])):
                if not isinstance(beat, dict):
                    errors.append(f"Scene[{scene_idx}].beat[{beat_idx}] must be an object")
                    continue
                for key in ("beat_id", "kind"):
                    if key not in beat:
                        errors.append(
                            f"Scene[{scene_idx}].beat[{beat_idx}] missing required field: '{key}'"
                        )
                if beat.get("kind") not in ("speech", "silent", None):
                    errors.append(
                        f"Scene[{scene_idx}].beat[{beat_idx}] kind must be 'speech' or 'silent'"
                    )
        return errors

    # ------------------------------------------------------------------
    # Business-rule checks
    # ------------------------------------------------------------------

    def _check_scene_environment_refs(self, data: dict[str, Any]) -> list[str]:
        envs = set(data.get("environments", {}).keys())
        errors = []
        for scene in data.get("scenes", []):
            env = scene.get("environment")
            if env and env not in envs:
                errors.append(
                    f"Scene '{scene.get('scene_id')}' references unknown environment '{env}'"
                )
        return errors

    def _check_scene_character_refs(self, data: dict[str, Any]) -> list[str]:
        cast = set(data.get("cast", {}).keys())
        errors = []
        for scene in data.get("scenes", []):
            for char in scene.get("characters_present", []):
                if char not in cast:
                    errors.append(
                        f"Scene '{scene.get('scene_id')}' references unknown character '{char}'"
                    )
        return errors

    def _check_beat_ids_unique(self, data: dict[str, Any]) -> list[str]:
        seen: set[str] = set()
        errors = []
        for scene in data.get("scenes", []):
            for beat in scene.get("beats", []):
                bid = beat.get("beat_id")
                if bid in seen:
                    errors.append(f"Duplicate beat_id: '{bid}'")
                if bid:
                    seen.add(bid)
        return errors

    def _check_beat_speaker_refs(self, data: dict[str, Any]) -> list[str]:
        cast = set(data.get("cast", {}).keys())
        errors = []
        for scene in data.get("scenes", []):
            for beat in scene.get("beats", []):
                speaker = beat.get("speaker")
                if speaker and beat.get("kind") == "speech" and speaker not in cast:
                    errors.append(
                        f"Beat '{beat.get('beat_id')}' in scene "
                        f"'{scene.get('scene_id')}' references unknown speaker '{speaker}'"
                    )
        return errors

    def _check_speech_beats_have_text(self, data: dict[str, Any]) -> list[str]:
        errors = []
        for scene in data.get("scenes", []):
            for beat in scene.get("beats", []):
                if beat.get("kind") == "speech":
                    if not beat.get("text"):
                        errors.append(
                            f"Speech beat '{beat.get('beat_id')}' in scene "
                            f"'{scene.get('scene_id')}' is missing 'text'"
                        )
                    if not beat.get("speaker"):
                        errors.append(
                            f"Speech beat '{beat.get('beat_id')}' in scene "
                            f"'{scene.get('scene_id')}' is missing 'speaker'"
                        )
        return errors


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """validate-episode <path> [<path> ...]

    Exits 0 if all files are valid, 1 if any have errors.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="validate-episode",
        description="Validate one or more episode JSON files against the v2.0 schema.",
    )
    parser.add_argument(
        "paths", nargs="+", metavar="EPISODE_JSON", help="Path(s) to episode JSON file(s)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only print errors, not OK messages"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict business-rule checks (speaker refs, etc.)",
    )
    args = parser.parse_args(argv)

    validator = EpisodeValidator()
    any_failed = False

    for raw_path in args.paths:
        path = Path(raw_path)
        errors = validator.validate_file(path, strict=args.strict)
        if errors:
            any_failed = True
            print(f"FAIL  {path}")
            for err in errors:
                print(f"      - {err}")
        else:
            if not args.quiet:
                print(f"OK    {path}")

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
