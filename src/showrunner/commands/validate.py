from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from showrunner.schemas.episode import Episode


def validate_episode(path: Path) -> tuple[bool, list[str]]:
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"Cannot parse JSON: {exc}"]

    if not isinstance(data, dict):
        return False, [f"Expected a JSON object at top level, got {type(data).__name__}"]

    try:
        Episode(**data)
    except ValidationError as exc:
        errors = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            msg = err["msg"]
            errors.append(f"{loc}: {msg}")
        return False, errors

    return True, []
