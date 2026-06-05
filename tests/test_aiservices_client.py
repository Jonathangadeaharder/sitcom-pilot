from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from showrunner.aiservices_client import AIServicesClient, _build_speech_tags, _div8
from showrunner.loader import CharacterData, VoiceConfig


def _mock_aiservice_package(name: str):
    """Create real submodule so `from pkg.client import generate` works."""
    pkg_mod = types.ModuleType(name)
    pkg_mod.__path__ = [name]
    client_mod = types.ModuleType(f"{name}.client")
    client_mod.generate = MagicMock()
    sys.modules[name] = pkg_mod
    sys.modules[f"{name}.client"] = client_mod


def _mock_aiservices_package():
    """Create the ``aiservices`` package with ``generate_text2image``,
    ``generate_image2image``, and ``aiservices.generate.VideoGenerator``."""
    pkg = types.ModuleType("aiservices")
    pkg.__path__ = ["aiservices"]
    pkg.generate_text2image = MagicMock()
    pkg.generate_image2image = MagicMock()

    generate_mod = types.ModuleType("aiservices.generate")
    generate_mod.VideoGenerator = MagicMock()
    sys.modules["aiservices"] = pkg
    sys.modules["aiservices.generate"] = generate_mod


@pytest.fixture(autouse=True)
def _mock_aiservice_packages():
    # Core aiservices package (text2image, image2image, image2video)
    _mock_aiservices_package()
    # Separate service packages (text2speech, audio2subtitle)
    for pkg in ["text2speech", "audio2subtitle"]:
        if pkg not in sys.modules:
            _mock_aiservice_package(pkg)
    yield
    # Cleanup: remove mock modules so they don't leak between tests
    for key in list(sys.modules):
        if key.startswith(("aiservices", "text2speech", "audio2subtitle")):
            del sys.modules[key]


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
        mock_result = MagicMock()
        mock_result.path = tmp_path / "out.png"
        gen = sys.modules["aiservices"].generate_text2image
        gen.return_value = mock_result
        result = client.text2image("a cat", tmp_path / "out.png", seed=42)
        assert isinstance(result, Path)
        gen.assert_called_once()

    def test_import_error_with_fallback_raises(self, client, tmp_path):
        sys.modules["aiservices"].generate_text2image.side_effect = ImportError
        with pytest.raises(RuntimeError, match="aiservices package not available"):
            client.text2image("a cat", tmp_path / "out.png", seed=42)

    def test_no_fallback_raises(self, client_no_fallback, tmp_path):
        sys.modules["aiservices"].generate_text2image.side_effect = ImportError
        with pytest.raises(RuntimeError, match="no provider"):
            client_no_fallback.text2image("a cat", tmp_path / "out.png")


class TestImage2Image:
    def test_python_api_success(self, client, tmp_path):
        mock_result = MagicMock()
        mock_result.path = tmp_path / "out.png"
        gen = sys.modules["aiservices"].generate_image2image
        gen.return_value = mock_result
        result = client.image2image(
            tmp_path / "input.png", "edit this", tmp_path / "out.png", seed=42
        )
        assert isinstance(result, Path)
        gen.assert_called_once()

    def test_import_error_with_fallback_raises(self, client, tmp_path):
        sys.modules["aiservices"].generate_image2image.side_effect = ImportError
        with pytest.raises(RuntimeError, match="aiservices package not available"):
            client.image2image(tmp_path / "input.png", "edit", tmp_path / "out.png")


class TestImage2Video:
    def test_python_api_success(self, client, tmp_path):
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate.return_value = tmp_path / "out.mp4"
        sys.modules["aiservices.generate"].VideoGenerator.return_value = mock_gen_instance
        result = client.image2video(
            tmp_path / "input.png", "animate this", tmp_path / "out.mp4", seed=42
        )
        assert isinstance(result, Path)
        mock_gen_instance.generate.assert_called_once()

    def test_import_error_raises(self, client, tmp_path):
        sys.modules["aiservices.generate"].VideoGenerator.side_effect = ImportError
        with pytest.raises(ImportError):
            client.image2video(
                tmp_path / "input.png", "animate this", tmp_path / "out.mp4", seed=42
            )

    @patch("showrunner.aiservices_client._mux_audio")
    def test_audio_mux(self, mock_mux, client, tmp_path):
        mock_mux.return_value = tmp_path / "out.mp4"
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate.return_value = tmp_path / "out.mp4"
        sys.modules["aiservices.generate"].VideoGenerator.return_value = mock_gen_instance
        (tmp_path / "audio.wav").write_text("fake audio")
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
    def test_creates_parent_dirs(self, client, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "out.png"
        mock_result = MagicMock()
        mock_result.path = deep
        sys.modules["aiservices"].generate_text2image.return_value = mock_result
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


class TestResolveVoiceConfig:
    def test_voice_returns_voice(self):
        voice = VoiceConfig(provider="test", voice_id="v1")
        result = AIServicesClient._resolve_voice_config(voice, None)
        assert result is voice

    def test_no_voice_uses_character_voice(self):
        char_voice = VoiceConfig(provider="test", voice_id="char_v1")
        char = CharacterData(name="Test", voice=char_voice)
        result = AIServicesClient._resolve_voice_config(None, char)
        assert result is char_voice

    def test_no_voice_no_character_returns_none(self):
        result = AIServicesClient._resolve_voice_config(None, None)
        assert result is None

    def test_no_voice_character_no_voice_returns_none(self):
        char = CharacterData(name="Test", voice=None)
        result = AIServicesClient._resolve_voice_config(None, char)
        assert result is None
