import json
import pytest
from unittest.mock import patch, MagicMock
from orchestrator.comfyui_client import ComfyUIClient


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
            assert call_count == 2


def test_queue_prompt_raises_after_max_retries(client):
    with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
        with patch("time.sleep"):
            with pytest.raises(ConnectionError):
                client.queue_prompt({"test": True}, max_retries=2)


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
                "9": {"images": [{"filename": "output_001.mp4", "subfolder": "", "type": "output"}]},
                "15": {"videos": [{"filename": "final.mp4", "subfolder": "batch", "type": "output"}]},
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
        mock_popen.return_value = MagicMock()
        client.start_server(cmd=["python", "main.py"], cwd="/opt/comfyui")
        mock_popen.assert_called_once_with(["python", "main.py"], cwd="/opt/comfyui")


def test_ensure_server_running_does_nothing_when_up(client):
    with patch.object(client, "is_server_running", return_value=True):
        with patch.object(client, "start_server") as mock_start:
            client.ensure_server_running(cmd=["python", "main.py"], cwd="/opt/comfyui")
            mock_start.assert_not_called()


def test_ensure_server_running_starts_when_down(client):
    with patch.object(client, "is_server_running", return_value=False):
        with patch.object(client, "start_server") as mock_start:
            client.ensure_server_running(cmd=["python", "main.py"], cwd="/opt/comfyui")
            mock_start.assert_called_once_with(cmd=["python", "main.py"], cwd="/opt/comfyui")


def test_ensure_server_running_raises_without_cmd(client):
    with patch.object(client, "is_server_running", return_value=False):
        with pytest.raises(RuntimeError, match="no start command"):
            client.ensure_server_running()


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
