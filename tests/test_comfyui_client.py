import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from showrunner.comfyui_client import ComfyUIClient


@pytest.fixture
def client():
    return ComfyUIClient(base_url="http://localhost:8188")


def test_queue_prompt_returns_prompt_id(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"prompt_id": "abc-123"}).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        prompt_id = client.queue_prompt({"6": {"inputs": {"text": "test"}}})
        assert prompt_id == "abc-123"


def test_queue_prompt_retries_on_connection_error(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"prompt_id": "xyz"}).encode()
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Connection refused")
        return mock_response

    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep"):
            prompt_id = client.queue_prompt({"test": True}, max_retries=3)
            assert prompt_id == "xyz"


def test_queue_prompt_raises_after_max_retries(client):
    with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
        with patch("time.sleep"):
            with pytest.raises(ConnectionError) as exc_info:
                client.queue_prompt({"test": True}, max_retries=2)
            assert "refused" in str(exc_info.value)


def test_is_server_running_returns_true(client):
    mock_response = MagicMock()
    mock_response.status = 200
    with patch("urllib.request.urlopen", return_value=mock_response):
        assert client.is_server_running() is True


def test_is_server_running_returns_false_on_error(client):
    with patch("urllib.request.urlopen", side_effect=Exception("down")):
        assert client.is_server_running() is False


def test_wait_for_completion_returns_true(client):
    history = {"abc-123": {"status": {"completed": True}}}
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(history).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        result = client.wait_for_completion("abc-123", timeout=5, poll_interval=0.1)
        assert result is True


def test_wait_for_completion_returns_false_on_timeout(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({}).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        result = client.wait_for_completion("missing", timeout=0.3, poll_interval=0.1)
        assert result is False


def test_get_output_paths_returns_file_list(client):
    history = {
        "abc-123": {
            "outputs": {
                "9": {
                    "images": [{"filename": "output_001.mp4", "subfolder": "", "type": "output"}]
                },
                "15": {
                    "videos": [{"filename": "final.mp4", "subfolder": "batch", "type": "output"}]
                },
            }
        }
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(history).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        paths = client.get_output_paths("abc-123")
        assert len(paths) == 2
        assert "output_001.mp4" in paths[0]
        assert "final.mp4" in paths[1]


def test_get_output_paths_returns_empty_on_missing(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({}).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        paths = client.get_output_paths("nonexistent")
        assert paths == []


def test_get_output_paths_combines_images_and_gifs(client):
    history = {
        "p1": {
            "outputs": {
                "5": {"images": [{"filename": "a.png", "subfolder": "", "type": "output"}]},
                "6": {"gifs": [{"filename": "b.mp4", "subfolder": "", "type": "output"}]},
            }
        }
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(history).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        paths = client.get_output_paths("p1")
        assert len(paths) == 2
        assert "a.png" in paths[0]
        assert "b.mp4" in paths[1]


def test_start_server_launches_subprocess(client):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        client.start_server(cmd=["python", "main.py"], cwd="/opt/comfyui")
        assert client._server_process is mock_process


def test_ensure_server_running_does_nothing_when_up(client):
    with patch.object(client, "is_server_running", return_value=True):
        with patch.object(client, "start_server") as mock_start:
            result = client.ensure_server_running(cmd=["python", "main.py"], cwd="/opt/comfyui")
            mock_start.assert_not_called()
            assert result is None


def test_ensure_server_running_starts_when_down(client):
    with patch.object(client, "is_server_running", return_value=False):
        with patch.object(client, "start_server") as mock_start:
            client.ensure_server_running(cmd=["python", "main.py"], cwd="/opt/comfyui")
            mock_start.assert_called_once()


def test_ensure_server_running_raises_without_cmd(client):
    with patch.object(client, "is_server_running", return_value=False):
        with pytest.raises(RuntimeError, match="no start command") as exc_info:
            client.ensure_server_running()
        assert "no start command" in str(exc_info.value)


def test_wait_for_completion_recovers_from_exception(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"abc": {}}).encode()
    with patch("urllib.request.urlopen", side_effect=[Exception("err"), mock_response]):
        result = client.wait_for_completion("abc", timeout=5, poll_interval=0.01)
        assert result is True


def test_get_output_paths_returns_empty_on_exception(client):
    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        paths = client.get_output_paths("abc")
        assert paths == []


def test_get_output_paths_returns_empty_on_no_entry(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"other-id": {}}).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        paths = client.get_output_paths("abc")
        assert paths == []


def test_queue_prompt_sends_correct_request(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"prompt_id": "abc"}).encode()
    workflow = {"6": {"inputs": {"text": "test"}}}
    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        client.queue_prompt(workflow)
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://localhost:8188/prompt"
        assert req.headers.get("Content-type") == "application/json"
        body = json.loads(req.data)
        assert body == {"prompt": workflow}
        assert mock_urlopen.call_args[1]["timeout"] == 30


def test_queue_prompt_retry_backoff(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"prompt_id": "ok"}).encode()
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("retry")
        return mock_response

    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep") as mock_sleep:
            client.queue_prompt({"test": True}, max_retries=3)
            assert mock_sleep.call_args_list[0][0][0] == 1
            assert mock_sleep.call_args_list[1][0][0] == 2


def test_queue_prompt_retries_on_url_error(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"prompt_id": "ok"}).encode()
    with patch("urllib.request.urlopen", side_effect=[urllib.error.URLError("err"), mock_response]):
        with patch("time.sleep"):
            prompt_id = client.queue_prompt({"t": 1}, max_retries=3)
            assert prompt_id == "ok"


def test_queue_prompt_returns_empty_default_on_missing_key(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({}).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        prompt_id = client.queue_prompt({"t": 1})
        assert prompt_id == ""


def test_start_server_assigns_process(client):
    mock_process = MagicMock()
    with patch("subprocess.Popen", return_value=mock_process):
        with patch("time.sleep"):
            client.start_server(cmd=["python", "main.py"], cwd="/opt/comfyui")
            assert client._server_process is mock_process


def test_start_server_sleeps_for_readiness(client):
    with patch("subprocess.Popen", return_value=MagicMock()):
        with patch("time.sleep") as mock_sleep:
            client.start_server(cmd=["python", "main.py"], cwd="/opt/comfyui")
            assert client._server_process is not None


def test_wait_for_completion_uses_correct_url(client):
    history = {"abc-123": {}}
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(history).encode()
    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        with patch("time.time", side_effect=[0, 0.001]):
            client.wait_for_completion("abc-123", timeout=5, poll_interval=0.01)
            url = mock_urlopen.call_args[0][0]
            assert "/history/abc-123" in url
            assert mock_urlopen.call_args[1]["timeout"] == 10


def test_wait_for_completion_polls_with_correct_interval(client):
    call_count = 0

    def time_side_effect():
        nonlocal call_count
        call_count += 1
        return call_count * 0.05

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"x": {}}).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        with patch("time.time", side_effect=time_side_effect):
            with patch("time.sleep") as mock_sleep:
                client.wait_for_completion("abc", timeout=0.15, poll_interval=0.05)
                if mock_sleep.called:
                    assert mock_sleep.call_args[0][0] == 0.05


def test_get_output_paths_all_three_media_types(client):
    history = {
        "p1": {
            "outputs": {
                "5": {
                    "images": [{"filename": "a.png", "subfolder": "", "type": "output"}],
                    "videos": [{"filename": "b.mp4", "subfolder": "", "type": "output"}],
                    "gifs": [{"filename": "c.gif", "subfolder": "", "type": "output"}],
                }
            }
        }
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(history).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        paths = client.get_output_paths("p1")
        assert paths == ["a.png", "b.mp4", "c.gif"]


def test_get_output_paths_missing_outputs_key(client):
    history = {"p1": {"status": "done"}}
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(history).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        paths = client.get_output_paths("p1")
        assert paths == []


def test_get_output_paths_exact_order(client):
    history = {
        "p1": {
            "outputs": {
                "1": {"images": [{"filename": "first.png", "subfolder": "", "type": "output"}]},
                "2": {"images": [{"filename": "second.png", "subfolder": "", "type": "output"}]},
            }
        }
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(history).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        paths = client.get_output_paths("p1")
        assert paths[0] == "first.png"
        assert paths[1] == "second.png"


def test_is_server_running_checks_system_stats(client):
    mock_response = MagicMock()
    mock_response.status = 200
    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        client.is_server_running()
        url = mock_urlopen.call_args[0][0]
        assert "/system_stats" in url
        assert mock_urlopen.call_args[1]["timeout"] == 5
