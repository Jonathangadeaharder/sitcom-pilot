from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from showrunner.assembler import (
    EpisodeAssembler,
    _fmt_srt_time,
    _run,
    concat_clips,
    extract_thumbnail,
    uniformize_clip,
)


class TestFmtSrtTime:
    def test_zero(self):
        assert _fmt_srt_time(0.0) == "00:00:00,000"

    def test_seconds_only(self):
        assert _fmt_srt_time(3.5) == "00:00:03,500"

    def test_minutes(self):
        assert _fmt_srt_time(125.0) == "00:02:05,000"

    def test_hours(self):
        assert _fmt_srt_time(3661.789) == "01:01:01,789"


class TestRun:
    def test_success_returns_completed_process(self):
        with patch("showrunner.assembler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _run(["echo", "hello"])
            assert result.returncode == 0

    def test_failure_raises_runtime_error(self):
        with patch("showrunner.assembler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
            with pytest.raises(RuntimeError, match="ffmpeg failed"):
                _run(["ffmpeg"])


class TestUniformizeClipEdgeCases:
    def test_custom_dimensions(self, tmp_path):
        with patch("showrunner.assembler._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            inp = tmp_path / "in.mp4"
            inp.write_bytes(b"f")
            out = tmp_path / "out.mp4"
            uniformize_clip(inp, out, width=640, height=480, fps=24)
            cmd = " ".join(mock_run.call_args[0][0])
            assert "640:480" in cmd
            assert "24" in cmd


class TestExtractThumbnailEdgeCases:
    def test_custom_timestamp(self, tmp_path):
        with patch("showrunner.assembler._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            out = tmp_path / "thumb.jpg"
            extract_thumbnail(tmp_path / "v.mp4", out, timestamp=5.5)
            cmd = " ".join(mock_run.call_args[0][0])
            assert "5.5" in cmd


class TestConcatClipsEdgeCases:
    def test_single_clip(self, tmp_path):
        captured = {}

        def grab_list_path(cmd, **kwargs):
            captured["content"] = Path(cmd[7]).read_text()
            return MagicMock(returncode=0)

        with patch("showrunner.assembler._run", side_effect=grab_list_path):
            out = tmp_path / "final.mp4"
            concat_clips([Path("/a/1.mp4")], out)
            assert "/a/1.mp4" in captured["content"]


class TestEpisodeAssemblerEdgeCases:
    def test_concatenate_empty_clips_returns_false(self, tmp_path):
        with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=False):
            assembler = EpisodeAssembler(output_dir=tmp_path / "out")
            result = assembler.concatenate([], tmp_path / "out.mp4")
            assert result is False

    def test_detect_videotoolbox_file_not_found(self):
        with patch("showrunner.assembler.subprocess.run", side_effect=FileNotFoundError):
            result = EpisodeAssembler._detect_videotoolbox()
            assert result is False

    def test_detect_videotoolbox_subprocess_error(self):
        with patch("showrunner.assembler.subprocess.run", side_effect=subprocess.SubprocessError):
            result = EpisodeAssembler._detect_videotoolbox()
            assert result is False
