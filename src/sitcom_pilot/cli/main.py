from __future__ import annotations

import typer
from pathlib import Path
from sitcom_pilot.config import PipelineConfig
from sitcom_pilot.loader import EpisodeLoader
from sitcom_pilot.validator import EpisodeValidator

app = typer.Typer(help="Sitcom Pilot CLI")


@app.command()
def validate(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    strict: bool = typer.Option(False, help="Enable strict validation"),
) -> None:
    """Validate an episode JSON file."""
    validator = EpisodeValidator()
    errors = validator.validate_file(Path(episode_path), strict=strict)
    if errors:
        for error in errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Episode is valid!")


@app.command()
def run(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    config_file: str = typer.Option(None, help="Path to config file"),
) -> None:
    """Run the sitcom pilot pipeline."""
    typer.echo(f"Running pipeline for {episode_path}")
    # Implementation here
    pass


if __name__ == "__main__":
    app()
