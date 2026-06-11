from __future__ import annotations

import json
from dataclasses import dataclass, field
from showrunner.paths import RunPaths

@dataclass
class SceneReport:
    scene_id: str
    total_beats: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_sec: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.completed / self.total_beats if self.total_beats else 0.0


def save_report(paths: RunPaths, reports: list[SceneReport]) -> None:
    data = []
    for r in reports:
        data.append(
            {
                "scene_id": r.scene_id,
                "total_beats": r.total_beats,
                "completed": r.completed,
                "failed": r.failed,
                "skipped": r.skipped,
                "duration_sec": r.duration_sec,
                "success_rate": r.success_rate,
                "errors": r.errors,
            }
        )
    report_path = paths.run_dir / "render_report.json"
    report_path.write_text(json.dumps(data, indent=2))
