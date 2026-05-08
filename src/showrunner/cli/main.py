from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import structlog
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from showrunner.validator import EpisodeValidator

logger = structlog.get_logger()
console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="sitcom-pilot",
    help="Beat-based AI sitcom pilot pipeline (Buffering S01)",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

render_app = typer.Typer(help="Render beats, scenes, or full episodes")
app.add_typer(render_app, name="render")


def _setup_logging(verbose: bool = False) -> None:
    level = "DEBUG" if verbose else "INFO"
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _load_episode(path: Path) -> dict:
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        err_console.print(f"[red]Cannot parse episode JSON:[/red] {exc}")
        raise typer.Exit(code=1)
    return data


def _resolve_output_dir(output_dir: str | None) -> Path:
    return Path(output_dir) if output_dir else Path("output")


# ---------------------------------------------------------------------------
# E7.1: validate
# ---------------------------------------------------------------------------


@app.command()
def validate(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    strict: bool = typer.Option(False, "--strict", help="Enable strict business-rule checks"),
) -> None:
    """Validate an episode JSON file against the v2 schema."""
    validator = EpisodeValidator()
    errors = validator.validate_file(Path(episode_path), strict=strict)
    if errors:
        for error in errors:
            err_console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)
    console.print(f"[green]OK[/green]  {episode_path}")


# ---------------------------------------------------------------------------
# E7.2: plan (dry run)
# ---------------------------------------------------------------------------


@app.command()
def plan(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full prompts"),
) -> None:
    """Show beat plan with prompts (dry run)."""
    _setup_logging(verbose)

    from sitcom_pilot.cast_manifest import CastManifest
    from sitcom_pilot.loader import EpisodeLoader
    from sitcom_pilot.scene_render import plan_beats

    data = _load_episode(Path(episode_path))

    loader = EpisodeLoader()
    episode = loader.load(Path(episode_path))

    manifest = CastManifest()
    for slug, char in episode.cast.items():
        from sitcom_pilot.cast_manifest import CharacterProfile

        manifest.add(
            CharacterProfile(
                name=char.name or slug,
                slug=slug,
                visual=char.visual,
                role="",
            )
        )

    from sitcom_pilot.paths import RunPaths

    paths = RunPaths(Path("output"))
    jobs = plan_beats(episode, manifest, paths, episode_id=data.get("title", ""))

    table = Table(title=f"Beat Plan: {episode.title}")
    table.add_column("Scene", style="cyan")
    table.add_column("Beat", style="green")
    table.add_column("Kind", style="magenta")
    table.add_column("Duration", justify="right")
    table.add_column("Speaker", style="yellow")
    if verbose:
        table.add_column("Prompt", max_width=60)

    for job in jobs:
        row = [
            job.scene_id,
            job.beat_id,
            job.kind,
            f"{job.duration_sec:.1f}s",
            job.speaker or "-",
        ]
        if verbose:
            row.append(job.prompt[:80])
        table.add_row(*row)

    console.print(table)
    console.print(f"\nTotal beats: [bold]{len(jobs)}[/bold]")
    total_dur = sum(j.duration_sec for j in jobs)
    console.print(f"Total duration: [bold]{total_dur:.1f}s[/bold]")


# ---------------------------------------------------------------------------
# E7.3: bootstrap
# ---------------------------------------------------------------------------


@app.command()
def bootstrap(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
) -> None:
    """Generate reference images and voice samples for cast."""
    _setup_logging()

    from sitcom_pilot.aiservices_client import AIServicesClient
    from sitcom_pilot.cast_manifest import CastManifest, CharacterProfile, CharacterRef
    from sitcom_pilot.loader import EpisodeLoader

    loader = EpisodeLoader()
    episode = loader.load(Path(episode_path))

    out = _resolve_output_dir(output_dir) / "bootstrap"
    out.mkdir(parents=True, exist_ok=True)

    client = AIServicesClient()
    manifest = CastManifest()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        char_task = progress.add_task("Generating character refs...", total=len(episode.cast))

        for slug, char in episode.cast.items():
            ref_dir = out / "cast" / slug
            ref_dir.mkdir(parents=True, exist_ok=True)

            refs = CharacterRef()
            if char.visual:
                front_path = ref_dir / "front.png"
                try:
                    client.text2image(
                        f"{char.visual}, front view, character reference sheet",
                        front_path,
                    )
                    refs = CharacterRef(front=str(front_path.relative_to(out.parent)))
                except Exception as exc:
                    logger.warning("Failed to generate ref image", character=slug, error=str(exc))

            if char.voice and char.voice.clone_from:
                voice_dir = out / "voices" / slug
                voice_dir.mkdir(parents=True, exist_ok=True)
                src = Path(char.voice.clone_from)
                if src.exists():
                    dst = voice_dir / src.name
                    shutil.copy2(src, dst)

            manifest.add(
                CharacterProfile(
                    name=char.name or slug,
                    slug=slug,
                    visual=char.visual,
                    refs=refs,
                    voice=char.voice,
                )
            )
            progress.advance(char_task)

        env_task = progress.add_task(
            "Generating environment refs...", total=len(episode.environments)
        )
        for env_name, env_data in episode.environments.items():
            env_dir = out / "environments" / env_name
            env_dir.mkdir(parents=True, exist_ok=True)
            if env_data.style or env_data.trigger_word:
                ref_path = env_dir / "reference.png"
                try:
                    prompt = (
                        f"{env_data.style or env_data.trigger_word}, establishing shot, sitcom set"
                    )
                    client.text2image(prompt, ref_path, width=1280, height=720)
                except Exception as exc:
                    logger.warning(
                        "Failed to generate env ref", environment=env_name, error=str(exc)
                    )
            progress.advance(env_task)

    manifest_path = out / "cast_manifest.json"
    manifest.save(manifest_path)
    console.print(f"\n[green]Bootstrap complete.[/green] Manifest saved to {manifest_path}")


# ---------------------------------------------------------------------------
# E7.4: render commands
# ---------------------------------------------------------------------------


@render_app.command("beat")
def render_beat(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    beat_id: str = typer.Argument(..., help="Beat ID to render"),
    scene_id: str | None = typer.Option(
        None, "--scene", "-s", help="Scene ID (auto-detected if omitted)"
    ),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
) -> None:
    """Render a single beat."""
    _setup_logging()

    from sitcom_pilot.aiservices_client import AIServicesClient
    from sitcom_pilot.loader import EpisodeLoader
    from sitcom_pilot.paths import RunPaths
    from sitcom_pilot.scene_render import _render_beat, plan_beats

    loader = EpisodeLoader()
    episode = loader.load(Path(episode_path))

    manifest = _build_manifest(episode)
    paths = RunPaths(_resolve_output_dir(output_dir))
    paths.ensure_dirs()

    jobs = plan_beats(episode, manifest, paths)
    target = None
    for job in jobs:
        if job.beat_id == beat_id:
            if scene_id is None or job.scene_id == scene_id:
                target = job
                break

    if target is None:
        err_console.print(f"[red]Beat '{beat_id}' not found.[/red]")
        raise typer.Exit(code=1)

    scene = _find_scene(episode, target.scene_id)
    client = AIServicesClient()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Rendering beat {beat_id}...", total=None)
        _render_beat(target, client, manifest, episode, scene=scene)

    if target.status.value == "done":
        console.print(f"[green]Beat {beat_id} rendered:[/green] {target.video_path}")
    else:
        err_console.print(f"[red]Beat {beat_id} failed:[/red] {target.error}")
        raise typer.Exit(code=1)


@render_app.command("scene")
def render_scene(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    scene_id: str = typer.Argument(..., help="Scene ID to render"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    max_workers: int = typer.Option(1, "--workers", "-w", help="Parallel workers"),
) -> None:
    """Render all beats in a scene."""
    _setup_logging()

    from sitcom_pilot.aiservices_client import AIServicesClient
    from sitcom_pilot.loader import EpisodeLoader
    from sitcom_pilot.paths import RunPaths
    from sitcom_pilot.scene_render import plan_beats, render_scene

    loader = EpisodeLoader()
    episode = loader.load(Path(episode_path))

    manifest = _build_manifest(episode)
    paths = RunPaths(_resolve_output_dir(output_dir))
    paths.ensure_dirs()

    scene = _find_scene(episode, scene_id)
    if scene is None:
        err_console.print(f"[red]Scene '{scene_id}' not found.[/red]")
        raise typer.Exit(code=1)

    jobs = plan_beats(episode, manifest, paths)
    scene_jobs = [j for j in jobs if j.scene_id == scene_id]
    client = AIServicesClient()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Rendering scene {scene_id}...", total=len(scene_jobs))
        report = render_scene(scene, scene_jobs, client, manifest, episode, max_workers=max_workers)
        progress.update(task, completed=report.completed + report.failed)

    console.print(f"Scene {scene_id}: [green]{report.completed}[/green]/{report.total_beats} done")
    if report.errors:
        for err in report.errors:
            err_console.print(f"  [red]{err}[/red]")


@render_app.command("episode")
def render_episode_cmd(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    max_workers: int = typer.Option(1, "--workers", "-w", help="Parallel workers"),
) -> None:
    """Render all beats in an episode."""
    _setup_logging()

    from sitcom_pilot.aiservices_client import AIServicesClient
    from sitcom_pilot.loader import EpisodeLoader
    from sitcom_pilot.paths import RunPaths
    from sitcom_pilot.scene_render import plan_beats, render_episode

    loader = EpisodeLoader()
    episode = loader.load(Path(episode_path))

    manifest = _build_manifest(episode)
    paths = RunPaths(_resolve_output_dir(output_dir))
    paths.ensure_dirs()

    client = AIServicesClient()
    jobs = plan_beats(episode, manifest, paths)

    total_beats = len(jobs)
    scene_count = len(episode.scenes)
    console.print(
        Panel(
            f"Rendering [bold]{episode.title}[/bold]\n"
            f"{total_beats} beats across {scene_count} scenes"
        )
    )

    reports = render_episode(
        episode,
        manifest,
        paths,
        client,
        max_workers=max_workers,
    )

    total_done = sum(r.completed for r in reports)
    total_failed = sum(r.failed for r in reports)
    console.print(f"\n[green]Done:[/green] {total_done}/{total_beats} beats rendered")
    if total_failed:
        err_console.print(f"[red]Failed:[/red] {total_failed} beats")


# ---------------------------------------------------------------------------
# E7.5: assemble
# ---------------------------------------------------------------------------


@app.command()
def assemble(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    run_id: str | None = typer.Option(None, "--run-id", help="Specific run ID to assemble"),
    burn_captions: bool = typer.Option(False, "--captions", help="Burn in captions"),
) -> None:
    """Assemble rendered clips into final video."""
    _setup_logging()

    from sitcom_pilot.assembler import (
        burn_in_captions,
        concat_clips,
        generate_srt,
    )
    from sitcom_pilot.loader import EpisodeLoader
    from sitcom_pilot.paths import RunPaths
    from sitcom_pilot.scene_render import plan_beats

    loader = EpisodeLoader()
    episode = loader.load(Path(episode_path))

    root = _resolve_output_dir(output_dir)
    if run_id:
        paths = RunPaths(root, run_id=run_id)
    else:
        latest = _find_latest_run(root)
        if latest is None:
            err_console.print("[red]No runs found in output directory.[/red]")
            raise typer.Exit(code=1)
        paths = RunPaths(root, run_id=latest)

    manifest = _build_manifest(episode)
    jobs = plan_beats(episode, manifest, paths)

    video_paths = []
    beat_durations: list[tuple] = []
    for job in jobs:
        if job.video_path.exists():
            video_paths.append(job.video_path)
            from sitcom_pilot.loader import BeatData

            beat = BeatData(
                beat_id=job.beat_id,
                kind=job.kind,
                speaker=job.speaker,
                text=job.text,
            )
            beat_durations.append((beat, job.duration_sec))

    if not video_paths:
        err_console.print("[red]No rendered clips found.[/red]")
        raise typer.Exit(code=1)

    paths.assembly_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
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

    console.print(f"\n[green]Assembly complete:[/green] {final_path}")
    console.print(f"Subtitles: {srt_path}")


# ---------------------------------------------------------------------------
# E7.6: doctor
# ---------------------------------------------------------------------------


@app.command()
def doctor() -> None:
    """Check dependencies (ffmpeg, MLX providers, etc.)."""
    checks = []

    # ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        result = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True)
        version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
        checks.append(("ffmpeg", True, version_line))
    else:
        checks.append(("ffmpeg", False, "not found"))

    # ffprobe
    checks.append(
        ("ffprobe", shutil.which("ffprobe") is not None, shutil.which("ffprobe") or "not found")
    )

    # Python
    checks.append(("Python", True, sys.version.split()[0]))

    # Provider CLIs
    for cmd_name in ["text2image", "image2image", "image2video", "text2speech"]:
        found = shutil.which(cmd_name)
        checks.append((cmd_name, found is not None, found or "not found"))

    # Python packages
    for pkg in ["structlog", "rich", "typer", "pydantic", "jsonschema"]:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "installed")
            checks.append((pkg, True, ver))
        except ImportError:
            checks.append((pkg, False, "not installed"))

    table = Table(title="Dependency Check")
    table.add_column("Dependency", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Detail")

    all_ok = True
    for name, ok, detail in checks:
        status = "[green]OK[/green]" if ok else "[red]MISSING[/red]"
        if not ok:
            all_ok = False
        table.add_row(name, status, detail)

    console.print(table)
    if not all_ok:
        err_console.print("\n[yellow]Some dependencies are missing.[/yellow]")
        raise typer.Exit(code=1)
    console.print("\n[green]All dependencies OK.[/green]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_manifest(episode):
    from sitcom_pilot.cast_manifest import CastManifest, CharacterProfile

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
    return manifest


def _find_scene(episode, scene_id):
    for scene in episode.scenes:
        if scene.scene_id == scene_id:
            return scene
    return None


def _find_latest_run(root: Path) -> str | None:
    if not root.exists():
        return None
    runs = sorted(
        [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")],
        reverse=True,
    )
    return runs[0] if runs else None


# ---------------------------------------------------------------------------
# Legacy run command (kept for backward compat)
# ---------------------------------------------------------------------------


@app.command(hidden=True)
def run(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    config_file: str | None = typer.Option(None, help="Path to config file"),
) -> None:
    """Run the sitcom pilot pipeline (legacy)."""
    err_console.print(
        "The 'run' command is deprecated. Use render-episode + assemble instead.",
    )
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
