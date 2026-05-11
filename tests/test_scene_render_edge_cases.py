from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from showrunner.cast_manifest import CastManifest
from showrunner.loader import EpisodeData, SceneData
from showrunner.scene_render import (
    BeatJob,
    BeatStatus,
    SceneReport,
    _render_beat,
    _save_report,
    allocate_durations,
)


class TestBeatStatus:
    def test_enum_values(self):
        assert BeatStatus.PENDING.value == "pending"
        assert BeatStatus.RUNNING.value == "running"
        assert BeatStatus.DONE.value == "done"
        assert BeatStatus.FAILED.value == "failed"
        assert BeatStatus.SKIPPED.value == "skipped"


class TestAllocateDurationsEdgeCases:
    def _make_job(self, beat_id: str, dur: float):
        return BeatJob(
            scene_id="s",
            beat_id=beat_id,
            kind="silent",
            prompt="",
            seed=0,
            duration_sec=dur,
            needs_audio=False,
        )

    def test_zero_current_total_distributes_evenly(self):
        jobs = [self._make_job("b1", 0.0), self._make_job("b2", 0.0)]
        allocate_durations(jobs, 10.0)
        assert jobs[0].duration_sec == pytest.approx(5.0)
        assert jobs[1].duration_sec == pytest.approx(5.0)

    def test_exact_budget_no_change(self):
        jobs = [self._make_job("b", 5.0)]
        allocate_durations(jobs, 5.0)
        assert jobs[0].duration_sec == 5.0

    def test_under_budget_no_scale_up(self):
        jobs = [self._make_job("b", 3.0)]
        allocate_durations(jobs, 10.0)
        assert jobs[0].duration_sec == 3.0


class TestSaveReport:
    def test_saves_report_file(self, tmp_path):
        from showrunner.paths import RunPaths

        paths = RunPaths(tmp_path, "test-save")
        paths.ensure_dirs()
        reports = [
            SceneReport(scene_id="001", total_beats=2, completed=2, duration_sec=6.0),
            SceneReport(scene_id="002", total_beats=1, completed=0, failed=1, errors=["b1: boom"]),
        ]
        _save_report(paths, reports)
        report_path = paths.run_dir / "render_report.json"
        assert report_path.exists()
        import json

        data = json.loads(report_path.read_text())
        assert len(data) == 2
        assert data[0]["scene_id"] == "001"
        assert data[0]["success_rate"] == 1.0
        assert data[1]["scene_id"] == "002"
        assert data[1]["success_rate"] == 0.0
        assert data[1]["errors"] == ["b1: boom"]


class TestRenderBeatEdgeCases:
    def test_retry_then_succeeds(self, tmp_path):
        client = MagicMock()
        client.text2image.side_effect = [RuntimeError("first fail"), tmp_path / "img.png"]
        client.image2video.return_value = tmp_path / "vid.mp4"

        scene = SceneData(scene_id="001", environment="office", characters_present=[])
        episode = EpisodeData(title="T", cast={}, environments={}, scenes=[scene])
        manifest = CastManifest()
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="silent",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=False,
            image_path=tmp_path / "img.png",
            video_path=tmp_path / "vid.mp4",
        )

        result = _render_beat(job, client, manifest, episode, scene, max_retries=2)
        assert result.status == BeatStatus.DONE
        assert result.error == ""

    def test_all_retries_exhausted(self, tmp_path):
        client = MagicMock()
        client.text2image.side_effect = RuntimeError("always fail")

        scene = SceneData(scene_id="001", environment="office", characters_present=[])
        episode = EpisodeData(title="T", cast={}, environments={}, scenes=[scene])
        manifest = CastManifest()
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="silent",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=False,
            image_path=tmp_path / "img.png",
            video_path=tmp_path / "vid.mp4",
        )

        result = _render_beat(job, client, manifest, episode, scene, max_retries=1)
        assert result.status == BeatStatus.FAILED
        assert "always fail" in result.error


class TestSceneReportEdgeCases:
    def test_skipped_beats_counted(self):
        r = SceneReport(scene_id="001", total_beats=3, completed=1, skipped=2)
        assert r.skipped == 2

    def test_errors_listed(self):
        r = SceneReport(scene_id="001", total_beats=2, failed=2, errors=["b1: err", "b2: err"])
        assert len(r.errors) == 2
