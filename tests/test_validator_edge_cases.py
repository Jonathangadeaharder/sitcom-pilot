from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from showrunner.validator import EpisodeValidator, ValidationError, main


class TestValidatorEdgeCases:
    def test_top_level_non_dict_returns_error(self, tmp_path):
        v = EpisodeValidator()
        p = tmp_path / "list.json"
        p.write_text(json.dumps([1, 2, 3]))
        errors = v.validate_file(p)
        assert any("object" in e.lower() for e in errors)

    def test_empty_dict_validates_version_error(self):
        v = EpisodeValidator()
        errors = v.validate({})
        assert any("schema_version" in e for e in errors)

    def _minimal_episode(self):
        return {
            "schema_version": "2.0",
            "cast": {},
            "environments": {},
            "scenes": [],
            "show": "x",
            "title": "y",
        }

    def test_schema_file_missing_returns_error(self):
        with patch("showrunner.validator._JSONSCHEMA_AVAILABLE", True):
            with patch("showrunner.validator._SCHEMA_PATH", Path("/nonexistent/schema.json")):
                v = EpisodeValidator()
                errors = v.validate(self._minimal_episode())
                assert any("Schema file not found" in e for e in errors)

    def test_jsonschema_validate_exception_returns_error(self):
        with patch("showrunner.validator._JSONSCHEMA_AVAILABLE", True):
            with patch("showrunner.validator._SCHEMA_PATH", Path(__file__)):
                v = EpisodeValidator()
                errors = v.validate(self._minimal_episode())
                assert any("JSON Schema validation error" in e for e in errors)

    def test_scene_object_not_dict_returns_error(self):
        v = EpisodeValidator()
        with patch("showrunner.validator._JSONSCHEMA_AVAILABLE", False):
            errors = v.validate(
                {
                    "schema_version": "2.0",
                    "show": "x",
                    "title": "y",
                    "cast": {},
                    "environments": {},
                    "scenes": ["not_a_dict"],
                }
            )
        assert any("object" in e.lower() for e in errors)

    def test_beat_object_not_dict_returns_error(self):
        v = EpisodeValidator()
        with patch("showrunner.validator._JSONSCHEMA_AVAILABLE", False):
            errors = v.validate(
                {
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
                            "beats": ["not_a_dict"],
                        }
                    ],
                }
            )
        assert any("object" in e.lower() for e in errors)

    def test_empty_beat_id_not_duplicated(self):
        v = EpisodeValidator()
        with patch("showrunner.validator._JSONSCHEMA_AVAILABLE", False):
            errors = v.validate(
                {
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
                            "beats": [
                                {"beat_id": "", "kind": "silent"},
                                {"beat_id": "", "kind": "silent"},
                            ],
                        }
                    ],
                }
            )
        assert not any("Duplicate" in e for e in errors)

    def test_scene_no_environment_ref_skips_check(self):
        v = EpisodeValidator()
        with patch("showrunner.validator._JSONSCHEMA_AVAILABLE", False):
            errors = v.validate(
                {
                    "schema_version": "2.0",
                    "show": "x",
                    "title": "y",
                    "cast": {},
                    "environments": {},
                    "scenes": [
                        {
                            "scene_id": "001",
                            "environment": "",
                            "characters_present": [],
                            "beats": [],
                        }
                    ],
                }
            )
        assert not any("environment" in e for e in errors)

    def test_strict_no_speech_checks_by_default(self):
        v = EpisodeValidator()
        errors = v.validate(
            {
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
                        "beats": [
                            {"beat_id": "b1", "kind": "speech", "speaker": "ghost", "seed": 1}
                        ],
                    }
                ],
            },
            strict=False,
        )
        assert not any("ghost" in e for e in errors)


class TestValidationError:
    def test_is_exception(self):
        assert issubclass(ValidationError, Exception)

    def test_can_be_raised(self):
        with pytest.raises(ValidationError):
            raise ValidationError("test error")


class TestMainEdgeCases:
    def test_main_nonexistent_file_with_quiet(self, capsys):
        exit_code = main(["/nonexistent/path.json", "--quiet"])
        assert exit_code == 1
        assert "FAIL" in capsys.readouterr().out
