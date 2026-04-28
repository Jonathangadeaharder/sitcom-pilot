import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from sitcom_pilot.assembler import EpisodeAssembler


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


def test_concatenate_command_structure(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assembler.concatenate([Path("/a/shot1.mp4")], output)
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert cmd[1] == "-y"
        assert cmd[2] == "-f"
        assert cmd[3] == "concat"
        assert cmd[4] == "-safe"
        assert cmd[5] == "0"
        assert cmd[6] == "-i"
        assert cmd[8] == "-c:v"
        assert cmd[10] == "-pix_fmt"
        assert cmd[11] == "yuv420p"
        assert cmd[12] == "-c:a"
        assert cmd[13] == "aac"
        assert cmd[14] == "-movflags"
        assert cmd[15] == "+faststart"
        assert cmd[16] == str(output)


def test_concatenate_subprocess_kwargs(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assembler.concatenate([Path("/a/shot1.mp4")], output)
        kwargs = mock_run.call_args.kwargs
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["timeout"] == 300


def test_concatenate_negative_returncode_returns_false(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=-1)
        result = assembler.concatenate([Path("/a/shot1.mp4")], output)
        assert result is False


def test_concatenate_uses_video_codec(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assembler.concatenate([Path("/a/shot1.mp4")], output)
        cmd = mock_run.call_args[0][0]
        assert assembler._video_codec in cmd


def test_init_creates_nested_output_dir(tmp_path):
    deep_dir = tmp_path / "a" / "b" / "c" / "output"
    with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=False):
        assembler = EpisodeAssembler(output_dir=deep_dir)
    assert deep_dir.exists()


def test_init_creates_existing_dir_without_error(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=False):
        assembler = EpisodeAssembler(output_dir=output)


def test_init_video_codec_when_videotoolbox_available(tmp_path):
    with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=True):
        assembler = EpisodeAssembler(output_dir=tmp_path / "out")
        assert assembler._video_codec == "h264_videotoolbox"


def test_init_video_codec_when_videotoolbox_unavailable(tmp_path):
    with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=False):
        assembler = EpisodeAssembler(output_dir=tmp_path / "out")
        assert assembler._video_codec == "libx264"
