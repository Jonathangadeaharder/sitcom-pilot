from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from showrunner.cast_manifest import CastManifest, CharacterProfile, CharacterRef
from showrunner.loader import EpisodeLoader
from showrunner.paths import RunPaths
from showrunner.scene_render import BeatStatus, plan_beats, render_episode, render_scene
from showrunner.validator import EpisodeValidator

EPISODE_02 = Path(__file__).resolve().parent.parent / "episode_02.json"


@pytest.fixture
def episode_02():
    return EpisodeLoader().load(EPISODE_02)


@pytest.fixture
def manifest_02(episode_02):
    m = CastManifest()
    for slug, char in episode_02.cast.items():
        m.add(
            CharacterProfile(
                name=char.name,
                slug=slug,
                visual=char.visual,
                refs=CharacterRef(),
            )
        )
    return m


@pytest.fixture
def paths(tmp_path):
    rp = RunPaths(tmp_path, run_id="test-run")
    rp.ensure_dirs()
    return rp


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.text2image.side_effect = lambda prompt, path, **kw: _write_dummy(path)
    client.text2speech.side_effect = lambda text, path, **kw: _write_dummy(path)
    client.image2video.side_effect = lambda img, prompt, path, **kw: _write_dummy(path)
    return client


def _write_dummy(path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x00" * 16)
    return p


def _read_episode_02_data():
    with open(EPISODE_02) as f:
        return json.load(f)


class TestPlanBeats:
    def test_creates_jobs_for_all_beats(self, episode_02, manifest_02, paths):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        all_beats = [b for s in episode_02.scenes for b in s.beats]
        assert len(jobs) == len(all_beats)

    def test_jobs_have_correct_scene(self, episode_02, manifest_02, paths):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        scene_001_jobs = [j for j in jobs if j.scene_id == "001"]
        assert len(scene_001_jobs) == len(episode_02.scenes[0].beats)

    def test_jobs_pending_initially(self, episode_02, manifest_02, paths):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        assert all(j.status == BeatStatus.PENDING for j in jobs)

    def test_speech_beats_marked_needs_audio(self, episode_02, manifest_02, paths):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        speech_jobs = [j for j in jobs if j.kind == "speech"]
        assert all(j.needs_audio for j in speech_jobs)

    def test_silent_beats_no_audio(self, episode_02, manifest_02, paths):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        silent_jobs = [j for j in jobs if j.kind == "silent"]
        assert all(not j.needs_audio for j in silent_jobs)


class TestRenderScene:
    def test_render_scene_001(self, episode_02, manifest_02, paths, mock_client):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        scene = episode_02.scenes[0]
        scene_jobs = [j for j in jobs if j.scene_id == "001"]
        report = render_scene(scene, scene_jobs, mock_client, manifest_02, episode_02)
        assert report.scene_id == "001"
        assert report.total_beats == len(scene.beats)
        assert report.completed == report.total_beats

    def test_render_scene_creates_files(self, episode_02, manifest_02, paths, mock_client):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        scene = episode_02.scenes[0]
        scene_jobs = [j for j in jobs if j.scene_id == "001"]
        render_scene(scene, scene_jobs, mock_client, manifest_02, episode_02)
        for j in scene_jobs:
            assert j.image_path.exists(), f"Missing image for {j.beat_id}"

    def test_render_failure_reported(self, episode_02, manifest_02, paths):
        failing_client = MagicMock()
        failing_client.text2image.side_effect = RuntimeError("boom")
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        scene = episode_02.scenes[0]
        scene_jobs = [j for j in jobs if j.scene_id == "001"]
        report = render_scene(scene, scene_jobs, failing_client, manifest_02, episode_02)
        assert report.failed == report.total_beats
        assert len(report.errors) == report.total_beats


class TestRenderEpisode:
    def test_full_episode(self, episode_02, manifest_02, paths, mock_client):
        reports = render_episode(episode_02, manifest_02, paths, mock_client, episode_id="002")
        assert len(reports) == len(episode_02.scenes)
        assert all(r.completed == r.total_beats for r in reports)

    def test_report_saved(self, episode_02, manifest_02, paths, mock_client):
        render_episode(episode_02, manifest_02, paths, mock_client, episode_id="002")
        report_path = paths.run_dir / "render_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert isinstance(data, list)
        assert len(data) == len(episode_02.scenes)

    def test_cache_hit_skips_generation(self, episode_02, manifest_02, paths, mock_client):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        for j in jobs:
            if j.scene_id == "001":
                _write_dummy(j.image_path)
        scene = episode_02.scenes[0]
        scene_jobs = [j for j in jobs if j.scene_id == "001"]
        render_scene(scene, scene_jobs, mock_client, manifest_02, episode_02)
        first_job = scene_jobs[0]
        text2img_calls = [
            c
            for c in mock_client.text2image.call_args_list
            if str(c[0][1]) == str(first_job.image_path)
        ]
        assert len(text2img_calls) == 0


class TestIntegrationRenderScene001:
    """Integration test: load → validate → plan → render → verify for scene 001."""

    def test_full_pipeline(self, episode_02, manifest_02, paths, mock_client):
        data = _read_episode_02_data()
        validator = EpisodeValidator()
        errors = validator.validate(data)
        assert not errors, f"Validation errors: {errors}"

        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        scene = episode_02.scenes[0]
        scene_jobs = [j for j in jobs if j.scene_id == "001"]

        report = render_scene(scene, scene_jobs, mock_client, manifest_02, episode_02)

        assert report.scene_id == "001"
        assert report.completed == len(scene.beats)
        assert report.failed == 0

        for j in scene_jobs:
            assert j.image_path.exists(), f"Missing image for {j.beat_id}"
            assert j.image_path.stat().st_size > 0, f"Empty image for {j.beat_id}"
            assert j.beat_id.startswith("001_b")
            assert j.scene_id == "001"

    def test_speech_beats_have_audio_output(self, episode_02, manifest_02, paths, mock_client):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        scene = episode_02.scenes[0]
        scene_jobs = [j for j in jobs if j.scene_id == "001"]

        render_scene(scene, scene_jobs, mock_client, manifest_02, episode_02)

        for j in scene_jobs:
            if j.needs_audio:
                assert j.audio_path.exists(), f"Missing audio for speech beat {j.beat_id}"
                assert j.audio_path.stat().st_size > 0, f"Empty audio for {j.beat_id}"
                assert j.speaker == "maya"
                assert j.text
            else:
                assert not j.audio_path.exists(), f"Silent beat {j.beat_id} has audio"

    def test_scene_001_beat_seeds_correct(self, episode_02, manifest_02, paths, mock_client):
        jobs = plan_beats(episode_02, manifest_02, paths, episode_id="002")
        scene = episode_02.scenes[0]
        scene_jobs = [j for j in jobs if j.scene_id == "001"]

        for j, beat in zip(scene_jobs, scene.beats, strict=False):
            assert j.seed == beat.seed, f"{j.beat_id}: seed mismatch"
            assert j.beat_id == beat.beat_id
            assert j.kind == beat.kind

    def test_validation_rejects_bad_schema(self):
        data = _read_episode_02_data()
        validator = EpisodeValidator()
        errors = validator.validate(data)
        assert not errors

        bad = dict(data)
        bad["schema_version"] = "1.5"
        errors = validator.validate(bad)
        assert errors
        assert any("schema_version" in e for e in errors)
