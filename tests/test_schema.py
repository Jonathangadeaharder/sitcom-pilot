from __future__ import annotations

import json
from pathlib import Path

import pytest

from showrunner.loader import (
    BeatData,
    CharacterData,
    EnvironmentData,
    EpisodeData,
    EpisodeLoader,
    SceneData,
    ShotData,
    VoiceConfig,
)


class TestVoiceConfig:
    def test_defaults(self):
        v = VoiceConfig()
        assert v.provider == ""
        assert v.voice_id == ""
        assert v.clone_from == ""
        assert v.seed == 0
        assert v.temperature == pytest.approx(0.8)
        assert v.language == "en"

    def test_custom_values(self):
        v = VoiceConfig(
            provider="mlx",
            voice_id="v1",
            clone_from="char",
            seed=42,
            temperature=0.5,
            language="fr",
        )
        assert v.provider == "mlx"
        assert v.temperature == pytest.approx(0.5)
        assert v.language == "fr"

    def test_boundary_temperature(self):
        v = VoiceConfig(temperature=0.0)
        assert v.temperature == pytest.approx(0.0)
        v2 = VoiceConfig(temperature=1.0)
        assert v2.temperature == pytest.approx(1.0)

    def test_negative_seed(self):
        v = VoiceConfig(seed=-1)
        assert v.seed == -1


class TestCharacterData:
    def test_defaults(self):
        c = CharacterData()
        assert c.name == ""
        assert c.visual == ""
        assert c.lora is None
        assert c.voice is None
        assert c.reference_images == ()
        assert c.profile == ""
        assert c.trigger_word == ""

    def test_v2_fields(self):
        voice = VoiceConfig(provider="test")
        c = CharacterData(name="Jerry", visual="man in hat", lora="jerry.safetensors", voice=voice)
        assert c.name == "Jerry"
        assert c.lora == "jerry.safetensors"
        assert c.voice is not None
        assert c.voice.provider == "test"

    def test_none_lora(self):
        c = CharacterData(lora=None)
        assert c.lora is None

    def test_empty_reference_images(self):
        c = CharacterData(reference_images=())
        assert c.reference_images == ()

    def test_populated_reference_images(self):
        c = CharacterData(reference_images=("front.png", "side.png"))
        assert len(c.reference_images) == 2
        assert c.reference_images[0] == "front.png"


class TestEnvironmentData:
    def test_defaults(self):
        e = EnvironmentData()
        assert e.trigger_word == ""
        assert e.style == ""
        assert e.reference_image == ""
        assert e.profile == ""

    def test_v2_fields(self):
        e = EnvironmentData(trigger_word="coffee_shop", style="modern", reference_image="ref.jpg")
        assert e.trigger_word == "coffee_shop"
        assert e.reference_image == "ref.jpg"

    def test_v1_profile(self):
        e = EnvironmentData(profile="cafe_v1")
        assert e.profile == "cafe_v1"


class TestBeatData:
    def test_required_fields(self):
        b = BeatData(beat_id="b1", kind="speech")
        assert b.beat_id == "b1"
        assert b.kind == "speech"

    def test_defaults(self):
        b = BeatData(beat_id="b1", kind="silent")
        assert b.camera == ""
        assert b.action == ""
        assert b.duration_sec == pytest.approx(3.0)
        assert b.seed == 0
        assert b.speaker == ""
        assert b.text == ""
        assert b.audio_path == ""

    def test_zero_duration(self):
        b = BeatData(beat_id="b1", kind="silent", duration_sec=0.0)
        assert b.duration_sec == pytest.approx(0.0)

    def test_negative_duration(self):
        b = BeatData(beat_id="b1", kind="silent", duration_sec=-1.0)
        assert b.duration_sec == pytest.approx(-1.0)

    def test_kind_values(self):
        assert BeatData(beat_id="b1", kind="speech").kind == "speech"
        assert BeatData(beat_id="b2", kind="silent").kind == "silent"

    def test_empty_beat_id(self):
        assert BeatData(beat_id="", kind="silent").beat_id == ""


class TestShotData:
    def test_required_fields(self):
        s = ShotData(
            shot_id="s1", camera_angle="wide", action_start="enter", action_end="exit", seed=0
        )
        assert s.shot_id == "s1"
        assert s.seed == 0

    def test_dialogue_defaults_empty_list(self):
        s = ShotData(
            shot_id="s1", camera_angle="wide", action_start="enter", action_end="exit", seed=0
        )
        assert s.dialogue == []

    def test_dialogue_provided(self):
        s = ShotData(
            shot_id="s1",
            camera_angle="wide",
            action_start="enter",
            action_end="exit",
            seed=0,
            dialogue=[{"speaker": "Jerry", "text": "Hello"}],
        )
        assert len(s.dialogue) == 1
        assert s.dialogue[0]["speaker"] == "Jerry"

    def test_audio_path_default(self):
        s = ShotData(
            shot_id="s1", camera_angle="wide", action_start="enter", action_end="exit", seed=0
        )
        assert s.audio_path == ""

    def test_negative_seed(self):
        s = ShotData(
            shot_id="s1", camera_angle="wide", action_start="enter", action_end="exit", seed=-5
        )
        assert s.seed == -5

    def test_none_dialogue_becomes_empty(self):
        s = ShotData(
            shot_id="s1",
            camera_angle="wide",
            action_start="enter",
            action_end="exit",
            seed=0,
            dialogue=None,
        )
        assert s.dialogue == []


class TestSceneData:
    def test_required_fields(self):
        s = SceneData(scene_id="s1", environment="office", characters_present=["Jerry"])
        assert s.scene_id == "s1"
        assert s.characters_present == ["Jerry"]

    def test_empty_beats(self):
        s = SceneData(scene_id="s1", environment="office", characters_present=[])
        assert s.beats == []

    def test_empty_shots(self):
        s = SceneData(scene_id="s1", environment="office", characters_present=[])
        assert s.shots == []

    def test_target_duration_default(self):
        s = SceneData(scene_id="s1", environment="office", characters_present=[])
        assert s.target_duration_sec == 60

    def test_custom_target_duration(self):
        s = SceneData(
            scene_id="s1", environment="office", characters_present=[], target_duration_sec=120
        )
        assert s.target_duration_sec == 120

    def test_zero_target_duration(self):
        s = SceneData(
            scene_id="s1", environment="office", characters_present=[], target_duration_sec=0
        )
        assert s.target_duration_sec == 0

    def test_title_and_mood_defaults(self):
        s = SceneData(scene_id="s1", environment="office", characters_present=[])
        assert s.title == ""
        assert s.mood == ""

    def test_with_beats(self):
        beats = [BeatData(beat_id="b1", kind="speech"), BeatData(beat_id="b2", kind="silent")]
        s = SceneData(scene_id="s1", environment="office", characters_present=[], beats=beats)
        assert len(s.beats) == 2

    def test_mixed_beats_and_shots(self):
        beats = [BeatData(beat_id="b1", kind="speech")]
        shots = [
            ShotData(shot_id="sh1", camera_angle="wide", action_start="a", action_end="b", seed=0)
        ]
        s = SceneData(
            scene_id="s1", environment="office", characters_present=[], beats=beats, shots=shots
        )
        assert len(s.beats) == 1
        assert len(s.shots) == 1

    def test_empty_characters(self):
        s = SceneData(scene_id="s1", environment="office", characters_present=[])
        assert s.characters_present == []


class TestEpisodeData:
    def test_required_fields(self):
        e = EpisodeData(title="Test", cast={}, environments={}, scenes=[])
        assert e.title == "Test"

    def test_defaults(self):
        e = EpisodeData(title="Test", cast={}, environments={}, scenes=[])
        assert e.schema_version == "1.0"
        assert e.show == ""
        assert e.season == 0
        assert e.episode_number == 0
        assert e.render_config == {}

    def test_empty_title(self):
        e = EpisodeData(title="", cast={}, environments={}, scenes=[])
        assert e.title == ""

    def test_custom_render_config(self):
        e = EpisodeData(title="T", cast={}, environments={}, scenes=[], render_config={"fps": 30})
        assert e.render_config["fps"] == 30

    def test_nonzero_season_episode(self):
        e = EpisodeData(title="T", cast={}, environments={}, scenes=[], season=2, episode_number=5)
        assert e.season == 2
        assert e.episode_number == 5


class TestEpisodeLoader:
    def test_invalid_schema_version(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps({"schema_version": "3.0", "cast": {}, "environments": {}, "scenes": []})
        )
        with pytest.raises(ValueError, match="Unsupported schema_version"):
            EpisodeLoader().load(p)

    def test_empty_json(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text("{}")
        loader = EpisodeLoader()
        episode = loader.load(p)
        assert episode.cast == {}
        assert episode.environments == {}
        assert episode.scenes == []

    def test_no_scenes_key(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(json.dumps({"cast": {}, "environments": {}}))
        episode = EpisodeLoader().load(p)
        assert episode.scenes == []

    def test_no_cast_key(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(json.dumps({"scenes": [], "environments": {}}))
        episode = EpisodeLoader().load(p)
        assert episode.cast == {}

    def test_no_environments_key(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(json.dumps({"cast": {}, "scenes": []}))
        episode = EpisodeLoader().load(p)
        assert episode.environments == {}

    def test_missing_scene_id_raises(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "cast": {},
                    "environments": {},
                    "scenes": [{"environment": "office", "characters_present": []}],
                }
            )
        )
        with pytest.raises(KeyError):
            EpisodeLoader().load(p)

    def test_v2_beat_minimal(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "cast": {},
                    "environments": {"office": {"trigger_word": "office", "reference_image": ""}},
                    "scenes": [
                        {
                            "scene_id": "S1",
                            "environment": "office",
                            "characters_present": [],
                            "beats": [{"beat_id": "b1", "kind": "speech"}],
                        }
                    ],
                }
            )
        )
        episode = EpisodeLoader().load(p)
        assert len(episode.scenes[0].beats) == 1
        assert episode.scenes[0].beats[0].beat_id == "b1"

    def test_v2_cast_with_voice(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "cast": {
                        "jerry": {
                            "name": "Jerry",
                            "visual": "man in hat",
                            "voice": {"provider": "mlx", "voice_id": "jerry_v1"},
                        },
                    },
                    "environments": {},
                    "scenes": [],
                }
            )
        )
        episode = EpisodeLoader().load(p)
        assert episode.cast["jerry"].name == "Jerry"
        assert episode.cast["jerry"].voice is not None
        assert episode.cast["jerry"].voice.provider == "mlx"

    def test_v2_cast_without_voice(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "cast": {"jerry": {"name": "Jerry", "visual": "man in hat"}},
                    "environments": {},
                    "scenes": [],
                }
            )
        )
        episode = EpisodeLoader().load(p)
        assert episode.cast["jerry"].voice is None

    def test_v2_environment_minimal(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "cast": {},
                    "environments": {"office": {}},
                    "scenes": [],
                }
            )
        )
        episode = EpisodeLoader().load(p)
        assert episode.environments["office"].trigger_word == ""

    def test_v1_legacy_shot_audio_default(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "cast": {"A": {"profile": "a", "trigger_word": "aa"}},
                    "environments": {"R": {"profile": "r", "trigger_word": "rr"}},
                    "scenes": [
                        {
                            "scene_id": "S1",
                            "environment": "R",
                            "characters_present": ["A"],
                            "shots": [
                                {
                                    "shot_id": "SH1",
                                    "camera_angle": "wide",
                                    "action_start": "enter",
                                    "action_end": "exit",
                                    "seed": 1,
                                }
                            ],
                        }
                    ],
                }
            )
        )
        episode = EpisodeLoader().load(p)
        shot = episode.scenes[0].shots[0]
        assert shot.audio_path == ""

    def test_target_seconds_fallback(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "cast": {},
                    "environments": {},
                    "scenes": [
                        {
                            "scene_id": "S1",
                            "environment": "R",
                            "characters_present": [],
                            "shots": [],
                            "target_seconds": 90,
                        }
                    ],
                }
            )
        )
        episode = EpisodeLoader().load(p)
        assert episode.scenes[0].target_duration_sec == 90

    def test_episode_field_fallbacks(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "cast": {},
                    "environments": {},
                    "scenes": [],
                }
            )
        )
        episode = EpisodeLoader().load(p)
        assert episode.show == ""
        assert episode.season == 0
        assert episode.episode_number == 0
        assert episode.render_config == {}

    def test_render_config_carried(self, tmp_path):
        p = tmp_path / "ep.json"
        p.write_text(
            json.dumps(
                {
                    "cast": {},
                    "environments": {},
                    "scenes": [],
                    "render": {"fps": 24, "quality": "high"},
                }
            )
        )
        episode = EpisodeLoader().load(p)
        assert episode.render_config["fps"] == 24

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            EpisodeLoader().load(Path("/nonexistent/path.json"))
