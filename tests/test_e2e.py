import json
from unittest.mock import MagicMock, patch

from showrunner.assembler import concat_clips
from showrunner.comfyui_client import ComfyUIClient
from showrunner.loader import (
    EpisodeLoader,
)
from showrunner.progress import ProgressTracker
from showrunner.prompts import PromptBuilder
from showrunner.renderer import ShotRenderer

EPISODE_JSON = {
    "episode_title": "E2E Test Episode",
    "cast": {
        "Maya": {"profile": "maya_v1", "trigger_word": "mya_girl, purple hoodie"},
        "Derek": {"profile": "derek_v1", "trigger_word": "drk_man, navy blazer"},
    },
    "environments": {
        "LivingRoom": {"profile": "living_room_v2", "trigger_word": "SF apartment"},
    },
    "scenes": [
        {
            "scene_id": "S01",
            "environment": "LivingRoom",
            "characters_present": ["Maya", "Derek"],
            "shots": [
                {
                    "shot_id": "S01_SH01",
                    "camera_angle": "wide",
                    "action_start": "entering room",
                    "action_end": "sitting down",
                    "audio_path": "audio/s1_shot1.wav",
                    "seed": 42,
                },
            ],
        },
        {
            "scene_id": "S02",
            "environment": "LivingRoom",
            "characters_present": ["Maya"],
            "shots": [
                {
                    "shot_id": "S02_SH01",
                    "camera_angle": "close up",
                    "action_start": "smiling",
                    "action_end": "laughing",
                    "audio_path": "audio/s2_shot1.wav",
                    "seed": 99,
                },
            ],
        },
    ],
}


def test_full_pipeline_load_render_assemble(tmp_path):
    ep_file = tmp_path / "episode.json"
    ep_file.write_text(json.dumps(EPISODE_JSON))
    episode = EpisodeLoader().load(ep_file)
    assert episode.title == "E2E Test Episode"
    assert len(episode.scenes) == 2

    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
        "42": {"inputs": {"lora_name": ""}},
    }

    mock_client = MagicMock(spec=ComfyUIClient)
    mock_client.queue_prompt.side_effect = ["pid1", "pid2"]
    mock_client.wait_for_completion.return_value = True
    mock_client.get_output_paths.side_effect = [["output/s01_sh01.mp4"], ["output/s02_sh01.mp4"]]

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    progress = ProgressTracker(state_file=tmp_path / "progress.json")
    all_outputs = []
    for scene in episode.scenes:
        for shot in scene.shots:
            result = renderer.render_shot(shot, scene, episode, template)
            assert result.success
            outputs = mock_client.get_output_paths(result.prompt_id)
            all_outputs.extend(outputs)
            progress.mark_done(shot.shot_id)

    assert len(all_outputs) == 2
    assert progress.is_done("S01_SH01")
    assert progress.is_done("S02_SH01")

    fake_clips = [tmp_path / "clip1.mp4", tmp_path / "clip2.mp4"]
    for c in fake_clips:
        c.write_bytes(b"\x00\x00\x00")
    with patch("sitcom_pilot.assembler._run", return_value=MagicMock(returncode=0)):
        result = concat_clips(fake_clips, tmp_path / "final" / "episode.mp4")
        assert result == tmp_path / "final" / "episode.mp4"

    wf = mock_client.queue_prompt.call_args_list[0][0][0]
    assert wf["40"]["inputs"]["lora_name"] == "living_room_v2.safetensors"
    assert wf["41"]["inputs"]["lora_name"] == "maya_v1.safetensors"
    assert wf["42"]["inputs"]["lora_name"] == "derek_v1.safetensors"
    assert "entering room" in wf["6"]["inputs"]["text"]
    assert "sitting down" in wf["12"]["inputs"]["text"]


def test_pipeline_resume_after_partial_failure(tmp_path):
    ep_file = tmp_path / "episode.json"
    ep_file.write_text(json.dumps(EPISODE_JSON))
    episode = EpisodeLoader().load(ep_file)

    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
        "42": {"inputs": {"lora_name": ""}},
    }

    mock_client = MagicMock(spec=ComfyUIClient)
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.side_effect = [True, False]
    mock_client.get_output_paths.return_value = ["shot.mp4"]

    progress = ProgressTracker(state_file=tmp_path / "progress.json")
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())

    for scene in episode.scenes:
        for shot in scene.shots:
            if progress.is_done(shot.shot_id):
                continue
            result = renderer.render_shot(shot, scene, episode, template)
            if result.success:
                mock_client.get_output_paths(result.prompt_id)
                progress.mark_done(shot.shot_id)

    assert progress.is_done("S01_SH01")
    assert not progress.is_done("S02_SH01")

    progress2 = ProgressTracker(state_file=tmp_path / "progress.json")
    assert progress2.is_done("S01_SH01")
    assert not progress2.is_done("S02_SH01")
