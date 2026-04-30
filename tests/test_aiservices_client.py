from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sitcom_pilot.aiservices_client import AIServicesClient, _build_speech_tags, _div8
from sitcom_pilot.loader import VoiceConfig
from sitcom_pilot.providers import (
    auto_configure,
    ensure_registered,
    provider_name,
)


def _make_t2i_models():
    """Create a mock text2image.models module with real Text2ImageRequest."""
    import types
    from typing import Any

    from pydantic import BaseModel, Field

    class Text2ImageRequest(BaseModel):
        prompt: str = Field(...)
        negative_prompt: str | None = Field(None)
        guidance_scale: float = Field(7.5)
        num_inference_steps: int = Field(50)
        seed: int | None = Field(None)
        width: int = Field(1024)
        height: int = Field(1024)

    class Text2ImageResponse(BaseModel):
        output_path: str = Field(...)
        metadata: dict[str, Any] = Field(default_factory=dict)

    mod = types.ModuleType("text2image.models")
    mod.Text2ImageRequest = Text2ImageRequest
    mod.Text2ImageResponse = Text2ImageResponse
    return {"text2image.models": mod}


@pytest.fixture
def client():
    return AIServicesClient(
        image_provider="text2image.mlx",
        image_edit_provider="image2image.mlx",
        video_provider="image2video.mlx",
        tts_provider="text2speech.fish_mlx",
        subprocess_fallback=True,
    )


@pytest.fixture
def client_no_fallback():
    return AIServicesClient(
        subprocess_fallback=False,
    )


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
        mock_resp = MagicMock()
        mock_resp.output_path = str(tmp_path / "out.png")
        mock_provider = MagicMock()
        mock_provider.generate.return_value = mock_resp
        client._providers["text2image.mlx"] = mock_provider

        with patch.dict(
            "sys.modules", {"text2image": MagicMock(), "text2image.models": MagicMock()}
        ):
            with patch("sitcom_pilot.aiservices_client._run_cli") as mock_cli:
                result = client.text2image("a cat", tmp_path / "out.png", seed=42)
                assert isinstance(result, Path)
                mock_provider.generate.assert_called_once()
                mock_cli.assert_not_called()

    @patch("sitcom_pilot.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        client._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            result = client.text2image("a cat", tmp_path / "out.png", seed=42)
            assert isinstance(result, Path)
            mock_cli.assert_called_once()

    def test_no_fallback_raises(self, client_no_fallback, tmp_path):
        client_no_fallback._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            with pytest.raises(RuntimeError, match="no provider"):
                client_no_fallback.text2image("a cat", tmp_path / "out.png")


class TestImage2Image:
    @patch("sitcom_pilot.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        client._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            result = client.image2image(
                tmp_path / "input.png", "edit this", tmp_path / "out.png", seed=42
            )
            assert isinstance(result, Path)
            mock_cli.assert_called_once()


class TestImage2Video:
    @patch("sitcom_pilot.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        client._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            result = client.image2video(
                tmp_path / "input.png", "animate this", tmp_path / "out.mp4", seed=42
            )
            assert isinstance(result, Path)
            mock_cli.assert_called_once()

    @patch("sitcom_pilot.aiservices_client._mux_audio")
    @patch("sitcom_pilot.aiservices_client._run_cli")
    def test_audio_mux(self, mock_cli, mock_mux, client, tmp_path):
        mock_mux.return_value = tmp_path / "out.mp4"
        client._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
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
    @patch("sitcom_pilot.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        client._providers.clear()
        voice = VoiceConfig(provider="mlx-audio", voice_id="maya_v1", seed=42, temperature=0.8)
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            result = client.text2speech(
                "Hello world", tmp_path / "out.wav", voice=voice, emotion="happy"
            )
            assert isinstance(result, Path)
            mock_cli.assert_called_once()

    def test_character_voice_extraction(self, client, tmp_path):
        from sitcom_pilot.loader import CharacterData

        char = CharacterData(
            name="Maya",
            voice=VoiceConfig(provider="mlx-audio", voice_id="maya_v1", clone_from="ref.wav"),
        )
        client._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            with patch("sitcom_pilot.aiservices_client._run_cli"):
                result = client.text2speech("Hi", tmp_path / "out.wav", character=char)
                assert isinstance(result, Path)


class TestEstimateCost:
    def test_known_operation(self, client):
        result = client.estimate_cost("text2image", num_inference_steps=50)
        assert "time_sec" in result
        assert "memory_gb" in result

    def test_unknown_operation(self, client):
        result = client.estimate_cost("nonexistent")
        assert result["time_sec"] == 0.0


class TestDiscoverCapabilities:
    def test_returns_providers(self, client):
        caps = client.discover_capabilities()
        assert "text2image" in caps
        assert "image2image" in caps
        assert "image2video" in caps
        assert "text2speech" in caps

    def test_asr_optional(self):
        client = AIServicesClient(asr_provider="whisper.mlx")
        caps = client.discover_capabilities()
        assert "audio2subtitle" in caps

    def test_no_asr(self):
        client = AIServicesClient(asr_provider=None)
        caps = client.discover_capabilities()
        assert "audio2subtitle" not in caps


class TestProviderCaching:
    def test_provider_cached(self, client):
        mock_prov = MagicMock()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", return_value=mock_prov
        ):
            pass
        client._providers["text2image.mlx"] = mock_prov
        assert client._providers["text2image.mlx"] is mock_prov


class TestOutputDirCreation:
    @patch("sitcom_pilot.aiservices_client._run_cli")
    def test_creates_parent_dirs(self, mock_cli, client, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "out.png"
        client._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            client.text2image("test", deep)
            assert deep.parent.exists()


class TestProvidersModule:
    def test_provider_name_known(self):
        assert provider_name("text2image") == "text2image.mlx"
        assert provider_name("text2speech") == "text2speech.fish_mlx"
        assert provider_name("audio2subtitle") == "audio2subtitle.mlx"

    def test_provider_name_unknown(self):
        assert provider_name("nonexistent") == ""

    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    def test_auto_configure_macos_arm64(self, mock_mach, mock_sys):
        cfg = auto_configure()
        assert cfg["preferred_backend"] == "mlx"
        assert cfg["text2image"] == "text2image.mlx"
        assert cfg["text2speech"] == "text2speech.fish_mlx"

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="x86_64")
    def test_auto_configure_linux(self, mock_mach, mock_sys):
        cfg = auto_configure()
        assert cfg["preferred_backend"] == "cli"

    def test_ensure_registered_returns_availability(self):
        with patch("sitcom_pilot.providers._try_import", return_value=False):
            avail = ensure_registered()
            assert not avail.all_available
            assert "text2image" in avail.missing

    def test_ensure_registered_all_available(self):
        with patch("sitcom_pilot.providers._try_import", return_value=True):
            avail = ensure_registered()
            assert avail.all_available
            assert "text2image" in avail.available


class TestAudio2Subtitle:
    @patch("sitcom_pilot.aiservices_client._run_cli")
    def test_subprocess_fallback(self, mock_cli, client, tmp_path):
        client._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            result = client.audio2subtitle(tmp_path / "audio.wav", tmp_path / "out.srt")
            assert isinstance(result, Path)
            mock_cli.assert_called_once()

    def test_no_fallback_raises(self, client_no_fallback, tmp_path):
        client_no_fallback._providers.clear()
        with patch(
            "sitcom_pilot.aiservices_client.AIServicesClient._get_provider", side_effect=ImportError
        ):
            with pytest.raises(RuntimeError, match="no provider"):
                client_no_fallback.audio2subtitle(tmp_path / "audio.wav", tmp_path / "out.srt")


class TestDefaultProviders:
    def test_tts_default_is_fish_mlx(self):
        c = AIServicesClient()
        assert c._tts_provider == "text2speech.fish_mlx"

    def test_asr_default_is_mlx(self):
        c = AIServicesClient()
        assert c._asr_provider == "audio2subtitle.mlx"

    def test_discover_capabilities_includes_asr(self):
        c = AIServicesClient()
        caps = c.discover_capabilities()
        assert "audio2subtitle" in caps
        assert caps["audio2subtitle"] == ["audio2subtitle.mlx"]
