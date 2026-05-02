from __future__ import annotations

import pytest

from sitcom_pilot.beat_prompts import build_beat_prompt, build_character_prompt, build_scene_prompt
from sitcom_pilot.cast_manifest import CastManifest, CharacterProfile, WardrobeEntry
from sitcom_pilot.loader import BeatData, EpisodeData, SceneData


@pytest.fixture
def manifest():
    return CastManifest(
        characters={
            "maya": CharacterProfile(
                name="Maya Chen",
                slug="maya",
                visual="East Asian woman, late 20s, purple hoodie",
                wardrobe=(
                    WardrobeEntry(episode="s01e01", description="dark purple hoodie, jeans"),
                ),
                consistency_notes="always wears glasses",
            ),
            "derek": CharacterProfile(
                name="Derek Okafor",
                slug="derek",
                visual="Black man, early 30s, navy blazer",
            ),
        },
    )


@pytest.fixture
def episode():
    return EpisodeData(
        title="Test Episode",
        scenes=[
            SceneData(
                scene_id="001",
                environment="office",
                characters_present=["maya", "derek"],
            ),
        ],
        cast={},
        environments={},
    )


class TestBuildCharacterPrompt:
    def test_basic(self, manifest):
        prompt = build_character_prompt(manifest.get("maya"))
        assert "East Asian woman" in prompt
        assert "purple hoodie" in prompt

    def test_with_wardrobe(self, manifest):
        prompt = build_character_prompt(
            manifest.get("maya"), include_wardrobe=True, episode_id="s01e01"
        )
        assert "dark purple hoodie" in prompt

    def test_no_wardrobe(self, manifest):
        prompt = build_character_prompt(
            manifest.get("maya"), include_wardrobe=True, episode_id="s99e99"
        )
        assert "Wardrobe" not in prompt

    def test_consistency_notes(self, manifest):
        prompt = build_character_prompt(manifest.get("maya"))
        assert "glasses" in prompt


class TestBuildScenePrompt:
    def test_with_manifest(self, manifest, episode):
        scene = episode.scenes[0]
        prompt = build_scene_prompt(scene, episode, manifest)
        assert "East Asian woman" in prompt
        assert "Black man" in prompt


class TestBuildBeatPrompt:
    def test_beat_prompt(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="Maya enters the room")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        assert "Maya enters" in prompt
        assert "8k" in prompt
