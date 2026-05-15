import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_episode(tmp_path):
    ep = {
        "show": "Buffering",
        "season": 1,
        "episode": 2,
        "title": "The Demo Day",
        "target_duration_min": 9.5,
        "cast": {
            "maya": {
                "name": "Maya Chen",
                "voice_seed": 42,
                "voice_temp": 0.8,
                "visual": "test visual",
                "trigger_word": "test trigger",
                "profile": "maya_v1",
            },
            "finn": {
                "name": "Finn O'Brien",
                "voice_seed": 389,
                "voice_temp": 0.8,
                "visual": "test visual",
                "trigger_word": "test trigger",
                "profile": "finn_v1",
            },
        },
        "environments": {
            "maya_desk": {
                "profile": "maya_desk_v1",
                "trigger_word": "test env",
            },
        },
        "scenes": [
            {
                "scene_id": "001",
                "title": "Cold Open",
                "environment": "maya_desk",
                "characters_present": ["maya"],
                "target_duration_sec": 60,
                "shots": [
                    {
                        "shot_id": "001_01",
                        "camera_angle": "close-up",
                        "action_start": "Maya sits at desk",
                        "action_end": "Maya stares at screen",
                        "seed": 2000,
                        "dialogue": [
                            {
                                "speaker": "maya",
                                "emotion": "frustrated",
                                "tone": None,
                                "effect": None,
                                "text": "The man has never even seen the product.",
                            },
                            {
                                "speaker": "maya",
                                "emotion": "scared",
                                "tone": None,
                                "effect": None,
                                "text": "Forty-eight hours to demo an AI chatbot.",
                            },
                        ],
                    },
                    {
                        "shot_id": "001_02",
                        "camera_angle": "medium shot",
                        "action_start": "Maya pushes back",
                        "action_end": "Maya grabs phone",
                        "seed": 2001,
                        "dialogue": [
                            {
                                "speaker": "maya",
                                "emotion": "resigned",
                                "tone": None,
                                "effect": "sighing",
                                "text": "I'm going to need coffee and a miracle.",
                            },
                            {
                                "speaker": "maya",
                                "emotion": "determined",
                                "tone": None,
                                "effect": None,
                                "text": "Fine. Let's go.",
                            },
                        ],
                    },
                ],
            },
            {
                "scene_id": "002",
                "title": "Kitchen Scene",
                "environment": "maya_desk",
                "characters_present": ["maya", "finn"],
                "target_duration_sec": 90,
                "shots": [
                    {
                        "shot_id": "002_01",
                        "camera_angle": "wide",
                        "action_start": "Everyone in kitchen",
                        "action_end": "Talking",
                        "seed": 2010,
                        "dialogue": [
                            {
                                "speaker": "finn",
                                "emotion": "nervous",
                                "tone": "whispering",
                                "effect": None,
                                "text": "The chatbot's response time is eleven seconds.",
                            },
                            {
                                "speaker": "maya",
                                "emotion": "sarcastic",
                                "tone": None,
                                "effect": "laughing",
                                "text": "That's not latency, that's a confession.",
                            },
                        ],
                    },
                ],
            },
        ],
    }
    path = tmp_path / "episode_test.json"
    path.write_text(json.dumps(ep))
    return path


class TestBuildFishText:
    def test_emotion_only(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": "frustrated",
            "tone": None,
            "effect": None,
            "text": "The man has never even seen the product.",
        }
        assert build_fish_text(line) == "(frustrated) The man has never even seen the product."

    def test_emotion_and_effect(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": "resigned",
            "tone": None,
            "effect": "sighing",
            "text": "I'm going to need coffee.",
        }
        assert build_fish_text(line) == "(resigned)(sighing) I'm going to need coffee."

    def test_emotion_tone_and_effect(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "finn",
            "emotion": "nervous",
            "tone": "whispering",
            "effect": None,
            "text": "The chatbot is live.",
        }
        assert build_fish_text(line) == "(nervous)(whispering) The chatbot is live."

    def test_all_three_tags(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": "sarcastic",
            "tone": None,
            "effect": "laughing",
            "text": "That's not latency.",
        }
        assert build_fish_text(line) == "(sarcastic)(laughing) That's not latency."

    def test_no_tags(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": None,
            "tone": None,
            "effect": None,
            "text": "Plain text, no emotion.",
        }
        assert build_fish_text(line) == "Plain text, no emotion."

    def test_invalid_emotion_ignored(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": "nonexistent_emotion",
            "tone": None,
            "effect": None,
            "text": "Should be plain text.",
        }
        assert build_fish_text(line) == "Should be plain text."

    def test_invalid_tone_ignored(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": "angry",
            "tone": "nonexistent_tone",
            "effect": None,
            "text": "Text here.",
        }
        assert build_fish_text(line) == "(angry) Text here."

    def test_invalid_effect_ignored(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": None,
            "tone": None,
            "effect": "nonexistent_effect",
            "text": "Text here.",
        }
        assert build_fish_text(line) == "Text here."

    def test_tone_only(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": None,
            "tone": "shouting",
            "effect": None,
            "text": "Get out!",
        }
        assert build_fish_text(line) == "(shouting) Get out!"

    def test_effect_only(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "finn",
            "emotion": None,
            "tone": None,
            "effect": "chuckling",
            "text": "The fridge ordered cheese.",
        }
        assert build_fish_text(line) == "(chuckling) The fridge ordered cheese."

    def test_text_stripped(self):
        from voice_generator_v3 import build_fish_text

        line = {
            "speaker": "maya",
            "emotion": "calm",
            "tone": None,
            "effect": None,
            "text": "  padded text  ",
        }
        assert build_fish_text(line) == "(calm) padded text"


class TestLoadEpisode:
    def test_loads_valid_episode(self, sample_episode):
        from voice_generator_v3 import load_episode

        data = load_episode(sample_episode)
        assert data["show"] == "Buffering"
        assert data["season"] == 1
        assert data["episode"] == 2
        assert len(data["scenes"]) == 2
        assert "maya" in data["cast"]
        assert "finn" in data["cast"]

    def test_rejects_missing_scenes(self, tmp_path):
        from voice_generator_v3 import load_episode

        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"cast": {}, "environments": {}}))
        with pytest.raises(ValueError, match="scenes"):
            load_episode(path)

    def test_rejects_missing_cast(self, tmp_path):
        from voice_generator_v3 import load_episode

        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"scenes": [], "environments": {}}))
        with pytest.raises(ValueError, match="cast"):
            load_episode(path)

    def test_rejects_missing_environments(self, tmp_path):
        from voice_generator_v3 import load_episode

        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"scenes": [], "cast": {}}))
        with pytest.raises(ValueError, match="environments"):
            load_episode(path)


class TestGetSceneDialogue:
    def test_collects_all_lines_in_order(self, sample_episode):
        from voice_generator_v3 import get_scene_dialogue, load_episode

        data = load_episode(sample_episode)
        lines = get_scene_dialogue(data["scenes"][0])
        assert len(lines) == 4
        assert lines[0]["speaker"] == "maya"
        assert lines[0]["emotion"] == "frustrated"
        assert lines[3]["emotion"] == "determined"

    def test_empty_scene(self):
        from voice_generator_v3 import get_scene_dialogue

        scene = {"shots": [{"dialogue": []}]}
        assert get_scene_dialogue(scene) == []


class TestGenerateFishPayload:
    def test_basic_payload(self):
        from voice_generator_v3 import generate_fish_payload

        payload = generate_fish_payload(
            fish_text="(frustrated) The deployment is broken.",
            character_id="maya",
            seed=42,
            temperature=0.8,
        )
        assert payload["text"] == "(frustrated) The deployment is broken."
        assert payload["reference_id"] == "maya"
        assert payload["seed"] == 42
        assert payload["temperature"] == 0.8
        assert payload["format"] == "wav"
        assert payload["streaming"] is False
        assert payload["normalize"] is True

    def test_default_params(self):
        from voice_generator_v3 import generate_fish_payload

        payload = generate_fish_payload(
            fish_text="Hello",
            character_id="finn",
        )
        assert payload["seed"] == 42
        assert payload["temperature"] == 0.8
        assert payload["reference_id"] == "finn"


class TestSynthesizeLine:
    @patch.dict("sys.modules", {"ormsgpack": MagicMock(packb=MagicMock(return_value=b"packed"))})
    @patch("voice_generator_v3.urllib.request.urlopen")
    def test_successful_synthesis(self, mock_urlopen, tmp_path):
        from voice_generator_v3 import synthesize_line

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"fake_audio_data"
        mock_urlopen.return_value = mock_resp

        output = tmp_path / "line_000_maya.wav"
        result = synthesize_line(
            fish_text="(frustrated) Broken deployment.",
            character_id="maya",
            output_path=output,
            seed=42,
            temperature=0.8,
        )
        assert result is True
        assert output.exists()
        assert output.read_bytes() == b"fake_audio_data"

    @patch("voice_generator_v3.urllib.request.urlopen")
    def test_skips_existing_file(self, mock_urlopen, tmp_path):
        from voice_generator_v3 import synthesize_line

        output = tmp_path / "line_000_maya.wav"
        output.write_bytes(b"existing")

        result = synthesize_line(
            fish_text="text",
            character_id="maya",
            output_path=output,
        )
        assert result is True
        mock_urlopen.assert_not_called()
        assert output.read_bytes() == b"existing"

    @patch("voice_generator_v3.urllib.request.urlopen")
    def test_http_error_returns_false(self, mock_urlopen, tmp_path):
        import urllib.error

        from voice_generator_v3 import synthesize_line

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=500, msg="Error", hdrs={}, fp=None
        )
        output = tmp_path / "line_000_maya.wav"
        result = synthesize_line(
            fish_text="text",
            character_id="maya",
            output_path=output,
        )
        assert result is False


class TestGenerateEpisodeAudio:
    @patch("voice_generator_v3.synthesize_line")
    @patch("voice_generator_v3.concatenate_audio")
    def test_generates_all_lines_and_scenes(
        self, mock_concat, mock_synth, sample_episode, tmp_path
    ):
        from voice_generator_v3 import generate_episode_audio, load_episode

        mock_synth.return_value = True
        mock_concat.return_value = True

        data = load_episode(sample_episode)
        results = generate_episode_audio(data, tmp_path)

        assert "001" in results
        assert "002" in results

    @patch("voice_generator_v3.synthesize_line")
    @patch("voice_generator_v3.concatenate_audio")
    def test_uses_character_voice_params(self, mock_concat, mock_synth, sample_episode, tmp_path):
        from voice_generator_v3 import generate_episode_audio, load_episode

        mock_synth.return_value = True
        mock_concat.return_value = True

        data = load_episode(sample_episode)
        results = generate_episode_audio(data, tmp_path)

        assert results["001"]["lines_generated"] == 4
        synth_kwargs = [c.kwargs for c in mock_synth.call_args_list]
        assert any(k.get("seed") == 42 and k.get("temperature") == 0.8 for k in synth_kwargs)

    @patch("voice_generator_v3.synthesize_line")
    @patch("voice_generator_v3.concatenate_audio")
    def test_builds_fish_text_for_each_line(self, mock_concat, mock_synth, sample_episode, tmp_path):
        from voice_generator_v3 import generate_episode_audio, load_episode

        mock_synth.return_value = True
        mock_concat.return_value = True

        data = load_episode(sample_episode)
        results = generate_episode_audio(data, tmp_path)

        assert results["001"]["lines_generated"] == 4
        synth_kwargs = [c.kwargs for c in mock_synth.call_args_list]
        assert any(k.get("fish_text", "").startswith("(") for k in synth_kwargs)


class TestEmotionValidation:
    def test_all_valid_emotions_accepted(self):
        from voice_generator_v3 import VALID_EMOTIONS

        assert len(VALID_EMOTIONS) >= 49
        assert "frustrated" in VALID_EMOTIONS
        assert "sarcastic" in VALID_EMOTIONS
        assert "determined" in VALID_EMOTIONS
        assert "resigned" in VALID_EMOTIONS

    def test_all_valid_tones_accepted(self):
        from voice_generator_v3 import VALID_TONES

        assert "whispering" in VALID_TONES
        assert "shouting" in VALID_TONES
        assert "soft tone" in VALID_TONES
        assert "screaming" in VALID_TONES
        assert "in a hurry tone" in VALID_TONES

    def test_all_valid_effects_accepted(self):
        from voice_generator_v3 import VALID_EFFECTS

        assert "laughing" in VALID_EFFECTS
        assert "sighing" in VALID_EFFECTS
        assert "chuckling" in VALID_EFFECTS
        assert "sobbing" in VALID_EFFECTS


class TestCheckFishApi:
    @patch("voice_generator_v3.urllib.request.urlopen")
    def test_api_running(self, mock_urlopen):
        from voice_generator_v3 import check_fish_api

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp
        assert check_fish_api() is True

    @patch("voice_generator_v3.urllib.request.urlopen")
    def test_api_not_running(self, mock_urlopen):
        from voice_generator_v3 import check_fish_api

        mock_urlopen.side_effect = Exception("connection refused")
        assert check_fish_api() is False


class TestConcatenateAudio:
    def test_empty_list_returns_false(self, tmp_path):
        from voice_generator_v3 import concatenate_audio

        out = tmp_path / "out.wav"
        assert concatenate_audio([], out) is False

    def test_single_file_copies(self, tmp_path):
        from voice_generator_v3 import concatenate_audio

        wav = tmp_path / "single.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)
        out = tmp_path / "out.wav"
        assert concatenate_audio([wav], out) is True
        assert out.read_bytes() == wav.read_bytes()

    @patch("voice_generator_v3.subprocess.run")
    def test_multiple_files_calls_ffmpeg(self, mock_run, tmp_path):
        from voice_generator_v3 import concatenate_audio

        wav1 = tmp_path / "a.wav"
        wav2 = tmp_path / "b.wav"
        wav1.write_bytes(b"RIFF" + b"\x00" * 50)
        wav2.write_bytes(b"RIFF" + b"\x00" * 50)
        out = tmp_path / "out.wav"

        mock_run.return_value = MagicMock(returncode=0)
        out.write_bytes(b"concatenated")

        assert concatenate_audio([wav1, wav2], out, pause_sec=0.3) is True
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd[0] or cmd[0] == "ffmpeg"
        assert "concat=n=2:v=0:a=1" in " ".join(cmd)
        assert "pad_dur=0.3" in " ".join(cmd)

    @patch("voice_generator_v3.subprocess.run")
    def test_ffmpeg_failure_returns_false(self, mock_run, tmp_path):
        from voice_generator_v3 import concatenate_audio

        wav1 = tmp_path / "a.wav"
        wav2 = tmp_path / "b.wav"
        wav1.write_bytes(b"RIFF" + b"\x00" * 50)
        wav2.write_bytes(b"RIFF" + b"\x00" * 50)
        out = tmp_path / "out.wav"

        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        assert concatenate_audio([wav1, wav2], out) is False


class TestSynthesizeLineEdgeCases:
    @patch("voice_generator_v3.urllib.request.urlopen")
    def test_generic_exception_returns_false(self, mock_urlopen, tmp_path):
        from voice_generator_v3 import synthesize_line

        mock_urlopen.side_effect = OSError("network error")
        output = tmp_path / "line.wav"
        result = synthesize_line(
            fish_text="text",
            character_id="maya",
            output_path=output,
        )
        assert result is False
        assert not output.exists()

    def test_no_ormsgpack_returns_false(self, tmp_path):
        from voice_generator_v3 import synthesize_line

        output = tmp_path / "line.wav"
        with patch.dict("sys.modules", {"ormsgpack": None}):
            result = synthesize_line(
                fish_text="text",
                character_id="maya",
                output_path=output,
            )
        assert result is False


class TestGenerateEpisodeAudioEdgeCases:
    @patch("voice_generator_v3.synthesize_line")
    @patch("voice_generator_v3.concatenate_audio")
    def test_failed_synthesis_not_in_line_files(
        self, mock_concat, mock_synth, sample_episode, tmp_path
    ):
        from voice_generator_v3 import generate_episode_audio, load_episode

        mock_synth.return_value = False
        mock_concat.return_value = False

        data = load_episode(sample_episode)
        results = generate_episode_audio(data, tmp_path)

        assert results["001"]["lines_generated"] == 0

    @patch("voice_generator_v3.synthesize_line")
    @patch("voice_generator_v3.concatenate_audio")
    def test_unknown_speaker_uses_defaults(self, mock_concat, mock_synth, tmp_path):
        from voice_generator_v3 import generate_episode_audio

        mock_synth.return_value = True
        mock_concat.return_value = True

        ep = {
            "cast": {
                "known_char": {
                    "name": "Known",
                    "voice_seed": 42,
                    "voice_temp": 0.8,
                    "visual": "v",
                    "trigger_word": "t",
                    "profile": "p",
                }
            },
            "environments": {"env1": {"profile": "e1", "trigger_word": "t"}},
            "scenes": [
                {
                    "scene_id": "099",
                    "shots": [
                        {
                            "dialogue": [
                                {
                                    "speaker": "totally_unknown",
                                    "emotion": "calm",
                                    "tone": None,
                                    "effect": None,
                                    "text": "Hello.",
                                }
                            ]
                        }
                    ],
                }
            ],
        }
        results = generate_episode_audio(ep, tmp_path)
        assert results["099"]["lines_generated"] == 1
        _, kwargs = mock_synth.call_args
        assert kwargs["seed"] == 42
        assert kwargs["temperature"] == 0.8


class TestMain:
    @patch("voice_generator_v3.generate_episode_audio")
    @patch("voice_generator_v3.check_fish_api")
    def test_main_happy_path(self, mock_check, mock_gen, sample_episode, tmp_path):
        from voice_generator_v3 import main

        mock_check.return_value = True
        mock_gen.return_value = {"001": {"lines_generated": 4, "scene_audio": None}}

        results = main(sample_episode, tmp_path)
        assert "001" in results

    @patch("voice_generator_v3.check_fish_api")
    def test_main_raises_when_api_down(self, mock_check, sample_episode, tmp_path):
        import voice_generator_v3

        mock_check.return_value = False
        with pytest.raises(RuntimeError, match="unavailable"):
            voice_generator_v3.main(sample_episode, tmp_path)
