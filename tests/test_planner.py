from __future__ import annotations

import json
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
from showrunner.planner import plan_episode
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


@pytest.fixture
def episode_01_path() -> Path:
    return Path(__file__).parent.parent / "episode_01.json"


@pytest.fixture
def episode_01(episode_01_path: Path) -> dict:
    with open(episode_01_path) as f:
        return json.load(f)


@pytest.fixture
def one_scene_one_beat() -> dict:
    return {
        "title": "Single Beat",
        "schema_version": "2.0",
        "cast": {"alice": {"name": "Alice"}},
        "environments": {"room": {"trigger_word": "a room", "style": "bright"}},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "room",
                "characters_present": ["alice"],
                "target_seconds": 10,
                "beats": [
                    {
                        "beat_id": "001_b00",
                        "kind": "silent",
                        "action": "Alice enters the room",
                        "camera": "wide shot",
                    },
                ],
            },
        ],
    }


@pytest.fixture
def mixed_beat_types() -> dict:
    return {
        "title": "Mixed Types",
        "schema_version": "2.0",
        "cast": {"bob": {"name": "Bob"}},
        "environments": {"set": {"trigger_word": "a set"}},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "set",
                "characters_present": ["bob"],
                "target_seconds": 30,
                "beats": [
                    {
                        "beat_id": "001_b00",
                        "kind": "silent",
                        "action": "Bob walks in",
                    },
                    {
                        "beat_id": "001_b01",
                        "kind": "speech",
                        "speaker": "bob",
                        "text": "Hello world",
                    },
                    {
                        "beat_id": "001_b02",
                        "kind": "transition",
                        "description": "Fade to black",
                        "camera": "fade",
                    },
                ],
            },
        ],
    }


@pytest.fixture
def multiple_scenes() -> dict:
    return {
        "title": "Multi Scene",
        "schema_version": "2.0",
        "cast": {"alice": {"name": "Alice"}, "bob": {"name": "Bob"}},
        "environments": {"a": {"trigger_word": "room A"}, "b": {"trigger_word": "room B"}},
        "scenes": [
            {
                "scene_id": "001",
                "environment": "a",
                "characters_present": ["alice"],
                "target_seconds": 20,
                "beats": [
                    {"beat_id": "001_b00", "kind": "silent", "action": "Alice waits"},
                    {"beat_id": "001_b01", "kind": "speech", "speaker": "alice", "text": "Hi"},
                ],
            },
            {
                "scene_id": "002",
                "environment": "b",
                "characters_present": ["bob"],
                "target_seconds": 10,
                "beats": [
                    {"beat_id": "002_b00", "kind": "silent", "action": "Bob enters"},
                ],
            },
        ],
    }


class TestPlanEpisode:
    def test_empty_episode_returns_no_beats(self):
        beats = plan_episode({"title": "Empty", "scenes": []})
        assert beats == []

    def test_episode_without_scenes_key_returns_empty(self):
        beats = plan_episode({"title": "No Scenes Key"})
        assert beats == []

    def test_scene_without_beats_key_returns_no_beats(self):
        beats = plan_episode({"scenes": [{"scene_id": "001", "environment": "room"}]})
        assert beats == []

    def test_scene_missing_target_duration_uses_default_60(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "beats": [
                            {"beat_id": "001_b00", "kind": "silent", "action": "beat"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].duration_seconds == 60.0

    def test_beat_without_kind_defaults_to_silent(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {"beat_id": "001_b00", "action": "beat with no kind"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].type == "silent"

    def test_scene_with_empty_beats_list_skips_gracefully(self):
        beats = plan_episode(
            {
                "scenes": [
                    {"scene_id": "001", "target_seconds": 10, "beats": []},
                ],
            }
        )
        assert beats == []

    def test_target_duration_sec_takes_precedence(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_duration_sec": 30,
                        "target_seconds": 60,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "silent", "action": "a"},
                            {"beat_id": "001_b01", "kind": "silent", "action": "b"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].duration_seconds == pytest.approx(15.0)
        assert beats[1].duration_seconds == pytest.approx(15.0)

    def test_beat_without_duration_sec_uses_budget(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 20,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "silent", "action": "a"},
                            {"beat_id": "001_b01", "kind": "silent", "action": "b"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].duration_seconds == pytest.approx(10.0)
        assert beats[1].duration_seconds == pytest.approx(10.0)

    def test_unknown_beat_kind_uses_default_cost_and_strategy(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "mystery", "action": "unknown"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].rendering_strategy == "text2image"
        assert beats[0].estimated_cost == 0.01 * beats[0].duration_seconds

    def test_speech_beat_without_speaker_omits_prefix(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "speech", "text": "Hello"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].description == "Hello"

    def test_speech_beat_without_text_falls_back_to_action(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {
                                "beat_id": "001_b00",
                                "kind": "speech",
                                "speaker": "bob",
                                "action": "Bob nods",
                            },
                        ],
                    },
                ],
            }
        )
        assert beats[0].description == "Bob nods"

    def test_speech_beat_without_text_or_action_returns_empty(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "speech", "speaker": "bob"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].description == ""

    def test_silent_beat_without_action_returns_empty(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "silent"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].description == ""

    def test_transition_beat_uses_camera_when_no_description(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "transition", "camera": "fade out"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].description == "fade out"

    def test_transition_without_description_or_camera_returns_empty(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "transition"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].description == ""

    def test_fallback_beat_kind_uses_action_field(self):
        beats = plan_episode(
            {
                "scenes": [
                    {
                        "scene_id": "001",
                        "target_seconds": 10,
                        "beats": [
                            {"beat_id": "001_b00", "kind": "custom", "action": "custom action"},
                        ],
                    },
                ],
            }
        )
        assert beats[0].description == "custom action"

    def test_one_scene_one_beat(self, one_scene_one_beat):
        beats = plan_episode(one_scene_one_beat)
        assert len(beats) == 1
        b = beats[0]
        assert b.beat_number == 1
        assert b.type == "silent"
        assert b.description == "Alice enters the room"
        assert b.duration_seconds > 0
        assert b.estimated_cost >= 0
        assert b.rendering_strategy == "text2image"

    def test_mixed_beat_types(self, mixed_beat_types):
        beats = plan_episode(mixed_beat_types)
        assert len(beats) == 3
        assert beats[0].type == "silent"
        assert beats[1].type == "speech"
        assert beats[2].type == "transition"

    def test_speech_description_includes_speaker_and_text(self, mixed_beat_types):
        beats = plan_episode(mixed_beat_types)
        speech = beats[1]
        assert "[bob]" in speech.description
        assert "Hello world" in speech.description

    def test_transition_uses_description_field(self, mixed_beat_types):
        beats = plan_episode(mixed_beat_types)
        trans = beats[2]
        assert trans.description == "Fade to black"

    def test_rendering_strategies(self, mixed_beat_types):
        beats = plan_episode(mixed_beat_types)
        assert beats[0].rendering_strategy == "text2image"
        assert beats[1].rendering_strategy == "voice_clone+video"
        assert beats[2].rendering_strategy == "video_transition"

    def test_estimated_cost_varies_by_type(self, mixed_beat_types):
        beats = plan_episode(mixed_beat_types)
        silent_cost = beats[0].estimated_cost
        speech_cost = beats[1].estimated_cost
        assert speech_cost > silent_cost

    def test_beat_numbering_sequential(self, multiple_scenes):
        beats = plan_episode(multiple_scenes)
        for i, b in enumerate(beats, start=1):
            assert b.beat_number == i

    def test_multiple_scenes(self, multiple_scenes):
        beats = plan_episode(multiple_scenes)
        assert len(beats) == 3

    def test_duration_budget_calculation(self, multiple_scenes):
        beats = plan_episode(multiple_scenes)
        assert beats[0].duration_seconds == pytest.approx(10.0)
        assert beats[1].duration_seconds == pytest.approx(10.0)
        assert beats[2].duration_seconds == pytest.approx(10.0)

    def test_explicit_duration_overrides_budget(self, one_scene_one_beat):
        one_scene_one_beat["scenes"][0]["beats"][0]["duration_sec"] = 5.0
        beats = plan_episode(one_scene_one_beat)
        assert beats[0].duration_seconds == 5.0

    def test_real_episode_01_creates_all_beats(self, episode_01):
        beats = plan_episode(episode_01)
        total_beats = sum(len(s["beats"]) for s in episode_01["scenes"])
        assert len(beats) == total_beats

    def test_real_episode_all_beats_have_required_fields(self, episode_01):
        beats = plan_episode(episode_01)
        for b in beats:
            assert b.beat_number >= 1
            assert b.type in ("silent", "speech", "transition")
            assert isinstance(b.description, str) and b.description
            assert b.duration_seconds > 0
            assert b.estimated_cost >= 0
            assert b.rendering_strategy in ("text2image", "voice_clone+video", "video_transition")
