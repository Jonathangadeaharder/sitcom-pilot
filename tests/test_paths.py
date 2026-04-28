"""Tests for sitcom_pilot.paths — RunPaths output directory contract."""
from __future__ import annotations

from sitcom_pilot.paths import RunPaths


def test_run_dir_uses_provided_run_id(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="test-run-001")
    assert rp.run_dir == tmp_path / "test-run-001"


def test_run_id_auto_generated_when_empty(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="")
    assert rp.run_id != ""
    assert len(rp.run_id) > 8


def test_beats_dir_is_under_run_dir(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.beats_dir == tmp_path / "r1" / "beats"


def test_audio_dir_is_under_run_dir(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.audio_dir == tmp_path / "r1" / "audio"


def test_assembly_dir_is_under_run_dir(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.assembly_dir == tmp_path / "r1" / "assembly"


def test_manifest_path(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.manifest_path == tmp_path / "r1" / "manifest.json"


def test_progress_path(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.progress_path == tmp_path / "r1" / "progress.json"


def test_beat_image_path(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.beat_image("001", "001_b01") == tmp_path / "r1" / "beats" / "001" / "001_b01.png"


def test_beat_video_path(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.beat_video("001", "001_b01") == tmp_path / "r1" / "beats" / "001" / "001_b01.mp4"


def test_beat_audio_path(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.beat_audio("001", "001_b01") == tmp_path / "r1" / "audio" / "001" / "001_b01.wav"


def test_episode_video_path(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    assert rp.episode_video == tmp_path / "r1" / "assembly" / "episode.mp4"


def test_ensure_dirs_creates_all_directories(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    rp.ensure_dirs()
    assert rp.beats_dir.exists()
    assert rp.audio_dir.exists()
    assert rp.assembly_dir.exists()
    assert rp.subtitles_dir.exists()


def test_ensure_scene_dirs_creates_scene_subdirectories(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    rp.ensure_scene_dirs("scene_001")
    assert (rp.beats_dir / "scene_001").exists()
    assert (rp.audio_dir / "scene_001").exists()
    assert (rp.subtitles_dir / "scene_001").exists()


def test_ensure_dirs_is_idempotent(tmp_path):
    rp = RunPaths(root=tmp_path, run_id="r1")
    rp.ensure_dirs()
    rp.ensure_dirs()  # Should not raise
    assert rp.beats_dir.exists()
