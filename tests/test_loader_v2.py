"""Tests for EpisodeLoader v2.0 beat-based schema support."""

from __future__ import annotations

import json

import pytest

from showrunner.loader import BeatData, EpisodeLoader, VoiceConfig

V2_EPISODE = {
    "show": "Buffering",
    "season": 1,
    "episode": 1,
    "title": "The Bug",
    "schema_version": "2.0",
    "render": {
        "fps": 24,
        "resolution": [1280, 720],
        "image_provider": "mlx-flux",
        "image_model": "flux-schnell",
        "video_provider": "mlx-ltx",
        "video_model": "ltx-2",
        "tts_provider": "mlx-audio",
        "tts_model": "xtts-v2",
        "subtitle_provider": "mlx-whisper",
    },
    "cast": {
        "maya": {
            "name": "Maya Chen",
            "role": "Lead engineer",
            "visual": "East Asian woman, short black hair",
            "reference_images": ["assets/maya_front.png"],
            "lora": None,
            "voice": {
                "provider": "mlx-audio",
                "voice_id": "maya_v1",
                "clone_from": "assets/voices/maya.wav",
                "seed": 42,
                "temperature": 0.8,
                "language": "en",
            },
        },
        "finn": {
            "name": "Finn O'Brien",
            "role": "QA tester",
            "visual": "Irish man, curly red hair",
            "lora": "finn_lora_v2",
            "voice": {
                "provider": "mlx-audio",
                "voice_id": "finn_v1",
                "clone_from": "",
                "seed": 389,
                "temperature": 0.8,
                "language": "en",
            },
        },
    },
    "environments": {
        "maya_desk": {
            "trigger_word": "Corner desk setup, monitors glowing",
            "style": "cinematic, warm desk lamp",
            "reference_image": "assets/env/desk.png",
        },
        "living_room": {
            "trigger_word": "Modern SF apartment living room",
            "style": "golden hour",
        },
    },
    "scenes": [
        {
            "scene_id": "001",
            "title": "The Bug Discovered",
            "environment": "maya_desk",
            "characters_present": ["maya"],
            "target_seconds": 70,
            "mood": "tense",
            "beats": [
                {
                    "beat_id": "001_b00",
                    "kind": "silent",
                    "camera": "wide shot",
                    "action": "Maya at desk",
                    "duration_sec": 4.0,
                    "seed": 110001,
                },
                {
                    "beat_id": "001_b01",
                    "kind": "speech",
                    "speaker": "maya",
                    "text": "This can't be right.",
                    "camera": "close-up",
                    "duration_sec": 3.0,
                    "seed": 110002,
                    "audio_path": "audio/001_b01.wav",
                },
            ],
        },
        {
            "scene_id": "002",
            "title": "Kitchen",
            "environment": "living_room",
            "characters_present": ["maya", "finn"],
            "beats": [
                {
                    "beat_id": "002_b00",
                    "kind": "silent",
                    "camera": "wide",
                    "action": "Both in kitchen",
                    "duration_sec": 4.0,
                    "seed": 120001,
                },
            ],
        },
    ],
}


def test_v2_schema_version_loaded(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.schema_version == "2.0"


def test_v2_title_and_metadata_loaded(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.title == "The Bug"
    assert ep.show == "Buffering"
    assert ep.season == 1
    assert ep.episode_number == 1


def test_v2_render_config_loaded(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.render_config["fps"] == 24
    assert ep.render_config["image_provider"] == "mlx-flux"
    assert ep.render_config["tts_provider"] == "mlx-audio"


def test_v2_cast_names_loaded(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert "maya" in ep.cast
    assert "finn" in ep.cast


def test_v2_cast_character_name(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.cast["maya"].name == "Maya Chen"


def test_v2_cast_visual_loaded(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert "East Asian" in ep.cast["maya"].visual


def test_v2_cast_lora_none(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.cast["maya"].lora is None


def test_v2_cast_lora_string(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.cast["finn"].lora == "finn_lora_v2"


def test_v2_cast_voice_config(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    voice = ep.cast["maya"].voice
    assert isinstance(voice, VoiceConfig)
    assert voice.voice_id == "maya_v1"
    assert voice.seed == 42
    assert voice.temperature == pytest.approx(0.8)
    assert voice.language == "en"


def test_v2_cast_reference_images(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert "assets/maya_front.png" in ep.cast["maya"].reference_images


def test_v2_environments_loaded(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert "maya_desk" in ep.environments
    assert "living_room" in ep.environments


def test_v2_environment_trigger_word(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert "Corner desk" in ep.environments["maya_desk"].trigger_word


def test_v2_environment_style(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.environments["maya_desk"].style == "cinematic, warm desk lamp"


def test_v2_scenes_loaded(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert len(ep.scenes) == 2


def test_v2_scene_metadata(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    s = ep.scenes[0]
    assert s.scene_id == "001"
    assert s.title == "The Bug Discovered"
    assert s.environment == "maya_desk"
    assert s.mood == "tense"


def test_v2_scene_characters_present(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.scenes[0].characters_present == ["maya"]
    assert set(ep.scenes[1].characters_present) == {"maya", "finn"}


def test_v2_beats_loaded(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert len(ep.scenes[0].beats) == 2


def test_v2_silent_beat_fields(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    beat = ep.scenes[0].beats[0]
    assert isinstance(beat, BeatData)
    assert beat.beat_id == "001_b00"
    assert beat.kind == "silent"
    assert beat.camera == "wide shot"
    assert beat.action == "Maya at desk"
    assert beat.duration_sec == pytest.approx(4.0)
    assert beat.seed == 110001


def test_v2_speech_beat_fields(tmp_path):
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    beat = ep.scenes[0].beats[1]
    assert beat.kind == "speech"
    assert beat.speaker == "maya"
    assert beat.text == "This can't be right."
    assert beat.audio_path == "audio/001_b01.wav"


def test_v2_scenes_have_no_shots(tmp_path):
    """v2 scenes should have empty shots list (shots is for legacy v1 only)."""
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(V2_EPISODE))
    ep = EpisodeLoader().load(path)
    assert ep.scenes[0].shots == []


def test_v1_backward_compat_still_works(tmp_path):
    """Legacy v1 episode with shots must still load correctly."""
    v1_ep = {
        "episode_title": "Test v1",
        "cast": {"Jerry": {"profile": "jerry_v2", "trigger_word": "jry_guy"}},
        "environments": {"Apt": {"profile": "apt_v1", "trigger_word": "apartment"}},
        "scenes": [
            {
                "scene_id": "S01",
                "environment": "Apt",
                "characters_present": ["Jerry"],
                "shots": [
                    {
                        "shot_id": "S01_SH01",
                        "camera_angle": "wide",
                        "action_start": "standing",
                        "action_end": "sitting",
                        "seed": 42,
                    }
                ],
            }
        ],
    }
    path = tmp_path / "ep_v1.json"
    path.write_text(json.dumps(v1_ep))
    ep = EpisodeLoader().load(path)
    assert ep.title == "Test v1"
    assert ep.schema_version == "1.0"
    assert len(ep.scenes[0].shots) == 1
    assert ep.scenes[0].shots[0].shot_id == "S01_SH01"
    assert ep.scenes[0].beats == []


def test_v1_cast_profile_and_trigger_word(tmp_path):
    v1_ep = {
        "episode_title": "T",
        "cast": {"Alice": {"profile": "alice_v1", "trigger_word": "alice_woman"}},
        "environments": {},
        "scenes": [],
    }
    path = tmp_path / "ep.json"
    path.write_text(json.dumps(v1_ep))
    ep = EpisodeLoader().load(path)
    assert ep.cast["Alice"].profile == "alice_v1"
    assert ep.cast["Alice"].trigger_word == "alice_woman"
