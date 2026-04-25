import json
import pytest
from pathlib import Path
from orchestrator.loader import EpisodeLoader


def test_load_valid_episode_returns_episode_data(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "Test Episode",
        "cast": {
            "Jerry": {"profile": "jerry_v2", "trigger_word": "jry_guy, wearing a puffy shirt"}
        },
        "environments": {
            "Apt": {"profile": "apt_v1", "trigger_word": "apartment, couch, daylight"}
        },
        "scenes": [{
            "scene_id": "S01", "environment": "Apt",
            "characters_present": ["Jerry"],
            "shots": [{
                "shot_id": "S01_SH01", "camera_angle": "wide shot",
                "action_start": "standing", "action_end": "sitting",
                "audio_path": "audio/s1_shot1.wav", "seed": 42
            }]
        }]
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.title == "Test Episode"
    assert len(episode.scenes) == 1
    assert episode.scenes[0].shots[0].shot_id == "S01_SH01"


def test_load_missing_title_raises(tmp_path):
    episode_json = tmp_path / "bad.json"
    episode_json.write_text(json.dumps({"cast": {}, "environments": {}, "scenes": []}))
    loader = EpisodeLoader()
    with pytest.raises(KeyError):
        loader.load(episode_json)


def test_load_empty_scenes_returns_empty_list(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "Empty", "cast": {}, "environments": {}, "scenes": []
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.scenes == []


def test_load_preserves_unknown_env_reference(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "T", "cast": {},
        "environments": {"Apt": {"profile": "a", "trigger_word": "b"}},
        "scenes": [{"scene_id": "S1", "environment": "NONEXISTENT",
                     "characters_present": [], "shots": []}]
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.scenes[0].environment == "NONEXISTENT"


def test_load_assigns_all_shot_fields(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "FieldCheck",
        "cast": {"A": {"profile": "ap", "trigger_word": "at"}},
        "environments": {"R": {"profile": "rp", "trigger_word": "rt"}},
        "scenes": [{"scene_id": "S1", "environment": "R",
                     "characters_present": ["A"],
                     "shots": [{"shot_id": "S1_SH1", "camera_angle": "close",
                                "action_start": "walking", "action_end": "running",
                                "audio_path": "snd.wav", "seed": 77}]}]
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    shot = episode.scenes[0].shots[0]
    assert shot.shot_id == "S1_SH1"
    assert shot.camera_angle == "close"
    assert shot.action_start == "walking"
    assert shot.action_end == "running"
    assert shot.audio_path == "snd.wav"
    assert shot.seed == 77


def test_load_assigns_cast_profile_and_trigger(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "CastCheck",
        "cast": {"Bob": {"profile": "bob_v3", "trigger_word": "bob_man"}},
        "environments": {},
        "scenes": []
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.cast["Bob"].profile == "bob_v3"
    assert episode.cast["Bob"].trigger_word == "bob_man"


def test_load_assigns_env_profile_and_trigger(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "EnvCheck",
        "cast": {},
        "environments": {"Cafe": {"profile": "cafe_v2", "trigger_word": "coffee shop"}},
        "scenes": []
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.environments["Cafe"].profile == "cafe_v2"
    assert episode.environments["Cafe"].trigger_word == "coffee shop"


def test_load_assigns_scene_characters_present(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "CharsCheck",
        "cast": {
            "A": {"profile": "a", "trigger_word": "aa"},
            "B": {"profile": "b", "trigger_word": "bb"},
        },
        "environments": {},
        "scenes": [{"scene_id": "S1", "environment": "R",
                     "characters_present": ["A", "B"], "shots": []}]
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.scenes[0].characters_present == ["A", "B"]
