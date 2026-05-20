from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from showrunner.cast_manifest import CastManifest, CharacterProfile
from showrunner.loader import BeatData, EpisodeData, SceneData
from showrunner.plate_generator import generate_beat_plate, generate_scene_plate


@pytest.fixture
def manifest():
    return CastManifest(
        characters={
            "maya": CharacterProfile(slug="maya", visual="woman in hoodie"),
        },
    )


@pytest.fixture
def episode():
    return EpisodeData(
        title="Test Episode",
        scenes=[
            SceneData(scene_id="001", environment="office", characters_present=["maya"]),
        ],
        cast={},
        environments={},
    )


class TestGenerateScenePlate:
    @patch("showrunner.plate_generator.AIServicesClient")
    def test_generates_image(self, mock_client_cls, manifest, episode, tmp_path):
        mock_client = MagicMock()
        mock_client.text2image.return_value = tmp_path / "plate.png"
        out = tmp_path / "scene_001.png"
        result = generate_scene_plate(
            episode.scenes[0], episode, manifest, mock_client, out, seed=42
        )
        mock_client.text2image.assert_called_once()
        assert result == tmp_path / "plate.png"


class TestGenerateBeatPlate:
    @patch("showrunner.plate_generator.AIServicesClient")
    def test_generates_from_scene_plate(self, mock_client_cls, manifest, episode, tmp_path):
        mock_client = MagicMock()
        mock_client.image2image.return_value = tmp_path / "beat.png"
        scene_plate = tmp_path / "scene_001.png"
        scene_plate.write_bytes(b"fake")
        out = tmp_path / "beat_001_001.png"
        beat = BeatData(beat_id="001_001", kind="speech", action="Maya enters")
        result = generate_beat_plate(
            beat, episode.scenes[0], episode, manifest, mock_client, scene_plate, out, seed=42
        )
        mock_client.image2image.assert_called_once()
        assert result == tmp_path / "beat.png"

    @patch("showrunner.plate_generator.AIServicesClient")
    def test_rejects_strength_out_of_range(self, mock_client_cls, manifest, episode, tmp_path):
        mock_client = MagicMock()
        scene_plate = tmp_path / "scene_001.png"
        scene_plate.write_bytes(b"fake")
        out = tmp_path / "beat_bad.png"
        beat = BeatData(beat_id="001_001", kind="speech", action="Maya enters")
        with pytest.raises(ValueError, match="strength must be between"):
            generate_beat_plate(
                beat,
                episode.scenes[0],
                episode,
                manifest,
                mock_client,
                scene_plate,
                out,
                strength=-0.5,
            )
        with pytest.raises(ValueError, match="strength must be between"):
            generate_beat_plate(
                beat,
                episode.scenes[0],
                episode,
                manifest,
                mock_client,
                scene_plate,
                out,
                strength=1.5,
            )
        # valid boundary should not raise
        generate_beat_plate(
            beat,
            episode.scenes[0],
            episode,
            manifest,
            mock_client,
            scene_plate,
            out,
            strength=0.0,
        )
