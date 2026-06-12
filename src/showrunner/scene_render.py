from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import structlog

from showrunner.aiservices_client import AIServicesClient
from showrunner.beat_prompts import build_beat_prompt
from showrunner.cast_manifest import CastManifest
from showrunner.determinism import SeedStrategy
from showrunner.paths import RunPaths
from showrunner.progress import BeatProgressEvent, NullProgressCallback, ProgressCallback
from showrunner.reporting import SceneReport, save_report
from showrunner.schemas.episode import EpisodeData, Scene

logger = structlog.get_logger()


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


def _render_image(job: BeatJob, client: AIServicesClient) -> None:
    img_path = Path(job.image_path)
    if img_path.exists():
        logger.info("image cache hit", path=str(img_path))
        return
    client.text2image(job.prompt, job.image_path, seed=job.seed)


def _render_audio(
    job: BeatJob,
    client: AIServicesClient,
    manifest: CastManifest,
    episode: EpisodeData,
) -> None:
    if not job.needs_audio or not job.text:
        return
    if job.audio_path.exists():
        logger.info("audio cache hit", path=str(job.audio_path))
        return
    voice = None
    char = manifest.get(job.speaker)
    if char and char.voice:
        voice = char.voice
    client.text2speech(
        job.text, job.audio_path, voice=voice, character=episode.cast.get(job.speaker)
    )


def _render_video(job: BeatJob, client: AIServicesClient) -> None:
    if job.video_path.exists():
        logger.info("video cache hit", path=str(job.video_path))
        return
    if not job.image_path.exists():
        return
    audio_arg = job.audio_path if job.audio_path.exists() else None
    client.image2video(
        job.image_path, job.prompt, job.video_path, audio_path=audio_arg, seed=job.seed
    )


def _render_beat(
    job: BeatJob,
    client: AIServicesClient,
    manifest: CastManifest,
    episode: EpisodeData,
    scene: Scene,
    *,
    max_retries: int = 1,
) -> BeatJob:
    structlog.contextvars.bind_contextvars(
        scene_id=scene.scene_id,
        beat_id=job.beat_id,
        beat_kind=job.kind,
    )
    for attempt in range(max_retries + 1):
        job.status = BeatStatus.RUNNING
        try:
            _render_image(job, client)
            _render_audio(job, client, manifest, episode)
            _render_video(job, client)

            job.status = BeatStatus.DONE
            job.error = ""
            return job
        except Exception as exc:
            if attempt == max_retries:
                job.error = str(exc)
                job.status = BeatStatus.FAILED
                logger.error("beat render failed", error=str(exc))
                return job
            logger.warning(
                "beat render attempt failed",
                attempt=attempt + 1,
                max_attempts=max_retries + 1,
                error=str(exc),
            )
    return job


def render_scene(
    scene: Scene,
    jobs: list[BeatJob],
    client: AIServicesClient,
    manifest: CastManifest,
    episode: EpisodeData,
    *,
    max_workers: int = 1,
    progress_callback: ProgressCallback | None = None,
) -> SceneReport:
    scene_jobs = [j for j in jobs if j.scene_id == scene.scene_id]
    report = SceneReport(scene_id=scene.scene_id, total_beats=len(scene_jobs))
    on_progress = progress_callback or NullProgressCallback()

    structlog.contextvars.bind_contextvars(scene_id=scene.scene_id)

    if max_workers <= 1:
        for idx, job in enumerate(scene_jobs):
            on_progress(
                BeatProgressEvent(
                    scene_id=job.scene_id,
                    beat_id=job.beat_id,
                    beat_index=idx,
                    total_beats=len(scene_jobs),
                    status="running",
                )
            )
            _render_beat(job, client, manifest, episode, scene=scene)
            on_progress(
                BeatProgressEvent(
                    scene_id=job.scene_id,
                    beat_id=job.beat_id,
                    beat_index=idx,
                    total_beats=len(scene_jobs),
                    status=job.status.value,
                )
            )
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_render_beat, job, client, manifest, episode, scene): job
                for job in scene_jobs
            }
            for fut in as_completed(futures):
                job = futures[fut]
                fut.result()
                idx = next(i for i, j in enumerate(scene_jobs) if j.beat_id == job.beat_id)
                on_progress(
                    BeatProgressEvent(
                        scene_id=job.scene_id,
                        beat_id=job.beat_id,
                        beat_index=idx,
                        total_beats=len(scene_jobs),
                        status=job.status.value,
                    )
                )

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
    progress_callback: ProgressCallback | None = None,
    jobs: list[BeatJob] | None = None,
) -> list[SceneReport]:
    structlog.contextvars.bind_contextvars(
        episode_title=episode.title,
        episode_id=episode_id or episode.title,
    )
    jobs = jobs if jobs is not None else plan_beats(episode, manifest, paths, episode_id=episode_id)
    reports: list[SceneReport] = []
    for scene in episode.scenes:
        scene_jobs = [j for j in jobs if j.scene_id == scene.scene_id]
        report = render_scene(
            scene,
            scene_jobs,
            client,
            manifest,
            episode,
            max_workers=max_workers,
            progress_callback=progress_callback,
        )
        reports.append(report)
        logger.info(
            "scene complete",
            scene_id=scene.scene_id,
            completed=report.completed,
            total=report.total_beats,
        )
    save_report(paths, reports)
    return reports
