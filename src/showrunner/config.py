from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

_DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"


class PipelineConfig(BaseSettings):
    """Runtime configuration for the Sitcom Pilot pipeline.

    Values are read (in priority order) from:
    1. Environment variables prefixed with ``SITCOM_``
    2. A ``.env`` file in the working directory
    3. The defaults defined below
    """

    model_config = SettingsConfigDict(
        env_prefix="SITCOM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    comfyui_url: str = Field(
        default=_DEFAULT_COMFYUI_URL,
        description="Base URL of the running ComfyUI server.",
    )

    output_dir: Path = Field(
        default=Path("output"),
        description="Root directory for all pipeline output artefacts.",
    )
    run_id: str = Field(
        default="",
        description="Unique identifier for this run (auto-generated if empty).",
    )

    cooldown_seconds: float = Field(
        default=0.0,
        description="Pause between consecutive shots (seconds).",
    )
    max_crash_retries: int = Field(
        default=3,
        description="Number of times to retry a shot after a ComfyUI crash.",
    )

    image_provider: str = Field(default="mlx-flux")
    video_provider: str = Field(default="mlx-ltx")
    tts_provider: str = Field(default="mlx-audio")
    asr_provider: str | None = Field(default=None)
