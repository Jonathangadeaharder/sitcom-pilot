# AI Showrunner Orchestrator — TDD Implementation Plan

> **DEPRECATED:** This plan describes the original v1 architecture (shot-based, ComfyUI-driven, argparse CLI). The codebase has since evolved to a v2 beat-based architecture with AIServices providers, Typer CLI, and ~25 source modules. See README.md for the current architecture. This document is kept for historical reference only.
>
> **Key divergences from current code:**
> - Schema v1 (`shots[]`, `shot_id`, `camera_angle`, `action_start`, `action_end`) → Schema v2 (`beats[]`, `beat_id`, `kind`, `camera`, `action`)
> - Python 3.9+ → Python >=3.11
> - argparse CLI → Typer CLI (`showrunner.cli.main:app`)
> - `PromptBuilder` (ComfyUI `build_start_prompt`/`build_end_prompt`) → `beat_prompts.build_beat_prompt()` (AIServices)
> - `ShotRenderer` (ComfyUI workflow injection) → `scene_render.render_scene/episode` (AIServicesClient)
> - `EpisodeAssembler` (class-based) → `assembler` module functions (`concat_clips`, `generate_srt`, `burn_in_captions`, etc.)
> - 5 source modules → ~25 source modules including determinism, cast_manifest, planner, progress, render_buffer, etc.
> - Stdlib-only deps → pydantic, structlog, typer, rich, jsonschema, pillow, scikit-image, aiservices packages
> - All TDD tasks have been completed (implemented differently than described here)

**Goal:** Build a decoupled, testable showrunner that drives ComfyUI via API to render video shots from a JSON cut-sheet, with crash recovery and Apple Silicon MPS optimization.

**Architecture:** Pipeline is split into 5 units with clear interfaces: (1) `EpisodeLoader` parses the JSON cut-sheet, (2) `PromptBuilder` constructs ComfyUI-ready prompts from shot data, (3) `ComfyUIClient` handles API communication with retry/crash recovery, (4) `ShotRenderer` orchestrates per-shot rendering, (5) `EpisodeAssembler` concatenates outputs. Each unit is independently testable.

**Tech Stack:** Python 3.9+, pytest, urllib (stdlib), subprocess (stdlib), json (stdlib)

---

## File Structure (v1 — as planned)

> **Note:** The actual current file structure is much larger. See README.md "Project Structure" for the current layout.

```
├── src/
│   └── showrunner/
│       ├── __init__.py          # Package init, exports __version__
│       ├── loader.py            # EpisodeLoader — parses episode JSON (v1 + v2)
│       ├── prompts.py           # PromptBuilder — builds ComfyUI text prompts (v1 legacy)
│       ├── comfyui_client.py    # ComfyUIClient — API communication + retry
│       ├── renderer.py          # ShotRenderer — drives per-shot render pipeline (v1 legacy)
│       ├── assembler.py         # FFmpeg assembly functions (concat, SRT, captions, music)
│       ├── beat_prompts.py      # Beat-based prompt generation (v2)
│       ├── scene_render.py      # BeatJob orchestration (v2)
│       ├── validator.py         # EpisodeValidator (jsonschema + business rules)
│       ├── planner.py           # Episode beat planning with cost estimation
│       ├── aiservices_client.py # AIServices unified facade
│       ├── config.py            # PipelineConfig (pydantic-settings)
│       ├── determinism.py       # Seed strategy and manifest hashing
│       ├── cast_manifest.py     # CastManifest tracking
│       └── cli/
│           └── main.py          # CLI entry point (Typer)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_loader.py           # Unit tests for EpisodeLoader
│   ├── test_prompts.py          # Unit tests for PromptBuilder
│   ├── test_comfyui_client.py   # Unit tests for ComfyUIClient
│   ├── test_renderer.py         # Unit tests for ShotRenderer
│   ├── test_assembler.py        # Unit tests for assembler functions
│   ├── test_integration.py      # Integration tests
│   └── ... (25+ additional test files)
└── episode_01.json              # The Buffering S01E01 episode
```

## Test Pyramid

```
        ╱  E2E  ╲           — Full pipeline with real ComfyUI (manual/ci)
       ╱──────────╲
      ╱ Integration ╲       — Pairs of units interacting (tests/test_integration.py)
     ╱────────────────╲
    ╱    Unit Tests     ╲   — Each unit in isolation (tests/test_*.py)
   ╱──────────────────────╲
```

---

## Task 1: EpisodeLoader — Parse Episode JSON

**Files:**
- Create: `src/showrunner/loader.py`
- Create: `tests/conftest.py`
- Create: `tests/test_loader.py`

### RED

- [x] **Step 1: Write failing test for loading a valid episode**

```python
# tests/test_loader.py
import json
import pytest
from pathlib import Path
from showrunner.loader import EpisodeLoader


def test_load_valid_episode_returns_episode_data(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "Test Episode",
        "cast": {
            "Jerry": {
                "profile": "jerry_v2",
                "trigger_word": "jry_guy, wearing a puffy shirt"
            }
        },
        "environments": {
            "Apt": {
                "profile": "apt_v1",
                "trigger_word": "apartment, couch, daylight"
            }
        },
        "scenes": [
            {
                "scene_id": "S01",
                "environment": "Apt",
                "characters_present": ["Jerry"],
                "shots": [
                    {
                        "shot_id": "S01_SH01",
                        "camera_angle": "wide shot",
                        "action_start": "standing",
                        "action_end": "sitting",
                        "audio_path": "audio/s1_shot1.wav",
                        "seed": 42
                    }
                ]
            }
        ]
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.title == "Test Episode"
    assert len(episode.scenes) == 1
    assert episode.scenes[0].shots[0].shot_id == "S01_SH01"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'showrunner'`

### GREEN

- [x] **Step 3: Create package init and minimal loader**

```python
# src/showrunner/__init__.py

from showrunner.loader import EpisodeLoader

__all__ = ["EpisodeLoader"]
```

```python
# src/showrunner/loader.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ShotData:
    shot_id: str
    camera_angle: str
    action_start: str
    action_end: str
    audio_path: str
    seed: int


@dataclass(frozen=True)
class CharacterData:
    profile: str
    trigger_word: str


@dataclass(frozen=True)
class EnvironmentData:
    profile: str
    trigger_word: str


@dataclass(frozen=True)
class SceneData:
    scene_id: str
    environment: str
    characters_present: list[str]
    shots: list[ShotData]


@dataclass(frozen=True)
class EpisodeData:
    title: str
    cast: dict[str, CharacterData]
    environments: dict[str, EnvironmentData]
    scenes: list[SceneData]


class EpisodeLoader:
    def load(self, path: Path) -> EpisodeData:
        with open(path) as f:
            raw = json.load(f)

        cast = {
            name: CharacterData(profile=v["profile"], trigger_word=v["trigger_word"])
            for name, v in raw["cast"].items()
        }

        environments = {
            name: EnvironmentData(profile=v["profile"], trigger_word=v["trigger_word"])
            for name, v in raw["environments"].items()
        }

        scenes = []
        for s in raw["scenes"]:
            shots = [
                ShotData(
                    shot_id=sh["shot_id"],
                    camera_angle=sh["camera_angle"],
                    action_start=sh["action_start"],
                    action_end=sh["action_end"],
                    audio_path=sh["audio_path"],
                    seed=sh["seed"],
                )
                for sh in s["shots"]
            ]
            scenes.append(SceneData(
                scene_id=s["scene_id"],
                environment=s["environment"],
                characters_present=s["characters_present"],
                shots=shots,
            ))

        return EpisodeData(
            title=raw["episode_title"],
            cast=cast,
            environments=environments,
            scenes=scenes,
        )
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_loader.py -v`
Expected: PASS

### MORE TESTS

- [x] **Step 5: Write test for missing required fields**

```python
def test_load_missing_title_raises(tmp_path):
    episode_json = tmp_path / "bad.json"
    episode_json.write_text(json.dumps({"cast": {}, "environments": {}, "scenes": []}))
    loader = EpisodeLoader()
    with pytest.raises(KeyError):
        loader.load(episode_json)
```

- [x] **Step 6: Write test for empty scenes**

```python
def test_load_empty_scenes_returns_empty_list(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "Empty",
        "cast": {},
        "environments": {},
        "scenes": []
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.scenes == []
```

- [x] **Step 7: Write test for unknown environment reference**

```python
def test_load_references_preserved_as_strings(tmp_path):
    episode_json = tmp_path / "episode.json"
    episode_json.write_text(json.dumps({
        "episode_title": "T",
        "cast": {},
        "environments": {"Apt": {"profile": "a", "trigger_word": "b"}},
        "scenes": [{"scene_id": "S1", "environment": "NONEXISTENT",
                     "characters_present": [], "shots": []}]
    }))
    loader = EpisodeLoader()
    episode = loader.load(episode_json)
    assert episode.scenes[0].environment == "NONEXISTENT"
```

- [x] **Step 8: Run all loader tests**

Run: `python3 -m pytest tests/test_loader.py -v`
Expected: All PASS

- [x] **Step 9: Commit**

```bash
git add src/showrunner/__init__.py src/showrunner/loader.py tests/conftest.py tests/test_loader.py
git commit -m "feat: add EpisodeLoader with full test coverage"
```

---

## Task 2: PromptBuilder — Construct ComfyUI Prompts

**Files:**
- Create: `src/showrunner/prompts.py`
- Create: `tests/test_prompts.py`

### RED

- [x] **Step 1: Write failing test for building start/end prompts**

```python
# tests/test_prompts.py
import pytest
from showrunner.loader import (
    CharacterData, EnvironmentData, SceneData, ShotData, EpisodeData,
)
from showrunner.prompts import PromptBuilder


@pytest.fixture
def sample_episode():
    return EpisodeData(
        title="Test",
        cast={
            "Jerry": CharacterData(profile="jerry_v2", trigger_word="jry_guy, wearing a puffy shirt"),
            "George": CharacterData(profile="george_v1", trigger_word="grg_man, wearing a red jacket"),
        },
        environments={
            "Apt": EnvironmentData(profile="apt_v1", trigger_word="90s apartment, couch, daylight"),
        },
        scenes=[
            SceneData(
                scene_id="S01",
                environment="Apt",
                characters_present=["Jerry", "George"],
                shots=[
                    ShotData(
                        shot_id="S01_SH01",
                        camera_angle="wide shot of Jerry and George talking",
                        action_start="Jerry standing, George sitting",
                        action_end="Jerry pointing, George nodding",
                        audio_path="audio/s1.wav",
                        seed=42,
                    )
                ],
            )
        ],
    )


def test_build_start_prompt_combines_all_elements(sample_episode):
    builder = PromptBuilder()
    scene = sample_episode.scenes[0]
    shot = scene.shots[0]
    prompt = builder.build_start_prompt(shot, scene, sample_episode)
    assert "90s apartment, couch, daylight" in prompt
    assert "jry_guy, wearing a puffy shirt" in prompt
    assert "grg_man, wearing a red jacket" in prompt
    assert "wide shot of Jerry and George talking" in prompt
    assert "Jerry standing, George sitting" in prompt
    assert "RAW photo, 8k" in prompt


def test_build_end_prompt_uses_action_end(sample_episode):
    builder = PromptBuilder()
    scene = sample_episode.scenes[0]
    shot = scene.shots[0]
    prompt = builder.build_end_prompt(shot, scene, sample_episode)
    assert "Jerry pointing, George nodding" in prompt
    assert "RAW photo, 8k" in prompt


def test_build_start_prompt_no_characters():
    builder = PromptBuilder()
    episode = EpisodeData(
        title="T",
        cast={},
        environments={"Rooftop": EnvironmentData(profile="roof", trigger_word="rooftop at dusk")},
        scenes=[SceneData(scene_id="S1", environment="Rooftop",
                          characters_present=[], shots=[
                              ShotData("S1_SH1", "establishing shot", "empty", "empty", "a.wav", 1)
                          ])],
    )
    prompt = builder.build_start_prompt(episode.scenes[0].shots[0], episode.scenes[0], episode)
    assert "rooftop at dusk" in prompt
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'showrunner.prompts'`

### GREEN

- [x] **Step 3: Implement PromptBuilder**

```python
# src/showrunner/prompts.py
from __future__ import annotations

from showrunner.loader import EpisodeData, SceneData, ShotData


class PromptBuilder:
    QUALITY_SUFFIX = " -- RAW photo, 8k resolution"

    def _character_triggers(self, scene: SceneData, episode: EpisodeData) -> str:
        parts = []
        for name in scene.characters_present:
            char = episode.cast.get(name)
            if char:
                parts.append(char.trigger_word)
        return ", ".join(parts)

    def build_start_prompt(self, shot: ShotData, scene: SceneData, episode: EpisodeData) -> str:
        env = episode.environments.get(scene.environment)
        env_trigger = env.trigger_word if env else ""
        char_triggers = self._character_triggers(scene, episode)
        parts = [p for p in [env_trigger, shot.camera_angle, char_triggers, shot.action_start] if p]
        return ", ".join(parts) + self.QUALITY_SUFFIX

    def build_end_prompt(self, shot: ShotData, scene: SceneData, episode: EpisodeData) -> str:
        env = episode.environments.get(scene.environment)
        env_trigger = env.trigger_word if env else ""
        char_triggers = self._character_triggers(scene, episode)
        parts = [p for p in [env_trigger, shot.camera_angle, char_triggers, shot.action_end] if p]
        return ", ".join(parts) + self.QUALITY_SUFFIX
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_prompts.py -v`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add src/showrunner/prompts.py tests/test_prompts.py
git commit -m "feat: add PromptBuilder with full test coverage"
```

---

## Task 3: ComfyUIClient — API Communication with Crash Recovery

**Files:**
- Create: `src/showrunner/comfyui_client.py`
- Create: `tests/test_comfyui_client.py`

### RED

- [x] **Step 1: Write failing test for queuing a prompt**

```python
# tests/test_comfyui_client.py
import json
import pytest
from unittest.mock import patch, MagicMock
from showrunner.comfyui_client import ComfyUIClient


@pytest.fixture
def client():
    return ComfyUIClient(base_url="http://localhost:8188")


def test_queue_prompt_returns_prompt_id(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"prompt_id": "abc-123"}).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        prompt_id = client.queue_prompt({"6": {"inputs": {"text": "test"}}})
        assert prompt_id == "abc-123"
        mock_urlopen.assert_called_once()


def test_queue_prompt_retries_on_connection_error(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"prompt_id": "xyz"}).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

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
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = client.wait_for_completion("abc-123", timeout=5, poll_interval=0.1)
        assert result is True


def test_wait_for_completion_returns_false_on_timeout(client):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({}).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = client.wait_for_completion("missing", timeout=0.3, poll_interval=0.1)
        assert result is False
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_comfyui_client.py -v`
Expected: FAIL — `ModuleNotFoundError`

### GREEN

- [x] **Step 3: Implement ComfyUIClient**

```python
# src/showrunner/comfyui_client.py
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class ComfyUIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self._base_url = base_url.rstrip("/")

    def is_server_running(self) -> bool:
        try:
            resp = urllib.request.urlopen(
                f"{self._base_url}/system_stats", timeout=5
            )
            return resp.status == 200
        except Exception:
            return False

    def queue_prompt(
        self, workflow: dict[str, Any], max_retries: int = 3
    ) -> str:
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
                time.sleep(2 ** attempt)
        raise last_error

    def wait_for_completion(
        self, prompt_id: str, timeout: int = 600, poll_interval: float = 3.0
    ) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = urllib.request.urlopen(
                    f"{self._base_url}/history/{prompt_id}", timeout=10
                )
                history = json.loads(resp.read())
                if prompt_id in history:
                    return True
            except Exception:
                pass
            time.sleep(poll_interval)
        return False

    def start_server(self, comfy_dir: str, start_cmd: list[str]) -> Any:
        import subprocess
        logger.info(f"Starting ComfyUI: {start_cmd}")
        return subprocess.Popen(start_cmd, cwd=comfy_dir)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_comfyui_client.py -v`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add src/showrunner/comfyui_client.py tests/test_comfyui_client.py
git commit -m "feat: add ComfyUIClient with retry and crash recovery tests"
```

---

## Task 4: ShotRenderer — Drive Per-Shot Rendering

**Files:**
- Create: `src/showrunner/renderer.py`
- Create: `tests/test_renderer.py`

### RED

- [x] **Step 1: Write failing tests for ShotRenderer**

```python
# tests/test_renderer.py
import json
import pytest
from unittest.mock import MagicMock, call, patch
from showrunner.renderer import ShotRenderer
from showrunner.loader import (
    CharacterData, EnvironmentData, SceneData, ShotData, EpisodeData,
)
from showrunner.comfyui_client import ComfyUIClient
from showrunner.prompts import PromptBuilder


@pytest.fixture
def episode():
    return EpisodeData(
        title="Test",
        cast={"Jerry": CharacterData("jerry_v2", "jry_guy")},
        environments={"Apt": EnvironmentData("apt_v1", "apartment")},
        scenes=[SceneData("S01", "Apt", ["Jerry"], [
            ShotData("S01_SH01", "wide shot", "standing", "sitting", "a.wav", 42),
            ShotData("S01_SH02", "close up", "smiling", "frowning", "b.wav", 99),
        ])],
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
    results = renderer.render_scene(
        episode.scenes[0], episode, workflow_template
    )

    assert len(results) == 2
    assert results[0].shot_id == "S01_SH01"
    assert results[0].success is True
    assert results[1].shot_id == "S01_SH02"
    assert mock_client.queue_prompt.call_count == 2


def test_render_shot_injects_prompts_into_template(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid-1"
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(
        episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template
    )

    call_args = mock_client.queue_prompt.call_args[0][0]
    assert "apartment" in call_args["6"]["inputs"]["text"]
    assert "jry_guy" in call_args["6"]["inputs"]["text"]
    assert call_args["3"]["inputs"]["seed"] == 42
    assert call_args["25"]["inputs"]["audio"] == "a.wav"


def test_render_shot_injects_environment_lora(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid-1"
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(
        episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template
    )

    call_args = mock_client.queue_prompt.call_args[0][0]
    assert call_args["40"]["inputs"]["lora_name"] == "apt_v1.safetensors"


def test_render_shot_injects_character_loras(episode, mock_client, workflow_template):
    mock_client.queue_prompt.return_value = "pid-1"
    mock_client.wait_for_completion.return_value = True

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(
        episode.scenes[0].shots[0], episode.scenes[0], episode, workflow_template
    )

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
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_renderer.py -v`
Expected: FAIL — `ModuleNotFoundError`

### GREEN

- [x] **Step 3: Implement ShotRenderer**

```python
# src/showrunner/renderer.py
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from typing import Any

from showrunner.comfyui_client import ComfyUIClient
from showrunner.loader import EpisodeData, SceneData, ShotData
from showrunner.prompts import PromptBuilder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderResult:
    shot_id: str
    prompt_id: str
    success: bool


class ShotRenderer:
    def __init__(self, client: ComfyUIClient, builder: PromptBuilder):
        self._client = client
        self._builder = builder

    def render_shot(
        self,
        shot: ShotData,
        scene: SceneData,
        episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> RenderResult:
        workflow = copy.deepcopy(workflow_template)

        env_data = episode.environments.get(scene.environment)
        if env_data:
            env_file = f"{env_data.profile}.safetensors"
            self._inject_env(workflow, env_file)

        char_files = []
        for char_name in scene.characters_present:
            char_data = episode.cast.get(char_name)
            if char_data:
                char_files.append(f"{char_data.profile}.safetensors")
        self._inject_chars(workflow, char_files)

        start_prompt = self._builder.build_start_prompt(shot, scene, episode)
        end_prompt = self._builder.build_end_prompt(shot, scene, episode)

        self._inject_prompts(workflow, start_prompt, end_prompt)
        self._inject_meta(workflow, shot)

        prompt_id = self._client.queue_prompt(workflow)
        success = self._client.wait_for_completion(prompt_id)

        return RenderResult(shot_id=shot.shot_id, prompt_id=prompt_id, success=success)

    def render_scene(
        self,
        scene: SceneData,
        episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> list[RenderResult]:
        results = []
        for shot in scene.shots:
            logger.info(f"Rendering {shot.shot_id}")
            result = self.render_shot(shot, scene, episode, workflow_template)
            results.append(result)
        return results

    def render_episode(
        self,
        episode: EpisodeData,
        workflow_template: dict[str, Any],
    ) -> dict[str, list[RenderResult]]:
        results = {}
        for scene in episode.scenes:
            results[scene.scene_id] = self.render_scene(scene, episode, workflow_template)
        return results

    def _inject_env(self, workflow: dict, env_file: str) -> None:
        env_node = workflow.get("40")
        if env_node:
            env_node["inputs"]["lora_name"] = env_file

    def _inject_chars(self, workflow: dict, char_files: list[str]) -> None:
        if len(char_files) > 0:
            node = workflow.get("41")
            if node:
                node["inputs"]["lora_name"] = char_files[0]

    def _inject_prompts(self, workflow: dict, start: str, end: str) -> None:
        start_node = workflow.get("6")
        if start_node:
            start_node["inputs"]["text"] = start
        end_node = workflow.get("12")
        if end_node:
            end_node["inputs"]["text"] = end

    def _inject_meta(self, workflow: dict, shot: ShotData) -> None:
        seed_node = workflow.get("3")
        if seed_node:
            seed_node["inputs"]["seed"] = shot.seed
        audio_node = workflow.get("25")
        if audio_node:
            audio_node["inputs"]["audio"] = shot.audio_path
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_renderer.py -v`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add src/showrunner/renderer.py tests/test_renderer.py
git commit -m "feat: add ShotRenderer with full test coverage"
```

---

## Task 5: EpisodeAssembler — FFmpeg Concatenation

**Files:**
- Create: `src/showrunner/assembler.py`
- Create: `tests/test_assembler.py`

### RED

- [x] **Step 1: Write failing tests for EpisodeAssembler**

```python
# tests/test_assembler.py
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from showrunner.assembler import EpisodeAssembler


@pytest.fixture
def assembler(tmp_path):
    return EpisodeAssembler(output_dir=tmp_path / "output")


def test_write_concat_list_creates_file(assembler, tmp_path):
    clips = [Path("/a/shot1.mp4"), Path("/a/shot2.mp4"), Path("/a/shot3.mp4")]
    concat_file = assembler._write_concat_list(clips)
    assert concat_file.exists()
    content = concat_file.read_text()
    assert "shot1.mp4" in content
    assert "shot2.mp4" in content
    assert "shot3.mp4" in content


def test_concatenate_runs_ffmpeg(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    clips = [Path("/a/shot1.mp4")]
    output = assembler.output_dir / "final.mp4"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assembler.concatenate(clips, output)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd[0]
        assert "-f" in cmd
        assert "concat" in cmd


def test_concatenate_returns_true_on_success(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = assembler.concatenate([Path("/a/shot1.mp4")], output)
        assert result is True


def test_concatenate_returns_false_on_failure(assembler, tmp_path):
    assembler.output_dir.mkdir(parents=True, exist_ok=True)
    output = assembler.output_dir / "final.mp4"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = assembler.concatenate([Path("/a/shot1.mp4")], output)
        assert result is False


def test_detect_video_toolbox():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="h264_videotoolbox\nlibx264\n")
        assert EpisodeAssembler._detect_videotoolbox() is True


def test_detect_no_video_toolbox():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="libx264\n")
        assert EpisodeAssembler._detect_videotoolbox() is False
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_assembler.py -v`
Expected: FAIL

### GREEN

- [x] **Step 3: Implement EpisodeAssembler**

```python
# src/showrunner/assembler.py
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class EpisodeAssembler:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._video_codec = self._detect_videotoolbox() and "h264_videotoolbox" or "libx264"

    @staticmethod
    def _detect_videotoolbox() -> bool:
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders"], capture_output=True, text=True, check=True
            )
            return "h264_videotoolbox" in result.stdout
        except Exception:
            return False

    def _write_concat_list(self, clips: list[Path]) -> Path:
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, "w") as f:
            for clip in clips:
                f.write(f"file '{clip.resolve()}'\n")
        return concat_file

    def concatenate(self, clips: list[Path], output_path: Path) -> bool:
        if not clips:
            return False
        concat_file = self._write_concat_list(clips)
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c:v", self._video_codec, "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Concatenation failed: {e}")
            return False
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_assembler.py -v`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add src/showrunner/assembler.py tests/test_assembler.py
git commit -m "feat: add EpisodeAssembler with VideoToolbox detection and tests"
```

---

## Task 6: Integration Tests — Pairs of Units

**Files:**
- Create: `tests/test_integration.py`

### Tests

- [x] **Step 1: Write integration tests**

```python
# tests/test_integration.py
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from showrunner.loader import EpisodeLoader
from showrunner.prompts import PromptBuilder
from showrunner.renderer import ShotRenderer
from showrunner.comfyui_client import ComfyUIClient
from showrunner.assembler import EpisodeAssembler


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


def test_loader_to_renderer_end_to_end(episode):
    mock_client = MagicMock(spec=ComfyUIClient)
    mock_client.queue_prompt.side_effect = ["pid1", "pid2", "pid3"]
    mock_client.wait_for_completion.return_value = True

    template = {
        "6": {"inputs": {"text": ""}},
        "12": {"inputs": {"text": ""}},
        "25": {"inputs": {"audio": ""}},
        "3": {"inputs": {"seed": 0}},
        "40": {"inputs": {"lora_name": ""}},
        "41": {"inputs": {"lora_name": ""}},
    }

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    results = renderer.render_episode(episode, template)

    assert "S01" in results
    assert "S02" in results
    assert len(results["S01"]) == 2
    assert len(results["S02"]) == 1
    assert all(r.success for r in results["S01"])
    assert results["S01"][0].prompt_id == "pid1"

    workflow = mock_client.queue_prompt.call_args_list[0][0][0]
    assert "maya_v1.safetensors" == workflow["41"]["inputs"]["lora_name"]
    assert "derek_v1.safetensors" not in workflow["41"]["inputs"]["lora_name"]
    assert workflow["40"]["inputs"]["lora_name"] == "living_room_v2.safetensors"


def test_prompt_builder_to_renderer_injects_both_prompts(episode):
    mock_client = MagicMock(spec=ComfyUIClient)
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

    renderer = ShotRenderer(client=mock_client, builder=PromptBuilder())
    renderer.render_shot(
        episode.scenes[0].shots[0], episode.scenes[0], episode, template
    )

    workflow = mock_client.queue_prompt.call_args[0][0]
    start_text = workflow["6"]["inputs"]["text"]
    end_text = workflow["12"]["inputs"]["text"]
    assert start_text != end_text
    assert "typing furiously" in start_text
    assert "throwing hands up" in end_text


def test_renderer_to_assembler_concat_list(tmp_path, episode):
    assembler = EpisodeAssembler(output_dir=tmp_path / "out")
    fake_clips = [tmp_path / f"shot{i}.mp4" for i in range(3)]
    for c in fake_clips:
        c.write_bytes(b"\x00")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assembler.concatenate(fake_clips, tmp_path / "out" / "final.mp4")

    concat_file = tmp_path / "out" / "concat_list.txt"
    assert concat_file.exists()
    lines = concat_file.read_text().strip().split("\n")
    assert len(lines) == 3


def test_full_pipeline_loader_to_assembler(tmp_path, episode):
    mock_client = MagicMock(spec=ComfyUIClient)
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
```

- [x] **Step 2: Run integration tests**

Run: `python3 -m pytest tests/test_integration.py -v`
Expected: All PASS (all units already implemented)

- [x] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for all unit pairs"
```

---

## Task 7: Episode JSON for Buffering S01E01

**Files:**
- Create: `episode_01.json`

- [x] **Step 1: Create the Buffering episode JSON cut-sheet**

Convert the existing `script.py` data into the new JSON format with 6 scenes, 4 characters, 5 environments, and shots per scene. Each scene gets 2-3 shots based on dialogue beats.

- [x] **Step 2: Write test that episode_01.json loads cleanly**

```python
# tests/test_episode_01.py
from pathlib import Path
from showrunner.loader import EpisodeLoader


def test_episode_01_loads():
    path = Path(__file__).parent.parent / "episode_01.json"
    loader = EpisodeLoader()
    episode = loader.load(path)
    assert episode.title
    assert len(episode.scenes) == 6
    assert "maya" in episode.cast
    assert "derek" in episode.cast
    total_shots = sum(len(s.shots) for s in episode.scenes)
    assert total_shots > 0
```

- [x] **Step 3: Commit**

```bash
git add episode_01.json tests/test_episode_01.py
git commit -m "feat: add Buffering S01E01 episode cut-sheet in JSON format"
```

---

## Task 8: CLI Entry Point

**Files:**
- Create: `src/showrunner/cli/main.py`

- [x] **Step 1: Create thin CLI wrapper**

```python
# src/showrunner/cli/main.py
#!/usr/bin/env python3
import argparse
import json
import logging
import sys
from pathlib import Path

from showrunner.loader import EpisodeLoader
from showrunner.prompts import PromptBuilder
from showrunner.comfyui_client import ComfyUIClient
from showrunner.renderer import ShotRenderer
from showrunner.assembler import EpisodeAssembler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Sitcom Pilot CLI")
    parser.add_argument("episode", help="Path to episode JSON cut-sheet")
    parser.add_argument("--workflow", default="workflow_api.json", help="ComfyUI workflow template")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--output-dir", default="output/rendered")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without rendering")
    args = parser.parse_args()

    episode = EpisodeLoader().load(Path(args.episode))

    with open(args.workflow) as f:
        template = json.load(f)

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

    client = ComfyUIClient(base_url=args.comfy_url)
    if not client.is_server_running():
        print("ComfyUI is not running. Start it first.")
        sys.exit(1)

    renderer = ShotRenderer(client=client, builder=PromptBuilder())
    results = renderer.render_episode(episode, template)

    assembler = EpisodeAssembler(output_dir=Path(args.output_dir))
    print(f"\nRendering complete. {sum(len(r) for r in results.values())} shots processed.")


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Commit**

```bash
git add src/showrunner/cli/main.py
git commit -m "feat: add CLI entry point for showrunner"
```

---

## Task 9: Run Full Test Suite

- [x] **Run all unit tests**

Run: `python3 -m pytest tests/test_loader.py tests/test_prompts.py tests/test_comfyui_client.py tests/test_renderer.py tests/test_assembler.py -v`
Expected: All PASS

- [x] **Run all integration tests**

Run: `python3 -m pytest tests/test_integration.py -v`
Expected: All PASS

- [x] **Run full suite**

Run: `python3 -m pytest tests/ -v --tb=short`
Expected: All PASS
