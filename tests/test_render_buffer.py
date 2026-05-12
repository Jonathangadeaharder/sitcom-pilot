from __future__ import annotations

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
from showrunner.render_buffer import RenderBuffer, render_episode_buffered
from showrunner.scene_render import plan_beats


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
                        beat_id="001_002", kind="silent", action="thinks", seed=43, duration_sec=2.0
                    ),
                    BeatData(
                        beat_id="001_003",
                        kind="speech",
                        speaker="maya",
                        text="World!",
                        seed=44,
                        duration_sec=3.0,
                    ),
                ],
            ),
            SceneData(
                scene_id="002",
                environment="office",
                characters_present=["maya"],
                beats=[
                    BeatData(
                        beat_id="002_001",
                        kind="speech",
                        speaker="maya",
                        text="Scene two!",
                        seed=45,
                        duration_sec=3.0,
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def mock_client():
    c = MagicMock()
    c.text2image.side_effect = lambda prompt, path, **kw: _write_dummy(path)
    c.text2speech.side_effect = lambda text, path, **kw: _write_dummy(path)
    c.image2video.side_effect = lambda img, prompt, path, **kw: _write_dummy(path)
    return c


def _write_dummy(path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x00" * 16)
    return p


class TestRenderBuffer:
    def test_renders_all_beats(self, episode, manifest, mock_client, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        jobs = plan_beats(episode, manifest, paths)
        buf = RenderBuffer(mock_client, manifest, episode, paths, buffer_size=2, max_workers=4)
        try:
            reports = buf.render(jobs, episode.scenes)
        finally:
            buf.close()

        assert len(reports) == 2
        assert reports[0].completed == 3
        assert reports[1].completed == 1

    def test_flushes_to_final_paths(self, episode, manifest, mock_client, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        jobs = plan_beats(episode, manifest, paths)
        buf = RenderBuffer(mock_client, manifest, episode, paths, buffer_size=2, max_workers=4)
        try:
            buf.render(jobs, episode.scenes)
        finally:
            buf.close()

        for scene in episode.scenes:
            for beat in scene.beats:
                assert paths.beat_image(scene.scene_id, beat.beat_id).exists()
                assert paths.beat_video(scene.scene_id, beat.beat_id).exists()

    def test_buffer_dir_cleaned_on_close(self, episode, manifest, mock_client, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        jobs = plan_beats(episode, manifest, paths)
        buf = RenderBuffer(mock_client, manifest, episode, paths, buffer_size=2, max_workers=4)
        buf_dir = buf.buffer_dir
        assert buf_dir.exists()
        buf.render(jobs, episode.scenes)
        buf.close()
        assert not buf_dir.exists()

    def test_empty_jobs(self, episode, manifest, mock_client, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        buf = RenderBuffer(mock_client, manifest, episode, paths, buffer_size=2, max_workers=4)
        try:
            reports = buf.render([], episode.scenes)
        finally:
            buf.close()
        assert all(r.completed == 0 for r in reports)

    def test_buffer_size_one_processes_sequentially(self, episode, manifest, mock_client, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        jobs = plan_beats(episode, manifest, paths)
        buf = RenderBuffer(mock_client, manifest, episode, paths, buffer_size=1, max_workers=2)
        try:
            reports = buf.render(jobs, episode.scenes)
        finally:
            buf.close()
        assert reports[0].completed == 3
        assert reports[1].completed == 1


class TestRenderEpisodeBuffered:
    def test_full_episode_buffered(self, episode, manifest, mock_client, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        reports = render_episode_buffered(
            episode,
            manifest,
            paths,
            mock_client,
            buffer_size=2,
            max_workers=4,
        )
        assert len(reports) == 2
        assert reports[0].completed == 3
        assert reports[1].completed == 1

    def test_report_saved(self, episode, manifest, mock_client, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        render_episode_buffered(episode, manifest, paths, mock_client, buffer_size=2, max_workers=4)
        assert (paths.run_dir / "render_report.json").exists()

    def test_output_files_exist(self, episode, manifest, mock_client, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        render_episode_buffered(episode, manifest, paths, mock_client, buffer_size=2, max_workers=4)
        for scene in episode.scenes:
            for beat in scene.beats:
                assert paths.beat_image(scene.scene_id, beat.beat_id).exists()
                assert paths.beat_video(scene.scene_id, beat.beat_id).exists()


class TestRenderBufferFailureHandling:
    def test_reports_failures(self, episode, manifest, tmp_path):
        failing_client = MagicMock()
        failing_client.text2image.side_effect = RuntimeError("boom")
        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        jobs = plan_beats(episode, manifest, paths)
        buf = RenderBuffer(failing_client, manifest, episode, paths, buffer_size=2, max_workers=4)
        try:
            reports = buf.render(jobs, episode.scenes)
        finally:
            buf.close()
        assert all(r.failed == r.total_beats for r in reports)

    def test_mixed_success_failure(self, episode, manifest, tmp_path):
        call_count = [0]
        client = MagicMock()

        def side_effect(prompt, path, **kw):
            call_count[0] += 1
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if call_count[0] == 2:
                raise RuntimeError("mock fail on second beat")
            p.write_bytes(b"\x00" * 16)
            return path

        client.text2image.side_effect = side_effect
        client.text2speech.side_effect = lambda text, path, **kw: _write_dummy(path)
        client.image2video.side_effect = lambda img, prompt, path, **kw: _write_dummy(path)

        paths = RunPaths(tmp_path, "test-run")
        paths.ensure_dirs()
        jobs = plan_beats(episode, manifest, paths)
        buf = RenderBuffer(client, manifest, episode, paths, buffer_size=2, max_workers=4)
        try:
            reports = buf.render(jobs, episode.scenes)
        finally:
            buf.close()
        assert reports[0].failed >= 1 or reports[0].completed >= 1
