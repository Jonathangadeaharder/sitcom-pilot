import pytest
from pathlib import Path
from sitcom_pilot.progress import ProgressTracker


def test_mark_done_creates_entry(tmp_path):
    tracker = ProgressTracker(state_file=tmp_path / "state.json")
    tracker.mark_done("S01_SH01")
    assert tracker.is_done("S01_SH01")


def test_is_done_returns_false_for_unknown(tmp_path):
    tracker = ProgressTracker(state_file=tmp_path / "state.json")
    assert tracker.is_done("S99_SH99") is False


def test_persists_across_instances(tmp_path):
    state = tmp_path / "state.json"
    t1 = ProgressTracker(state_file=state)
    t1.mark_done("S01_SH01")
    t1.mark_done("S01_SH02")
    t2 = ProgressTracker(state_file=state)
    assert t2.is_done("S01_SH01")
    assert t2.is_done("S01_SH02")
    assert t2.is_done("S02_SH01") is False


def test_completed_shot_ids_returns_all(tmp_path):
    tracker = ProgressTracker(state_file=tmp_path / "state.json")
    tracker.mark_done("A")
    tracker.mark_done("B")
    tracker.mark_done("C")
    assert set(tracker.completed_shot_ids()) == {"A", "B", "C"}


def test_reset_clears_all(tmp_path):
    tracker = ProgressTracker(state_file=tmp_path / "state.json")
    tracker.mark_done("X")
    tracker.reset()
    assert tracker.is_done("X") is False
    assert tracker.completed_shot_ids() == []


def test_load_handles_corrupt_json(tmp_path):
    state = tmp_path / "state.json"
    state.write_text("NOT VALID JSON{{{")
    tracker = ProgressTracker(state_file=state)
    assert tracker.completed_shot_ids() == []


def test_save_creates_parent_directory(tmp_path):
    state = tmp_path / "subdir" / "deep" / "state.json"
    tracker = ProgressTracker(state_file=state)
    tracker.mark_done("X")
    assert state.exists()


def test_save_writes_sorted_json(tmp_path):
    state = tmp_path / "state.json"
    tracker = ProgressTracker(state_file=state)
    tracker.mark_done("C")
    tracker.mark_done("A")
    tracker.mark_done("B")
    import json
    data = json.loads(state.read_text())
    assert data["completed"] == ["A", "B", "C"]


def test_load_handles_missing_key(tmp_path):
    state = tmp_path / "state.json"
    state.write_text('{"other_key": []}')
    tracker = ProgressTracker(state_file=state)
    assert tracker.completed_shot_ids() == []
