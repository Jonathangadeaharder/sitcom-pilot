from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from showrunner.cast_manifest import CastManifest, CharacterProfile
from showrunner.loader import (
    BeatData,
    CharacterData,
    EpisodeData,
    SceneData,
    VoiceConfig,
)
from showrunner.paths import RunPaths
from showrunner.scene_render import (
    BeatJob,
    SceneReport,
    _render_audio,
    _render_image,
    _render_video,
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
        assert result[0].duration_sec == pytest.approx(2.0)

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
        assert r.success_rate == pytest.approx(0.0)


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


class TestProgressCallback:
    def test_render_scene_calls_progress(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        client = MagicMock()
        client.text2image.return_value = tmp_path / "img.png"
        client.text2speech.return_value = tmp_path / "aud.wav"
        client.image2video.return_value = tmp_path / "vid.mp4"

        events: list = []
        report = render_scene(
            episode.scenes[0],
            jobs,
            client,
            manifest,
            episode,
            progress_callback=events.append,
        )
        assert report.total_beats == 2
        assert len(events) == 4
        assert events[0].status == "running"
        assert events[1].status == "done"
        assert events[2].status == "running"
        assert events[3].status == "done"

    def test_render_episode_calls_progress(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        client = MagicMock()
        client.text2image.return_value = tmp_path / "img.png"
        client.text2speech.return_value = tmp_path / "aud.wav"
        client.image2video.return_value = tmp_path / "vid.mp4"

        events: list = []
        reports = render_episode(
            episode,
            manifest,
            paths,
            client,
            progress_callback=events.append,
        )
        assert len(reports) == 1
        assert len(events) == 4
        assert events[0].status == "running"
        assert events[-1].status == "done"

    def test_progress_reports_failure(self, episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(episode, manifest, paths)
        client = MagicMock()
        client.text2image.side_effect = RuntimeError("boom")

        events: list = []
        report = render_scene(
            episode.scenes[0],
            jobs,
            client,
            manifest,
            episode,
            progress_callback=events.append,
        )
        assert report.failed == 2
        assert all(e.status == "failed" for e in events if e.status != "running")


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


class TestRenderImage:
    def test_renders_image_when_not_cached(self, tmp_path):
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="silent",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=False,
            image_path=tmp_path / "img.png",
        )
        client = MagicMock()
        client.text2image.return_value = tmp_path / "img.png"
        _render_image(job, client)
        client.text2image.assert_called_once_with("test", job.image_path, seed=42)

    def test_skips_when_image_exists(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"data")
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="silent",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=False,
            image_path=img,
        )
        client = MagicMock()
        _render_image(job, client)
        client.text2image.assert_not_called()


class TestRenderAudio:
    def test_renders_audio_when_needed(self, tmp_path, manifest, episode):
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="speech",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=True,
            speaker="maya",
            text="Hello!",
            audio_path=tmp_path / "aud.wav",
        )
        client = MagicMock()
        client.text2speech.return_value = tmp_path / "aud.wav"
        _render_audio(job, client, manifest, episode)
        client.text2speech.assert_called_once()

    def test_skips_when_audio_not_needed(self, tmp_path):
        episode = EpisodeData(title="T", cast={}, environments={}, scenes=[])
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="silent",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=False,
            audio_path=tmp_path / "aud.wav",
        )
        client = MagicMock()
        _render_audio(job, client, CastManifest(), episode)
        client.text2speech.assert_not_called()

    def test_skips_when_audio_exists(self, tmp_path, manifest, episode):
        aud = tmp_path / "aud.wav"
        aud.write_bytes(b"data")
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="speech",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=True,
            speaker="maya",
            text="Hello!",
            audio_path=aud,
        )
        client = MagicMock()
        _render_audio(job, client, manifest, episode)
        client.text2speech.assert_not_called()


class TestRenderVideo:
    def test_renders_video_when_not_cached(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"data")
        vid = tmp_path / "vid.mp4"
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="silent",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=False,
            image_path=img,
            video_path=vid,
        )
        client = MagicMock()
        _render_video(job, client)
        client.image2video.assert_called_once()

    def test_skips_when_video_exists(self, tmp_path):
        vid = tmp_path / "vid.mp4"
        vid.write_bytes(b"data")
        img = tmp_path / "img.png"
        img.write_bytes(b"data")
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="silent",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=False,
            image_path=img,
            video_path=vid,
        )
        client = MagicMock()
        _render_video(job, client)
        client.image2video.assert_not_called()

    def test_skips_when_image_missing(self, tmp_path):
        job = BeatJob(
            scene_id="001",
            beat_id="b1",
            kind="silent",
            prompt="test",
            seed=42,
            duration_sec=3.0,
            needs_audio=False,
            image_path=tmp_path / "nonexistent.png",
            video_path=tmp_path / "vid.mp4",
        )
        client = MagicMock()
        _render_video(job, client)
        client.image2video.assert_not_called()
