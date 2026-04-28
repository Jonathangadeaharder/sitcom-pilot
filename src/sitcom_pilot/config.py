from __future__ import annotations

from pathlib import Path

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False

import os

if _PYDANTIC_AVAILABLE:
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

        # ComfyUI
        comfyui_url: str = Field(
            default="http://127.0.0.1:8188",
            description="Base URL of the running ComfyUI server.",
        )

        # Output
        output_dir: Path = Field(
            default=Path("output"),
            description="Root directory for all pipeline output artefacts.",
        )
        run_id: str = Field(
            default="",
            description="Unique identifier for this run (auto-generated if empty).",
        )

        # Render
        cooldown_seconds: float = Field(
            default=0.0,
            description="Pause between consecutive shots (seconds).",
        )
        max_crash_retries: int = Field(
            default=3,
            description="Number of times to retry a shot after a ComfyUI crash.",
        )

        # Providers (override per episode via render block)
        image_provider: str = Field(default="mlx-flux")
        video_provider: str = Field(default="mlx-ltx")
        tts_provider: str = Field(default="mlx-audio")
        asr_provider: str | None = Field(default=None)

else:
    # Minimal fallback when pydantic-settings is not installed
    class PipelineConfig:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            defaults = {
                "comfyui_url": os.environ.get("SITCOM_COMFYUI_URL", "http://127.0.0.1:8188"),
                "output_dir": Path(os.environ.get("SITCOM_OUTPUT_DIR", "output")),
                "run_id": os.environ.get("SITCOM_RUN_ID", ""),
                "cooldown_seconds": float(os.environ.get("SITCOM_COOLDOWN_SECONDS", "0.0")),
                "max_crash_retries": int(os.environ.get("SITCOM_MAX_CRASH_RETRIES", "3")),
                "image_provider": os.environ.get("SITCOM_IMAGE_PROVIDER", "mlx-flux"),
                "video_provider": os.environ.get("SITCOM_VIDEO_PROVIDER", "mlx-ltx"),
                "tts_provider": os.environ.get("SITCOM_TTS_PROVIDER", "mlx-audio"),
                "asr_provider": os.environ.get("SITCOM_ASR_PROVIDER") or None,
            }
            for k, v in {**defaults, **kwargs}.items():
                setattr(self, k, v)

        @classmethod
        def from_env(cls) -> PipelineConfig:
            return cls(
                comfyui_url=os.environ.get("SITCOM_COMFYUI_URL", "http://127.0.0.1:8188"),
                output_dir=Path(os.environ.get("SITCOM_OUTPUT_DIR", "output")),
                run_id=os.environ.get("SITCOM_RUN_ID", ""),
                cooldown_seconds=float(os.environ.get("SITCOM_COOLDOWN_SECONDS", "0.0")),
                max_crash_retries=int(os.environ.get("SITCOM_MAX_CRASH_RETRIES", "3")),
                image_provider=os.environ.get("SITCOM_IMAGE_PROVIDER", "mlx-flux"),
                video_provider=os.environ.get("SITCOM_VIDEO_PROVIDER", "mlx-ltx"),
                tts_provider=os.environ.get("SITCOM_TTS_PROVIDER", "mlx-audio"),
                asr_provider=os.environ.get("SITCOM_ASR_PROVIDER") or None,
            )
