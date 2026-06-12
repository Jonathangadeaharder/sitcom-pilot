"""HTTP client for the ComfyUI API (v1 render path).

Design rules (TDD-010):
- httpx instead of hand-rolled urllib plumbing.
- No silent excepts: every swallowed error is logged with context.
- Only ``queue_prompt`` raises (after exhausting retries); polling helpers
  degrade gracefully and log, since callers treat them as best-effort.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_HEALTH_TIMEOUT = 5.0
_QUEUE_TIMEOUT = 30.0
_POLL_TIMEOUT = 10.0
_STARTUP_TIMEOUT = 60.0

_RECOVERABLE = (httpx.HTTPError, json.JSONDecodeError)


class ComfyUIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self._base_url = base_url.rstrip("/")
        self._server_process: subprocess.Popen[bytes] | None = None
        self._http = httpx.Client(base_url=self._base_url, timeout=_POLL_TIMEOUT)

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    def is_server_running(self) -> bool:
        try:
            resp = self._http.get("/system_stats", timeout=_HEALTH_TIMEOUT)
        except httpx.HTTPError as exc:
            logger.debug("ComfyUI health check failed: %s", exc)
            return False
        return resp.status_code == 200

    def start_server(self, cmd: list[str], cwd: str) -> None:
        logger.info("Starting ComfyUI: %s", " ".join(cmd))
        self._server_process = subprocess.Popen(cmd, cwd=cwd)
        deadline = time.monotonic() + _STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            if self.is_server_running():
                logger.info("ComfyUI is ready")
                return
            time.sleep(1.0)
        raise RuntimeError(f"ComfyUI did not become ready within {_STARTUP_TIMEOUT:.0f}s")

    def ensure_server_running(self, cmd: list[str] | None = None, cwd: str | None = None) -> None:
        if not self.is_server_running():
            if cmd and cwd:
                self.start_server(cmd=cmd, cwd=cwd)
            else:
                raise RuntimeError("ComfyUI is not running and no start command provided")

    def queue_prompt(self, workflow: dict[str, Any], max_retries: int = 3) -> str:
        """Submit a workflow; retries with exponential backoff, raises on exhaustion."""
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                resp = self._http.post(
                    "/prompt", json={"prompt": workflow}, timeout=_QUEUE_TIMEOUT
                )
                resp.raise_for_status()
                prompt_id = str(resp.json().get("prompt_id", ""))
                if not prompt_id:
                    logger.warning("ComfyUI accepted the prompt but returned no prompt_id")
                return prompt_id
            except _RECOVERABLE as exc:
                last_error = exc
                logger.warning(
                    "Queue attempt %d/%d failed: %s", attempt + 1, max_retries, exc
                )
                time.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 600,
        poll_interval: float = 3.0,
    ) -> bool:
        """Poll history until the prompt completes; False on timeout (never raises)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            history = self._fetch_history(prompt_id)
            if history is not None and prompt_id in history:
                return True
            time.sleep(poll_interval)
        logger.warning("Timed out after %ds waiting for prompt %s", timeout, prompt_id)
        return False

    def get_output_paths(self, prompt_id: str) -> list[str]:
        history = self._fetch_history(prompt_id)
        if history is None:
            return []

        entry = history.get(prompt_id)
        if not entry:
            logger.warning("Prompt %s not present in ComfyUI history", prompt_id)
            return []

        outputs = entry.get("outputs", {})
        filenames: list[str] = []
        for _node_id, node_output in outputs.items():
            for key in ("images", "videos", "gifs"):
                for item in node_output.get(key, []):
                    filenames.append(item["filename"])
        return filenames

    def _fetch_history(self, prompt_id: str) -> dict[str, Any] | None:
        """One history fetch; logs and returns None on failure instead of raising."""
        try:
            resp = self._http.get(f"/history/{prompt_id}", timeout=_POLL_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except _RECOVERABLE as exc:
            logger.warning("History fetch for %s failed: %s", prompt_id, exc)
            return None
