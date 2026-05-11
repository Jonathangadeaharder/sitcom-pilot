from __future__ import annotations

import json

import pytest

from showrunner_utils.helpers import ensure_dir, load_json, save_json


class TestEnsureDir:
    def test_creates_directory(self, tmp_path):
        d = tmp_path / "a" / "b" / "c"
        result = ensure_dir(d)
        assert result == d
        assert d.exists()

    def test_returns_path(self, tmp_path):
        result = ensure_dir(tmp_path)
        assert result == tmp_path

    def test_idempotent(self, tmp_path):
        d = tmp_path / "sub"
        ensure_dir(d)
        ensure_dir(d)
        assert d.exists()


class TestLoadJson:
    def test_loads_file(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text(json.dumps({"key": "value"}))
        assert load_json(p) == {"key": "value"}

    def test_empty_object(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("{}")
        assert load_json(p) == {}

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_json(tmp_path / "nonexistent.json")

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            load_json(p)

    def test_list_top_level(self, tmp_path):
        p = tmp_path / "list.json"
        p.write_text(json.dumps([1, 2, 3]))
        assert load_json(p) == [1, 2, 3]


class TestSaveJson:
    def test_saves_file(self, tmp_path):
        p = tmp_path / "out.json"
        save_json({"a": 1}, p)
        assert p.exists()
        assert json.loads(p.read_text()) == {"a": 1}

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "deep" / "nested" / "out.json"
        save_json({"x": "y"}, p)
        assert p.exists()
        assert json.loads(p.read_text()) == {"x": "y"}

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text(json.dumps({"old": "data"}))
        save_json({"new": "data"}, p)
        assert json.loads(p.read_text()) == {"new": "data"}

    def test_empty_dict(self, tmp_path):
        p = tmp_path / "out.json"
        save_json({}, p)
        assert json.loads(p.read_text()) == {}
