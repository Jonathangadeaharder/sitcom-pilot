from __future__ import annotations

import importlib
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


def _setup_logging(verbose: bool = False, json_logs: bool = False) -> None:
    level = "DEBUG" if verbose else "INFO"
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    structlog.configure(
        processors=processors,
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
    from showrunner.commands.validate import validate_episode as pydantic_validate

    ep_path = Path(episode_path)
    valid, errors = pydantic_validate(ep_path)
    if not valid:
        for error in errors:
            err_console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)
    if strict:
        validator = EpisodeValidator()
        strict_errors = validator.validate_file(ep_path, strict=True)
        if strict_errors:
            for error in strict_errors:
                err_console.print(f"[red]Error:[/red] {error}")
            raise typer.Exit(code=1)
    console.print(f"[green]Valid:[/green] {episode_path}")


# ---------------------------------------------------------------------------
# E7.2: plan (dry run)
# ---------------------------------------------------------------------------


@app.command()
def plan(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
) -> None:
    """Plan beats for an episode and output as JSON."""
    from showrunner.planner import plan_episode
    from showrunner.validator import EpisodeValidator

    data = _load_episode(Path(episode_path))

    validator = EpisodeValidator()
    errors = validator.validate(data)
    if errors:
        for error in errors:
            err_console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)

    try:
        plan = plan_episode(data)
    except Exception as exc:
        err_console.print(f"[red]Error:[/red] Failed to plan episode: {exc}")
        raise typer.Exit(code=1)

    output = [b.model_dump() for b in plan]
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")


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

    from showrunner.aiservices_client import AIServicesClient
    from showrunner.cast_manifest import CastManifest, CharacterProfile, CharacterRef
    from showrunner.loader import EpisodeLoader

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

    from showrunner.aiservices_client import AIServicesClient
    from showrunner.loader import EpisodeLoader
    from showrunner.paths import RunPaths
    from showrunner.scene_render import _render_beat, plan_beats

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
    if scene is None:
        err_console.print(f"[red]Scene '{target.scene_id}' not found.[/red]")
        raise typer.Exit(code=1)

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
    json_logs: bool = typer.Option(False, "--json", help="Output structured JSON logs"),
) -> None:
    """Render all beats in a scene."""
    _setup_logging(json_logs=json_logs)

    from showrunner.aiservices_client import AIServicesClient
    from showrunner.loader import EpisodeLoader
    from showrunner.paths import RunPaths
    from showrunner.progress import RichRenderProgress
    from showrunner.scene_render import plan_beats, render_scene

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

    with RichRenderProgress(console=console) as on_progress:
        report = render_scene(
            scene,
            scene_jobs,
            client,
            manifest,
            episode,
            max_workers=max_workers,
            progress_callback=on_progress,
        )

    console.print(f"Scene {scene_id}: [green]{report.completed}[/green]/{report.total_beats} done")
    if report.errors:
        for err in report.errors:
            err_console.print(f"  [red]{err}[/red]")


@render_app.command("episode")
def render_episode_cmd(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    max_workers: int = typer.Option(1, "--workers", "-w", help="Parallel workers"),
    json_logs: bool = typer.Option(False, "--json", help="Output structured JSON logs"),
    buffer: int | None = typer.Option(
        None, "--buffer", "-b", help="Buffer N beats ahead (default: sequential)"
    ),
) -> None:
    """Render all beats in an episode."""
    _setup_logging(json_logs=json_logs)

    from showrunner.aiservices_client import AIServicesClient
    from showrunner.loader import EpisodeLoader
    from showrunner.paths import RunPaths
    from showrunner.progress import RichRenderProgress
    from showrunner.render_buffer import render_episode_buffered
    from showrunner.scene_render import plan_beats, render_episode

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
            + (f" (buffer={buffer})" if buffer else "")
        )
    )

    if buffer:
        reports = render_episode_buffered(
            episode,
            manifest,
            paths,
            client,
            buffer_size=buffer,
            max_workers=max(4, buffer + 1),
        )
    else:
        with RichRenderProgress(console=console) as on_progress:
            reports = render_episode(
                episode,
                manifest,
                paths,
                client,
                max_workers=max_workers,
                progress_callback=on_progress,
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

    from showrunner.assembler import (
        burn_in_captions,
        concat_clips,
        generate_srt,
    )
    from showrunner.loader import EpisodeLoader
    from showrunner.paths import RunPaths
    from showrunner.scene_render import plan_beats

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
            from showrunner.loader import BeatData

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
# E9.4: showcase
# ---------------------------------------------------------------------------


@app.command()
def showcase(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    scene: str = typer.Option("007", "--scene", help="Scene ID or 1-based index"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    run_id: str | None = typer.Option(None, "--run-id", help="Specific run ID"),
) -> None:
    """Extract a scene clip + thumbnail from a render run."""
    _setup_logging()

    from showrunner.assembler import concat_clips, extract_thumbnail
    from showrunner.loader import EpisodeLoader
    from showrunner.paths import RunPaths
    from showrunner.scene_render import plan_beats

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

    # Resolve scene: try as scene_id first, then as 1-based index
    target_scene = _find_scene(episode, scene)
    if target_scene is None:
        try:
            idx = int(scene) - 1
            if 0 <= idx < len(episode.scenes):
                target_scene = episode.scenes[idx]
            else:
                err_console.print(
                    f"[red]Scene index '{scene}' out of range (1-{len(episode.scenes)}).[/red]"
                )
                raise typer.Exit(code=1)
        except ValueError:
            err_console.print(f"[red]Scene '{scene}' not found.[/red]")
            raise typer.Exit(code=1)

    scene_id = target_scene.scene_id
    scene_jobs = [j for j in jobs if j.scene_id == scene_id]
    video_paths = [j.video_path for j in scene_jobs if j.video_path.exists()]

    if not video_paths:
        err_console.print(f"[red]No rendered clips found for scene '{scene_id}'.[/red]")
        raise typer.Exit(code=1)

    showcase_dir = paths.run_dir / "showcase"
    showcase_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        clip_path = showcase_dir / f"{scene_id}.mp4"
        progress.add_task(f"Concatenating scene {scene_id} clips...", total=None)
        concat_clips(video_paths, clip_path)

        thumb_path = showcase_dir / f"{scene_id}.jpg"
        progress.add_task("Extracting thumbnail...", total=None)
        extract_thumbnail(clip_path, thumb_path)

    console.print(f"\n[green]Showcase clip:[/green] {clip_path}")
    console.print(f"[green]Thumbnail:[/green] {thumb_path}")


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
            importlib.import_module(pkg)
            from importlib.metadata import version as _pkg_version

            ver = _pkg_version(pkg)
            checks.append((pkg, True, ver))
        except (ImportError, ModuleNotFoundError):
            checks.append((pkg, False, "not installed"))

    # Config files
    config_checks = [
        ("pyproject.toml", Path("pyproject.toml")),
        ("Episode schema", Path("schemas/episode_v2.schema.json")),
    ]
    for label, path in config_checks:
        ok = path.exists()
        checks.append((label, ok, str(path.resolve()) if ok else "not found"))

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
    from showrunner.cast_manifest import CastManifest, CharacterProfile

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
# E7.7: run (full pipeline)
# ---------------------------------------------------------------------------


@app.command()
def run(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    max_workers: int = typer.Option(1, "--workers", "-w", help="Parallel render workers"),
    skip_bootstrap: bool = typer.Option(
        False, "--skip-bootstrap", help="Skip bootstrap (character refs) step"
    ),
    skip_validate: bool = typer.Option(
        False, "--skip-validate", help="Skip schema validation step"
    ),
    burn_captions: bool = typer.Option(False, "--captions", help="Burn in captions"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Run full pipeline: validate plan bootstrap render assemble."""
    _setup_logging(verbose)

    from showrunner.aiservices_client import AIServicesClient
    from showrunner.assembler import burn_in_captions, concat_clips, generate_srt
    from showrunner.cast_manifest import CastManifest, CharacterProfile
    from showrunner.loader import BeatData, EpisodeLoader
    from showrunner.paths import RunPaths
    from showrunner.scene_render import BeatStatus, plan_beats, render_episode
    from showrunner.validator import EpisodeValidator

    ep_path = Path(episode_path)
    out = _resolve_output_dir(output_dir)

    # ------------------------------------------------------------------
    # Stage 1: Validate
    # ------------------------------------------------------------------
    if not skip_validate:
        validator = EpisodeValidator()
        errors = validator.validate_file(ep_path)
        if errors:
            for e in errors:
                err_console.print(f"  [red]Error:[/red] {e}")
            raise typer.Exit(code=1)
        console.print("[bold green]\u2713[/bold green]  Episode validated")
    else:
        console.print("[yellow]\u26a0[/yellow]  Validation skipped")

    # ------------------------------------------------------------------
    # Stage 2: Load + Plan
    # ------------------------------------------------------------------
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
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

        paths = RunPaths(out)
        jobs = plan_beats(episode, manifest, paths, episode_id=episode.title)

    total_beats = len(jobs)
    scene_count = len(episode.scenes)
    console.print(f"  [dim]{total_beats} beats across {scene_count} scenes[/dim]")

    # ------------------------------------------------------------------
    # Stage 3: Bootstrap
    # ------------------------------------------------------------------
    client = AIServicesClient()
    if not skip_bootstrap:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
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
                    except Exception:
                        pass
                progress.advance(task)

            env_task = progress.add_task(
                "Bootstrapping environment refs...", total=len(episode.environments)
            )
            for env_name in episode.environments:
                progress.advance(env_task)

        console.print("[bold green]\u2713[/bold green]  Bootstrap complete")
    else:
        console.print("[yellow]\u26a0[/yellow]  Bootstrap skipped")

    # ------------------------------------------------------------------
    # Stage 4: Render
    # ------------------------------------------------------------------
    console.print(f"\n[bold]Rendering[/bold] {episode.title}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Rendering scenes...", total=total_beats)

        def _progress_callback(_report):
            progress.update(task, advance=0)

        reports = render_episode(
            episode,
            manifest,
            paths,
            client,
            max_workers=max_workers,
            jobs=jobs,
        )

        total_done = sum(r.completed for r in reports)
        total_failed = sum(r.failed for r in reports)
        progress.update(task, completed=total_done + total_failed)

    console.print(
        f"[bold green]\u2713[/bold green]  Rendered [green]{total_done}[/green]/{total_beats} beats"
    )
    if total_failed:
        err_console.print(f"  [red]{total_failed} beats failed[/red]")

    # ------------------------------------------------------------------
    # Stage 5: Assemble
    # ------------------------------------------------------------------
    video_paths: list[Path] = []
    beat_durations: list[tuple] = []
    for job in jobs:
        if job.status == BeatStatus.DONE:
            video_paths.append(job.video_path)
            beat = BeatData(
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

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
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


if __name__ == "__main__":
    app()
