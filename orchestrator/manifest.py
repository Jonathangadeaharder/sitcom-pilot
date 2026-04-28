from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BeatRecord:
    beat_id: str
    scene_id: str
    kind: str           # "speech" | "silent"
    status: str         # "pending" | "rendered" | "failed" | "skipped"
    prompt_id: str = ""
    image_path: str = ""
    video_path: str = ""
    audio_path: str = ""
    error: str = ""


@dataclass
class SceneRecord:
    scene_id: str
    title: str = ""
    beats: list[BeatRecord] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.beats)

    @property
    def rendered(self) -> int:
        return sum(1 for b in self.beats if b.status == "rendered")

    @property
    def failed(self) -> int:
        return sum(1 for b in self.beats if b.status == "failed")


@dataclass
class RunManifest:
    """Serialisable record of a single pipeline run.

    Written to ``<run_dir>/manifest.json`` at the end of the run (and
    incrementally updated on each beat completion for crash-resume support).
    """

    run_id: str
    episode_path: str
    episode_title: str
    schema_version: str
    started_at: str = ""
    finished_at: str = ""
    status: str = "running"   # "running" | "completed" | "failed" | "partial"
    scenes: list[SceneRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, run_id: str, episode_path: Path, episode_title: str, schema_version: str = "2.0") -> "RunManifest":
        return cls(
            run_id=run_id,
            episode_path=str(episode_path),
            episode_title=episode_title,
            schema_version=schema_version,
            started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "RunManifest":
        with open(path) as f:
            data = json.load(f)
        scenes = [
            SceneRecord(
                scene_id=s["scene_id"],
                title=s.get("title", ""),
                beats=[BeatRecord(**b) for b in s.get("beats", [])],
            )
            for s in data.get("scenes", [])
        ]
        return cls(
            run_id=data["run_id"],
            episode_path=data["episode_path"],
            episode_title=data["episode_title"],
            schema_version=data.get("schema_version", "2.0"),
            started_at=data.get("started_at", ""),
            finished_at=data.get("finished_at", ""),
            status=data.get("status", "running"),
            scenes=scenes,
            metadata=data.get("metadata", {}),
        )

    def _to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "episode_path": self.episode_path,
            "episode_title": self.episode_title,
            "schema_version": self.schema_version,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "scenes": [
                {
                    "scene_id": sc.scene_id,
                    "title": sc.title,
                    "total": sc.total,
                    "rendered": sc.rendered,
                    "failed": sc.failed,
                    "beats": [asdict(b) for b in sc.beats],
                }
                for sc in self.scenes
            ],
            "metadata": self.metadata,
        }

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def finish(self, status: str = "completed") -> None:
        self.status = status
        self.finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def summary(self) -> dict[str, int]:
        total = sum(s.total for s in self.scenes)
        rendered = sum(s.rendered for s in self.scenes)
        failed = sum(s.failed for s in self.scenes)
        return {"total": total, "rendered": rendered, "failed": failed, "pending": total - rendered - failed}
