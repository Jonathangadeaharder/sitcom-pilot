from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from sitcom_pilot.cast_manifest import CastManifest, CharacterProfile
from sitcom_pilot.loader import (
    BeatData,
    CharacterData,
    EpisodeData,
    SceneData,
    VoiceConfig,
)
from sitcom_pilot.paths import RunPaths
from sitcom_pilot.scene_render import (
    BeatJob,
    SceneReport,
    allocate_durations,
    plan_beats,
    render_episode,
    render_scene,
)


@pytest.fixture
def manifest():
    return CastManifest(
        characters={
            "maya": CharacterProfile(
                slug="maya",
                visual="woman in hoodie",
                voice=VoiceConfig(provider="mlx-audio", voice_id="maya_v1"),
            ),
        },
    )


@pytest.fixture
def episode():
    return EpisodeData(
        title="Test",
        cast={
            "maya": CharacterData(
                name="Maya",
                visual="woman in hoodie",
                voice=VoiceConfig(provider="mlx-audio", voice_id="maya_v1"),
            ),
        },
        environments={},
        scenes=[
            SceneData(
                scene_id="001",
                environment="office",
                characters_present=["maya"],
                beats=[
                    BeatData(
                        beat_id="001_001",
                        kind="speech",
                        speaker="maya",
                        text="Hello!",
                        seed=42,
                        duration_sec=3.0,
                    ),
                    BeatData(
                        beat_id="001_002",
                        kind="silent",
                        action="Maya walks to desk",
                        seed=43,
                        duration_sec=2.0,
                    ),
                ],
            ),
        ],
    )


class TestPlanBeats:
    def test_creates_jobs(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        assert len(jobs) == 2
        assert jobs[0].beat_id == "001_001"
        assert jobs[0].kind == "speech"
        assert jobs[0].needs_audio
        assert not jobs[1].needs_audio

    def test_paths_assigned(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        assert "001_001" in str(jobs[0].image_path)
        assert jobs[0].image_path.suffix == ".png"


class TestAllocateDurations:
    def test_scales_down(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=5.0,
                needs_audio=False,
            ),
            BeatJob(
                scene_id="s",
                beat_id="c",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=5.0,
                needs_audio=False,
            ),
        ]
        result = allocate_durations(jobs, 6.0)
        assert result[0].duration_sec == pytest.approx(3.0)

    def test_no_change_under_budget(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=2.0,
                needs_audio=False,
            ),
        ]
        result = allocate_durations(jobs, 10.0)
        assert result[0].duration_sec == 2.0

    def test_empty(self):
        assert allocate_durations([], 10.0) == []


class TestRenderScene:
    def test_renders_beats(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        client = MagicMock()
        client.text2image.return_value = tmp_path / "img.png"
        client.text2speech.return_value = tmp_path / "aud.wav"
        client.image2video.return_value = tmp_path / "vid.mp4"

        report = render_scene(episode.scenes[0], jobs, client, manifest, episode)
        assert report.total_beats == 2
        assert report.completed == 2
        assert report.failed == 0

    def test_failure_isolation(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        client = MagicMock()
        client.text2image.side_effect = RuntimeError("boom")

        report = render_scene(episode.scenes[0], jobs, client, manifest, episode)
        assert report.failed == 2


class TestSceneReport:
    def test_success_rate(self):
        r = SceneReport(scene_id="001", total_beats=4, completed=3)
        assert r.success_rate == pytest.approx(0.75)

    def test_success_rate_zero(self):
        r = SceneReport(scene_id="001")
        assert r.success_rate == 0.0


class TestRenderEpisode:
    def test_full_pipeline(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        client = MagicMock()
        client.text2image.return_value = tmp_path / "img.png"
        client.text2speech.return_value = tmp_path / "aud.wav"
        client.image2video.return_value = tmp_path / "vid.mp4"

        reports = render_episode(episode, manifest, paths, client)
        assert len(reports) == 1
        assert reports[0].completed == 2
        report_path = paths.run_dir / "render_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data[0]["scene_id"] == "001"


class TestCacheResume:
    def test_skips_existing_image(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        jobs[0].image_path.parent.mkdir(parents=True, exist_ok=True)
        jobs[0].image_path.write_bytes(b"fake")
        client = MagicMock()

        render_scene(episode.scenes[0], jobs, client, manifest, episode)
        client.text2image.assert_called_once()
