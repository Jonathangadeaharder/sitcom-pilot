# AI Showrunner Blueprint Enhancements — Implementation Plan

> **DEPRECATED:** This plan describes enhancements to the v1 ComfyUI-based architecture. The codebase has since evolved to a v2 beat-based architecture with AIServices providers and Typer CLI. Many enhancements described here (NodeMap, crash recovery, multi-char LoRA, cooldown, output retrieval, server management) have been implemented differently in the current codebase. See README.md for the current architecture. This document is kept for historical reference only.
>
> **Key divergences from current code:**
> - `NodeMap` → exists but used only by legacy `ShotRenderer` (ComfyUI path); v2 uses `AIServicesClient` directly
> - `ProgressTracker` → current `progress.py` provides `RichRenderProgress` callback, not a file-based tracker
> - CLI is Typer, not argparse; `--crash-recovery`, `--resume`, `--assemble-only`, `--node-map` flags don't exist
> - `ShotRenderer` has crash recovery but v2 `scene_render._render_beat` uses `AIServicesClient` with retry
> - Episode schema uses `beats[]` not `shots[]`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the existing showrunner to match the master blueprint — add crash recovery, multi-character LoRA injection, configurable node mapping, output retrieval, VRAM cooldown, and full render→assemble pipeline.

**Architecture:** The existing 5-unit pipeline (EpisodeLoader → PromptBuilder → ShotRenderer → ComfyUIClient → EpisodeAssembler) is preserved. We add a `NodeMap` config layer to decouple hardcoded node IDs, extend `ComfyUIClient` with server management and output retrieval, enhance `ShotRenderer` with crash recovery and multi-character support, and wire the CLI for full end-to-end execution.

**Tech Stack:** Python 3.9+, pytest, urllib (stdlib), subprocess (stdlib), json (stdlib)

---

## Current State

36 tests passing across 7 test files. All units implemented:
- `src/showrunner/loader.py` — EpisodeLoader + dataclasses
- `src/showrunner/prompts.py` — PromptBuilder
- `src/showrunner/comfyui_client.py` — ComfyUIClient (queue, wait, retry)
- `src/showrunner/renderer.py` — ShotRenderer + RenderResult
- `src/showrunner/assembler.py` — EpisodeAssembler (FFmpeg concat, VideoToolbox)
- `src/showrunner/cli/main.py` — CLI entry point
- `episode_01.json` — Buffering S01E01 cut-sheet

## Gap Analysis (Blueprint vs Current)

| Feature | Blueprint | Current | Gap |
|---------|-----------|---------|-----|
| Node ID mapping | Named constants (`NODE_START_PROMPT = "6"`) | Hardcoded `"6"`, `"12"`, etc. in renderer | Task 1 |
| Multi-character LoRA | N character slots (nodes 41, 42, 43...) | Only first character injected (node 41) | Task 2 |
| ComfyUI output retrieval | Not explicit but implied | `wait_for_completion` returns bool only | Task 3 |
| Crash recovery / server restart | `while True` loop + `start_comfyui()` | Retry on queue only, no restart | Task 4 |
| VRAM cooldown | `time.sleep(10)` between shots | No cooldown | Task 5 |
| Progress tracking / resume | Implied by crash recovery | No state persistence | Task 5 |
| Full pipeline CLI | render → collect outputs → assemble | render only, no assembly | Task 6 |

---

## File Structure

```
showrunner/
├── src/
│   └── showrunner/
│       ├── __init__.py              # MODIFY: export new public API
│       ├── loader.py                # KEEP AS-IS
│       ├── prompts.py               # KEEP AS-IS
│       ├── comfyui_client.py        # MODIFY: add get_output_paths(), start_server()
│       ├── renderer.py              # MODIFY: multi-char LoRA, crash recovery, cooldown
│       ├── assembler.py             # KEEP AS-IS
│       ├── node_map.py              # CREATE: configurable node ID mapping
│       └── cli/
│           └── main.py              # MODIFY: full pipeline with assembly
├── tests/
│   ├── test_node_map.py         # CREATE
│   ├── test_renderer.py         # MODIFY: add multi-char tests, update existing
│   ├── test_comfyui_client.py   # MODIFY: add output retrieval + server mgmt tests
│   └── ... (existing tests unchanged)
└── episode_01.json              # KEEP AS-IS
```

---

## Task 1: NodeMap — Configurable Node ID Mapping

**Files:**
- Create: `src/showrunner/node_map.py`
- Create: `tests/test_node_map.py`

### Why

The blueprint uses named constants (`NODE_START_PROMPT`, `NODE_AUDIO_LOADER`, etc.) and the renderer currently hardcodes `"6"`, `"12"`, `"25"`, `"3"`, `"40"`, `"41"`. A `NodeMap` dataclass lets users configure their workflow's node IDs without touching code.

### RED

- [ ] **Step 1: Write failing tests**

```python
# tests/test_node_map.py
import pytest
from showrunner.node_map import NodeMap


def test_default_node_map_has_required_fields():
    nm = NodeMap()
    assert nm.start_prompt == "6"
    assert nm.end_prompt == "12"
    assert nm.audio == "25"
    assert nm.seed == "3"
    assert nm.env_profile == "40"
    assert nm.char_profiles == ["41", "42", "43"]


def test_custom_node_map_overrides():
    nm = NodeMap(start_prompt="10", end_prompt="20", audio="30", seed="1", env_profile="50", char_profiles=["51", "52"])
    assert nm.start_prompt == "10"
    assert nm.end_prompt == "20"
    assert nm.audio == "30"
    assert nm.seed == "1"
    assert nm.env_profile == "50"
    assert nm.char_profiles == ["51", "52"]


def test_from_dict_creates_node_map():
    data = {"start_prompt": "99", "end_prompt": "88", "audio": "77", "seed": "1", "env_profile": "55", "char_profiles": ["60", "61"]}
    nm = NodeMap.from_dict(data)
    assert nm.start_prompt == "99"
    assert nm.char_profiles == ["60", "61"]


def test_from_dict_uses_defaults_for_missing_keys():
    nm = NodeMap.from_dict({})
    assert nm.start_prompt == "6"
    assert nm.char_profiles == ["41", "42", "43"]


def test_from_dict_partial_override():
    nm = NodeMap.from_dict({"start_prompt": "100"})
    assert nm.start_prompt == "100"
    assert nm.end_prompt == "12"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_node_map.py -v`
Expected: FAIL (module not found)

### GREEN

- [ ] **Step 3: Implement NodeMap**

```python
# src/showrunner/node_map.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class NodeMap:
    start_prompt: str = "6"
    end_prompt: str = "12"
    audio: str = "25"
    seed: str = "3"
    env_profile: str = "40"
    char_profiles: list[str] = field(default_factory=lambda: ["41", "42", "43"])

    @classmethod
    def from_dict(cls, data: dict) -> NodeMap:
        return cls(
            start_prompt=data.get("start_prompt", cls.start_prompt),
            end_prompt=data.get("end_prompt", cls.end_prompt),
            audio=data.get("audio", cls.audio),
            seed=data.get("seed", cls.seed),
            env_profile=data.get("env_profile", cls.env_profile),
            char_profiles=data.get("char_profiles", ["41", "42", "43"]),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_node_map.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/showrunner/node_map.py tests/test_node_map.py
git commit -m "feat: add NodeMap for configurable ComfyUI node ID mapping"
```

---

## Task 2: ShotRenderer — Multi-Character LoRA + NodeMap

**Files:**
- Modify: `src/showrunner/renderer.py`
- Modify: `tests/test_renderer.py`

### Why

The renderer currently injects only the first character LoRA into node `"41"`. The blueprint supports multiple character slots. We also switch from hardcoded node IDs to `NodeMap`.

### RED

- [ ] **Step 1: Write failing tests**

Add these tests to `tests/test_renderer.py`. Also update existing fixtures to use `NodeMap`.

```python
# Add to top of tests/test_renderer.py
from showrunner.node_map import NodeMap


# Add new fixtures and tests after existing ones:


@pytest.fixture
def multi_char_episode():
    return EpisodeData(
        title="Multi",
        cast={
            "A": CharacterData("a_v1", "aaa"),
            "B": CharacterData("b_v1", "bbb"),
            "C": CharacterData("c_v1", "ccc"),
        },
        environments={"Room": EnvironmentData("room_v1", "room")},
        scenes=[SceneData("S01", "Room", ["A", "B", "C"], [
            ShotData("S01_SH01", "wide", "standing", "sitting", "a.wav", 1),
        ])],
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
    renderer.render_shot(multi_char_episode.scenes[0].shots[0], multi_char_episode.scenes[0], multi_char_episode, template)
    call_args = mock_client.queue_prompt.call_args[0][0]
    assert call_args["41"]["inputs"]["lora_name"] == "a_v1.safetensors"
    assert call_args["42"]["inputs"]["lora_name"] == "b_v1.safetensors"
    assert call_args["43"]["inputs"]["lora_name"] == "c_v1.safetensors"


def test_render_shot_uses_node_map_for_injection(episode, mock_client):
    custom_map = NodeMap(start_prompt="100", end_prompt="200", audio="300", seed="400", env_profile="500", char_profiles=["600"])
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_renderer.py::test_render_shot_injects_multiple_character_loras tests/test_renderer.py::test_render_shot_uses_node_map_for_injection -v`
Expected: FAIL

### GREEN

- [ ] **Step 3: Update ShotRenderer to use NodeMap and inject multiple character LoRAs**

Replace the entire contents of `src/showrunner/renderer.py`:

```python
# src/showrunner/renderer.py
from __future__ import annotations
import copy
import logging
from dataclasses import dataclass
from typing import Any
from showrunner.comfyui_client import ComfyUIClient
from showrunner.loader import EpisodeData, SceneData, ShotData
from showrunner.node_map import NodeMap
from showrunner.prompts import PromptBuilder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderResult:
    shot_id: str
    prompt_id: str
    success: bool


class ShotRenderer:
    def __init__(
        self,
        client: ComfyUIClient,
        builder: PromptBuilder,
        node_map: NodeMap | None = None,
        cooldown_seconds: float = 0.0,
    ):
        self._client = client
        self._builder = builder
        self._node_map = node_map or NodeMap()
        self._cooldown_seconds = cooldown_seconds

    def render_shot(
        self, shot: ShotData, scene: SceneData, episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> RenderResult:
        workflow = copy.deepcopy(workflow_template)
        nm = self._node_map

        env_data = episode.environments.get(scene.environment)
        if env_data:
            workflow.get(nm.env_profile, {}).setdefault("inputs", {})["lora_name"] = f"{env_data.profile}.safetensors"

        for idx, char_name in enumerate(scene.characters_present):
            if idx >= len(nm.char_profiles):
                break
            char_data = episode.cast.get(char_name)
            if char_data:
                node_id = nm.char_profiles[idx]
                workflow.get(node_id, {}).setdefault("inputs", {})["lora_name"] = f"{char_data.profile}.safetensors"

        start_prompt = self._builder.build_start_prompt(shot, scene, episode)
        end_prompt = self._builder.build_end_prompt(shot, scene, episode)

        workflow.get(nm.start_prompt, {}).setdefault("inputs", {})["text"] = start_prompt
        workflow.get(nm.end_prompt, {}).setdefault("inputs", {})["text"] = end_prompt
        workflow.get(nm.seed, {}).setdefault("inputs", {})["seed"] = shot.seed
        workflow.get(nm.audio, {}).setdefault("inputs", {})["audio"] = shot.audio_path

        prompt_id = self._client.queue_prompt(workflow)
        success = self._client.wait_for_completion(prompt_id)
        return RenderResult(shot_id=shot.shot_id, prompt_id=prompt_id, success=success)

    def render_scene(
        self, scene: SceneData, episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> list[RenderResult]:
        import time
        results = []
        for shot in scene.shots:
            logger.info(f"Rendering {shot.shot_id}")
            results.append(self.render_shot(shot, scene, episode, workflow_template))
            if self._cooldown_seconds > 0:
                logger.info(f"Cooldown {self._cooldown_seconds}s")
                time.sleep(self._cooldown_seconds)
        return results

    def render_episode(
        self, episode: EpisodeData, workflow_template: dict[str, Any],
    ) -> dict[str, list[RenderResult]]:
        results = {}
        for scene in episode.scenes:
            results[scene.scene_id] = self.render_scene(scene, episode, workflow_template)
        return results
```

- [ ] **Step 4: Run ALL renderer tests (old + new)**

Run: `python3 -m pytest tests/test_renderer.py -v`
Expected: All 9 PASS (7 existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add src/showrunner/renderer.py tests/test_renderer.py
git commit -m "feat: add multi-character LoRA injection and NodeMap support to ShotRenderer"
```

---

## Task 3: ComfyUIClient — Output Retrieval + Server Management

**Files:**
- Modify: `src/showrunner/comfyui_client.py`
- Modify: `tests/test_comfyui_client.py`

### Why

The blueprint's crash recovery loop needs to know if ComfyUI is alive and be able to restart it. The full pipeline needs to retrieve output file paths from ComfyUI history after a render completes.

### RED

- [ ] **Step 1: Write failing tests**

Add these to `tests/test_comfyui_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_comfyui_client.py::test_get_output_paths_returns_file_list tests/test_comfyui_client.py::test_start_server_launches_subprocess -v`
Expected: FAIL

### GREEN

- [ ] **Step 3: Add `get_output_paths()`, `start_server()`, and `ensure_server_running()` to ComfyUIClient**

Replace `src/showrunner/comfyui_client.py`:

```python
# src/showrunner/comfyui_client.py
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
                self.start_server(cmd, cwd)
            else:
                raise RuntimeError("ComfyUI is not running and no start command provided")

    def queue_prompt(self, workflow: dict[str, Any], max_retries: int = 3) -> str:
        data = json.dumps({"prompt": workflow}).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/prompt", data=data,
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
                time.sleep(2 ** attempt)
        raise last_error

    def wait_for_completion(self, prompt_id: str, timeout: int = 600, poll_interval: float = 3.0) -> bool:
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
        for node_id, node_output in outputs.items():
            for key in ("images", "videos", "gifs"):
                for item in node_output.get(key, []):
                    filenames.append(item["filename"])
        return filenames
```

- [ ] **Step 4: Run ALL ComfyUIClient tests (old + new)**

Run: `python3 -m pytest tests/test_comfyui_client.py -v`
Expected: All 13 PASS (7 existing + 6 new)

- [ ] **Step 5: Commit**

```bash
git add src/showrunner/comfyui_client.py tests/test_comfyui_client.py
git commit -m "feat: add output retrieval and server management to ComfyUIClient"
```

---

## Task 4: ShotRenderer — Crash Recovery Loop

**Files:**
- Modify: `src/showrunner/renderer.py`
- Modify: `tests/test_renderer.py`

### Why

The blueprint's `render_shot` has a `while True` loop that detects when ComfyUI crashes and restarts it before retrying. We add crash recovery to `ShotRenderer.render_shot`.

### RED

- [ ] **Step 1: Write failing tests**

Add to `tests/test_renderer.py`:

```python
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
        client=mock_client, builder=PromptBuilder(), node_map=node_map,
        crash_recovery=True, server_cmd=["python", "main.py"], server_cwd="/opt/comfyui",
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_renderer.py::test_render_shot_retries_on_server_crash tests/test_renderer.py::test_render_shot_crash_recovery_disabled_raises -v`
Expected: FAIL

### GREEN

- [ ] **Step 3: Add crash recovery to ShotRenderer.render_shot**

Replace `src/showrunner/renderer.py`:

```python
# src/showrunner/renderer.py
from __future__ import annotations
import copy
import logging
import time
from dataclasses import dataclass
from typing import Any
from showrunner.comfyui_client import ComfyUIClient
from showrunner.loader import EpisodeData, SceneData, ShotData
from showrunner.node_map import NodeMap
from showrunner.prompts import PromptBuilder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderResult:
    shot_id: str
    prompt_id: str
    success: bool


class ShotRenderer:
    def __init__(
        self,
        client: ComfyUIClient,
        builder: PromptBuilder,
        node_map: NodeMap | None = None,
        cooldown_seconds: float = 0.0,
        crash_recovery: bool = False,
        server_cmd: list[str] | None = None,
        server_cwd: str | None = None,
        max_crash_retries: int = 5,
    ):
        self._client = client
        self._builder = builder
        self._node_map = node_map or NodeMap()
        self._cooldown_seconds = cooldown_seconds
        self._crash_recovery = crash_recovery
        self._server_cmd = server_cmd
        self._server_cwd = server_cwd
        self._max_crash_retries = max_crash_retries

    def _inject_workflow(self, shot: ShotData, scene: SceneData, episode: EpisodeData, workflow: dict[str, Any]) -> None:
        nm = self._node_map
        env_data = episode.environments.get(scene.environment)
        if env_data:
            workflow.get(nm.env_profile, {}).setdefault("inputs", {})["lora_name"] = f"{env_data.profile}.safetensors"

        for idx, char_name in enumerate(scene.characters_present):
            if idx >= len(nm.char_profiles):
                break
            char_data = episode.cast.get(char_name)
            if char_data:
                node_id = nm.char_profiles[idx]
                workflow.get(node_id, {}).setdefault("inputs", {})["lora_name"] = f"{char_data.profile}.safetensors"

        start_prompt = self._builder.build_start_prompt(shot, scene, episode)
        end_prompt = self._builder.build_end_prompt(shot, scene, episode)
        workflow.get(nm.start_prompt, {}).setdefault("inputs", {})["text"] = start_prompt
        workflow.get(nm.end_prompt, {}).setdefault("inputs", {})["text"] = end_prompt
        workflow.get(nm.seed, {}).setdefault("inputs", {})["seed"] = shot.seed
        workflow.get(nm.audio, {}).setdefault("inputs", {})["audio"] = shot.audio_path

    def render_shot(
        self, shot: ShotData, scene: SceneData, episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> RenderResult:
        workflow = copy.deepcopy(workflow_template)
        self._inject_workflow(shot, scene, episode, workflow)

        if not self._crash_recovery:
            prompt_id = self._client.queue_prompt(workflow)
            success = self._client.wait_for_completion(prompt_id)
            return RenderResult(shot_id=shot.shot_id, prompt_id=prompt_id, success=success)

        for attempt in range(self._max_crash_retries):
            try:
                if not self._client.is_server_running():
                    logger.warning(f"[{shot.shot_id}] ComfyUI down, restarting...")
                    self._client.ensure_server_running(self._server_cmd, self._server_cwd)
                prompt_id = self._client.queue_prompt(workflow)
                logger.info(f"[{shot.shot_id}] Queued as {prompt_id}")
                success = self._client.wait_for_completion(prompt_id)
                return RenderResult(shot_id=shot.shot_id, prompt_id=prompt_id, success=success)
            except Exception as e:
                logger.warning(f"[{shot.shot_id}] Crash attempt {attempt + 1}/{self._max_crash_retries}: {e}")
                time.sleep(5)
        return RenderResult(shot_id=shot.shot_id, prompt_id="", success=False)

    def render_scene(
        self, scene: SceneData, episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> list[RenderResult]:
        results = []
        for shot in scene.shots:
            logger.info(f"Rendering {shot.shot_id}")
            results.append(self.render_shot(shot, scene, episode, workflow_template))
            if self._cooldown_seconds > 0:
                logger.info(f"Cooldown {self._cooldown_seconds}s")
                time.sleep(self._cooldown_seconds)
        return results

    def render_episode(
        self, episode: EpisodeData, workflow_template: dict[str, Any],
    ) -> dict[str, list[RenderResult]]:
        results = {}
        for scene in episode.scenes:
            results[scene.scene_id] = self.render_scene(scene, episode, workflow_template)
        return results
```

- [ ] **Step 4: Run ALL renderer tests**

Run: `python3 -m pytest tests/test_renderer.py -v`
Expected: All 11 PASS (9 previous + 2 new)

- [ ] **Step 5: Commit**

```bash
git add src/showrunner/renderer.py tests/test_renderer.py
git commit -m "feat: add crash recovery loop with server restart to ShotRenderer"
```

---

## Task 5: Progress Tracking — Crash Resume

**Files:**
- Create: `src/showrunner/progress.py`
- Create: `tests/test_progress.py`

### Why

Long render sessions (2-12 hours per the blueprint) need crash resume. A `ProgressTracker` records completed shots to disk so the pipeline can skip them on restart.

### RED

- [ ] **Step 1: Write failing tests**

```python
# tests/test_progress.py
import pytest
from pathlib import Path
from showrunner.progress import ProgressTracker


def test_mark_done_creates_entry(tmp_path):
    tracker = ProgressTracker(state_file=tmp_path / "state.json")
    tracker.mark_done("S01_SH01")
    assert tracker.is_done("S01_SH01")


def test_is_done_returns_false_for_unknown(tmp_path):
    tracker = ProgressTracker(state_file=tmp_path / "state.json")
    assert tracker.is_done("S99_SH99") is False


def test_persists_across_instances(tmp_path):
    state = tmp_path / "state.json"
    t1 = ProgressTracker(state_file=state)
    t1.mark_done("S01_SH01")
    t1.mark_done("S01_SH02")
    t2 = ProgressTracker(state_file=state)
    assert t2.is_done("S01_SH01")
    assert t2.is_done("S01_SH02")
    assert t2.is_done("S02_SH01") is False


def test_completed_shot_ids_returns_all(tmp_path):
    tracker = ProgressTracker(state_file=tmp_path / "state.json")
    tracker.mark_done("A")
    tracker.mark_done("B")
    tracker.mark_done("C")
    assert set(tracker.completed_shot_ids()) == {"A", "B", "C"}


def test_reset_clears_all(tmp_path):
    tracker = ProgressTracker(state_file=tmp_path / "state.json")
    tracker.mark_done("X")
    tracker.reset()
    assert tracker.is_done("X") is False
    assert tracker.completed_shot_ids() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_progress.py -v`
Expected: FAIL

### GREEN

- [ ] **Step 3: Implement ProgressTracker**

```python
# src/showrunner/progress.py
from __future__ import annotations
import json
from pathlib import Path


class ProgressTracker:
    def __init__(self, state_file: Path):
        self._state_file = state_file
        self._done: set[str] = self._load()

    def _load(self) -> set[str]:
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())
                return set(data.get("completed", []))
            except (json.JSONDecodeError, KeyError):
                pass
        return set()

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps({"completed": sorted(self._done)}))

    def mark_done(self, shot_id: str) -> None:
        self._done.add(shot_id)
        self._save()

    def is_done(self, shot_id: str) -> bool:
        return shot_id in self._done

    def completed_shot_ids(self) -> list[str]:
        return sorted(self._done)

    def reset(self) -> None:
        self._done.clear()
        self._save()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_progress.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/showrunner/progress.py tests/test_progress.py
git commit -m "feat: add ProgressTracker for crash-resume state persistence"
```

---

## Task 6: CLI — Full Pipeline (Render → Assemble)

**Files:**
- Modify: `src/showrunner/cli/main.py`
- Modify: `src/showrunner/__init__.py`

### Why

The CLI currently renders shots but doesn't collect outputs or assemble them. The blueprint's Phase 5 requires collecting all shot outputs and concatenating into the final episode. We also add `--node-map`, `--cooldown`, `--crash-recovery`, and `--resume` flags.

### RED

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:

```python
# tests/test_cli.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from showrunner.node_map import NodeMap


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


def test_dry_run_prints_prompts(tmp_path, capsys):
    ep = tmp_path / "episode.json"
    ep.write_text(json.dumps(EPISODE_JSON))
    wf = tmp_path / "workflow.json"
    wf.write_text(json.dumps({"6": {"inputs": {"text": ""}}, "12": {"inputs": {"text": ""}}, "25": {"inputs": {"audio": ""}}, "3": {"inputs": {"seed": 0}}, "40": {"inputs": {"lora_name": ""}}, "41": {"inputs": {"lora_name": ""}}}))
    import sys
    with patch.object(sys, "argv", ["showrunner", str(ep), "--workflow", str(wf), "--dry-run"]):
        from showrunner.cli.main import main
        main()
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

    with patch("showrunner.ComfyUIClient", return_value=mock_client):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_ffmpeg:
            import sys
            with patch.object(sys, "argv", ["showrunner", str(ep), "--workflow", str(wf), "--output-dir", str(out_dir)]):
                from showrunner.cli.main import main
                main()

    assert mock_client.queue_prompt.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: FAIL

### GREEN

- [ ] **Step 3: Update CLI with full pipeline**

Replace `src/showrunner/cli/main.py`:

```python
#!/usr/bin/env python3
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from showrunner.loader import EpisodeLoader
from showrunner.node_map import NodeMap
from showrunner.progress import ProgressTracker
from showrunner.prompts import PromptBuilder
from showrunner.comfyui_client import ComfyUIClient
from showrunner.renderer import ShotRenderer, RenderResult
from showrunner.assembler import EpisodeAssembler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="AI Showrunner Orchestrator")
    parser.add_argument("episode", help="Path to episode JSON cut-sheet")
    parser.add_argument("--workflow", default="workflow_api.json", help="ComfyUI workflow template")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--output-dir", default="output/rendered")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without rendering")
    parser.add_argument("--cooldown", type=float, default=10.0, help="Seconds between shots for VRAM cooldown")
    parser.add_argument("--crash-recovery", action="store_true", help="Auto-restart ComfyUI on crash")
    parser.add_argument("--server-cmd", nargs="+", default=None, help="Command to start ComfyUI server")
    parser.add_argument("--server-cwd", default=None, help="Working directory for ComfyUI server")
    parser.add_argument("--node-map", default=None, help="JSON file with custom node ID mapping")
    parser.add_argument("--resume", action="store_true", help="Resume from previous progress")
    parser.add_argument("--assemble-only", action="store_true", help="Skip rendering, assemble existing outputs")
    args = parser.parse_args()

    episode = EpisodeLoader().load(Path(args.episode))
    template = json.load(open(args.workflow))

    node_map = NodeMap()
    if args.node_map:
        node_map = NodeMap.from_dict(json.load(open(args.node_map)))

    if args.dry_run:
        builder = PromptBuilder()
        for scene in episode.scenes:
            for shot in scene.shots:
                start = builder.build_start_prompt(shot, scene, episode)
                end = builder.build_end_prompt(shot, scene, episode)
                print(f"\n[{shot.shot_id}]")
                print(f"  START: {start}")
                print(f"  END:   {end}")
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    progress = ProgressTracker(state_file=output_dir / "progress.json")

    client = ComfyUIClient(base_url=args.comfy_url)
    if not client.is_server_running():
        if args.server_cmd and args.server_cwd:
            client.start_server(args.server_cmd, args.server_cwd)
        else:
            print("ComfyUI is not running. Use --server-cmd and --server-cwd or start it manually.")
            sys.exit(1)

    renderer = ShotRenderer(
        client=client,
        builder=PromptBuilder(),
        node_map=node_map,
        cooldown_seconds=args.cooldown,
        crash_recovery=args.crash_recovery,
        server_cmd=args.server_cmd,
        server_cwd=args.server_cwd,
    )

    output_clips: list[Path] = []
    total = sum(len(s.shots) for s in episode.scenes)
    rendered = 0

    for scene in episode.scenes:
        for shot in scene.shots:
            if args.resume and progress.is_done(shot.shot_id):
                print(f"[SKIP] {shot.shot_id} (already done)")
                rendered += 1
                continue

            result = renderer.render_shot(shot, scene, episode, template)
            rendered += 1

            if result.success:
                outputs = client.get_output_paths(result.prompt_id)
                if outputs:
                    output_clips.append(Path(outputs[0]))
                progress.mark_done(shot.shot_id)
                print(f"[{rendered}/{total}] {shot.shot_id} done ({len(outputs)} outputs)")
            else:
                print(f"[{rendered}/{total}] {shot.shot_id} FAILED")

    if output_clips:
        assembler = EpisodeAssembler(output_dir=output_dir)
        final = output_dir / "final_episode.mp4"
        if assembler.concatenate(output_clips, final):
            print(f"\nFinal episode: {final}")
        else:
            print("\nAssembly failed")
    else:
        print("\nNo clips to assemble")

    print(f"\nRendering complete. {rendered}/{total} shots processed.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Update `src/showrunner/__init__.py`**

```python
# src/showrunner/__init__.py
from showrunner.loader import EpisodeLoader
from showrunner.node_map import NodeMap
from showrunner.progress import ProgressTracker
from showrunner.prompts import PromptBuilder
from showrunner.comfyui_client import ComfyUIClient
from showrunner.renderer import ShotRenderer
from showrunner.assembler import EpisodeAssembler

__all__ = [
    "EpisodeLoader", "NodeMap", "ProgressTracker", "PromptBuilder",
    "ComfyUIClient", "ShotRenderer", "EpisodeAssembler",
]
```

- [ ] **Step 5: Run ALL tests**

Run: `python3 -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/showrunner/cli/main.py src/showrunner/__init__.py tests/test_cli.py
git commit -m "feat: full pipeline CLI with crash recovery, cooldown, resume, and assembly"
```

---

## Task 7: Update Integration Tests

**Files:**
- Modify: `tests/test_integration.py`

### Why

The integration tests use hardcoded node IDs and the old single-character injection. They need to use `NodeMap` and test multi-character workflows.

### Implementation

- [ ] **Step 1: Update integration tests to use NodeMap and multi-char**

Update `test_loader_to_renderer_end_to_end` to verify multi-character LoRA injection, and add a test for the full pipeline including output retrieval:

```python
# tests/test_integration.py — replace entire file

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from showrunner.loader import EpisodeLoader
from showrunner.node_map import NodeMap
from showrunner.prompts import PromptBuilder
from showrunner.renderer import ShotRenderer
from showrunner.comfyui_client import ComfyUIClient
from showrunner.assembler import EpisodeAssembler
from showrunner.progress import ProgressTracker


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


@pytest.fixture
def episode(tmp_path):
    p = tmp_path / "episode.json"
    p.write_text(json.dumps(EPISODE_JSON))
    return EpisodeLoader().load(p)


@pytest.fixture
def template():
    return {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
        "42": {"inputs": {"lora_name": ""}},
    }


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


def test_loader_to_renderer_multi_char_lora(episode, template):
    mock_client = MagicMock(spec=ComfyUIClient)
    mock_client.queue_prompt.side_effect = ["pid1", "pid2", "pid3"]
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    results = renderer.render_episode(episode, template)

    assert len(results["S01"]) == 2
    assert len(results["S02"]) == 1
    assert all(r.success for r in results["S01"])

    workflow = mock_client.queue_prompt.call_args_list[0][0][0]
    assert workflow["41"]["inputs"]["lora_name"] == "maya_v1.safetensors"
    assert workflow["42"]["inputs"]["lora_name"] == "derek_v1.safetensors"
    assert workflow["40"]["inputs"]["lora_name"] == "living_room_v2.safetensors"


def test_prompt_builder_to_renderer_injects_both_prompts(episode, template):
    mock_client = MagicMock(spec=ComfyUIClient)
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)

    workflow = mock_client.queue_prompt.call_args[0][0]
    assert "typing furiously" in workflow["6"]["inputs"]["text"]
    assert "throwing hands up" in workflow["12"]["inputs"]["text"]


def test_renderer_to_assembler_concat_list(tmp_path, episode, template):
    mock_client = MagicMock(spec=ComfyUIClient)
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    results = renderer.render_episode(episode, template)

    all_successful = [r for scene_results in results.values() for r in scene_results if r.success]
    assert len(all_successful) == 3

    assembler = EpisodeAssembler(output_dir=tmp_path / "out")
    fake_clips = [tmp_path / f"{r.shot_id}.mp4" for r in all_successful]
    for c in fake_clips:
        c.write_bytes(b"\x00")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        ok = assembler.concatenate(fake_clips, tmp_path / "out" / "final.mp4")
        assert ok is True


def test_progress_tracker_with_render_results(tmp_path, episode, template):
    mock_client = MagicMock(spec=ComfyUIClient)
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True

    tracker = ProgressTracker(state_file=tmp_path / "progress.json")
    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    results = renderer.render_episode(episode, template)

    for scene_results in results.values():
        for r in scene_results:
            if r.success:
                tracker.mark_done(r.shot_id)

    assert tracker.is_done("S01_SH01")
    assert tracker.is_done("S01_SH02")
    assert tracker.is_done("S02_SH01")
    assert len(tracker.completed_shot_ids()) == 3


def test_node_map_custom_ids_used_in_renderer(episode, tmp_path):
    custom_map = NodeMap(start_prompt="100", end_prompt="200", audio="300", seed="400", env_profile="500", char_profiles=["600", "601"])
    template = {
        "100": {"inputs": {"text": ""}},
        "200": {"inputs": {"text": ""}},
        "300": {"inputs": {"audio": ""}},
        "400": {"inputs": {"seed": 0}},
        "500": {"inputs": {"lora_name": ""}},
        "600": {"inputs": {"lora_name": ""}},
        "601": {"inputs": {"lora_name": ""}},
    }
    mock_client = MagicMock(spec=ComfyUIClient)
    mock_client.queue_prompt.return_value = "pid"
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder(), node_map=custom_map)
    renderer.render_shot(episode.scenes[0].shots[0], episode.scenes[0], episode, template)

    workflow = mock_client.queue_prompt.call_args[0][0]
    assert workflow["500"]["inputs"]["lora_name"] == "living_room_v2.safetensors"
    assert workflow["600"]["inputs"]["lora_name"] == "maya_v1.safetensors"
    assert workflow["601"]["inputs"]["lora_name"] == "derek_v1.safetensors"
```

- [ ] **Step 2: Run integration tests**

Run: `python3 -m pytest tests/test_integration.py -v`
Expected: All PASS

- [ ] **Step 3: Run full test suite**

Run: `python3 -m pytest tests/ -v --tb=short`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: update integration tests for multi-char LoRA, NodeMap, and progress tracking"
```

---

## Task 8: Run Full Test Suite — Final Verification

- [ ] **Step 1: Run all tests**

Run: `python3 -m pytest tests/ -v --tb=short`
Expected: All PASS

- [ ] **Step 2: Run dry-run on real episode**

Run: `python3 -m showrunner.cli.main episode_01.json --dry-run`
Expected: Prints all 16 shot prompts with START and END text

- [ ] **Step 3: Verify test count**

Expected test counts by file:
- `test_node_map.py`: 5
- `test_loader.py`: 4
- `test_prompts.py`: 4
- `test_comfyui_client.py`: 13 (7 old + 6 new)
- `test_renderer.py`: 11 (7 old + 4 new)
- `test_assembler.py`: 8
- `test_progress.py`: 5
- `test_integration.py`: 6 (5 old updated + 1 new)
- `test_episode_01.py`: 1
- `test_cli.py`: 2

**Total: ~59 tests**
