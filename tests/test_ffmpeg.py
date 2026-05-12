from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from showrunner.assembler import (
    _fmt_srt_time,
    generate_srt,
    uniformize_clip,
)
from showrunner.assembler import (
    _run as _assembler_run,
)
from showrunner.beat_clip_uniformiser import BeatClipUniformiser, UniformiserConfig
from showrunner.beat_clip_uniformiser import _run as _uniformiser_run
from showrunner.loader import BeatData


class TestFmtSrtTime:
    def test_zero(self):
        assert _fmt_srt_time(0.0) == "00:00:00,000"

    def test_seconds_only(self):
        assert _fmt_srt_time(3.5) == "00:00:03,500"

    def test_minutes(self):
        assert _fmt_srt_time(65.0) == "00:01:05,000"

    def test_hours(self):
        assert _fmt_srt_time(3601.0) == "01:00:01,000"

    def test_milliseconds(self):
        assert _fmt_srt_time(1.123) == "00:00:01,123"

    def test_sub_millisecond(self):
        assert _fmt_srt_time(1.001) in ("00:00:01,000", "00:00:01,001")

    def test_large_hours(self):
        assert _fmt_srt_time(10000.0) == "02:46:40,000"

    def test_negative_seconds(self):
        assert _fmt_srt_time(-1.0) == "-1:59:59,000"


class TestRun:
    def test_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = _assembler_run(["ffmpeg", "-version"])
            assert result.returncode == 0

    def test_failure_raises(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
            with pytest.raises(RuntimeError, match="ffmpeg failed"):
                _assembler_run(["ffmpeg", "-i", "in.mp4"])

    def test_includes_stderr_in_error(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Invalid data found")
            with pytest.raises(RuntimeError) as exc:
                _assembler_run(["ffmpeg", "input"])
            assert "Invalid data found" in str(exc.value)

    def test_includes_stdout_in_error(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="Some output", stderr="")
            with pytest.raises(RuntimeError) as exc:
                _assembler_run(["ffmpeg", "input"])
            assert "Some output" in str(exc.value)

    def test_includes_full_command_in_error(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            with pytest.raises(RuntimeError) as exc:
                _assembler_run(["ffmpeg", "-i", "input.mp4", "output.mp4"])
            assert "-i input.mp4 output.mp4" in str(exc.value)

    def test_timeout_propagates(self):
        with patch("subprocess.run", side_effect=TimeoutError("timeout")):
            with pytest.raises(TimeoutError):
                _assembler_run(["ffmpeg", "-i", "in.mp4"])

    def test_long_output_truncated_in_error(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="x" * 5000, stderr="")
            with pytest.raises(RuntimeError) as exc:
                _assembler_run(["ffmpeg", "input"])
            msg = str(exc.value)
            assert len(msg) < 3000


class TestUniformizeClip:
    def test_default_args(self, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"data")
        out = tmp_path / "out.mp4"
        with patch("showrunner.assembler._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            uniformize_clip(inp, out)
            cmd_str = " ".join(mock_run.call_args[0][0])
        assert "-vf" in cmd_str
        assert "scale=1280:720" in cmd_str
        assert "-r" in cmd_str
        assert "16" in cmd_str
        assert "-c:v" in cmd_str
        assert "libx264" in cmd_str

    def test_custom_size(self, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"data")
        out = tmp_path / "out.mp4"
        with patch("showrunner.assembler._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            uniformize_clip(inp, out, width=640, height=480, fps=24)
            cmd_str = " ".join(mock_run.call_args[0][0])
        assert "scale=640:480" in cmd_str
        assert "24" in cmd_str

    def test_creates_output_dir(self, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"data")
        out = tmp_path / "deep" / "nested" / "out.mp4"
        with patch("showrunner.assembler._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            uniformize_clip(inp, out)
        assert out.parent.exists()


class TestGenerateSrtEdgeCases:
    def test_empty_beats(self, tmp_path):
        out = tmp_path / "subs.srt"
        generate_srt([], out)
        assert out.read_text() == ""

    def test_all_silent_beats(self, tmp_path):
        beats = [
            (BeatData(beat_id="b1", kind="silent", duration_sec=2.0), 2.0),
            (BeatData(beat_id="b2", kind="silent", duration_sec=3.0), 3.0),
        ]
        out = tmp_path / "subs.srt"
        generate_srt(beats, out)
        assert out.read_text() == ""

    def test_mixed_speech_silent(self, tmp_path):
        beats = [
            (
                BeatData(
                    beat_id="b1", kind="speech", speaker="Maya", text="Hello", duration_sec=2.0
                ),
                2.0,
            ),
            (BeatData(beat_id="b2", kind="silent", duration_sec=1.0), 1.0),
            (
                BeatData(beat_id="b3", kind="speech", speaker="Derek", text="Hi", duration_sec=2.0),
                2.0,
            ),
        ]
        out = tmp_path / "subs.srt"
        generate_srt(beats, out)
        content = out.read_text()
        assert "Maya: Hello" in content
        assert "Derek: Hi" in content
        assert content.count("-->") == 2

    def test_speech_without_speaker(self, tmp_path):
        beats = [
            (BeatData(beat_id="b1", kind="speech", text="Hello", duration_sec=2.0), 2.0),
        ]
        out = tmp_path / "subs.srt"
        generate_srt(beats, out)
        content = out.read_text()
        assert "Hello" in content
        assert ": Hello" not in content

    def test_timing_accumulates(self, tmp_path):
        beats = [
            (BeatData(beat_id="b1", kind="speech", text="A", duration_sec=2.5), 2.5),
            (BeatData(beat_id="b2", kind="speech", text="B", duration_sec=1.5), 1.5),
        ]
        out = tmp_path / "subs.srt"
        generate_srt(beats, out)
        content = out.read_text()
        assert "00:00:00,000 --> 00:00:02,500" in content
        assert "00:00:02,500 --> 00:00:04,000" in content


class TestUniformiserConfig:
    def test_defaults(self):
        c = UniformiserConfig()
        assert c.width == 1280
        assert c.height == 720
        assert c.fps == 16
        assert c.video_codec == "libx264"
        assert c.audio_codec == "aac"
        assert c.audio_sample_rate == 44100
        assert c.pix_fmt == "yuv420p"
        assert c.video_bitrate == ""
        assert c.audio_bitrate == "128k"

    def test_custom(self):
        c = UniformiserConfig(width=640, height=480, fps=24, video_bitrate="1M", pix_fmt="yuv422p")
        assert c.width == 640
        assert c.video_bitrate == "1M"
        assert c.pix_fmt == "yuv422p"


class TestBeatClipUniformiser:
    def test_default_config(self):
        u = BeatClipUniformiser()
        assert u.config.fps == 16

    def test_custom_config(self):
        c = UniformiserConfig(fps=24, video_bitrate="2M")
        u = BeatClipUniformiser(config=c)
        assert u.config.fps == 24
        assert u.config.video_bitrate == "2M"

    def test_build_cmd_defaults(self, tmp_path):
        u = BeatClipUniformiser()
        inp = tmp_path / "in.mp4"
        out = tmp_path / "out.mp4"
        cmd = u._build_cmd(inp, out)
        assert cmd[0] == "ffmpeg"
        assert cmd[1] == "-y"
        assert cmd[2] == "-i"
        assert cmd[3] == str(inp)
        assert cmd[4] == "-s"
        assert cmd[5] == "1280x720"
        assert cmd[6] == "-r"
        assert cmd[7] == "16"
        assert cmd[8] == "-c:v"
        assert cmd[9] == "libx264"
        assert "-pix_fmt" in cmd
        assert "yuv420p" in cmd
        assert "-c:a" in cmd
        assert "aac" in cmd
        assert "-b:a" in cmd
        assert "128k" in cmd
        assert "-ar" in cmd
        assert "44100" in cmd
        assert cmd[-1] == str(out)

    def test_build_cmd_with_bitrate(self, tmp_path):
        c = UniformiserConfig(video_bitrate="2M", audio_bitrate="256k")
        u = BeatClipUniformiser(config=c)
        inp = tmp_path / "in.mp4"
        out = tmp_path / "out.mp4"
        cmd = u._build_cmd(inp, out)
        assert "-b:v" in cmd
        assert "2M" in cmd
        assert "-b:a" in cmd
        assert "256k" in cmd

    def test_build_cmd_empty_video_bitrate(self, tmp_path):
        c = UniformiserConfig(video_bitrate="")
        u = BeatClipUniformiser(config=c)
        inp = tmp_path / "in.mp4"
        out = tmp_path / "out.mp4"
        cmd = u._build_cmd(inp, out)
        assert "-b:v" not in cmd

    def test_build_cmd_empty_pix_fmt(self, tmp_path):
        c = UniformiserConfig(pix_fmt="")
        u = BeatClipUniformiser(config=c)
        inp = tmp_path / "in.mp4"
        out = tmp_path / "out.mp4"
        cmd = u._build_cmd(inp, out)
        assert "-pix_fmt" not in cmd

    def test_uniformise_missing_beat_returns_none(self, tmp_path):
        u = BeatClipUniformiser()
        result = u.uniformise_beat(
            video_path=tmp_path / "nonexistent.mp4",
            paths=MagicMock(),
            scene_id="001",
            beat_id="b1",
        )
        assert result is None

    def test_uniformise_creates_output(self, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"data")
        out = tmp_path / "out.mp4"
        u = BeatClipUniformiser()
        with patch("showrunner.beat_clip_uniformiser._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = u.uniformise(inp, out)
        assert result == out

    def test_uniformise_ffmpeg_error_raises(self, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"data")
        out = tmp_path / "out.mp4"
        u = BeatClipUniformiser()
        with patch("showrunner.beat_clip_uniformiser._run") as mock_run:
            mock_run.side_effect = RuntimeError("ffmpeg failed (rc=1)")
            with pytest.raises(RuntimeError, match="ffmpeg failed"):
                u.uniformise(inp, out)

    def test_uniformiser_run_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = _uniformiser_run(["ffmpeg", "-version"])
            assert result.returncode == 0

    def test_uniformiser_run_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            with pytest.raises(RuntimeError, match="ffmpeg failed"):
                _uniformiser_run(["ffmpeg", "input"])

    def test_uniformiser_creates_parent_dirs(self, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"data")
        out = tmp_path / "deep" / "nested" / "out.mp4"
        u = BeatClipUniformiser()
        with patch("showrunner.beat_clip_uniformiser._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            u.uniformise(inp, out)
        assert out.parent.exists()

    def test_uniformise_beats_missing_skipped(self, tmp_path):
        u = BeatClipUniformiser()
        beats = [
            BeatData(beat_id="b1", kind="speech"),
            BeatData(beat_id="b2", kind="silent"),
        ]
        paths = MagicMock()
        paths.beat_video.return_value = tmp_path / "nonexistent.mp4"
        results = u.uniformise_beats(beats, paths, "001")
        assert results == []
