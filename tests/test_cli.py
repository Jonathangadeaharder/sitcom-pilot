import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from orchestrator.node_map import NodeMap

EPISODE_JSON = {
    "episode_title": "CLI Test",
    "cast": {"Maya": {"profile": "maya_v1", "trigger_word": "maya"}},
    "environments": {"Room": {"profile": "room_v1", "trigger_word": "room"}},
    "scenes": [
        {
            "scene_id": "S01",
            "environment": "Room",
            "characters_present": ["Maya"],
            "shots": [
                {"shot_id": "S01_SH01", "camera_angle": "wide", "action_start": "a", "action_end": "b", "audio_path": "a.wav", "seed": 1},
                {"shot_id": "S01_SH02", "camera_angle": "close", "action_start": "c", "action_end": "d", "audio_path": "b.wav", "seed": 2},
            ],
        },
    ],
}


def _load_main_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_orchestrator_main",
        str(Path(__file__).resolve().parent.parent / "legacy" / "orchestrator.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dry_run_prints_prompts(tmp_path, capsys):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps(EPISODE_JSON))
    wf = tmp_path / "workflow.json"
    wf.write_text(json.dumps({"6": {"inputs": {"text": ""}}, "12": {"inputs": {"text": ""}}, "25": {"inputs": {"audio": ""}}, "3": {"inputs": {"seed": 0}}, "40": {"inputs": {"lora_name": ""}}, "41": {"inputs": {"lora_name": ""}}}))
    import sys
    with patch.object(sys, "argv", ["orchestrator.py", str(ep), "--workflow", str(wf), "--dry-run"]):
        mod = _load_main_module()
        mod.main()
    output = capsys.readouterr().out
    assert "S01_SH01" in output
    assert "S01_SH02" in output
    assert "START:" in output
    assert "maya" in output


def test_render_and_assemble(tmp_path):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps(EPISODE_JSON))
    wf = tmp_path / "workflow.json"
    wf.write_text(json.dumps({"6": {"inputs": {"text": ""}}, "12": {"inputs": {"text": ""}}, "25": {"inputs": {"audio": ""}}, "3": {"inputs": {"seed": 0}}, "40": {"inputs": {"lora_name": ""}}, "41": {"inputs": {"lora_name": ""}}}))
    out_dir = tmp_path / "output"

    mock_client = MagicMock()
    mock_client.is_server_running.return_value = True
    mock_client.queue_prompt.side_effect = ["pid1", "pid2"]
    mock_client.wait_for_completion.return_value = True
    mock_client.get_output_paths.side_effect = [["shot1.mp4"], ["shot2.mp4"]]

    mock_client_cls = MagicMock(return_value=mock_client)

    with patch("orchestrator.comfyui_client.ComfyUIClient", mock_client_cls):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            import sys
            with patch.object(sys, "argv", ["orchestrator.py", str(ep), "--workflow", str(wf), "--output-dir", str(out_dir)]):
                mod = _load_main_module()
                mod.main()

    assert mock_client.queue_prompt.call_count == 2


def test_cli_exits_when_server_down(tmp_path):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps(EPISODE_JSON))
    wf = tmp_path / "workflow.json"
    wf.write_text(json.dumps({"6": {"inputs": {"text": ""}}, "12": {"inputs": {"text": ""}}, "25": {"inputs": {"audio": ""}}, "3": {"inputs": {"seed": 0}}, "40": {"inputs": {"lora_name": ""}}, "41": {"inputs": {"lora_name": ""}}}))
    mock_client = MagicMock()
    mock_client.is_server_running.return_value = False
    mock_client_cls = MagicMock(return_value=mock_client)
    with patch("orchestrator.comfyui_client.ComfyUIClient", mock_client_cls):
        import sys
        with patch.object(sys, "argv", ["orchestrator.py", str(ep), "--workflow", str(wf)]):
            mod = _load_main_module()
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 1


def test_cli_with_resume(tmp_path):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps(EPISODE_JSON))
    wf = tmp_path / "workflow.json"
    wf.write_text(json.dumps({"6": {"inputs": {"text": ""}}, "12": {"inputs": {"text": ""}}, "25": {"inputs": {"audio": ""}}, "3": {"inputs": {"seed": 0}}, "40": {"inputs": {"lora_name": ""}}, "41": {"inputs": {"lora_name": ""}}}))
    out_dir = tmp_path / "output"
    progress_file = tmp_path / "progress.json"
    mock_client = MagicMock()
    mock_client.is_server_running.return_value = True
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    mock_client.get_output_paths.return_value = ["shot.mp4"]
    mock_client_cls = MagicMock(return_value=mock_client)
    import sys
    with patch("orchestrator.comfyui_client.ComfyUIClient", mock_client_cls):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch.object(sys, "argv", ["orchestrator.py", str(ep), "--workflow", str(wf), "--output-dir", str(out_dir), "--resume", str(progress_file)]):
                mod = _load_main_module()
                mod.main()
    assert mock_client.queue_prompt.call_count == 2


def test_cli_with_node_map(tmp_path, capsys):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps(EPISODE_JSON))
    wf = tmp_path / "workflow.json"
    wf.write_text(json.dumps({"100": {"inputs": {"text": ""}}, "200": {"inputs": {"text": ""}}, "300": {"inputs": {"audio": ""}}, "400": {"inputs": {"seed": 0}}, "500": {"inputs": {"lora_name": ""}}, "600": {"inputs": {"lora_name": ""}}}))
    nm = tmp_path / "nodemap.json"
    nm.write_text(json.dumps({"start_prompt": "100", "end_prompt": "200", "audio": "300", "seed": "400", "env_profile": "500", "char_profiles": ["600"]}))
    import sys
    with patch.object(sys, "argv", ["orchestrator.py", str(ep), "--workflow", str(wf), "--dry-run", "--node-map", str(nm)]):
        mod = _load_main_module()
        mod.main()
    output = capsys.readouterr().out
    assert "S01_SH01" in output


def test_cli_no_outputs_to_assemble(tmp_path, capsys):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps(EPISODE_JSON))
    wf = tmp_path / "workflow.json"
    wf.write_text(json.dumps({"6": {"inputs": {"text": ""}}, "12": {"inputs": {"text": ""}}, "25": {"inputs": {"audio": ""}}, "3": {"inputs": {"seed": 0}}, "40": {"inputs": {"lora_name": ""}}, "41": {"inputs": {"lora_name": ""}}}))
    out_dir = tmp_path / "output"
    mock_client = MagicMock()
    mock_client.is_server_running.return_value = True
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = False
    mock_client_cls = MagicMock(return_value=mock_client)
    import sys
    with patch("orchestrator.comfyui_client.ComfyUIClient", mock_client_cls):
        with patch.object(sys, "argv", ["orchestrator.py", str(ep), "--workflow", str(wf), "--output-dir", str(out_dir)]):
            mod = _load_main_module()
            mod.main()
    output = capsys.readouterr().out
    assert "No outputs to assemble" in output


def test_cli_crash_recovery(tmp_path):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps(EPISODE_JSON))
    wf = tmp_path / "workflow.json"
    wf.write_text(json.dumps({"6": {"inputs": {"text": ""}}, "12": {"inputs": {"text": ""}}, "25": {"inputs": {"audio": ""}}, "3": {"inputs": {"seed": 0}}, "40": {"inputs": {"lora_name": ""}}, "41": {"inputs": {"lora_name": ""}}}))
    out_dir = tmp_path / "output"
    mock_client = MagicMock()
    mock_client.is_server_running.return_value = False
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True
    mock_client.get_output_paths.return_value = ["shot.mp4"]
    mock_client.ensure_server_running = MagicMock()
    mock_client_cls = MagicMock(return_value=mock_client)
    import sys
    with patch("orchestrator.comfyui_client.ComfyUIClient", mock_client_cls):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch.object(sys, "argv", ["orchestrator.py", str(ep), "--workflow", str(wf), "--output-dir", str(out_dir), "--crash-recovery", "--server-cmd", "python", "main.py", "--server-cwd", "/opt"]):
                mod = _load_main_module()
                mod.main()
    assert mock_client.queue_prompt.call_count == 2
