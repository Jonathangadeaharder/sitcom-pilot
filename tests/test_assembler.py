import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from orchestrator.assembler import EpisodeAssembler


@pytest.fixture
def assembler(tmp_path):
    return EpisodeAssembler(output_dir=tmp_path / "output")


def test_write_concat_list_creates_file(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    clips = [Path("/a/shot1.mp4"), Path("/a/shot2.mp4"), Path("/a/shot3.mp4")]
    concat_file = assembler._write_concat_list(clips)
    assert concat_file.exists()
    content = concat_file.read_text()
    assert "shot1.mp4" in content
    assert "shot2.mp4" in content
    assert "shot3.mp4" in content


def test_concatenate_runs_ffmpeg(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assembler.concatenate([Path("/a/shot1.mp4")], output)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd[0]
        assert "-f" in cmd
        assert "concat" in cmd


def test_concatenate_returns_true_on_success(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = assembler.concatenate([Path("/a/shot1.mp4")], output)
        assert result is True


def test_concatenate_returns_false_on_failure(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = assembler.concatenate([Path("/a/shot1.mp4")], output)
        assert result is False


def test_concatenate_empty_clips_returns_false(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"
    result = assembler.concatenate([], output)
    assert result is False


def test_detect_video_toolbox():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="h264_videotoolbox\nlibx264\n")
        assert EpisodeAssembler._detect_videotoolbox() is True


def test_detect_no_video_toolbox():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="libx264\n")
        assert EpisodeAssembler._detect_videotoolbox() is False


def test_uses_video_toolbox_when_available(assembler):
    assert assembler._video_codec == "h264_videotoolbox"


def test_detect_videotoolbox_exception_returns_false():
    with patch("subprocess.run", side_effect=FileNotFoundError("no ffmpeg")):
        assert EpisodeAssembler._detect_videotoolbox() is False


def test_concatenate_exception_returns_false(tmp_path):
    assembler = EpisodeAssembler(output_dir=tmp_path / "output")
    output = assembler.output_dir / "final.mp4"
    clip = tmp_path / "shot.mp4"
    clip.write_bytes(b"\x00")
    with patch("subprocess.run", side_effect=TimeoutError("ffmpeg hung")):
        result = assembler.concatenate([clip], output)
        assert result is False
