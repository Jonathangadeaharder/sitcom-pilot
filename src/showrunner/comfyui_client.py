from __future__ import annotations

import json
import logging
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class ComfyUIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self._base_url = base_url.rstrip("/")
        self._server_process = None

    def is_server_running(self) -> bool:
        try:
            resp = urllib.request.urlopen(f"{self._base_url}/system_stats", timeout=5)
            return resp.status == 200
        except Exception:
            return False

    def start_server(self, cmd: list[str], cwd: str) -> None:
        logger.info(f"Starting ComfyUI: {' '.join(cmd)}")
        self._server_process = subprocess.Popen(cmd, cwd=cwd)
        logger.info("ComfyUI process launched, waiting for readiness...")
        time.sleep(10)

    def ensure_server_running(self, cmd: list[str] | None = None, cwd: str | None = None) -> None:
        if not self.is_server_running():
            if cmd and cwd:
                self.start_server(cmd=cmd, cwd=cwd)
            else:
                raise RuntimeError("ComfyUI is not running and no start command provided")

    def queue_prompt(self, workflow: dict[str, Any], max_retries: int = 3) -> str:
        data = json.dumps({"prompt": workflow}).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        last_error = None
        for attempt in range(max_retries):
            try:
                resp = urllib.request.urlopen(req, timeout=30)
                result = json.loads(resp.read())
                return result.get("prompt_id", "")
            except (urllib.error.URLError, ConnectionError) as e:
                last_error = e
                logger.warning(f"Queue attempt {attempt + 1}/{max_retries} failed: {e}")
                time.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 600,
        poll_interval: float = 3.0,
    ) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = urllib.request.urlopen(f"{self._base_url}/history/{prompt_id}", timeout=10)
                history = json.loads(resp.read())
                if prompt_id in history:
                    return True
            except Exception:
                pass
            time.sleep(poll_interval)
        return False

    def get_output_paths(self, prompt_id: str) -> list[str]:
        try:
            resp = urllib.request.urlopen(f"{self._base_url}/history/{prompt_id}", timeout=10)
            history = json.loads(resp.read())
        except Exception:
            return []

        entry = history.get(prompt_id)
        if not entry:
            return []

        outputs = entry.get("outputs", {})
        filenames = []
        for _node_id, node_output in outputs.items():
            for key in ("images", "videos", "gifs"):
                for item in node_output.get(key, []):
                    filenames.append(item["filename"])
        return filenames
