from __future__ import annotations

import json
from pathlib import Path

import pytest

from showrunner.planner import plan_episode


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
