from __future__ import annotations

import logging
import shutil
import tempfile
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from showrunner.aiservices_client import AIServicesClient
from showrunner.cast_manifest import CastManifest
from showrunner.loader import EpisodeData, SceneData
from showrunner.paths import RunPaths
from showrunner.reporting import SceneReport, save_report
from showrunner.scene_render import BeatJob, BeatStatus, _render_beat

logger = logging.getLogger(__name__)

_DEFAULT_BUFFER_SIZE = 3


class RenderBuffer:
    """Renders beats ahead of current position into a temp buffer.

    Maintains a sliding window of in-flight beat renders. When a beat at
    position N finishes its buffer entry is flushed (copied) to the final
    ``RunPaths`` output and the next beat (N + buffer_size) is submitted.
    """

    def __init__(
        self,
        client: AIServicesClient,
        manifest: CastManifest,
        episode: EpisodeData,
        paths: RunPaths,
        *,
        buffer_size: int = _DEFAULT_BUFFER_SIZE,
        max_workers: int = 4,
    ):
        self._client = client
        self._manifest = manifest
        self._episode = episode
        self._paths = paths
        self._buffer_size = max(1, buffer_size)
        self._max_workers = max_workers
        self._buffer_dir = Path(tempfile.mkdtemp(prefix="render_buffer_"))
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)

    @property
    def buffer_dir(self) -> Path:
        return self._buffer_dir

    def close(self) -> None:
        self._executor.shutdown(wait=False)
        shutil.rmtree(self._buffer_dir, ignore_errors=True)

    def _buf_path_for(self, final_path: Path) -> Path:
        """Map a final output path to a corresponding buffer path."""
        return self._buffer_dir / final_path.relative_to(self._paths.run_dir)

    def _build_reports(
        self, jobs: list[BeatJob], scenes: list[SceneData]
    ) -> dict[str, SceneReport]:
        reports: dict[str, SceneReport] = {}
        for sc in scenes:
            reports[sc.scene_id] = SceneReport(
                scene_id=sc.scene_id,
                total_beats=sum(1 for j in jobs if j.scene_id == sc.scene_id),
            )
        return reports

    def _create_buffer_jobs(self, jobs: list[BeatJob]) -> list[BeatJob]:
        buffer_jobs: list[BeatJob] = []
        for job in jobs:
            buf_job = BeatJob(
                scene_id=job.scene_id,
                beat_id=job.beat_id,
                kind=job.kind,
                prompt=job.prompt,
                seed=job.seed,
                duration_sec=job.duration_sec,
                needs_audio=job.needs_audio,
                speaker=job.speaker,
                text=job.text,
                image_path=self._buf_path_for(job.image_path),
                audio_path=self._buf_path_for(job.audio_path)
                if job.needs_audio
                else job.audio_path,
                video_path=self._buf_path_for(job.video_path),
            )
            buffer_jobs.append(buf_job)
        return buffer_jobs

    def _submit_buffer_job(
        self,
        j: BeatJob,
        scenes: list[SceneData],
        futures: dict,
        submitted_ids: set[str],
    ) -> None:
        if j.beat_id in submitted_ids:
            return
        submitted_ids.add(j.beat_id)
        scene = _find_scene(scenes, j.scene_id)
        assert scene is not None, f"Scene {j.scene_id} not found"
        fut = self._executor.submit(
            _render_beat, j, self._client, self._manifest, self._episode, scene=scene
        )
        futures[fut] = j

    def render(
        self,
        jobs: list[BeatJob],
        scenes: list[SceneData],
    ) -> list[SceneReport]:
        reports = self._build_reports(jobs, scenes)
        if not jobs:
            return list(reports.values())

        buffer_jobs = self._create_buffer_jobs(jobs)

        futures: dict = {}
        submitted_ids: set[str] = set()
        next_to_submit = 0
        current_beat_idx = 0

        while next_to_submit < len(buffer_jobs) or futures:
            while len(futures) < self._max_workers and next_to_submit < len(buffer_jobs):
                self._submit_buffer_job(buffer_jobs[next_to_submit], scenes, futures, submitted_ids)
                next_to_submit += 1

            if not futures:
                break

            done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)

            for fut in done:
                futures.pop(fut)
                result = fut.result()
                _flush_beat(result, self._paths)
                _record_beat(reports, result)
                current_beat_idx += 1

                lookahead_pos = current_beat_idx + self._buffer_size
                if lookahead_pos < len(buffer_jobs):
                    self._submit_buffer_job(
                        buffer_jobs[lookahead_pos], scenes, futures, submitted_ids
                    )

        return list(reports.values())


def _find_scene(scenes: list[SceneData], scene_id: str) -> SceneData | None:
    for sc in scenes:
        if sc.scene_id == scene_id:
            return sc
    return None


def _flush_beat(job: BeatJob, paths: RunPaths) -> None:
    for buf_path, final_path in [
        (job.image_path, paths.beat_image(job.scene_id, job.beat_id)),
        (job.audio_path, paths.beat_audio(job.scene_id, job.beat_id)),
        (job.video_path, paths.beat_video(job.scene_id, job.beat_id)),
    ]:
        if buf_path.exists():
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(buf_path, final_path)
            buf_path.unlink(missing_ok=True)


def _record_beat(reports: dict[str, SceneReport], job: BeatJob) -> None:
    report = reports.get(job.scene_id)
    if report is None:
        return
    if job.status == BeatStatus.DONE:
        report.completed += 1
        report.duration_sec += job.duration_sec
    elif job.status == BeatStatus.FAILED:
        report.failed += 1
        report.errors.append(f"{job.beat_id}: {job.error}")


def render_episode_buffered(
    episode: EpisodeData,
    manifest: CastManifest,
    paths: RunPaths,
    client: AIServicesClient,
    *,
    episode_id: str = "",
    buffer_size: int = _DEFAULT_BUFFER_SIZE,
    max_workers: int = 4,
) -> list[SceneReport]:
    from showrunner.scene_render import plan_beats

    jobs = plan_beats(episode, manifest, paths, episode_id=episode_id)
    buffer = RenderBuffer(
        client,
        manifest,
        episode,
        paths,
        buffer_size=buffer_size,
        max_workers=max_workers,
    )
    try:
        reports = buffer.render(jobs, episode.scenes)
        save_report(paths, reports)
        return reports
    finally:
        buffer.close()
