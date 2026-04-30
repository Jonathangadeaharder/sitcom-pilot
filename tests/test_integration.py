import json
from unittest.mock import MagicMock, patch

import pytest

from sitcom_pilot.assembler import concat_clips
from sitcom_pilot.comfyui_client import ComfyUIClient
from sitcom_pilot.loader import EpisodeLoader
from sitcom_pilot.node_map import NodeMap
from sitcom_pilot.progress import ProgressTracker
from sitcom_pilot.prompts import PromptBuilder
from sitcom_pilot.renderer import ShotRenderer

EPISODE_JSON = {
    "episode_title": "Integration Test Episode",
    "cast": {
        "Maya": {"profile": "maya_v1", "trigger_word": "mya_girl, purple hoodie"},
        "Derek": {"profile": "derek_v1", "trigger_word": "drk_man, navy blazer"},
    },
    "environments": {
        "LivingRoom": {"profile": "living_room_v2", "trigger_word": "SF apartment living room, bay bridge view"},
    },
    "scenes": [
        {
            "scene_id": "S01",
            "environment": "LivingRoom",
            "characters_present": ["Maya", "Derek"],
            "shots": [
                {
                    "shot_id": "S01_SH01",
                    "camera_angle": "wide shot of Maya and Derek",
                    "action_start": "Maya typing furiously",
                    "action_end": "Maya throwing hands up",
                    "audio_path": "audio/s1_shot1.wav",
                    "seed": 42,
                },
                {
                    "shot_id": "S01_SH02",
                    "camera_angle": "close up on Derek",
                    "action_start": "looking confident",
                    "action_end": "looking confused",
                    "audio_path": "audio/s1_shot2.wav",
                    "seed": 99,
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
                    "camera_angle": "medium shot",
                    "action_start": "Maya standing",
                    "action_end": "Maya sitting down",
                    "audio_path": "audio/s2_shot1.wav",
                    "seed": 200,
                },
            ],
        },
    ],
}

WORKFLOW_TEMPLATE = {
    "6": {"inputs": {"text": ""}},
    "12": {"inputs": {"text": ""}},
    "25": {"inputs": {"audio": ""}},
    "3": {"inputs": {"seed": 0}},
    "40": {"inputs": {"lora_name": ""}},
    "41": {"inputs": {"lora_name": ""}},
    "42": {"inputs": {"lora_name": ""}},
    "43": {"inputs": {"lora_name": ""}},
}


@pytest.fixture
def episode(tmp_path):
    p = tmp_path / "episode.json"
    p.write_text(json.dumps(EPISODE_JSON))
    return EpisodeLoader().load(p)


@pytest.fixture
def node_map():
    return NodeMap()


@pytest.fixture
def mock_client():
    return MagicMock(spec=ComfyUIClient)


def test_loader_to_prompt_builder_produces_valid_prompts(episode):
    builder = PromptBuilder()
    for scene in episode.scenes:
        for shot in scene.shots:
            start = builder.build_start_prompt(shot, scene, episode)
            end = builder.build_end_prompt(shot, scene, episode)
            assert "SF apartment living room" in start
            assert "SF apartment living room" in end
            assert "RAW photo, 8k" in start
            assert "RAW photo, 8k" in end
            assert shot.action_start in start
            assert shot.action_end in end


def test_loader_to_renderer_injects_multi_char_lora(episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = ["pid1", "pid2", "pid3"]
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=node_map)
    results = renderer.render_episode(episode, WORKFLOW_TEMPLATE)

    assert "S01" in results
    assert "S02" in results
    assert len(results["S01"]) == 2
    assert len(results["S02"]) == 1
    assert all(r.success for r in results["S01"])

    workflow = mock_client.queue_prompt.call_args_list[0][0][0]
    assert workflow["41"]["inputs"]["lora_name"] == "maya_v1.safetensors"
    assert workflow["42"]["inputs"]["lora_name"] == "derek_v1.safetensors"
    assert workflow["40"]["inputs"]["lora_name"] == "living_room_v2.safetensors"


def test_prompt_builder_to_renderer_injects_both_prompts(episode, mock_client, node_map):
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=node_map)
    renderer.render_shot(
        episode.scenes[0].shots[0], episode.scenes[0], episode, WORKFLOW_TEMPLATE
    )

    workflow = mock_client.queue_prompt.call_args[0][0]
    start_text = workflow["6"]["inputs"]["text"]
    end_text = workflow["12"]["inputs"]["text"]
    assert start_text != end_text
    assert "typing furiously" in start_text
    assert "throwing hands up" in end_text


def test_renderer_to_assembler_concat_list(tmp_path, episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = ["pid1", "pid2", "pid3"]
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=node_map)
    results = renderer.render_episode(episode, WORKFLOW_TEMPLATE)
    all_results = [r for scene_results in results.values() for r in scene_results]

    fake_clips = [tmp_path / f"{r.shot_id}.mp4" for r in all_results]
    for c in fake_clips:
        c.write_bytes(b"\x00")

    with patch("sitcom_pilot.assembler._run", return_value=MagicMock(returncode=0)):
        result = concat_clips(fake_clips, tmp_path / "out" / "final.mp4")

    assert result == tmp_path / "out" / "final.mp4"


def test_progress_tracker_with_render_results(tmp_path, episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = ["pid1", "pid2"]
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=node_map)
    results = renderer.render_scene(episode.scenes[0], episode, WORKFLOW_TEMPLATE)

    tracker = ProgressTracker(state_file=tmp_path / "progress.json")
    for r in results:
        if r.success:
            tracker.mark_done(r.shot_id)

    assert tracker.is_done("S01_SH01")
    assert tracker.is_done("S01_SH02")
    assert not tracker.is_done("S02_SH01")
    assert len(tracker.completed_shot_ids()) == 2


def test_node_map_custom_ids_used_in_renderer(episode, mock_client):
    custom_map = NodeMap(
        start_prompt="100", end_prompt="200", audio="300",
        seed="400", env_profile="500", char_profiles=["600", "601"],
    )
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True

    custom_template = {
        "100": {"inputs": {"text": ""}},
        "200": {"inputs": {"text": ""}},
        "300": {"inputs": {"audio": ""}},
        "400": {"inputs": {"seed": 0}},
        "500": {"inputs": {"lora_name": ""}},
        "600": {"inputs": {"lora_name": ""}},
        "601": {"inputs": {"lora_name": ""}},
    }

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=custom_map)
    renderer.render_shot(
        episode.scenes[0].shots[0], episode.scenes[0], episode, custom_template
    )

    workflow = mock_client.queue_prompt.call_args[0][0]
    assert workflow["100"]["inputs"]["text"] != ""
    assert workflow["200"]["inputs"]["text"] != ""
    assert workflow["300"]["inputs"]["audio"] == "audio/s1_shot1.wav"
    assert workflow["400"]["inputs"]["seed"] == 42
    assert workflow["500"]["inputs"]["lora_name"] == "living_room_v2.safetensors"
    assert workflow["600"]["inputs"]["lora_name"] == "maya_v1.safetensors"
    assert workflow["601"]["inputs"]["lora_name"] == "derek_v1.safetensors"
