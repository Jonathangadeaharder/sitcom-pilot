from __future__ import annotations
import json
from pathlib import Path


class ProgressTracker:
    def __init__(self, state_file: Path):
        self._state_file = state_file
        self._done: set[str] = self._load()

    def _load(self) -> set[str]:
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())
                return set(data.get("completed", []))
            except (json.JSONDecodeError, KeyError):
                pass
        return set()

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps({"completed": sorted(self._done)}))

    def mark_done(self, shot_id: str) -> None:
        self._done.add(shot_id)
        self._save()

    def is_done(self, shot_id: str) -> bool:
        return shot_id in self._done

    def completed_shot_ids(self) -> list[str]:
        return sorted(self._done)

    def reset(self) -> None:
        self._done.clear()
        self._save()
