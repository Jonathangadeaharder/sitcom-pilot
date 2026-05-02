"""Tests for sitcom_pilot.validator — EpisodeValidator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from sitcom_pilot.validator import EpisodeValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_v2_episode():
    return {
        "show": "Buffering",
        "season": 1,
        "episode": 1,
        "title": "The Bug",
        "schema_version": "2.0",
        "cast": {
            "maya": {
                "name": "Maya Chen",
                "visual": "East Asian woman, dark hair",
                "lora": None,
                "voice": {
                    "provider": "mlx-audio",
                    "voice_id": "maya_v1",
                    "clone_from": "",
                    "seed": 42,
                    "temperature": 0.8,
                    "language": "en",
                },
            }
        },
        "environments": {
            "maya_desk": {
                "trigger_word": "Corner desk, monitors glowing",
                "style": "cinematic",
            }
        },
        "scenes": [
            {
                "scene_id": "001",
                "environment": "maya_desk",
                "characters_present": ["maya"],
                "beats": [
                    {
                        "beat_id": "001_b00",
                        "kind": "silent",
                        "camera": "wide",
                        "action": "Maya at desk",
                        "duration_sec": 4.0,
                        "seed": 1001,
                    },
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Valid episode
# ---------------------------------------------------------------------------


def test_valid_v2_episode_returns_no_errors():
    v = EpisodeValidator()
    assert v.validate(_valid_v2_episode()) == []


def test_valid_v2_file_returns_no_errors(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(_valid_v2_episode()))
    v = EpisodeValidator()
    assert v.validate_file(path) == []


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------


def test_wrong_schema_version_returns_error():
    ep = _valid_v2_episode()
    ep["schema_version"] = "1.0"
    errors = EpisodeValidator().validate(ep)
    assert any("schema_version" in e for e in errors)


def test_missing_schema_version_returns_error():
    ep = _valid_v2_episode()
    del ep["schema_version"]
    errors = EpisodeValidator().validate(ep)
    assert len(errors) > 0


# ---------------------------------------------------------------------------
# Environment references
# ---------------------------------------------------------------------------


def test_unknown_environment_ref_returns_error():
    ep = _valid_v2_episode()
    ep["scenes"][0]["environment"] = "nonexistent_env"
    errors = EpisodeValidator().validate(ep)
    assert any("nonexistent_env" in e for e in errors)


def test_known_environment_ref_is_ok():
    ep = _valid_v2_episode()
    ep["scenes"][0]["environment"] = "maya_desk"
    assert EpisodeValidator().validate(ep) == []


# ---------------------------------------------------------------------------
# Character references
# ---------------------------------------------------------------------------


def test_unknown_character_ref_returns_error():
    ep = _valid_v2_episode()
    ep["scenes"][0]["characters_present"].append("ghost_char")
    errors = EpisodeValidator().validate(ep)
    assert any("ghost_char" in e for e in errors)


# ---------------------------------------------------------------------------
# Beat ID uniqueness
# ---------------------------------------------------------------------------


def test_duplicate_beat_id_returns_error():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append({"beat_id": "001_b00", "kind": "silent", "seed": 1002})
    errors = EpisodeValidator().validate(ep)
    assert any("Duplicate" in e for e in errors)


# ---------------------------------------------------------------------------
# Speech beats require text + speaker
# ---------------------------------------------------------------------------


def test_speech_beat_missing_text_returns_error():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "speaker": "maya", "seed": 2}
    )
    errors = EpisodeValidator().validate(ep)
    assert any("text" in e.lower() or "missing" in e.lower() for e in errors)


def test_speech_beat_missing_speaker_returns_error():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "text": "Hello!", "seed": 2}
    )
    errors = EpisodeValidator().validate(ep)
    assert any("speaker" in e.lower() for e in errors)


def test_speech_beat_with_text_and_speaker_is_ok():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "speaker": "maya", "text": "Hello!", "seed": 2}
    )
    assert EpisodeValidator().validate(ep) == []


# ---------------------------------------------------------------------------
# File errors
# ---------------------------------------------------------------------------


def test_missing_file_returns_error():
    v = EpisodeValidator()
    errors = v.validate_file(Path("/nonexistent/path/episode.json"))
    assert len(errors) > 0


def test_invalid_json_returns_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ this is not json }")
    errors = EpisodeValidator().validate_file(path)
    assert len(errors) > 0
    assert any("JSON" in e or "parse" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Validate episode_01.json
# ---------------------------------------------------------------------------


def test_episode_01_validates_cleanly():
    ep_path = Path(__file__).parent.parent / "episode_01.json"
    errors = EpisodeValidator().validate_file(ep_path)
    # episode_01 has no speech beats yet, so no speech-related errors expected
    assert errors == [], f"Unexpected errors: {errors}"


def test_episode_02_validates_cleanly():
    ep_path = Path(__file__).parent.parent / "episode_02.json"
    errors = EpisodeValidator().validate_file(ep_path)
    assert errors == [], f"Unexpected errors: {errors}"


# ---------------------------------------------------------------------------
# Strict mode
# ---------------------------------------------------------------------------


def test_strict_speech_beat_missing_text_returns_error():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "speaker": "maya", "seed": 2}
    )
    errors = EpisodeValidator().validate(ep, strict=True)
    assert any("text" in e.lower() or "missing" in e.lower() for e in errors)


def test_strict_speech_beat_missing_speaker_returns_error():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "text": "Hello!", "seed": 2}
    )
    errors = EpisodeValidator().validate(ep, strict=True)
    assert any("speaker" in e.lower() for e in errors)


def test_strict_unknown_speaker_returns_error():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "speaker": "ghost", "text": "Hi", "seed": 2}
    )
    errors = EpisodeValidator().validate(ep, strict=True)
    assert any("ghost" in e for e in errors)


def test_strict_valid_speech_beat_passes():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "speaker": "maya", "text": "Hello!", "seed": 2}
    )
    assert EpisodeValidator().validate(ep, strict=True) == []


def test_non_strict_skips_speech_checks():
    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "speaker": "ghost", "seed": 2}
    )
    errors = EpisodeValidator().validate(ep, strict=False)
    assert not any("ghost" in e for e in errors)


# ---------------------------------------------------------------------------
# Structural validation (jsonschema fallback)
# ---------------------------------------------------------------------------


def test_structural_validate_missing_fields():
    from sitcom_pilot.validator import EpisodeValidator

    v = EpisodeValidator()
    with patch("sitcom_pilot.validator._JSONSCHEMA_AVAILABLE", False):
        errors = v.validate({"schema_version": "2.0"})
    assert any("show" in e for e in errors)
    assert any("title" in e for e in errors)
    assert any("cast" in e for e in errors)
    assert any("environments" in e for e in errors)
    assert any("scenes" in e for e in errors)


def test_structural_validate_scenes_not_list():
    from sitcom_pilot.validator import EpisodeValidator

    v = EpisodeValidator()
    with patch("sitcom_pilot.validator._JSONSCHEMA_AVAILABLE", False):
        errors = v.validate({"schema_version": "2.0", "scenes": "bad", "cast": {}, "environments": {}, "show": "x", "title": "y"})
    assert any("list" in e.lower() for e in errors)


def test_structural_validate_cast_not_dict():
    from sitcom_pilot.validator import EpisodeValidator

    v = EpisodeValidator()
    with patch("sitcom_pilot.validator._JSONSCHEMA_AVAILABLE", False):
        errors = v.validate({"schema_version": "2.0", "scenes": [], "cast": "bad", "environments": {}, "show": "x", "title": "y"})
    assert any("cast" in e.lower() for e in errors)


def test_structural_validate_scene_missing_fields():
    from sitcom_pilot.validator import EpisodeValidator

    v = EpisodeValidator()
    with patch("sitcom_pilot.validator._JSONSCHEMA_AVAILABLE", False):
        errors = v.validate({
            "schema_version": "2.0",
            "show": "x",
            "title": "y",
            "cast": {},
            "environments": {},
            "scenes": [{"scene_id": "001"}],
        })
    assert any("environment" in e for e in errors)


def test_structural_validate_beat_missing_fields():
    from sitcom_pilot.validator import EpisodeValidator

    v = EpisodeValidator()
    with patch("sitcom_pilot.validator._JSONSCHEMA_AVAILABLE", False):
        errors = v.validate({
            "schema_version": "2.0",
            "show": "x",
            "title": "y",
            "cast": {},
            "environments": {},
            "scenes": [
                {
                    "scene_id": "001",
                    "environment": "env",
                    "characters_present": [],
                    "beats": [{"kind": "silent"}],
                }
            ],
        })
    assert any("beat_id" in e for e in errors)


def test_structural_validate_invalid_beat_kind():
    from sitcom_pilot.validator import EpisodeValidator

    v = EpisodeValidator()
    with patch("sitcom_pilot.validator._JSONSCHEMA_AVAILABLE", False):
        errors = v.validate({
            "schema_version": "2.0",
            "show": "x",
            "title": "y",
            "cast": {},
            "environments": {},
            "scenes": [
                {
                    "scene_id": "001",
                    "environment": "env",
                    "characters_present": [],
                    "beats": [{"beat_id": "b1", "kind": "invalid_kind"}],
                }
            ],
        })
    assert any("speech" in e.lower() or "silent" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# CLI main()
# ---------------------------------------------------------------------------


def test_main_valid_file(capsys):
    from sitcom_pilot.validator import main

    ep_path = Path(__file__).parent.parent / "episode_01.json"
    exit_code = main([str(ep_path)])
    assert exit_code == 0
    assert "OK" in capsys.readouterr().out


def test_main_invalid_file(tmp_path, capsys):
    from sitcom_pilot.validator import main

    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": "1.0"}')
    exit_code = main([str(bad)])
    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_quiet_flag(tmp_path, capsys):
    from sitcom_pilot.validator import main

    ep_path = Path(__file__).parent.parent / "episode_01.json"
    exit_code = main([str(ep_path), "--quiet"])
    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_main_strict_flag(tmp_path, capsys):
    from sitcom_pilot.validator import main

    ep = _valid_v2_episode()
    ep["scenes"][0]["beats"].append(
        {"beat_id": "001_b01", "kind": "speech", "speaker": "ghost", "text": "Hi", "seed": 2}
    )
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(ep))
    exit_code = main([str(path), "--strict"])
    assert exit_code == 1
    output = capsys.readouterr().out
    assert "FAIL" in output
    assert "ghost" in output


def test_main_multiple_files(capsys):
    from sitcom_pilot.validator import main

    ep_path = Path(__file__).parent.parent / "episode_01.json"
    ep2_path = Path(__file__).parent.parent / "episode_02.json"
    exit_code = main([str(ep_path), str(ep2_path)])
    assert exit_code == 0


def test_main_nonexistent_file(capsys):
    from sitcom_pilot.validator import main

    exit_code = main(["/nonexistent/path.json"])
    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out
