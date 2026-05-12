from __future__ import annotations

import json
from pathlib import Path

from showrunner.commands.validate import validate_episode


def test_valid_episode_returns_true():
    path = Path(__file__).parent / "fixtures" / "valid-episode.json"
    valid, errors = validate_episode(path)
    assert valid
    assert errors == []


def test_valid_episode_from_fixture():
    path = Path(__file__).parent / "fixtures" / "valid-episode.json"
    valid, errors = validate_episode(path)
    assert valid
    assert errors == []


def test_missing_required_field_returns_false(tmp_path):
    data = {
        "show": "Buffering",
        "season": 1,
        "episode": 2,
        "title": "Test",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": [],
    }
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(data))
    valid, errors = validate_episode(path)
    assert not valid
    assert any("scenes" in e for e in errors)


def test_missing_show_returns_false(tmp_path):
    data = {
        "season": 1,
        "episode": 2,
        "title": "Test",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "x",
                "characters_present": ["a"],
                "beats": [{"beat_id": "b1", "kind": "silent"}],
            }
        ],
    }
    path = tmp_path / "missing_show.json"
    path.write_text(json.dumps(data))
    valid, errors = validate_episode(path)
    assert not valid
    assert any("show" in e for e in errors)


def test_invalid_field_type_returns_false(tmp_path):
    data = {
        "show": "Buffering",
        "season": "not_a_number",
        "episode": 2,
        "title": "Test",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "x",
                "characters_present": ["a"],
                "beats": [{"beat_id": "b1", "kind": "silent"}],
            }
        ],
    }
    path = tmp_path / "bad_type.json"
    path.write_text(json.dumps(data))
    valid, errors = validate_episode(path)
    assert not valid
    assert any("season" in e for e in errors)


def test_empty_file_returns_false(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("")
    valid, errors = validate_episode(path)
    assert not valid
    assert any("parse" in e.lower() for e in errors)


def test_invalid_json_returns_false(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ invalid json }")
    valid, errors = validate_episode(path)
    assert not valid
    assert any("parse" in e.lower() for e in errors)


def test_speech_beat_missing_speaker_returns_false(tmp_path):
    data = {
        "show": "Buffering",
        "season": 1,
        "episode": 2,
        "title": "Test",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "x",
                "characters_present": ["a"],
                "beats": [
                    {"beat_id": "b1", "kind": "speech", "text": "Hello"},
                ],
            }
        ],
    }
    path = tmp_path / "no_speaker.json"
    path.write_text(json.dumps(data))
    valid, errors = validate_episode(path)
    assert not valid
    assert any("speaker" in e for e in errors)


def test_speech_beat_missing_text_returns_false(tmp_path):
    data = {
        "show": "Buffering",
        "season": 1,
        "episode": 2,
        "title": "Test",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "x",
                "characters_present": ["a"],
                "beats": [
                    {"beat_id": "b1", "kind": "speech", "speaker": "maya"},
                ],
            }
        ],
    }
    path = tmp_path / "no_text.json"
    path.write_text(json.dumps(data))
    valid, errors = validate_episode(path)
    assert not valid
    assert any("text" in e for e in errors)


def test_invalid_beat_kind_returns_false(tmp_path):
    data = {
        "show": "Buffering",
        "season": 1,
        "episode": 2,
        "title": "Test",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "x",
                "characters_present": ["a"],
                "beats": [
                    {"beat_id": "b1", "kind": "invalid_kind"},
                ],
            }
        ],
    }
    path = tmp_path / "bad_kind.json"
    path.write_text(json.dumps(data))
    valid, errors = validate_episode(path)
    assert not valid
    assert any("kind" in e for e in errors)


def test_invalid_schema_version_returns_false(tmp_path):
    data = {
        "show": "Buffering",
        "season": 1,
        "episode": 2,
        "title": "Test",
        "schema_version": "1.0",
        "cast": {},
        "environments": {},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "x",
                "characters_present": ["a"],
                "beats": [{"beat_id": "b1", "kind": "silent"}],
            }
        ],
    }
    path = tmp_path / "bad_version.json"
    path.write_text(json.dumps(data))
    valid, errors = validate_episode(path)
    assert not valid
    assert any("schema_version" in e for e in errors)


def test_not_a_dict_returns_false(tmp_path):
    path = tmp_path / "not_dict.json"
    path.write_text('"just a string"')
    valid, errors = validate_episode(path)
    assert not valid
    assert any("object" in e.lower() for e in errors)


def test_nonexistent_file_returns_false():
    valid, errors = validate_episode(Path("/nonexistent/path/episode.json"))
    assert not valid
    assert any("parse" in e.lower() for e in errors)
