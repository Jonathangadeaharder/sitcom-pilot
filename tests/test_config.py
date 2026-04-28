"""Tests for sitcom_pilot.config — PipelineConfig."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from sitcom_pilot.config import PipelineConfig


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


def test_default_providers():
    cfg = PipelineConfig()
    assert cfg.image_provider == "mlx-flux"
    assert cfg.video_provider == "mlx-ltx"
    assert cfg.tts_provider == "mlx-audio"
    assert cfg.asr_provider is None


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


def test_env_override_image_provider():
    with patch.dict(os.environ, {"SITCOM_IMAGE_PROVIDER": "comfyui-flux"}):
        cfg = PipelineConfig()
        assert cfg.image_provider == "comfyui-flux"
