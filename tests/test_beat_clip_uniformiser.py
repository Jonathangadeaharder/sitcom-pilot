from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from showrunner.beat_clip_uniformiser import (
    BeatClipUniformiser,
    UniformiserConfig,
)
from showrunner.loader import BeatData
from showrunner.paths import RunPaths


@pytest.fixture
def mock_run():
    with patch("showrunner.beat_clip_uniformiser._run") as mock:
        mock.return_value = MagicMock(returncode=0)
        yield mock


@pytest.fixture
def config():
    return UniformiserConfig(
        width=1920,
        height=1080,
        fps=24,
        video_codec="libx265",
        audio_codec="aac",
        audio_sample_rate=48000,
        pix_fmt="yuv420p",
    )


class TestUniformiserConfig:
    def test_default_values(self):
        cfg = UniformiserConfig()
        assert cfg.width == 1280
        assert cfg.height == 720
        assert cfg.fps == 16
        assert cfg.video_codec == "libx264"
        assert cfg.audio_codec == "aac"
        assert cfg.audio_sample_rate == 44100
        assert cfg.pix_fmt == "yuv420p"
        assert cfg.video_bitrate == ""
        assert cfg.audio_bitrate == "128k"

    def test_custom_values(self, config):
        assert config.width == 1920
        assert config.height == 1080
        assert config.fps == 24
        assert config.video_codec == "libx265"


class TestBeatClipUniformiser:
    def test_uniformise_runs_ffmpeg(self, mock_run, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "out.mp4"
        uniformiser = BeatClipUniformiser()
        result = uniformiser.uniformise(inp, out)
        assert result == out
        mock_run.assert_called_once()

    def test_uniformise_creates_dirs(self, mock_run, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "deep" / "nested" / "out.mp4"
        uniformiser = BeatClipUniformiser()
        uniformiser.uniformise(inp, out)
        assert out.parent.exists()

    def test_uniformise_builds_correct_cmd(self, mock_run, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "out.mp4"
        cfg = UniformiserConfig(
            width=640,
            height=480,
            fps=12,
            video_codec="libx264rgb",
        )
        uniformiser = BeatClipUniformiser(cfg)
        uniformiser.uniformise(inp, out)
        cmd = mock_run.call_args[0][0]
        assert "-s" in cmd
        s_idx = cmd.index("-s")
        assert cmd[s_idx + 1] == "640x480"
        assert "-r" in cmd
        r_idx = cmd.index("-r")
        assert cmd[r_idx + 1] == "12"
        assert cmd[cmd.index("-c:v") + 1] == "libx264rgb"

    def test_uniformise_includes_audio_when_present(self, mock_run, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "out.mp4"
        uniformiser = BeatClipUniformiser()
        uniformiser.uniformise(inp, out)
        cmd = mock_run.call_args[0][0]
        assert "-c:a" in cmd
        assert cmd[cmd.index("-c:a") + 1] == "aac"
        assert "-ar" in cmd
        ar_idx = cmd.index("-ar")
        assert cmd[ar_idx + 1] == "44100"

    def test_uniformise_with_bitrates(self, mock_run, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "out.mp4"
        cfg = UniformiserConfig(video_bitrate="2M", audio_bitrate="192k")
        uniformiser = BeatClipUniformiser(cfg)
        uniformiser.uniformise(inp, out)
        cmd = mock_run.call_args[0][0]
        assert "-b:v" in cmd
        assert cmd[cmd.index("-b:v") + 1] == "2M"
        assert "-b:a" in cmd
        assert cmd[cmd.index("-b:a") + 1] == "192k"

    def test_uniformise_without_bitrates_omits_bv_ba(self, mock_run, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "out.mp4"
        cfg = UniformiserConfig(video_bitrate="", audio_bitrate="")
        uniformiser = BeatClipUniformiser(cfg)
        uniformiser.uniformise(inp, out)
        cmd = mock_run.call_args[0][0]
        assert "-b:v" not in cmd
        assert "-b:a" not in cmd

    def test_uniformise_no_pix_fmt_when_empty(self, mock_run, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "out.mp4"
        cfg = UniformiserConfig(pix_fmt="")
        uniformiser = BeatClipUniformiser(cfg)
        uniformiser.uniformise(inp, out)
        cmd = mock_run.call_args[0][0]
        assert "-pix_fmt" not in cmd

    def test_uniformise_ffmpeg_failure(self, mock_run, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "out.mp4"
        from showrunner.beat_clip_uniformiser import _RunError

        mock_run.side_effect = _RunError("ffmpeg failed")
        uniformiser = BeatClipUniformiser()
        with pytest.raises(_RunError, match="ffmpeg failed"):
            uniformiser.uniformise(inp, out)

    def test_uniformise_beat_with_paths(self, mock_run, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        scene_id = "s001"
        beat_id = "s001_b001"
        paths.ensure_scene_dirs(scene_id)
        inp = paths.beat_video(scene_id, beat_id)
        inp.write_bytes(b"f")
        uniformiser = BeatClipUniformiser()
        result = uniformiser.uniformise_beat(inp, paths, scene_id, beat_id)
        expected = paths.beats_dir / scene_id / f"{beat_id}.uniformised.mp4"
        assert result == expected
        mock_run.assert_called_once()

    def test_uniformise_beats_batch(self, mock_run, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        beat_data_list = [
            BeatData(beat_id="b1", kind="speech", text="Hi"),
            BeatData(beat_id="b2", kind="silent"),
            BeatData(beat_id="b3", kind="speech", text="Bye"),
        ]
        for bd in beat_data_list:
            paths.ensure_scene_dirs("s001")
            inp = paths.beat_video("s001", bd.beat_id)
            inp.write_bytes(b"f")

        uniformiser = BeatClipUniformiser()
        results = uniformiser.uniformise_beats(beat_data_list, paths, scene_id="s001")
        assert len(results) == 3
        for r in results:
            assert ".uniformised" in r.name
        assert mock_run.call_count == 3

    def test_uniformise_beats_missing_video_skipped(self, mock_run, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        beat = BeatData(beat_id="missing", kind="silent")
        uniformiser = BeatClipUniformiser()

        result = uniformiser.uniformise_beats([beat], paths, scene_id="s001")
        assert len(result) == 0
        mock_run.assert_not_called()

    def test_uniformise_beats_empty(self, mock_run, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        uniformiser = BeatClipUniformiser()
        result = uniformiser.uniformise_beats([], paths, scene_id="s001")
        assert result == []
        mock_run.assert_not_called()
