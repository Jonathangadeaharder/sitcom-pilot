"""Utility functions for Sitcom Pilot."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> dict[str, Any]:
    """Load and return JSON file."""
    import json
    with open(path) as f:
        return json.load(f)


def save_json(data: dict[str, Any], path: Path) -> None:
    """Save data to JSON file."""
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
