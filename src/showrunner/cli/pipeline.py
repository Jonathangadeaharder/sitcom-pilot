from __future__ import annotations

from pathlib import Path

import structlog
import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

logger = structlog.get_logger()
console = Console()
err_console = Console(stderr=True)

_PROGRESS_DESC_FMT = "[progress.description]{task.description}"


def pipeline_validate(ep_path: Path, skip: bool) -> None:
    from showrunner.commands.validate import validate_episode as pydantic_validate

    if skip:
        console.print("[yellow]\u26a0[/yellow]  Validation skipped")
        return
    valid, errors = pydantic_validate(ep_path)
    if not valid:
        for e in errors:
            err_console.print(f"  [red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    console.print("[bold green]\u2713[/bold green]  Episode validated")


def pipeline_determinism(json_data: dict, seed: int | None, deterministic: bool) -> int:
    from showrunner.determinism import (
        DeterminismConfig,
        compute_manifest_hash_from_dict,
        derive_seed,
    )

    manifest_hash = compute_manifest_hash_from_dict(json_data)
    effective_seed = seed if seed is not None else derive_seed(manifest_hash)
    det_config = DeterminismConfig(seed=effective_seed, deterministic=deterministic)
    structlog.contextvars.bind_contextvars(
        det_seed=det_config.seed, det_mode=det_config.deterministic
    )
    if deterministic:
        console.print(f"  [dim]Deterministic mode: seed={effective_seed}[/dim]")
    return effective_seed


def pipeline_load_plan(ep_path: Path, out: Path, effective_seed: int) -> tuple:
    from showrunner.cast_manifest import CastManifest, CharacterProfile
    from showrunner.determinism import SeedStrategy
    from showrunner.loader import EpisodeLoader
    from showrunner.paths import RunPaths
    from showrunner.scene_render import plan_beats

    with Progress(
        SpinnerColumn(),
        TextColumn(_PROGRESS_DESC_FMT),
        console=console,
    ) as progress:
        progress.add_task("Loading episode...", total=None)
        loader = EpisodeLoader()
        episode = loader.load(ep_path)

        manifest = CastManifest()
        for slug, char in episode.cast.items():
            manifest.add(
                CharacterProfile(
                    name=char.name or slug,
                    slug=slug,
                    visual=char.visual,
                    voice=char.voice,
                )
            )

        seed_strategy = SeedStrategy(episode.title, base_seed=effective_seed)
        paths = RunPaths(out)
        jobs = plan_beats(
            episode,
            manifest,
            paths,
            episode_id=episode.title,
            seed_strategy=seed_strategy,
        )

    total_beats = len(jobs)
    scene_count = len(episode.scenes)
    console.print(f"  [dim]{total_beats} beats across {scene_count} scenes[/dim]")
    return episode, manifest, paths, jobs, total_beats, scene_count


def pipeline_bootstrap(episode, paths, client, skip: bool) -> None:
    if skip:
        console.print("[yellow]\u26a0[/yellow]  Bootstrap skipped")
        return
    with Progress(
        SpinnerColumn(),
        TextColumn(_PROGRESS_DESC_FMT),
        console=console,
    ) as progress:
        task = progress.add_task("Bootstrapping character refs...", total=len(episode.cast))
        for slug, char in episode.cast.items():
            if char.visual:
                try:
                    client.text2image(
                        f"{char.visual}, front view, character reference sheet",
                        paths.beat_image("bootstrap", slug),
                    )
                except Exception as exc:
                    logger.warning("text2image failed for character %s: %s", slug, exc)
            progress.advance(task)

        env_task = progress.add_task(
            "Bootstrapping environment refs...", total=len(episode.environments)
        )
        for _ in episode.environments:
            progress.advance(env_task)

    console.print("[bold green]\u2713[/bold green]  Bootstrap complete")


def pipeline_render(episode, manifest, paths, client, max_workers, jobs, total_beats) -> tuple:
    from showrunner.scene_render import render_episode

    console.print(f"\n[bold]Rendering[/bold] {episode.title}")

    with Progress(
        SpinnerColumn(),
        TextColumn(_PROGRESS_DESC_FMT),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Rendering scenes...", total=total_beats)
        reports = render_episode(
            episode, manifest, paths, client, max_workers=max_workers, jobs=jobs
        )
        total_done = sum(r.completed for r in reports)
        total_failed = sum(r.failed for r in reports)
        progress.update(task, completed=total_done + total_failed)

    console.print(
        f"[bold green]\u2713[/bold green]  Rendered [green]{total_done}[/green]/{total_beats} beats"
    )
    if total_failed:
        err_console.print(f"  [red]{total_failed} beats failed[/red]")
    return total_done, total_failed


def pipeline_assemble(jobs, paths, burn_captions) -> tuple:
    from showrunner.assembler import burn_in_captions, concat_clips, generate_srt
    from showrunner.scene_render import BeatStatus
    from showrunner.schemas.episode import Beat

    video_paths: list[Path] = []
    beat_durations: list[tuple] = []
    for job in jobs:
        if job.status == BeatStatus.DONE:
            video_paths.append(job.video_path)
            beat = Beat(
                beat_id=job.beat_id,
                kind=job.kind,
                speaker=job.speaker,
                text=job.text,
            )
            beat_durations.append((beat, job.duration_sec))

    if not video_paths:
        err_console.print("[red]No rendered clips to assemble[/red]")
        raise typer.Exit(code=1)

    with Progress(
        SpinnerColumn(),
        TextColumn(_PROGRESS_DESC_FMT),
        console=console,
    ) as progress:
        progress.add_task("Concatenating clips...", total=None)
        concat_path = paths.assembly_dir / "episode_raw.mp4"
        concat_clips(video_paths, concat_path)

        progress.add_task("Generating subtitles...", total=None)
        srt_path = paths.assembly_dir / "episode.srt"
        generate_srt(beat_durations, srt_path)

        final_path = concat_path
        if burn_captions:
            progress.add_task("Burning in captions...", total=None)
            captioned = paths.assembly_dir / "episode.mp4"
            burn_in_captions(concat_path, srt_path, captioned)
            final_path = captioned

    return final_path, srt_path


def pipeline_summary(
    episode, jobs, total_done, total_beats, scene_count, final_path, srt_path
) -> None:
    from rich.table import Table

    total_dur = sum(j.duration_sec for j in jobs)
    table = Table(title="Pipeline Summary", show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row("Episode", episode.title)
    table.add_row("Scenes", str(scene_count))
    table.add_row("Beats", f"{total_done}/{total_beats}")
    table.add_row("Duration", f"{total_dur:.1f}s")
    table.add_row("Video", str(final_path))
    table.add_row("Subtitles", str(srt_path))
    console.print()
    console.print(table)
