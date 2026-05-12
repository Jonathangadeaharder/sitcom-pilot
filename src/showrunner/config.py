from __future__ import annotations

from pathlib import Path

try:
    from pydantic import Field  # pyright: ignore[reportPossiblyUnboundVariable]
    from pydantic_settings import (  # pyright: ignore[reportPossiblyUnboundVariable]
        BaseSettings,
        SettingsConfigDict,
    )

    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False

import os

if _PYDANTIC_AVAILABLE:

    class PipelineConfig(BaseSettings):  # pyright: ignore[reportPossiblyUnboundVariable, reportRedeclaration]
        """Runtime configuration for the Sitcom Pilot pipeline.

        Values are read (in priority order) from:
        1. Environment variables prefixed with ``SITCOM_``
        2. A ``.env`` file in the working directory
        3. The defaults defined below
        """

        model_config = SettingsConfigDict(  # pyright: ignore[reportPossiblyUnboundVariable]
            env_prefix="SITCOM_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        comfyui_url: str = Field(default="http://127.0.0.1:8188")  # pyright: ignore[reportPossiblyUnboundVariable]

        output_dir: Path = Field(default=Path("output"))  # pyright: ignore[reportPossiblyUnboundVariable]
        run_id: str = Field(default="")  # pyright: ignore[reportPossiblyUnboundVariable]

        # Render
        cooldown_seconds: float = Field(default=0.0)  # pyright: ignore[reportPossiblyUnboundVariable]
        max_crash_retries: int = Field(default=3)  # pyright: ignore[reportPossiblyUnboundVariable]


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
            )
