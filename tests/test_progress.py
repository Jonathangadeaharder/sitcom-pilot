from __future__ import annotations

import pytest

from showrunner.progress import (
    BeatProgressEvent,
    NullProgressCallback,
    ProgressTracker,
    RichRenderProgress,
)

# ---------------------------------------------------------------------------
# ProgressTracker (existing)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# BeatProgressEvent
# ---------------------------------------------------------------------------


class TestBeatProgressEvent:
    def test_creates_event(self):
        event = BeatProgressEvent(
            scene_id="001",
            beat_id="001_001",
            beat_index=0,
            total_beats=5,
            status="running",
        )
        assert event.scene_id == "001"
        assert event.beat_id == "001_001"
        assert event.beat_index == 0
        assert event.total_beats == 5
        assert event.status == "running"

    def test_immutable(self):
        event = BeatProgressEvent(
            scene_id="001",
            beat_id="001_001",
            beat_index=0,
            total_beats=5,
            status="done",
        )
        with pytest.raises(AttributeError):
            event.status = "failed"


# ---------------------------------------------------------------------------
# NullProgressCallback
# ---------------------------------------------------------------------------


class TestNullProgressCallback:
    def test_does_not_raise(self):
        cb = NullProgressCallback()
        event = BeatProgressEvent(
            scene_id="001",
            beat_id="001_001",
            beat_index=0,
            total_beats=5,
            status="running",
        )
        cb(event)


# ---------------------------------------------------------------------------
# RichRenderProgress
# ---------------------------------------------------------------------------


class TestRichRenderProgress:
    def test_context_manager(self):
        with RichRenderProgress() as on_progress:
            event = BeatProgressEvent(
                scene_id="001",
                beat_id="001_001",
                beat_index=0,
                total_beats=1,
                status="done",
            )
            on_progress(event)

    def test_multiple_events_same_scene(self):
        events: list[BeatProgressEvent] = []
        with RichRenderProgress() as on_progress:
            for i in range(3):
                event = BeatProgressEvent(
                    scene_id="001",
                    beat_id=f"001_00{i + 1}",
                    beat_index=i,
                    total_beats=3,
                    status="done",
                )
                on_progress(event)
                events.append(event)
        assert len(events) == 3

    def test_multiple_scenes(self):
        with RichRenderProgress() as on_progress:
            for i in range(2):
                event = BeatProgressEvent(
                    scene_id=f"scene_{i}",
                    beat_id=f"{i}_001",
                    beat_index=0,
                    total_beats=1,
                    status="done",
                )
                on_progress(event)

    def test_running_status(self):
        with RichRenderProgress() as on_progress:
            on_progress(
                BeatProgressEvent(
                    scene_id="001",
                    beat_id="001_001",
                    beat_index=0,
                    total_beats=2,
                    status="running",
                )
            )
            on_progress(
                BeatProgressEvent(
                    scene_id="001",
                    beat_id="001_001",
                    beat_index=0,
                    total_beats=2,
                    status="done",
                )
            )

    def test_failed_status(self):
        with RichRenderProgress() as on_progress:
            on_progress(
                BeatProgressEvent(
                    scene_id="001",
                    beat_id="001_001",
                    beat_index=0,
                    total_beats=1,
                    status="failed",
                )
            )
