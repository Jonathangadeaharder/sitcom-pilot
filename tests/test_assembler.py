from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sitcom_pilot.assembler import (
    EpisodeAssembler,
    burn_in_captions,
    concat_clips,
    extract_thumbnail,
    generate_srt,
    mix_beat_audio,
    mix_music_bed,
    mux_audio,
    uniformize_clip,
)
from sitcom_pilot.loader import BeatData


@pytest.fixture
def mock_ffmpeg():
    with patch("sitcom_pilot.assembler._run") as mock:
        mock.return_value = MagicMock(returncode=0)
        yield mock


class TestUniformizeClip:
    def test_runs_ffmpeg(self, mock_ffmpeg, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "out.mp4"
        uniformize_clip(inp, out)
        mock_ffmpeg.assert_called_once()
        cmd = " ".join(mock_ffmpeg.call_args[0][0])
        assert "scale" in cmd

    def test_creates_dirs(self, mock_ffmpeg, tmp_path):
        inp = tmp_path / "in.mp4"
        inp.write_bytes(b"f")
        out = tmp_path / "deep" / "nested" / "out.mp4"
        uniformize_clip(inp, out)
        assert out.parent.exists()


class TestConcatClips:
    def test_concatenates(self, mock_ffmpeg, tmp_path):
        out = tmp_path / "final.mp4"
        result = concat_clips([Path("/a/1.mp4"), Path("/a/2.mp4")], out)
        assert result == out
        mock_ffmpeg.assert_called_once()

    def test_empty_raises(self, tmp_path):
        with pytest.raises(ValueError, match="No clips"):
            concat_clips([], tmp_path / "out.mp4")

    def test_escapes_special_chars_in_paths(self, tmp_path):
        tricky = [Path("/path/with'quote/file.mp4"), Path("/path\\back/file.mp4")]
        out = tmp_path / "out.mp4"
        captured = {}

        def grab_list_path(cmd, **kwargs):
            list_path = cmd[7]
            captured["content"] = Path(list_path).read_text()
            return MagicMock(returncode=0)

        with patch("sitcom_pilot.assembler._run", side_effect=grab_list_path):
            concat_clips(tricky, out)

        content = captured["content"]
        assert "\\\\" in content
        assert "\\'" in content


class TestMuxAudio:
    def test_muxes(self, mock_ffmpeg, tmp_path):
        out = tmp_path / "muxed.mp4"
        result = mux_audio(tmp_path / "v.mp4", tmp_path / "a.wav", out)
        assert result == out
        cmd = mock_ffmpeg.call_args[0][0]
        assert "-map" in cmd


class TestExtractThumbnail:
    def test_extracts(self, mock_ffmpeg, tmp_path):
        out = tmp_path / "thumb.jpg"
        result = extract_thumbnail(tmp_path / "v.mp4", out)
        assert result == out
        cmd = mock_ffmpeg.call_args[0][0]
        assert "-frames:v" in cmd


class TestGenerateSrt:
    def test_generates_srt(self, tmp_path):
        beats = [
            (
                BeatData(
                    beat_id="1", kind="speech", speaker="Maya", text="Hello!", duration_sec=3.0
                ),
                3.0,
            ),
            (BeatData(beat_id="2", kind="silent", duration_sec=2.0), 2.0),
            (
                BeatData(
                    beat_id="3", kind="speech", speaker="Derek", text="Hi there", duration_sec=2.5
                ),
                2.5,
            ),
        ]
        out = tmp_path / "subs.srt"
        generate_srt(beats, out)
        content = out.read_text()
        assert "1\n" in content
        assert "Maya: Hello!" in content
        assert "Derek: Hi there" in content
        assert "-->" in content

    def test_srt_timing(self, tmp_path):
        beats = [
            (BeatData(beat_id="1", kind="speech", text="First", duration_sec=3.0), 3.0),
            (BeatData(beat_id="2", kind="speech", text="Second", duration_sec=2.0), 2.0),
        ]
        out = tmp_path / "subs.srt"
        generate_srt(beats, out)
        content = out.read_text()
        assert "00:00:00,000 --> 00:00:03,000" in content
        assert "00:00:03,000 --> 00:00:05,000" in content

    def test_srt_newlines_sanitized(self, tmp_path):
        beats = [
            (
                BeatData(
                    beat_id="1",
                    kind="speech",
                    speaker="Maya",
                    text="Line one\nLine two\r\nLine three",
                    duration_sec=3.0,
                ),
                3.0,
            ),
        ]
        out = tmp_path / "subs.srt"
        generate_srt(beats, out)
        content = out.read_text(encoding="utf-8")
        assert "\nLine" not in content.split("Maya:")[1].split("\n\n")[0]
        assert "Line one" in content
        assert "Line three" in content

    def test_srt_utf8_encoding(self, tmp_path):
        beats = [
            (
                BeatData(
                    beat_id="1",
                    kind="speech",
                    text="Ünïcödé: ça va?",
                    duration_sec=2.0,
                ),
                2.0,
            ),
        ]
        out = tmp_path / "subs.srt"
        generate_srt(beats, out)
        content = out.read_text(encoding="utf-8")
        assert "Ünïcödé: ça va?" in content


class TestBurnInCaptions:
    def test_burns(self, mock_ffmpeg, tmp_path):
        out = tmp_path / "burned.mp4"
        burn_in_captions(tmp_path / "v.mp4", tmp_path / "s.srt", out)
        cmd = " ".join(mock_ffmpeg.call_args[0][0])
        assert "subtitles" in cmd


class TestMixMusicBed:
    def test_mixes(self, mock_ffmpeg, tmp_path):
        out = tmp_path / "mixed.mp4"
        mix_music_bed(tmp_path / "v.mp4", tmp_path / "music.mp3", out)
        cmd = " ".join(mock_ffmpeg.call_args[0][0])
        assert "amix" in cmd


class TestMixBeatAudio:
    def test_voice_only(self, mock_ffmpeg, tmp_path):
        out = tmp_path / "out.mp4"
        mix_beat_audio(tmp_path / "v.mp4", tmp_path / "voice.wav", output_path=out)
        cmd = " ".join(mock_ffmpeg.call_args[0][0])
        assert "-map" in cmd

    def test_with_music(self, mock_ffmpeg, tmp_path):
        out = tmp_path / "out.mp4"
        music = tmp_path / "music.mp3"
        music.write_bytes(b"f")
        mix_beat_audio(
            tmp_path / "v.mp4",
            tmp_path / "voice.wav",
            music_path=music,
            output_path=out,
        )
        cmd = " ".join(mock_ffmpeg.call_args[0][0])
        assert "amix" in cmd

    def test_default_output_does_not_overwrite_input(self, mock_ffmpeg, tmp_path):
        video = tmp_path / "v.mp4"
        result = mix_beat_audio(video, tmp_path / "voice.wav")
        assert result != video
        assert result.suffix == ".mp4"
        assert ".mixed" in result.name

    def test_default_output_with_music(self, mock_ffmpeg, tmp_path):
        video = tmp_path / "v.mp4"
        music = tmp_path / "music.mp3"
        music.write_bytes(b"f")
        result = mix_beat_audio(video, tmp_path / "voice.wav", music_path=music)
        assert result != video
        assert ".mixed" in result.name


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
        EpisodeAssembler(output_dir=deep_dir)
    assert deep_dir.exists()


def test_init_creates_existing_dir_without_error(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=False):
        assembler = EpisodeAssembler(output_dir=output)
    assert assembler.output_dir == output


def test_init_video_codec_when_videotoolbox_available(tmp_path):
    with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=True):
        assembler = EpisodeAssembler(output_dir=tmp_path / "out")
        assert assembler._video_codec == "h264_videotoolbox"


def test_init_video_codec_when_videotoolbox_unavailable(tmp_path):
    with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=False):
        assembler = EpisodeAssembler(output_dir=tmp_path / "out")
        assert assembler._video_codec == "libx264"
