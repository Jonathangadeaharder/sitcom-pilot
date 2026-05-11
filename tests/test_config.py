"""Tests for showrunner.config — PipelineConfig."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from showrunner.config import PipelineConfig


def test_default_comfyui_url():
    cfg = PipelineConfig()
    assert cfg.comfyui_url == "http://127.0.0.1:8188"


def test_default_output_dir():
    cfg = PipelineConfig()
    assert cfg.output_dir == Path("output")


def test_default_cooldown_is_zero():
    cfg = PipelineConfig()
    assert cfg.cooldown_seconds == 0.0


def test_default_max_crash_retries():
    cfg = PipelineConfig()
    assert cfg.max_crash_retries == 3


def test_env_override_comfyui_url():
    with patch.dict(os.environ, {"SITCOM_COMFYUI_URL": "http://192.168.1.10:8188"}):
        cfg = PipelineConfig()
        assert cfg.comfyui_url == "http://192.168.1.10:8188"


def test_env_override_output_dir():
    with patch.dict(os.environ, {"SITCOM_OUTPUT_DIR": "/tmp/sitcom_out"}):
        cfg = PipelineConfig()
        assert cfg.output_dir == Path("/tmp/sitcom_out")


def test_env_override_cooldown():
    with patch.dict(os.environ, {"SITCOM_COOLDOWN_SECONDS": "2.5"}):
        cfg = PipelineConfig()
        assert cfg.cooldown_seconds == 2.5


def test_env_override_max_retries():
    with patch.dict(os.environ, {"SITCOM_MAX_CRASH_RETRIES": "5"}):
        cfg = PipelineConfig()
        assert cfg.max_crash_retries == 5


# ---------------------------------------------------------------------------
# Fallback PipelineConfig (when pydantic-settings unavailable)
# ---------------------------------------------------------------------------


class TestFallbackPipelineConfig:
    def test_fallback_defaults(self):
        import importlib
        import sys
        from unittest.mock import patch

        saved = sys.modules.pop("showrunner.config", None)
        try:
            with patch.dict(sys.modules, {"pydantic_settings": None, "pydantic": None}):
                import showrunner.config as cfg_mod

                importlib.reload(cfg_mod)
                cfg = cfg_mod.PipelineConfig()
                assert cfg.comfyui_url == "http://127.0.0.1:8188"
                assert cfg.output_dir == Path("output")
                assert cfg.cooldown_seconds == 0.0
                assert cfg.max_crash_retries == 3
        finally:
            if saved is not None:
                sys.modules["showrunner.config"] = saved
                importlib.reload(sys.modules["showrunner.config"])

    def test_fallback_from_env(self):
        import importlib
        import sys
        from unittest.mock import patch

        saved = sys.modules.pop("showrunner.config", None)
        try:
            with patch.dict(sys.modules, {"pydantic_settings": None, "pydantic": None}):
                import showrunner.config as cfg_mod

                importlib.reload(cfg_mod)
                env = {
                    "SITCOM_COMFYUI_URL": "http://192.168.1.50:8188",
                    "SITCOM_OUTPUT_DIR": "/tmp/fallback_out",
                    "SITCOM_RUN_ID": "test-run-42",
                    "SITCOM_COOLDOWN_SECONDS": "1.5",
                    "SITCOM_MAX_CRASH_RETRIES": "5",
                }
                with patch.dict(os.environ, env, clear=False):
                    cfg = cfg_mod.PipelineConfig.from_env()
                    assert cfg.comfyui_url == "http://192.168.1.50:8188"
                    assert cfg.output_dir == Path("/tmp/fallback_out")
                    assert cfg.run_id == "test-run-42"
                    assert cfg.cooldown_seconds == 1.5
                    assert cfg.max_crash_retries == 5
        finally:
            if saved is not None:
                sys.modules["showrunner.config"] = saved
                importlib.reload(sys.modules["showrunner.config"])
