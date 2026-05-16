from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from showrunner.aiservices_client import AIServicesClient, _build_speech_tags, _div8
from showrunner.loader import VoiceConfig


def _mock_aiservice_package(name: str):
    """Create real submodule so `from pkg.client import generate` works."""
    import types

    pkg_mod = types.ModuleType(name)
    pkg_mod.__path__ = [name]
    client_mod = types.ModuleType(f"{name}.client")
    client_mod.generate = MagicMock()
    sys.modules[name] = pkg_mod
    sys.modules[f"{name}.client"] = client_mod


@pytest.fixture(autouse=True)
def _mock_aiservice_packages():
    for pkg in ["text2image", "image2image", "image2video", "text2speech", "audio2subtitle"]:
        if pkg not in sys.modules:
            _mock_aiservice_package(pkg)


@pytest.fixture
def client():
    return AIServicesClient(subprocess_fallback=True)


@pytest.fixture
def client_no_fallback():
    return AIServicesClient(subprocess_fallback=False)


class TestDiv8:
    def test_rounds_down(self):
        assert _div8(720) == 720

    def test_rounds_non_multiple(self):
        assert _div8(721) == 720

    def test_minimum_512(self):
        assert _div8(100) == 512

    def test_large_value(self):
        assert _div8(1920) == 1920


class TestBuildSpeechTags:
    def test_all_tags(self):
        assert (
            _build_speech_tags("happy", "whispering", "laughing") == "(happy)(whispering)(laughing)"
        )

    def test_none_tags(self):
        assert _build_speech_tags(None, None, None) == ""

    def test_partial_tags(self):
        assert _build_speech_tags("angry", None, None) == "(angry)"


class TestText2Image:
    def test_python_api_success(self, client, tmp_path):
        mock_result = tmp_path / "out.png"
        gen = sys.modules["text2image.client"].generate
        gen.return_value = mock_result
        result = client.text2image("a cat", tmp_path / "out.png", seed=42)
        assert isinstance(result, Path)
        gen.assert_called_once()

    @patch("showrunner.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        sys.modules["text2image.client"].generate.side_effect = ImportError
        result = client.text2image("a cat", tmp_path / "out.png", seed=42)
        assert isinstance(result, Path)
        mock_cli.assert_called_once()

    def test_no_fallback_raises(self, client_no_fallback, tmp_path):
        sys.modules["text2image.client"].generate.side_effect = ImportError
        with pytest.raises(RuntimeError, match="no provider"):
            client_no_fallback.text2image("a cat", tmp_path / "out.png")


class TestImage2Image:
    @patch("showrunner.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        sys.modules["image2image.client"].generate.side_effect = ImportError
        result = client.image2image(
            tmp_path / "input.png", "edit this", tmp_path / "out.png", seed=42
        )
        assert isinstance(result, Path)
        mock_cli.assert_called_once()


class TestImage2Video:
    @patch("showrunner.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        sys.modules["image2video.client"].generate.side_effect = ImportError
        result = client.image2video(
            tmp_path / "input.png", "animate this", tmp_path / "out.mp4", seed=42
        )
        assert isinstance(result, Path)
        mock_cli.assert_called_once()

    @patch("showrunner.aiservices_client._mux_audio")
    @patch("showrunner.aiservices_client._run_cli")
    def test_audio_mux(self, mock_cli, mock_mux, client, tmp_path):
        mock_mux.return_value = tmp_path / "out.mp4"
        sys.modules["image2video.client"].generate.side_effect = ImportError
        result = client.image2video(
            tmp_path / "input.png",
            "animate",
            tmp_path / "out.mp4",
            audio_path=tmp_path / "audio.wav",
            seed=42,
        )
        assert isinstance(result, Path)
        mock_mux.assert_called_once()


class TestText2Speech:
    @patch("showrunner.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        voice = VoiceConfig(provider="mlx-audio", voice_id="maya_v1", seed=42, temperature=0.8)
        sys.modules["text2speech.client"].generate.side_effect = ImportError
        result = client.text2speech(
            "Hello world", tmp_path / "out.wav", voice=voice, emotion="happy"
        )
        assert isinstance(result, Path)
        mock_cli.assert_called_once()

    def test_character_voice_extraction(self, client, tmp_path):
        from showrunner.loader import CharacterData

        char = CharacterData(
            name="Maya",
            voice=VoiceConfig(provider="mlx-audio", voice_id="maya_v1", clone_from="ref.wav"),
        )
        sys.modules["text2speech.client"].generate.side_effect = ImportError
        with patch("showrunner.aiservices_client._run_cli"):
            result = client.text2speech("Hi", tmp_path / "out.wav", character=char)
            assert isinstance(result, Path)


class TestEstimateCost:
    def test_known_operation(self, client):
        result = client.estimate_cost("text2image", num_inference_steps=50)
        assert "time_sec" in result
        assert "memory_gb" in result

    def test_unknown_operation(self, client):
        result = client.estimate_cost("nonexistent")
        assert result["time_sec"] == pytest.approx(0.0)


class TestDiscoverCapabilities:
    def test_returns_providers(self, client):
        caps = client.discover_capabilities()
        assert "text2image" in caps
        assert "image2image" in caps
        assert "image2video" in caps
        assert "text2speech" in caps
        assert "audio2subtitle" in caps


class TestOutputDirCreation:
    @patch("showrunner.aiservices_client._run_cli")
    def test_creates_parent_dirs(self, mock_cli, client, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "out.png"
        sys.modules["text2image.client"].generate.side_effect = ImportError
        client.text2image("test", deep)
        assert deep.parent.exists()


class TestAudio2Subtitle:
    @patch("showrunner.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        sys.modules["audio2subtitle.client"].generate.side_effect = ImportError
        result = client.audio2subtitle(tmp_path / "audio.wav", tmp_path / "out.srt")
        assert isinstance(result, Path)
        mock_cli.assert_called_once()

    def test_no_fallback_raises(self, client_no_fallback, tmp_path):
        sys.modules["audio2subtitle.client"].generate.side_effect = ImportError
        with pytest.raises(RuntimeError, match="no provider"):
            client_no_fallback.audio2subtitle(tmp_path / "audio.wav", tmp_path / "out.srt")
