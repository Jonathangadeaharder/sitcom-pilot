from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Persisted progress tracker (resume checkpoint)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Rich progress bar for scene/beat rendering
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BeatProgressEvent:
    scene_id: str
    beat_id: str
    beat_index: int
    total_beats: int
    status: str


ProgressCallback = Callable[[BeatProgressEvent], None]


class NullProgressCallback:
    def __call__(self, event: BeatProgressEvent) -> None:
        pass


def make_progress_callback(console: Any = None) -> RichRenderProgress:
    """Build a rich Progress bar that reports per-beat progress.

    Returns a RichRenderProgress suitable for passing to render_scene()
    or render_episode().  Must be used as a context manager so the
    underlying rich Progress display is properly started/stopped.
    """
    return RichRenderProgress(console=console)


class RichRenderProgress:
    """Context manager that wraps ``rich.progress.Progress`` for beat rendering.

    Usage::

        with RichRenderProgress() as on_progress:
            report = render_scene(..., progress_callback=on_progress)
    """

    def __init__(self, console: Any = None):
        if console is None:
            from rich.console import Console

            console = Console()
        self._console = console

    def __enter__(self) -> ProgressCallback:
        from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self._console,
        )
        self._progress.__enter__()
        self._tasks: dict[str, int] = {}
        self._beat_index: dict[str, int] = {}
        return self._on_event

    def __exit__(self, *args: object) -> None:
        self._progress.__exit__(*args)

    def _on_event(self, event: BeatProgressEvent) -> None:
        task_id = self._tasks.get(event.scene_id)
        if task_id is None:
            task_id = self._progress.add_task(
                f"Scene {event.scene_id}",
                total=event.total_beats,
            )
            self._tasks[event.scene_id] = task_id

        if event.status == "running":
            desc = f"Scene {event.scene_id}: {event.beat_id} (rendering...)"
            prog = event.beat_index
        elif event.status == "done":
            desc = f"Scene {event.scene_id}: {event.beat_id} [green]done[/green]"
            prog = event.beat_index + 1
        elif event.status == "failed":
            desc = f"Scene {event.scene_id}: {event.beat_id} [red]failed[/red]"
            prog = event.beat_index + 1
        else:
            desc = f"Scene {event.scene_id}: {event.beat_id}"
            prog = event.beat_index + 1

        self._progress.update(task_id, description=desc, completed=prog)
