from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from showrunner.aiservices_client import AIServicesClient
from showrunner.beat_prompts import build_beat_prompt
from showrunner.cast_manifest import CastManifest
from showrunner.determinism import SeedStrategy
from showrunner.loader import EpisodeData, SceneData
from showrunner.paths import RunPaths

logger = logging.getLogger(__name__)


class BeatStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BeatJob:
    scene_id: str
    beat_id: str
    kind: str
    prompt: str
    seed: int
    duration_sec: float
    needs_audio: bool
    speaker: str = ""
    text: str = ""
    image_path: Path = field(default_factory=Path)
    audio_path: Path = field(default_factory=Path)
    video_path: Path = field(default_factory=Path)
    status: BeatStatus = BeatStatus.PENDING
    error: str = ""


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


def plan_beats(
    episode: EpisodeData,
    manifest: CastManifest,
    paths: RunPaths,
    *,
    episode_id: str = "",
    seed_strategy: SeedStrategy | None = None,
) -> list[BeatJob]:
    jobs: list[BeatJob] = []
    for scene in episode.scenes:
        paths.ensure_scene_dirs(scene.scene_id)
        for beat in scene.beats:
            prompt = build_beat_prompt(beat, scene, episode, manifest, episode_id=episode_id)
            seed = (
                seed_strategy.for_beat(scene.scene_id, beat.beat_id, beat.seed)
                if seed_strategy
                else beat.seed
            )
            job = BeatJob(
                scene_id=scene.scene_id,
                beat_id=beat.beat_id,
                kind=beat.kind,
                prompt=prompt,
                seed=seed,
                duration_sec=beat.duration_sec,
                needs_audio=beat.kind == "speech" and bool(beat.text),
                speaker=beat.speaker,
                text=beat.text,
                image_path=paths.beat_image(scene.scene_id, beat.beat_id),
                audio_path=paths.beat_audio(scene.scene_id, beat.beat_id),
                video_path=paths.beat_video(scene.scene_id, beat.beat_id),
            )
            jobs.append(job)
    return jobs


def allocate_durations(
    jobs: list[BeatJob],
    total_budget_sec: float,
) -> list[BeatJob]:
    if not jobs:
        return jobs
    current_total = sum(j.duration_sec for j in jobs)
    if current_total <= 0:
        per_beat = total_budget_sec / len(jobs)
        for j in jobs:
            j.duration_sec = per_beat
        return jobs
    if current_total > total_budget_sec:
        scale = total_budget_sec / current_total
        for j in jobs:
            j.duration_sec *= scale
    return jobs


def _render_beat(
    job: BeatJob,
    client: AIServicesClient,
    manifest: CastManifest,
    episode: EpisodeData,
    scene: SceneData,
    *,
    max_retries: int = 1,
) -> BeatJob:
    for attempt in range(max_retries + 1):
        job.status = BeatStatus.RUNNING
        try:
            if Path(job.image_path).exists():
                logger.info("Cache hit: %s", job.image_path)
            else:
                client.text2image(
                    job.prompt,
                    job.image_path,
                    seed=job.seed,
                )

            if job.needs_audio and job.text:
                if job.audio_path.exists():
                    logger.info("Cache hit: %s", job.audio_path)
                else:
                    voice = None
                    char = manifest.get(job.speaker)
                    if char and char.voice:
                        voice = char.voice
                    client.text2speech(
                        job.text,
                        job.audio_path,
                        voice=voice,
                        character=episode.cast.get(job.speaker),
                    )

            if job.video_path.exists():
                logger.info("Cache hit: %s", job.video_path)
            elif job.image_path.exists():
                audio_arg = job.audio_path if job.audio_path.exists() else None
                client.image2video(
                    job.image_path,
                    job.prompt,
                    job.video_path,
                    audio_path=audio_arg,
                    seed=job.seed,
                )

            job.status = BeatStatus.DONE
            job.error = ""
            return job
        except Exception as exc:
            if attempt == max_retries:
                job.error = str(exc)
                job.status = BeatStatus.FAILED
                logger.error("Beat %s failed: %s", job.beat_id, exc)
                return job
            logger.warning(
                "Beat %s attempt %d/%d failed: %s",
                job.beat_id,
                attempt + 1,
                max_retries + 1,
                exc,
            )
    return job


def render_scene(
    scene: SceneData,
    jobs: list[BeatJob],
    client: AIServicesClient,
    manifest: CastManifest,
    episode: EpisodeData,
    *,
    max_workers: int = 1,
) -> SceneReport:
    scene_jobs = [j for j in jobs if j.scene_id == scene.scene_id]
    report = SceneReport(scene_id=scene.scene_id, total_beats=len(scene_jobs))

    if max_workers <= 1:
        for job in scene_jobs:
            _render_beat(job, client, manifest, episode, scene=scene)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_render_beat, job, client, manifest, episode, scene): job
                for job in scene_jobs
            }
            for fut in as_completed(futures):
                fut.result()

    for job in scene_jobs:
        if job.status == BeatStatus.DONE:
            report.completed += 1
            report.duration_sec += job.duration_sec
        elif job.status == BeatStatus.FAILED:
            report.failed += 1
            report.errors.append(f"{job.beat_id}: {job.error}")
        elif job.status == BeatStatus.SKIPPED:
            report.skipped += 1

    return report


def render_episode(
    episode: EpisodeData,
    manifest: CastManifest,
    paths: RunPaths,
    client: AIServicesClient,
    *,
    episode_id: str = "",
    max_workers: int = 1,
) -> list[SceneReport]:
    jobs = plan_beats(episode, manifest, paths, episode_id=episode_id)
    reports: list[SceneReport] = []
    for scene in episode.scenes:
        scene_jobs = [j for j in jobs if j.scene_id == scene.scene_id]
        report = render_scene(scene, scene_jobs, client, manifest, episode, max_workers=max_workers)
        reports.append(report)
        logger.info(
            "Scene %s: %d/%d beats done", scene.scene_id, report.completed, report.total_beats
        )
    _save_report(paths, reports)
    return reports


def _save_report(paths: RunPaths, reports: list[SceneReport]) -> None:
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
