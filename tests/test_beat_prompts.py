from __future__ import annotations

import pytest

from showrunner.beat_prompts import build_beat_prompt, build_character_prompt, build_scene_prompt
from showrunner.cast_manifest import CastManifest, CharacterProfile, WardrobeEntry
from showrunner.loader import BeatData, EpisodeData, SceneData


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
def char_no_notes():
    return CharacterProfile(name="Extra", slug="extra", visual="background actor")


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


@pytest.fixture
def episode_with_env_and_cast():
    return EpisodeData(
        title="Test Episode",
        scenes=[
            SceneData(
                scene_id="001",
                environment="office",
                characters_present=["maya", "extra"],
            ),
        ],
        cast={
            "extra": CharacterProfile(
                name="Extra",
                slug="extra",
                visual="background actor",
            ),
        },
        environments={
            "office": type("Env", (), {"trigger_word": "in the office"})(),
        },
    )


class TestBuildCharacterPrompt:
    def test_basic(self, manifest):
        prompt = build_character_prompt(manifest.get("maya"))
        assert "East Asian woman" in prompt
        assert "purple hoodie" in prompt

    def test_default_include_wardrobe_is_true(self, manifest):
        prompt = build_character_prompt(manifest.get("maya"), episode_id="s01e01")
        assert "dark purple hoodie" in prompt

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

    def test_wardrobe_explicit_false(self, manifest):
        prompt = build_character_prompt(
            manifest.get("maya"), include_wardrobe=False, episode_id="s01e01"
        )
        assert "dark purple hoodie" not in prompt

    def test_wardrobe_empty_episode_id_default(self, manifest):
        prompt = build_character_prompt(manifest.get("maya"), include_wardrobe=True)
        assert "Wardrobe" not in prompt

    def test_consistency_notes(self, manifest):
        prompt = build_character_prompt(manifest.get("maya"))
        assert "glasses" in prompt

    def test_no_consistency_notes(self, char_no_notes):
        prompt = build_character_prompt(char_no_notes)
        assert "glasses" not in prompt

    def test_join_separator_is_comma_space(self, manifest):
        prompt = build_character_prompt(manifest.get("maya"))
        assert prompt.endswith("always wears glasses")
        assert "purple hoodie, always" in prompt

    def test_join_separator_not_contains_xx(self, manifest):
        prompt = build_character_prompt(manifest.get("maya"))
        assert "XX" not in prompt

    def test_and_operator_guards_wardrobe_access(self, manifest):
        char_no_wardrobe = CharacterProfile(name="Bob", slug="bob", visual="tall man")
        prompt = build_character_prompt(
            char_no_wardrobe, include_wardrobe=True, episode_id="s01e01"
        )
        assert "Wardrobe" not in prompt


class TestBuildScenePrompt:
    def test_with_manifest(self, manifest, episode):
        scene = episode.scenes[0]
        prompt = build_scene_prompt(scene, episode, manifest)
        assert "East Asian woman" in prompt
        assert "Black man" in prompt

    def test_character_not_in_manifest_falls_back_to_cast(self, episode_with_env_and_cast):
        scene = episode_with_env_and_cast.scenes[0]
        prompt = build_scene_prompt(scene, episode_with_env_and_cast, CastManifest(characters={}))
        assert "background actor" in prompt

    def test_cast_fallback_uses_visual_or_name(self, episode_with_env_and_cast):
        scene = episode_with_env_and_cast.scenes[0]
        ep_no_visual = EpisodeData(
            title="Test",
            scenes=[SceneData(scene_id="001", environment="room", characters_present=["extra"])],
            cast={
                "extra": CharacterProfile(name="Extra Person", slug="extra", visual=""),
            },
            environments={},
        )
        prompt = build_scene_prompt(scene, ep_no_visual, CastManifest(characters={}))
        assert "Extra Person" in prompt

    def test_manifest_takes_priority_over_cast(self, manifest, episode_with_env_and_cast):
        scene = episode_with_env_and_cast.scenes[0]
        prompt = build_scene_prompt(scene, episode_with_env_and_cast, manifest)
        assert "East Asian woman" in prompt
        assert "purple hoodie" in prompt

    def test_env_trigger_word_used(self, episode_with_env_and_cast):
        scene = episode_with_env_and_cast.scenes[0]
        prompt = build_scene_prompt(scene, episode_with_env_and_cast, CastManifest(characters={}))
        assert "in the office" in prompt

    def test_no_env_fallback_to_environment_name(self, episode):
        scene = episode.scenes[0]
        prompt = build_scene_prompt(scene, episode, CastManifest(characters={}))
        assert "office" in prompt
        assert "in the office" not in prompt

    def test_all_three_parts_joined(self, episode_with_env_and_cast):
        scene = episode_with_env_and_cast.scenes[0]
        prompt = build_scene_prompt(scene, episode_with_env_and_cast, CastManifest(characters={}))
        assert prompt == "in the office, background actor"

    def test_join_separator_comma_space(self, manifest, episode):
        scene = episode.scenes[0]
        prompt = build_scene_prompt(scene, episode, manifest)
        assert prompt.startswith("office, East Asian")
        assert prompt.endswith("navy blazer")

    def test_scene_prompt_passes_episode_id(self, manifest, episode):
        scene = episode.scenes[0]
        prompt = build_scene_prompt(scene, episode, manifest, episode_id="s01e01")
        assert "dark purple hoodie" in prompt

    def test_no_characters_returns_just_env(self, episode):
        empty_ep = EpisodeData(
            title="Test",
            scenes=[SceneData(scene_id="001", environment="void", characters_present=[])],
            cast={},
            environments={},
        )
        scene = empty_ep.scenes[0]
        prompt = build_scene_prompt(scene, empty_ep, CastManifest(characters={}))
        assert prompt == "void"


class TestBuildBeatPrompt:
    def test_beat_prompt(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="Maya enters the room")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        assert "Maya enters" in prompt
        assert "8k" in prompt

    def test_uses_scene_and_character_information(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="speaks")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        assert "East Asian woman" in prompt
        assert "Black man" in prompt

    def test_action_falls_back_to_text(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="", text="Maya waves")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        assert "Maya waves" in prompt

    def test_action_and_text_empty_omits_action_part(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="", text="")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        # action part empty: scene_prompt + quality = 2 logical parts joined by comma-space
        assert prompt.startswith("office, East Asian")
        assert prompt.endswith("cinematic lighting")
        assert "XXXX" not in prompt

    def test_quality_string_always_present(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="silent", action="", text="")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        assert "RAW" in prompt
        assert "8k" in prompt
        assert "cinematic lighting" in prompt

    def test_quality_string_case_sensitive(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="looks left")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        assert "RAW photo" in prompt
        assert "raw photo" not in prompt

    def test_join_separator_comma_space(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="acts")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        assert prompt.endswith("cinematic lighting")
        assert "acts" in prompt
        assert "acts, RAW" in prompt or prompt.endswith("acts, RAW")

    def test_join_separator_not_contains_xx(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="acts")
        prompt = build_beat_prompt(beat, scene, episode, manifest)
        assert "XX" not in prompt

    def test_beat_prompt_passes_episode_id(self, manifest, episode):
        scene = episode.scenes[0]
        beat = BeatData(beat_id="001_001", kind="speech", action="waves")
        prompt = build_beat_prompt(beat, scene, episode, manifest, episode_id="s01e01")
        assert "dark purple hoodie" in prompt
