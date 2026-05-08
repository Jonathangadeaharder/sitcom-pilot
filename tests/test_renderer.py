from unittest.mock import MagicMock, patch

import pytest

from showrunner.comfyui_client import ComfyUIClient
from showrunner.loader import (
    CharacterData,
    EnvironmentData,
    EpisodeData,
    SceneData,
    ShotData,
)
from showrunner.node_map import NodeMap
from showrunner.prompts import PromptBuilder
from showrunner.renderer import ShotRenderer


@pytest.fixture
def episode():
    return EpisodeData(
        title="Test",
        cast={"Jerry": CharacterData(profile="jerry_v2", trigger_word="jry_guy")},
        environments={"Apt": EnvironmentData(profile="apt_v1", trigger_word="apartment")},
        scenes=[
            SceneData(
                scene_id="S01",
                environment="Apt",
                characters_present=["Jerry"],
                shots=[
                    ShotData("S01_SH01", "wide shot", "standing", "sitting", 42, "a.wav"),
                    ShotData("S01_SH02", "close up", "smiling", "frowning", 99, "b.wav"),
                ],
            )
        ],
    )


@pytest.fixture
def mock_client():
    return MagicMock(spec=ComfyUIClient)


@pytest.fixture
def workflow_template():
    return {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }


def test_render_scene_renders_all_shots(episode, mock_client, workflow_template):
    mock_client.queue_prompt.side_effect = ["id1", "id2"]
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    results = renderer.render_scene(episode.scenes[0], episode, workflow_template)
    assert len(results) == 2
    assert results[0].shot_id == "S01_SH01"
    assert results[0].success is True
    assert results[1].shot_id == "S01_SH02"
    assert mock_client.queue_prompt.call_count == 2


def test_render_shot_injects_prompts_into_template(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid-1"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template)
    call_args = mock_client.queue_prompt.call_args[0][0]
    assert "apartment" in call_args["6"]["inputs"]["text"]
    assert "jry_guy" in call_args["6"]["inputs"]["text"]
    assert call_args["3"]["inputs"]["seed"] == 42
    assert call_args["25"]["inputs"]["audio"] == "a.wav"


def test_render_shot_injects_environment_lora(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid-1"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template)
    call_args = mock_client.queue_prompt.call_args[0][0]
    assert call_args["40"]["inputs"]["lora_name"] == "apt_v1.safetensors"


def test_render_shot_injects_character_loras(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid-1"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template)
    call_args = mock_client.queue_prompt.call_args[0][0]
    assert call_args["41"]["inputs"]["lora_name"] == "jerry_v2.safetensors"


def test_render_shot_handles_timeout_as_failure(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid-1"
    mock_client.wait_for_completion.return_value = False
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    result = renderer.render_shot(
        episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template
    )
    assert result.success is False


def test_render_episode_renders_all_scenes(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    results = renderer.render_episode(episode, workflow_template)
    assert "S01" in results
    assert len(results["S01"]) == 2


def test_render_shot_does_not_mutate_template(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    original_seed = workflow_template["3"]["inputs"]["seed"]
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template)
    assert workflow_template["3"]["inputs"]["seed"] == original_seed


@pytest.fixture
def multi_char_episode():
    return EpisodeData(
        title="Multi",
        cast={
            "A": CharacterData(profile="a_v1", trigger_word="aaa"),
            "B": CharacterData(profile="b_v1", trigger_word="bbb"),
            "C": CharacterData(profile="c_v1", trigger_word="ccc"),
        },
        environments={"Room": EnvironmentData(profile="room_v1", trigger_word="room")},
        scenes=[
            SceneData(
                scene_id="S01",
                environment="Room",
                characters_present=["A", "B", "C"],
                shots=[ShotData("S01_SH01", "wide", "standing", "sitting", 1, "a.wav")],
            )
        ],
    )


@pytest.fixture
def node_map():
    return NodeMap()


def test_render_shot_injects_multiple_character_loras(multi_char_episode, mock_client, node_map):
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
        "42": {"inputs": {"lora_name": ""}},
        "43": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=node_map)
    renderer.render_shot(
        multi_char_episode.scenes[0].shots[0],
        multi_char_episode.scenes[0],
        multi_char_episode,
        template,
    )
    call_args = mock_client.queue_prompt.call_args[0][0]
    assert call_args["41"]["inputs"]["lora_name"] == "a_v1.safetensors"
    assert call_args["42"]["inputs"]["lora_name"] == "b_v1.safetensors"
    assert call_args["43"]["inputs"]["lora_name"] == "c_v1.safetensors"


def test_render_shot_uses_node_map_for_injection(episode, mock_client):
    custom_map = NodeMap(
        start_prompt="100",
        end_prompt="200",
        audio="300",
        seed="400",
        env_profile="500",
        char_profiles=["600"],
    )
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    template = {
        "100": {"inputs": {"text": ""}},
        "200": {"inputs": {"text": ""}},
        "300": {"inputs": {"audio": ""}},
        "400": {"inputs": {"seed": 0}},
        "500": {"inputs": {"lora_name": ""}},
        "600": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=custom_map)
    renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)
    call_args = mock_client.queue_prompt.call_args[0][0]
    assert call_args["100"]["inputs"]["text"] != ""
    assert call_args["200"]["inputs"]["text"] != ""
    assert call_args["300"]["inputs"]["audio"] == "a.wav"
    assert call_args["400"]["inputs"]["seed"] == 42
    assert call_args["500"]["inputs"]["lora_name"] == "apt_v1.safetensors"
    assert call_args["600"]["inputs"]["lora_name"] == "jerry_v2.safetensors"


def test_render_shot_retries_on_server_crash(episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = [ConnectionError("refused"), "pid-retry"]
    mock_client.wait_for_completion.return_value = True
    mock_client.is_server_running.return_value = False
    mock_client.ensure_server_running = MagicMock()
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(
        client=mock_client,
        builder=PromptBuilder(),
        node_map=node_map,
        crash_recovery=True,
        server_cmd=["python", "main.py"],
        server_cwd="/opt/comfyui",
    )
    result = renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)
    assert result.success is True
    assert result.prompt_id == "pid-retry"
    assert mock_client.queue_prompt.call_count == 2


def test_render_shot_crash_recovery_disabled_raises(episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = ConnectionError("refused")
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=node_map)
    with pytest.raises(ConnectionError):
        renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)
    assert mock_client.queue_prompt.call_count >= 1


def test_render_shot_char_profiles_overflow(mock_client):
    single_char_map = NodeMap(char_profiles=["41"])
    multi_ep = EpisodeData(
        title="Overflow",
        cast={
            "A": CharacterData(profile="a_v1", trigger_word="aaa"),
            "B": CharacterData(profile="b_v1", trigger_word="bbb"),
        },
        environments={"Room": EnvironmentData(profile="room_v1", trigger_word="room")},
        scenes=[
            SceneData(
                scene_id="S01",
                environment="Room",
                characters_present=["A", "B"],
                shots=[ShotData("S01_SH01", "wide", "a", "b", 1, "a.wav")],
            )
        ],
    )
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=single_char_map)
    renderer.render_shot(multi_ep.scenes[0].shots[0], multi_ep.scenes[0], multi_ep, template)
    call_args = mock_client.queue_prompt.call_args[0][0]
    assert call_args["41"]["inputs"]["lora_name"] == "a_v1.safetensors"


def test_render_shot_crash_recovery_raises_after_max_retries(episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = ConnectionError("refused")
    mock_client.is_server_running.return_value = False
    mock_client.ensure_server_running = MagicMock()
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(
        client=mock_client,
        builder=PromptBuilder(),
        node_map=node_map,
        crash_recovery=True,
        server_cmd=["python", "main.py"],
        server_cwd="/opt",
        max_crash_retries=2,
    )
    with patch("time.sleep"):
        with pytest.raises(ConnectionError) as exc_info:
            renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)
    assert "refused" in str(exc_info.value)
    assert mock_client.queue_prompt.call_count == 2


def test_render_scene_with_cooldown(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), cooldown_seconds=0.01)
    with patch("time.sleep") as mock_sleep:
        renderer.render_scene(episode.scenes[0], episode, workflow_template)
        assert mock_sleep.call_count == 2


def test_render_shot_no_env_data(mock_client):
    ep = EpisodeData(
        title="NoEnv",
        cast={"X": CharacterData(profile="x_v1", trigger_word="xxx")},
        environments={},
        scenes=[
            SceneData(
                scene_id="S01",
                environment="NonExistent",
                characters_present=["X"],
                shots=[ShotData("S01_SH01", "wide", "a", "b", 1, "a.wav")],
            )
        ],
    )
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "41": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(
        client=mock_client, builder=PromptBuilder(), node_map=NodeMap(env_profile="40")
    )
    result = renderer.render_shot(ep.scenes[0].shots[0], ep.scenes[0], ep, template)
    assert result.success is True


def test_render_shot_start_end_prompts_go_to_correct_nodes(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template)
    call_args = mock_client.queue_prompt.call_args[0][0]
    start_text = call_args["6"]["inputs"]["text"]
    end_text = call_args["12"]["inputs"]["text"]
    assert "standing" in start_text
    assert "sitting" not in start_text
    assert "sitting" in end_text
    assert "standing" not in end_text


def test_render_shot_non_recovery_does_not_check_server(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), crash_recovery=False)
    result = renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template)
    mock_client.is_server_running.assert_not_called()
    assert result.success is True


def test_render_shot_result_contains_prompt_id(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "my-prompt-id"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    result = renderer.render_shot(
        episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template
    )
    assert result.prompt_id == "my-prompt-id"


def test_render_shot_retries_calls_ensure_server_with_correct_args(episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = [ConnectionError("refused"), "pid-retry"]
    mock_client.wait_for_completion.return_value = True
    mock_client.is_server_running.return_value = False
    mock_client.ensure_server_running = MagicMock()
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(
        client=mock_client,
        builder=PromptBuilder(),
        node_map=node_map,
        crash_recovery=True,
        server_cmd=["python", "main.py"],
        server_cwd="/opt/comfyui",
    )
    result = renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)
    mock_client.ensure_server_running.assert_called_once_with(["python", "main.py"], "/opt/comfyui")
    assert result.success is True


def test_render_shot_crash_recovery_skips_restart_when_server_up(episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = [ConnectionError("refused"), "pid-ok"]
    mock_client.wait_for_completion.return_value = True
    mock_client.is_server_running.return_value = True
    mock_client.ensure_server_running = MagicMock()
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(
        client=mock_client,
        builder=PromptBuilder(),
        node_map=node_map,
        crash_recovery=True,
        server_cmd=["python", "main.py"],
        server_cwd="/opt/comfyui",
    )
    result = renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)
    assert result.success is True
    mock_client.ensure_server_running.assert_not_called()


def test_render_shot_crash_recovery_raises_correct_exception(episode, mock_client, node_map):
    mock_client.queue_prompt.side_effect = ConnectionError("refused")
    mock_client.is_server_running.return_value = False
    mock_client.ensure_server_running = MagicMock()
    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }
    renderer = ShotRenderer(
        client=mock_client,
        builder=PromptBuilder(),
        node_map=node_map,
        crash_recovery=True,
        server_cmd=["python", "main.py"],
        server_cwd="/opt",
        max_crash_retries=2,
    )
    with patch("time.sleep"):
        with pytest.raises(ConnectionError) as exc_info:
            renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)
    assert "refused" in str(exc_info.value)
    assert mock_client.queue_prompt.call_count >= 1


def test_inject_workflow_with_minimal_template(mock_client):
    template = {"6": {}, "12": {}, "25": {}, "3": {}, "40": {}, "41": {}}
    ep = EpisodeData(
        title="T",
        cast={"X": CharacterData(profile="x_v1", trigger_word="xxx")},
        environments={"R": EnvironmentData(profile="r_v1", trigger_word="room")},
        scenes=[
            SceneData(
                scene_id="S1",
                environment="R",
                characters_present=["X"],
                shots=[ShotData("S1_SH1", "wide", "a", "b", 7, "aud.wav")],
            )
        ],
    )
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(ep.scenes[0].shots[0], ep.scenes[0], ep, template)
    wf = mock_client.queue_prompt.call_args[0][0]
    assert wf["6"]["inputs"]["text"] != ""
    assert wf["3"]["inputs"]["seed"] == 7
    assert wf["25"]["inputs"]["audio"] == "aud.wav"


def test_render_scene_cooldown_sleeps_correct_duration(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), cooldown_seconds=5.0)
    with patch("time.sleep") as mock_sleep:
        renderer.render_scene(episode.scenes[0], episode, workflow_template)
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 5.0
