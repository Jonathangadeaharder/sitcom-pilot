from __future__ import annotations

from pathlib import Path

import pytest

from showrunner.cast_manifest import CastManifest, CharacterProfile
from showrunner.determinism import SeedStrategy
from showrunner.loader import (
    BeatData,
    EnvironmentData,
    EpisodeData,
    SceneData,
    VoiceConfig,
)
from showrunner.paths import RunPaths
from showrunner.scene_render import BeatJob, BeatStatus, SceneReport, allocate_durations, plan_beats


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
def empty_episode():
    return EpisodeData(title="Empty", cast={}, environments={}, scenes=[])


@pytest.fixture
def single_beat_episode():
    return EpisodeData(
        title="Single",
        cast={},
        environments={"room": EnvironmentData(trigger_word="room")},
        scenes=[
            SceneData(
                scene_id="001",
                environment="room",
                characters_present=[],
                beats=[BeatData(beat_id="001_001", kind="silent", duration_sec=5.0)],
            ),
        ],
    )


@pytest.fixture
def multi_scene_episode():
    return EpisodeData(
        title="Multi",
        cast={},
        environments={
            "room": EnvironmentData(trigger_word="room"),
            "office": EnvironmentData(trigger_word="office"),
        },
        scenes=[
            SceneData(
                scene_id="001",
                environment="room",
                characters_present=[],
                beats=[
                    BeatData(
                        beat_id="001_001",
                        kind="speech",
                        speaker="maya",
                        text="Hi",
                        duration_sec=2.0,
                    ),
                    BeatData(beat_id="001_002", kind="silent", duration_sec=3.0),
                ],
            ),
            SceneData(
                scene_id="002",
                environment="office",
                characters_present=[],
                beats=[
                    BeatData(
                        beat_id="002_001",
                        kind="speech",
                        speaker="maya",
                        text="Bye",
                        duration_sec=1.0,
                    )
                ],
            ),
        ],
    )


class TestBeatJob:
    def test_defaults(self):
        j = BeatJob(
            scene_id="s",
            beat_id="b",
            kind="speech",
            prompt="",
            seed=0,
            duration_sec=1.0,
            needs_audio=False,
        )
        assert j.speaker == ""
        assert j.text == ""
        assert j.image_path == Path()
        assert j.audio_path == Path()
        assert j.video_path == Path()
        assert j.status == BeatStatus.PENDING
        assert j.error == ""

    def test_custom_values(self):
        j = BeatJob(
            scene_id="s",
            beat_id="b",
            kind="speech",
            prompt="hello",
            seed=42,
            duration_sec=3.0,
            needs_audio=True,
            speaker="maya",
            text="Hi there",
        )
        assert j.prompt == "hello"
        assert j.speaker == "maya"


class TestBeatStatus:
    def test_all_values(self):
        assert BeatStatus.PENDING.value == "pending"
        assert BeatStatus.RUNNING.value == "running"
        assert BeatStatus.DONE.value == "done"
        assert BeatStatus.FAILED.value == "failed"
        assert BeatStatus.SKIPPED.value == "skipped"

    def test_is_str_enum(self):
        assert isinstance(BeatStatus.PENDING, str)


class TestSceneReport:
    def test_success_rate_full(self):
        r = SceneReport(scene_id="s", total_beats=5, completed=5)
        assert r.success_rate == 1.0

    def test_success_rate_partial(self):
        r = SceneReport(scene_id="s", total_beats=10, completed=3)
        assert r.success_rate == pytest.approx(0.3)

    def test_success_rate_zero_total(self):
        r = SceneReport(scene_id="s", total_beats=0, completed=0)
        assert r.success_rate == 0.0

    def test_defaults(self):
        r = SceneReport(scene_id="s")
        assert r.total_beats == 0
        assert r.completed == 0
        assert r.failed == 0
        assert r.skipped == 0
        assert r.duration_sec == 0.0
        assert r.errors == []


class TestPlanBeats:
    def test_empty_episode(self, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(
            EpisodeData(title="E", cast={}, environments={}, scenes=[]), manifest, paths
        )
        assert jobs == []

    def test_empty_episode_seed_strategy(self, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        ss = SeedStrategy("ep1", base_seed=42)
        jobs = plan_beats(
            EpisodeData(title="E", cast={}, environments={}, scenes=[]),
            manifest,
            paths,
            episode_id="ep1",
            seed_strategy=ss,
        )
        assert jobs == []

    def test_scene_with_no_beats(self, manifest, tmp_path):
        ep = EpisodeData(
            title="E",
            cast={},
            environments={},
            scenes=[SceneData(scene_id="001", environment="room", characters_present=[], beats=[])],
        )
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(ep, manifest, paths)
        assert jobs == []

    def test_single_beat(self, single_beat_episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(single_beat_episode, manifest, paths)
        assert len(jobs) == 1
        assert jobs[0].beat_id == "001_001"

    def test_multi_scene(self, multi_scene_episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(multi_scene_episode, manifest, paths)
        assert len(jobs) == 3
        scene_ids = [j.scene_id for j in jobs]
        assert scene_ids == ["001", "001", "002"]

    def test_needs_audio_speech_with_text(self, multi_scene_episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(multi_scene_episode, manifest, paths)
        speech_jobs = [j for j in jobs if j.kind == "speech"]
        assert all(j.needs_audio for j in speech_jobs)

    def test_needs_audio_silent(self, multi_scene_episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(multi_scene_episode, manifest, paths)
        silent_jobs = [j for j in jobs if j.kind == "silent"]
        assert all(not j.needs_audio for j in silent_jobs)

    def test_seed_strategy_applied(self, multi_scene_episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        ss = SeedStrategy("multi", base_seed=42)
        jobs = plan_beats(
            multi_scene_episode, manifest, paths, episode_id="multi", seed_strategy=ss
        )
        no_ss = plan_beats(multi_scene_episode, manifest, paths)
        for j, j2 in zip(jobs, no_ss):
            assert j.seed != j2.seed

    def test_seed_strategy_deterministic(self, multi_scene_episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        ss = SeedStrategy("multi", base_seed=42)
        a = plan_beats(multi_scene_episode, manifest, paths, episode_id="multi", seed_strategy=ss)
        b = plan_beats(multi_scene_episode, manifest, paths, episode_id="multi", seed_strategy=ss)
        assert [j.seed for j in a] == [j.seed for j in b]

    def test_duration_preserved(self, multi_scene_episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(multi_scene_episode, manifest, paths)
        assert jobs[0].duration_sec == 2.0
        assert jobs[1].duration_sec == 3.0
        assert jobs[2].duration_sec == 1.0

    def test_scene_dirs_created(self, multi_scene_episode, manifest, tmp_path):
        paths = RunPaths(tmp_path, "test-run")
        plan_beats(multi_scene_episode, manifest, paths)
        assert (paths.beats_dir / "001").exists()
        assert (paths.beats_dir / "002").exists()

    def test_speech_without_text_no_audio(self, manifest, tmp_path):
        ep = EpisodeData(
            title="E",
            cast={},
            environments={"room": EnvironmentData(trigger_word="room")},
            scenes=[
                SceneData(
                    scene_id="001",
                    environment="room",
                    characters_present=[],
                    beats=[BeatData(beat_id="b1", kind="speech", speaker="maya", text="")],
                ),
            ],
        )
        paths = RunPaths(tmp_path, "test-run")
        jobs = plan_beats(ep, manifest, paths)
        assert not jobs[0].needs_audio


class TestAllocateDurations:
    def test_empty_list(self):
        assert allocate_durations([], 10.0) == []

    def test_single_beat_under_budget(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=2.0,
                needs_audio=False,
            )
        ]
        result = allocate_durations(jobs, 10.0)
        assert result[0].duration_sec == 2.0

    def test_single_beat_over_budget(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=10.0,
                needs_audio=False,
            )
        ]
        result = allocate_durations(jobs, 5.0)
        assert result[0].duration_sec == pytest.approx(5.0)

    def test_equal_distribution_zero_total(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b1",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=0.0,
                needs_audio=False,
            ),
            BeatJob(
                scene_id="s",
                beat_id="b2",
                kind="silent",
                prompt="",
                seed=0,
                duration_sec=0.0,
                needs_audio=False,
            ),
        ]
        result = allocate_durations(jobs, 10.0)
        assert result[0].duration_sec == pytest.approx(5.0)
        assert result[1].duration_sec == pytest.approx(5.0)

    def test_equal_distribution_negative_total(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b1",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=-1.0,
                needs_audio=False,
            ),
            BeatJob(
                scene_id="s",
                beat_id="b2",
                kind="silent",
                prompt="",
                seed=0,
                duration_sec=-1.0,
                needs_audio=False,
            ),
        ]
        result = allocate_durations(jobs, 10.0)
        assert result[0].duration_sec == pytest.approx(5.0)

    def test_exact_budget(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b1",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=3.0,
                needs_audio=False,
            ),
            BeatJob(
                scene_id="s",
                beat_id="b2",
                kind="silent",
                prompt="",
                seed=0,
                duration_sec=3.0,
                needs_audio=False,
            ),
        ]
        result = allocate_durations(jobs, 6.0)
        assert result[0].duration_sec == pytest.approx(3.0)
        assert result[1].duration_sec == pytest.approx(3.0)

    def test_scale_preserves_ratio(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b1",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=4.0,
                needs_audio=False,
            ),
            BeatJob(
                scene_id="s",
                beat_id="b2",
                kind="silent",
                prompt="",
                seed=0,
                duration_sec=2.0,
                needs_audio=False,
            ),
        ]
        result = allocate_durations(jobs, 3.0)
        assert result[0].duration_sec == pytest.approx(2.0)
        assert result[1].duration_sec == pytest.approx(1.0)

    def test_rounds_preserve_total(self):
        jobs = [
            BeatJob(
                scene_id="s",
                beat_id="b1",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=10.0,
                needs_audio=False,
            ),
            BeatJob(
                scene_id="s",
                beat_id="b2",
                kind="silent",
                prompt="",
                seed=0,
                duration_sec=10.0,
                needs_audio=False,
            ),
            BeatJob(
                scene_id="s",
                beat_id="b3",
                kind="speech",
                prompt="",
                seed=0,
                duration_sec=10.0,
                needs_audio=False,
            ),
        ]
        result = allocate_durations(jobs, 15.0)
        assert sum(j.duration_sec for j in result) == pytest.approx(15.0)
