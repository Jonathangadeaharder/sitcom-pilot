from __future__ import annotations

import json
from pathlib import Path
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


class TestSilentBeatVideo:
    def test_silent_beat_generates_video(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        silent_job = [j for j in jobs if not j.needs_audio][0]
        silent_job.image_path.parent.mkdir(parents=True, exist_ok=True)
        client = MagicMock()

        def fake_text2image(prompt, path, **kw):
            Path(path).write_bytes(b"img")
            return path

        client.text2image.side_effect = fake_text2image
        client.image2video.return_value = tmp_path / "vid.mp4"

        render_scene(episode.scenes[0], jobs, client, manifest, episode)

        client.image2video.assert_any_call(
            silent_job.image_path,
            silent_job.prompt,
            silent_job.video_path,
            audio_path=None,
            seed=silent_job.seed,
        )

    def test_speech_beat_passes_audio_to_video(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        speech_job = [j for j in jobs if j.needs_audio][0]
        speech_job.image_path.parent.mkdir(parents=True, exist_ok=True)
        speech_job.audio_path.parent.mkdir(parents=True, exist_ok=True)
        client = MagicMock()

        def fake_text2image(prompt, path, **kw):
            Path(path).write_bytes(b"img")
            return path

        def fake_text2speech(text, path, **kw):
            Path(path).write_bytes(b"aud")
            return path

        client.text2image.side_effect = fake_text2image
        client.text2speech.side_effect = fake_text2speech
        client.image2video.return_value = tmp_path / "vid.mp4"

        render_scene(episode.scenes[0], jobs, client, manifest, episode)

        client.image2video.assert_any_call(
            speech_job.image_path,
            speech_job.prompt,
            speech_job.video_path,
            audio_path=speech_job.audio_path,
            seed=speech_job.seed,
        )


class TestCacheResume:
    def test_skips_existing_image(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        jobs[0].image_path.parent.mkdir(parents=True, exist_ok=True)
        jobs[0].image_path.write_bytes(b"fake")
        client = MagicMock()

        render_scene(episode.scenes[0], jobs, client, manifest, episode)
        client.text2image.assert_called_once()

    def test_skips_existing_audio(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        speech_job = [j for j in jobs if j.needs_audio][0]
        speech_job.image_path.parent.mkdir(parents=True, exist_ok=True)
        speech_job.audio_path.parent.mkdir(parents=True, exist_ok=True)
        speech_job.image_path.write_bytes(b"fake")
        speech_job.audio_path.write_bytes(b"fake")
        client = MagicMock()
        client.image2video.return_value = tmp_path / "vid.mp4"

        render_scene(episode.scenes[0], jobs, client, manifest, episode)

        client.text2speech.assert_not_called()
        assert speech_job.status.value == "done"
