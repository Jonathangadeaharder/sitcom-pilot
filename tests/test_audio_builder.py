import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_episode_v2(tmp_path, scenes=None, cast=None, envs=None):
    ep = {
        "show": "Buffering",
        "season": 1,
        "episode": 2,
        "title": "The Demo Day",
        "target_duration_min": 9.5,
        "cast": cast or {"maya": {"profile": "m_v1", "trigger_word": "maya_desc", "name": "Maya Chen", "voice_seed": 42, "voice_temp": 0.8, "visual": "v"}},
        "environments": envs or {"desk": {"profile": "desk_v1", "trigger_word": "desk desc"}},
        "scenes": scenes or [],
    }
    p = tmp_path / "episode_v2.json"
    p.write_text(json.dumps(ep))
    return p


class TestLoadEpisodeV2:
    def test_loads_new_title_format(self, tmp_path):
        from sitcom_pilot.loader import EpisodeLoader

        path = _make_episode_v2(tmp_path)
        ep = EpisodeLoader().load(path)
        assert ep.title == "The Demo Day"

    def test_loads_old_episode_title_format(self, tmp_path):
        from sitcom_pilot.loader import EpisodeLoader

        p = tmp_path / "old.json"
        p.write_text(json.dumps({
            "episode_title": "Old Format",
            "cast": {},
            "environments": {},
            "scenes": [],
        }))
        ep = EpisodeLoader().load(p)
        assert ep.title == "Old Format"

    def test_prefers_title_over_episode_title(self, tmp_path):
        from sitcom_pilot.loader import EpisodeLoader

        p = tmp_path / "both.json"
        p.write_text(json.dumps({
            "title": "New Title",
            "episode_title": "Old Title",
            "cast": {},
            "environments": {},
            "scenes": [],
        }))
        ep = EpisodeLoader().load(p)
        assert ep.title == "New Title"

    def test_shot_has_dialogue(self, tmp_path):
        from sitcom_pilot.loader import EpisodeLoader

        path = _make_episode_v2(tmp_path, scenes=[{
            "scene_id": "001", "environment": "desk",
            "characters_present": ["maya"],
            "target_duration_sec": 60,
            "shots": [{
                "shot_id": "001_01", "camera_angle": "wide",
                "action_start": "start", "action_end": "end",
                "seed": 2000,
                "dialogue": [
                    {"speaker": "maya", "emotion": "frustrated", "tone": None, "effect": None, "text": "Broken."},
                    {"speaker": "maya", "emotion": "scared", "tone": None, "effect": None, "text": "Oh no."},
                ],
            }],
        }])
        ep = EpisodeLoader().load(path)
        shot = ep.scenes[0].shots[0]
        assert len(shot.dialogue) == 2
        assert shot.dialogue[0]["emotion"] == "frustrated"

    def test_shot_with_no_dialogue(self, tmp_path):
        from sitcom_pilot.loader import EpisodeLoader

        path = _make_episode_v2(tmp_path, scenes=[{
            "scene_id": "001", "environment": "desk",
            "characters_present": [],
            "shots": [{
                "shot_id": "001_01", "camera_angle": "wide",
                "action_start": "start", "action_end": "end",
                "seed": 2000,
            }],
        }])
        ep = EpisodeLoader().load(path)
        assert ep.scenes[0].shots[0].dialogue == []

    def test_old_audio_path_still_works(self, tmp_path):
        from sitcom_pilot.loader import EpisodeLoader

        path = _make_episode_v2(tmp_path, scenes=[{
            "scene_id": "001", "environment": "desk",
            "characters_present": [],
            "shots": [{
                "shot_id": "001_01", "camera_angle": "wide",
                "action_start": "start", "action_end": "end",
                "audio_path": "output/scene_001.wav", "seed": 2000,
            }],
        }])
        ep = EpisodeLoader().load(path)
        assert ep.scenes[0].shots[0].audio_path == "output/scene_001.wav"

    def test_scene_has_target_duration(self, tmp_path):
        from sitcom_pilot.loader import EpisodeLoader

        path = _make_episode_v2(tmp_path, scenes=[{
            "scene_id": "001", "environment": "desk",
            "characters_present": [],
            "target_duration_sec": 90,
            "shots": [],
        }])
        ep = EpisodeLoader().load(path)
        assert ep.scenes[0].target_duration_sec == 90

    def test_scene_default_target_duration(self, tmp_path):
        from sitcom_pilot.loader import EpisodeLoader

        path = _make_episode_v2(tmp_path, scenes=[{
            "scene_id": "001", "environment": "desk",
            "characters_present": [],
            "shots": [],
        }])
        ep = EpisodeLoader().load(path)
        assert ep.scenes[0].target_duration_sec == 60


class TestBuildShotAudio:
    @patch("sitcom_pilot.audio_builder.concatenate_wavs")
    @patch("sitcom_pilot.audio_builder.synthesize_dialogue_line")
    def test_generates_per_shot_audio(self, mock_synth, mock_concat, tmp_path):
        from sitcom_pilot.audio_builder import build_shot_audio

        mock_synth.return_value = True
        mock_concat.return_value = True

        dialogue = [
            {"speaker": "maya", "emotion": "frustrated", "tone": None, "effect": None, "text": "Broken."},
        ]
        output = tmp_path / "shot_001_01.wav"
        result = build_shot_audio(dialogue, "maya", output, voice_seed=42, voice_temp=0.8)
        assert result is True
        mock_synth.assert_called_once()

    @patch("sitcom_pilot.audio_builder.synthesize_dialogue_line")
    def test_empty_dialogue_returns_false(self, mock_synth, tmp_path):
        from sitcom_pilot.audio_builder import build_shot_audio

        output = tmp_path / "shot.wav"
        assert build_shot_audio([], "maya", output) is False

    @patch("sitcom_pilot.audio_builder.concatenate_wavs")
    @patch("sitcom_pilot.audio_builder.synthesize_dialogue_line")
    def test_multiple_lines_concatenated(self, mock_synth, mock_concat, tmp_path):
        from sitcom_pilot.audio_builder import build_shot_audio

        mock_synth.return_value = True
        mock_concat.return_value = True

        dialogue = [
            {"speaker": "maya", "emotion": "frustrated", "tone": None, "effect": None, "text": "Line 1."},
            {"speaker": "maya", "emotion": "scared", "tone": None, "effect": None, "text": "Line 2."},
        ]
        output = tmp_path / "shot.wav"
        result = build_shot_audio(dialogue, "maya", output)
        assert result is True
        assert mock_synth.call_count == 2
        mock_concat.assert_called_once()

    def test_existing_output_skips(self, tmp_path):
        from sitcom_pilot.audio_builder import build_shot_audio

        output = tmp_path / "shot.wav"
        output.write_bytes(b"existing")
        dialogue = [{"speaker": "maya", "emotion": "calm", "tone": None, "effect": None, "text": "Hi."}]
        result = build_shot_audio(dialogue, "maya", output)
        assert result is True


class TestBuildFishTextFromDialogue:
    def test_emotion_prepended(self):
        from sitcom_pilot.audio_builder import build_fish_text_from_dialogue

        line = {"speaker": "maya", "emotion": "frustrated", "tone": None, "effect": None, "text": "Broken."}
        assert build_fish_text_from_dialogue(line) == "(frustrated) Broken."

    def test_emotion_tone_effect(self):
        from sitcom_pilot.audio_builder import build_fish_text_from_dialogue

        line = {"speaker": "finn", "emotion": "nervous", "tone": "whispering", "effect": "sighing", "text": "Oh no."}
        assert build_fish_text_from_dialogue(line) == "(nervous)(whispering)(sighing) Oh no."

    def test_no_tags_plain(self):
        from sitcom_pilot.audio_builder import build_fish_text_from_dialogue

        line = {"speaker": "maya", "emotion": None, "tone": None, "effect": None, "text": "Plain."}
        assert build_fish_text_from_dialogue(line) == "Plain."
