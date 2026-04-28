from __future__ import annotations

from pathlib import Path

import typer

from sitcom_pilot.validator import EpisodeValidator

app = typer.Typer(help="Sitcom Pilot CLI")


@app.command()
def validate(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
) -> None:
    """Validate an episode JSON file."""
    validator = EpisodeValidator()
    errors = validator.validate_file(Path(episode_path))
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
    typer.echo(
        "The 'run' command is not yet implemented. "
        "Use the legacy scripts in legacy/ for now.",
        err=True,
    )
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
