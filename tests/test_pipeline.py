from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.loader import EpisodeData, SceneData, ShotData, CharacterData, EnvironmentData, EpisodeLoader
import sys
# legacy/ is already on sys.path via conftest.py — pipeline.py lives there now
_LEGACY = str(Path(__file__).parent.parent / "legacy")
if _LEGACY not in sys.path:
    sys.path.insert(0, _LEGACY)

from pipeline import (
    generate_audio_for_episode,
    inject_audio_paths,
    merge_audio_video,
    run_pipeline,
)


def _mini_episode(tmp_path: Path) -> Path:
    ep = {
        "title": "Test Episode",
        "cast": {
            "maya": {"name": "Maya", "role": "engineer", "visual": "test",
                      "trigger_word": "test", "profile": "maya_v1",
                      "voice_seed": 42, "voice_temp": 0.8},
        },
        "environments": {
            "desk": {"profile": "desk_v1", "trigger_word": "a desk"},
        },
        "scenes": [
            {
                "scene_id": "001",
                "environment": "desk",
                "characters_present": ["maya"],
                "target_duration_sec": 30,
                "shots": [
                    {
                        "shot_id": "001_01",
                        "camera_angle": "close-up",
                        "action_start": "start",
                        "action_end": "end",
                        "seed": 100,
                        "dialogue": [
                            {"speaker": "maya", "emotion": "calm", "tone": None, "effect": None, "text": "Hello world"},
                        ],
                    },
                    {
                        "shot_id": "001_02",
                        "camera_angle": "wide",
                        "action_start": "start2",
                        "action_end": "end2",
                        "seed": 101,
                        "audio_path": "",
                        "dialogue": [],
                    },
                ],
            },
        ],
    }
    p = tmp_path / "episode.json"
    p.write_text(json.dumps(ep))
    return p


def _make_episode_data():
    cast = {"maya": CharacterData(profile="maya_v1", trigger_word="test")}
    envs = {"desk": EnvironmentData(profile="desk_v1", trigger_word="a desk")}
    shots = [
        ShotData(shot_id="001_01", camera_angle="close", action_start="s",
                 action_end="e", seed=1, dialogue=[{"speaker": "maya", "text": "hi"}]),
        ShotData(shot_id="001_02", camera_angle="wide", action_start="s",
                 action_end="e", seed=2, dialogue=[]),
    ]
    scene = SceneData(scene_id="001", environment="desk",
                      characters_present=["maya"], shots=shots, target_duration_sec=30)
    return EpisodeData(title="Test", cast=cast, environments=envs, scenes=[scene])


class TestGenerateAudio:
    def _mock_build_shot_audio(dialogue, character_id, output_path, **kwargs):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake_audio")
        return True

    @patch("pipeline.build_shot_audio", side_effect=_mock_build_shot_audio)
    def test_generates_audio_for_shots_with_dialogue(self, mock_build, tmp_path):
        ep = _make_episode_data()
        cast = {"maya": {"voice_seed": 42, "voice_temp": 0.8}}
        out = tmp_path / "out"
        result = generate_audio_for_episode(ep, out, cast)
        assert "001_01" in result
        assert "001_02" not in result
        assert mock_build.call_count == 1

    @patch("pipeline.build_shot_audio", return_value=False)
    def test_handles_audio_failure(self, mock_build, tmp_path):
        ep = _make_episode_data()
        cast = {"maya": {}}
        out = tmp_path / "out"
        result = generate_audio_for_episode(ep, out, cast)
        assert len(result) == 0

    def test_empty_episode(self, tmp_path):
        cast = {}
        shots = [ShotData(shot_id="001_01", camera_angle="c", action_start="s",
                          action_end="e", seed=1)]
        scene = SceneData(scene_id="001", environment="desk",
                          characters_present=[], shots=shots)
        ep = EpisodeData(title="T", cast={}, environments={}, scenes=[scene])
        out = tmp_path / "out"
        result = generate_audio_for_episode(ep, out, cast)
        assert result == {}


class TestInjectAudioPaths:
    def test_injects_audio_paths(self):
        ep = _make_episode_data()
        audio_map = {"001_01": Path("/tmp/audio/001_01.wav")}
        updated = inject_audio_paths(ep, audio_map)
        assert updated.scenes[0].shots[0].audio_path == "/tmp/audio/001_01.wav"
        assert updated.scenes[0].shots[1].audio_path == ""

    def test_preserves_structure(self):
        ep = _make_episode_data()
        updated = inject_audio_paths(ep, {})
        assert len(updated.scenes) == len(ep.scenes)
        assert len(updated.scenes[0].shots) == len(ep.scenes[0].shots)

    def test_empty_map(self):
        ep = _make_episode_data()
        updated = inject_audio_paths(ep, {})
        assert updated.scenes[0].shots[0].audio_path == ""


class TestMergeAudioVideo:
    def test_merge_calls_ffmpeg(self, tmp_path):
        video = tmp_path / "video.mp4"
        audio = tmp_path / "audio.wav"
        output = tmp_path / "merged.mp4"
        video.write_bytes(b"fake_video")
        audio.write_bytes(b"fake_audio")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            output.write_bytes(b"merged")
            result = merge_audio_video(video, audio, output)
            assert result is True
            mock_run.assert_called_once()

    def test_merge_missing_video(self, tmp_path):
        video = tmp_path / "nonexistent.mp4"
        audio = tmp_path / "audio.wav"
        audio.write_bytes(b"audio")
        result = merge_audio_video(video, audio, tmp_path / "out.mp4")
        assert result is False

    def test_merge_missing_audio(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"video")
        result = merge_audio_video(video, tmp_path / "no.wav", tmp_path / "out.mp4")
        assert result is False


class TestRunPipelineDryRun:
    def test_dry_run_prints_prompts(self, tmp_path, capsys):
        ep_path = _mini_episode(tmp_path)
        out_dir = tmp_path / "output"
        run_pipeline(ep_path, out_dir, dry_run=True)
        captured = capsys.readouterr()
        assert "001_01" in captured.out
        assert "001_02" in captured.out


class TestRunPipelineAudioOnly:
    @patch("pipeline.generate_audio_for_episode", return_value={"001_01": Path("/a.wav")})
    def test_audio_only_skips_video(self, mock_audio, tmp_path):
        ep_path = _mini_episode(tmp_path)
        out_dir = tmp_path / "output"
        result = run_pipeline(ep_path, out_dir, audio_only=True)
        mock_audio.assert_called_once()


class TestLoaderV2:
    def test_loads_episode_02(self, tmp_path):
        ep_path = _mini_episode(tmp_path)
        ep = EpisodeLoader().load(ep_path)
        assert ep.title == "Test Episode"
        assert len(ep.scenes) == 1
        assert len(ep.scenes[0].shots) == 2
        assert ep.scenes[0].shots[0].dialogue[0]["speaker"] == "maya"
        assert ep.scenes[0].shots[1].dialogue == []
        assert ep.scenes[0].target_duration_sec == 30

    def test_loads_real_episode_02(self):
        ep_path = Path(__file__).parent.parent / "episode_02.json"
        if not ep_path.exists():
            pytest.skip("episode_02.json not found")
        ep = EpisodeLoader().load(ep_path)
        assert ep.title == "The Demo Day"
        assert ep.schema_version == "2.0"
        assert len(ep.scenes) == 8
        # episode_02 is v2.0: beats not shots
        total_beats = sum(len(s.beats) for s in ep.scenes)
        assert total_beats == 128
        total_speech = sum(
            1 for scene in ep.scenes for beat in scene.beats if beat.kind == "speech"
        )
        assert total_speech == 102
