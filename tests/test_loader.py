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
