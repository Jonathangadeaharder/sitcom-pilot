"""Tests for showrunner.manifest — RunManifest run record format."""
from __future__ import annotations

import json

from showrunner.manifest import BeatRecord, RunManifest, SceneRecord


def test_create_sets_run_id_and_episode_path(tmp_path):
    ep = tmp_path / "episode.json"
    m = RunManifest.create("run-001", ep, "The Bug", schema_version="2.0")
    assert m.run_id == "run-001"
    assert m.episode_path == str(ep)
    assert m.episode_title == "The Bug"
    assert m.schema_version == "2.0"


def test_create_sets_started_at(tmp_path):
    ep = tmp_path / "ep.json"
    m = RunManifest.create("r1", ep, "T")
    assert m.started_at != ""


def test_initial_status_is_running(tmp_path):
    m = RunManifest.create("r1", tmp_path / "ep.json", "T")
    assert m.status == "running"


def test_finish_sets_status_and_finished_at(tmp_path):
    m = RunManifest.create("r1", tmp_path / "ep.json", "T")
    m.finish("completed")
    assert m.status == "completed"
    assert m.finished_at != ""


def test_save_and_load_roundtrip(tmp_path):
    ep = tmp_path / "ep.json"
    m = RunManifest.create("run-42", ep, "Test Episode")
    m.scenes.append(
        SceneRecord(
            scene_id="001",
            title="Scene 1",
            beats=[
                BeatRecord("001_b00", "001", "silent", "rendered", prompt_id="p1"),
                BeatRecord("001_b01", "001", "speech", "failed", error="timeout"),
            ],
        )
    )
    m.finish("partial")
    path = tmp_path / "manifest.json"
    m.save(path)

    loaded = RunManifest.load(path)
    assert loaded.run_id == "run-42"
    assert loaded.status == "partial"
    assert len(loaded.scenes) == 1
    assert loaded.scenes[0].scene_id == "001"
    assert len(loaded.scenes[0].beats) == 2
    assert loaded.scenes[0].beats[0].prompt_id == "p1"
    assert loaded.scenes[0].beats[1].error == "timeout"


def test_scene_record_counts(tmp_path):
    sc = SceneRecord(
        scene_id="001",
        beats=[
            BeatRecord("b1", "001", "silent", "rendered"),
            BeatRecord("b2", "001", "speech", "rendered"),
            BeatRecord("b3", "001", "silent", "failed"),
            BeatRecord("b4", "001", "silent", "pending"),
        ],
    )
    assert sc.total == 4
    assert sc.rendered == 2
    assert sc.failed == 1


def test_summary_counts_across_scenes(tmp_path):
    ep = tmp_path / "ep.json"
    m = RunManifest.create("r1", ep, "T")
    m.scenes.append(
        SceneRecord(
            "001",
            beats=[
                BeatRecord("b1", "001", "silent", "rendered"),
                BeatRecord("b2", "001", "silent", "failed"),
            ],
        )
    )
    m.scenes.append(
        SceneRecord(
            "002",
            beats=[
                BeatRecord("b3", "002", "speech", "pending"),
            ],
        )
    )
    s = m.summary()
    assert s["total"] == 3
    assert s["rendered"] == 1
    assert s["failed"] == 1
    assert s["pending"] == 1


def test_save_creates_parent_dirs(tmp_path):
    ep = tmp_path / "ep.json"
    m = RunManifest.create("r1", ep, "T")
    nested = tmp_path / "deep" / "nested" / "manifest.json"
    m.save(nested)
    assert nested.exists()


def test_manifest_json_has_correct_keys(tmp_path):
    ep = tmp_path / "ep.json"
    m = RunManifest.create("r1", ep, "T")
    path = tmp_path / "manifest.json"
    m.save(path)
    with open(path) as f:
        data = json.load(f)
    assert "run_id" in data
    assert "episode_path" in data
    assert "started_at" in data
    assert "status" in data
    assert "scenes" in data
