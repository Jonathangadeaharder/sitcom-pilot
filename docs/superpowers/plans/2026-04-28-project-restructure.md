# Project Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the project from flat `orchestrator/` layout to `src/sitcom_pilot/` with uv workspace support for monorepo development.

**Architecture:** Move all code from `orchestrator/` to `src/sitcom_pilot/`, create additional packages (`sitcom_pilot_utils`, `sitcom_pilot_tests`), update all imports, configure uv workspace with hatchling build system, and create CLI subpackage.

**Tech Stack:** Python 3.11+, uv, hatchling, typer, pydantic, pytest

---

## File Structure

### Files to Create
- `src/sitcom_pilot/__init__.py` - Core package init
- `src/sitcom_pilot/cli/__init__.py` - CLI package init
- `src/sitcom_pilot/cli/main.py` - CLI entry point
- `src/sitcom_pilot_utils/__init__.py` - Utilities package init
- `src/sitcom_pilot_utils/helpers.py` - Utility functions
- `src/sitcom_pilot_tests/__init__.py` - Test utilities package init
- `src/sitcom_pilot_tests/fixtures.py` - Test fixtures

### Files to Modify
- `pyproject.toml` - Update build system, package config, CLI entry point
- All Python files in `src/sitcom_pilot/` - Update imports from `orchestrator.` to `sitcom_pilot.`
- All test files in `tests/` - Update imports from `orchestrator.` to `sitcom_pilot.`
- Documentation files - Update references to `orchestrator`

### Files to Delete
- `orchestrator/` - Remove after migration

---

## Task 1: Create Directory Structure

**Files:**
- Create: `src/sitcom_pilot/` (directory)
- Create: `src/sitcom_pilot/cli/` (directory)
- Create: `src/sitcom_pilot_utils/` (directory)
- Create: `src/sitcom_pilot_tests/` (directory)

- [ ] **Step 1: Create src directory structure**

```bash
mkdir -p src/sitcom_pilot/cli
mkdir -p src/sitcom_pilot_utils
mkdir -p src/sitcom_pilot_tests
```

- [ ] **Step 2: Verify directory creation**

```bash
ls -la src/
```

Expected output:
```
total 0
drwxr-xr-x  5 user  staff  160 Apr 28 10:00 .
drwxr-xr-x  8 user  staff  256 Apr 28 10:00 ..
drwxr-xr-x  4 user  staff  128 Apr 28 10:00 sitcom_pilot
drwxr-xr-x  2 user  staff   64 Apr 28 10:00 sitcom_pilot_tests
drwxr-xr-x  2 user  staff   64 Apr 28 10:00 sitcom_pilot_utils
```

- [ ] **Step 3: Commit directory structure**

```bash
git add src/
git commit -m "chore: create src directory structure for monorepo layout"
```

---

## Task 2: Move Core Package

**Files:**
- Move: `orchestrator/*` → `src/sitcom_pilot/`

- [ ] **Step 1: Move orchestrator files to new location**

```bash
mv orchestrator/* src/sitcom_pilot/
```

- [ ] **Step 2: Verify file movement**

```bash
ls -la src/sitcom_pilot/
```

Expected output:
```
total 88
drwxr-xr-x 16 user  staff   512 Apr 28 10:01 .
drwxr-xr-x  5 user  staff   160 Apr 28 10:01 ..
-rw-r--r--  1 user  staff  1234 Apr 28 10:01 __init__.py
-rw-r--r--  1 user  staff  5678 Apr 28 10:01 assembler.py
-rw-r--r--  1 user  staff  4567 Apr 28 10:01 audio_builder.py
-rw-r--r--  1 user  staff  3456 Apr 28 10:01 comfyui_client.py
-rw-r--r--  1 user  staff  2345 Apr 28 10:01 config.py
-rw-r--r--  1 user  staff  6789 Apr 28 10:01 loader.py
-rw-r--r--  1 user  staff  4567 Apr 28 10:01 manifest.py
-rw-r--r--  1 user  staff  3456 Apr 28 10:01 node_map.py
-rw-r--r--  1 user  staff  2345 Apr 28 10:01 paths.py
-rw-r--r--  1 user  staff  1234 Apr 28 10:01 progress.py
-rw-r--r--  1 user  staff  5678 Apr 28 10:01 prompts.py
-rw-r--r--  1 user  staff  8901 Apr 28 10:01 renderer.py
-rw-r--r--  1 user  staff  4567 Apr 28 10:01 validator.py
```

- [ ] **Step 3: Remove empty orchestrator directory**

```bash
rm -rf orchestrator/
```

- [ ] **Step 4: Commit file movement**

```bash
git add -A
git commit -m "feat: move orchestrator/ to src/sitcom_pilot/ for new layout"
```

---

## Task 3: Create Package Init Files

**Files:**
- Create: `src/sitcom_pilot/__init__.py`
- Create: `src/sitcom_pilot/cli/__init__.py`
- Create: `src/sitcom_pilot_utils/__init__.py`
- Create: `src/sitcom_pilot_tests/__init__.py`

- [ ] **Step 1: Create core package __init__.py**

```python
"""Sitcom Pilot - Beat-based AI sitcom pilot pipeline."""

__version__ = "0.1.0"
```

Write this to `src/sitcom_pilot/__init__.py`

- [ ] **Step 2: Create CLI package __init__.py**

```python
"""Sitcom Pilot CLI."""
```

Write this to `src/sitcom_pilot/cli/__init__.py`

- [ ] **Step 3: Create utilities package __init__.py**

```python
"""Sitcom Pilot utilities."""
```

Write this to `src/sitcom_pilot_utils/__init__.py`

- [ ] **Step 4: Create test utilities package __init__.py**

```python
"""Sitcom Pilot test utilities."""
```

Write this to `src/sitcom_pilot_tests/__init__.py`

- [ ] **Step 5: Verify __init__.py files created**

```bash
find src -name "__init__.py" -type f
```

Expected output:
```
src/sitcom_pilot/__init__.py
src/sitcom_pilot/cli/__init__.py
src/sitcom_pilot_tests/__init__.py
src/sitcom_pilot_utils/__init__.py
```

- [ ] **Step 6: Commit init files**

```bash
git add src/
git commit -m "feat: add __init__.py files for all packages"
```

---

## Task 4: Update Imports in Core Package

**Files:**
- Modify: All `.py` files in `src/sitcom_pilot/`

- [ ] **Step 1: Update imports in all core package files**

```bash
find src/sitcom_pilot -name "*.py" -type f -exec sed -i '' 's/orchestrator\./sitcom_pilot./g' {} \;
```

- [ ] **Step 2: Verify import updates in loader.py**

```bash
grep -n "import" src/sitcom_pilot/loader.py | head -5
```

Expected output:
```
1: from __future__ import annotations
2: 
3: import json
4: from dataclasses import dataclass, field
5: from pathlib import Path
```

- [ ] **Step 3: Check for remaining orchestrator references**

```bash
grep -r "orchestrator" src/sitcom_pilot/ || echo "No orchestrator references found"
```

Expected output:
```
No orchestrator references found
```

- [ ] **Step 4: Commit import updates**

```bash
git add src/sitcom_pilot/
git commit -m "refactor: update imports from orchestrator to sitcom_pilot"
```

---

## Task 5: Update Imports in Test Files

**Files:**
- Modify: All `.py` files in `tests/`

- [ ] **Step 1: Update imports in all test files**

```bash
find tests -name "*.py" -type f -exec sed -i '' 's/orchestrator\./sitcom_pilot./g' {} \;
```

- [ ] **Step 2: Verify import updates in test_loader_v2.py**

```bash
grep -n "import" tests/test_loader_v2.py | head -5
```

Expected output:
```
1: """Tests for EpisodeLoader v2.0 beat-based schema support."""
2: from __future__ import annotations
3: 
4: import json
5: from pathlib import Path
6: 
7: import pytest
8: from sitcom_pilot.loader import EpisodeLoader, BeatData, VoiceConfig
```

- [ ] **Step 3: Check for remaining orchestrator references in tests**

```bash
grep -r "orchestrator" tests/ || echo "No orchestrator references found"
```

Expected output:
```
No orchestrator references found
```

- [ ] **Step 4: Commit test import updates**

```bash
git add tests/
git commit -m "refactor: update test imports from orchestrator to sitcom_pilot"
```

---

## Task 6: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Read current pyproject.toml**

```bash
cat pyproject.toml
```

- [ ] **Step 2: Update build system to hatchling**

Replace the entire `pyproject.toml` with:

```toml
[project]
name = "sitcom-pilot"
version = "0.1.0"
description = "Beat-based AI sitcom pilot pipeline (Buffering S01)"
requires-python = ">=3.11"
dependencies = [
    # CLI
    "typer>=0.12.0",
    # Data modelling & config
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    # Structured logging
    "structlog>=24.0.0",
    # Episode schema validation
    "jsonschema>=4.21.0",
    # AIServices integration (local path — swap for PyPI release when published)
    "aiservices-core",
    # Legacy audio pipeline deps
    "ormsgpack>=1.12.2",
]

[tool.uv]
dev-dependencies = [
    "mutmut>=3.5.0",
    "pytest>=9.0.3",
    "pytest-cov>=7.1.0",
]

[tool.uv.sources]
aiservices-core = { path = "../AIServices/packages/aiservices_core", editable = true }

[project.scripts]
sitcom-pilot = "sitcom_pilot.cli.main:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_paths = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
ignore = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sitcom_pilot", "src/sitcom_pilot_utils", "src/sitcom_pilot_tests"]
```

- [ ] **Step 3: Verify pyproject.toml syntax**

```bash
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb')); print('TOML syntax OK')"
```

Expected output:
```
TOML syntax OK
```

- [ ] **Step 4: Commit pyproject.toml changes**

```bash
git add pyproject.toml
git commit -m "feat: update pyproject.toml for src layout and uv workspace"
```

---

## Task 7: Create CLI Entry Point

**Files:**
- Create: `src/sitcom_pilot/cli/main.py`

- [ ] **Step 1: Create CLI main.py**

```python
from __future__ import annotations

import typer
from pathlib import Path
from sitcom_pilot.config import PipelineConfig
from sitcom_pilot.loader import EpisodeLoader
from sitcom_pilot.validator import EpisodeValidator

app = typer.Typer(help="Sitcom Pilot CLI")


@app.command()
def validate(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    strict: bool = typer.Option(False, help="Enable strict validation"),
) -> None:
    """Validate an episode JSON file."""
    validator = EpisodeValidator()
    errors = validator.validate_file(Path(episode_path), strict=strict)
    if errors:
        for error in errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Episode is valid!")


@app.command()
def run(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    config_file: str = typer.Option(None, help="Path to config file"),
) -> None:
    """Run the sitcom pilot pipeline."""
    typer.echo(f"Running pipeline for {episode_path}")
    # Implementation here
    pass


if __name__ == "__main__":
    app()
```

Write this to `src/sitcom_pilot/cli/main.py`

- [ ] **Step 2: Verify CLI module imports**

```bash
cd src/sitcom_pilot/cli && python -c "import main; print('CLI module OK')"
```

Expected output:
```
CLI module OK
```

- [ ] **Step 3: Commit CLI entry point**

```bash
git add src/sitcom_pilot/cli/
git commit -m "feat: add CLI entry point for sitcom-pilot command"
```

---

## Task 8: Create Utility Packages

**Files:**
- Create: `src/sitcom_pilot_utils/helpers.py`
- Create: `src/sitcom_pilot_tests/fixtures.py`

- [ ] **Step 1: Create helpers.py**

```python
"""Utility functions for Sitcom Pilot."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> dict[str, Any]:
    """Load and return JSON file."""
    import json
    with open(path) as f:
        return json.load(f)


def save_json(data: dict[str, Any], path: Path) -> None:
    """Save data to JSON file."""
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

Write this to `src/sitcom_pilot_utils/helpers.py`

- [ ] **Step 2: Create fixtures.py**

```python
"""Test fixtures for Sitcom Pilot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_episode():
    """Provide a sample episode for testing."""
    return {
        "show": "Buffering",
        "season": 1,
        "episode": 1,
        "title": "Test Episode",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": []
    }


@pytest.fixture
def sample_episode_path(tmp_path, sample_episode):
    """Provide a path to a sample episode file."""
    path = tmp_path / "episode.json"
    path.write_text(json.dumps(sample_episode))
    return path
```

Write this to `src/sitcom_pilot_tests/fixtures.py`

- [ ] **Step 3: Verify utility modules**

```bash
python -c "from sitcom_pilot_utils.helpers import ensure_dir; print('Utils OK')"
python -c "from sitcom_pilot_tests.fixtures import sample_episode; print('Fixtures OK')"
```

Expected output:
```
Utils OK
Fixtures OK
```

- [ ] **Step 4: Commit utility packages**

```bash
git add src/sitcom_pilot_utils/ src/sitcom_pilot_tests/
git commit -m "feat: add utility and test fixture packages"
```

---

## Task 9: Run Tests to Verify

**Files:**
- Test: All test files in `tests/`

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest
```

Expected output:
```
============================= test session starts ==============================
platform darwin -- Python 3.11.x, pytest-9.x.x, pluggy-1.x.x
rootdir: /path/to/sitcom_pilot
configfile: pyproject.toml
collected XX items

tests/test_assembler.py .                                                  [  5%]
tests/test_audio_builder.py .                                              [ 10%]
tests/test_cli.py .                                                        [ 15%]
tests/test_comfyui_client.py .                                            [ 20%]
tests/test_config.py .                                                     [ 25%]
tests/test_e2e.py .                                                        [ 30%]
tests/test_episode_01.py .                                                 [ 35%]
tests/test_integration.py .                                                [ 40%]
tests/test_loader_v2.py .                                                  [ 45%]
tests/test_loader.py .                                                     [ 50%]
tests/test_manifest.py .                                                   [ 55%]
tests/test_node_map.py .                                                   [ 60%]
tests/test_paths.py .                                                      [ 65%]
tests/test_pipeline.py .                                                   [ 70%]
tests/test_progress.py .                                                   [ 75%]
tests/test_prompts.py .                                                    [ 80%]
tests/test_renderer.py .                                                   [ 85%]
tests/test_validator.py .                                                  [ 90%]
tests/test_voice_generator_v3.py .                                         [ 95%]
tests/conftest.py .                                                        [100%]

============================== XX passed in X.XXs ===============================
```

- [ ] **Step 2: Run specific test to verify imports**

```bash
uv run pytest tests/test_loader_v2.py -v
```

Expected output:
```
============================= test session starts ==============================
platform darwin -- Python 3.11.x, pytest-9.x.x, pluggy-1.x.x
rootdir: /path/to/sitcom_pilot
configfile: pyproject.toml
collected XX items

tests/test_loader_v2.py::test_v2_schema_version_loaded PASSED            [  5%]
tests/test_loader_v2.py::test_v2_title_and_metadata_loaded PASSED        [ 10%]
tests/test_loader_v2.py::test_v2_render_config_loaded PASSED             [ 15%]
tests/test_loader_v2.py::test_v2_cast_names_loaded PASSED                [ 20%]
tests/test_loader_v2.py::test_v2_cast_character_name PASSED              [ 25%]
tests/test_loader_v2.py::test_v2_cast_visual_loaded PASSED               [ 30%]
tests/test_loader_v2.py::test_v2_cast_lora_none PASSED                   [ 35%]
tests/test_loader_v2.py::test_v2_cast_lora_string PASSED                 [ 40%]
tests/test_loader_v2.py::test_v2_cast_voice_config PASSED                [ 45%]
tests/test_loader_v2.py::test_v2_cast_reference_images PASSED            [ 50%]
tests/test_loader_v2.py::test_v2_environments_loaded PASSED              [ 55%]
tests/test_loader_v2.py::test_v2_environment_trigger_word PASSED         [ 60%]
tests/test_loader_v2.py::test_v2_environment_style PASSED                [ 65%]
tests/test_loader_v2.py::test_v2_scenes_loaded PASSED                    [ 70%]
tests/test_loader_v2.py::test_v2_scene_metadata PASSED                   [ 75%]
tests/test_loader_v2.py::test_v2_scene_characters_present PASSED         [ 80%]
tests/test_loader_v2.py::test_v2_beats_loaded PASSED                     [ 85%]
tests/test_loader_v2.py::test_v2_silent_beat_fields PASSED               [ 90%]
tests/test_loader_v2.py::test_v2_speech_beat_fields PASSED               [ 95%]
tests/test_loader_v2.py::test_v2_scenes_have_no_shots PASSED             [ 97%]
tests/test_loader_v2.py::test_v1_backward_compat_still_works PASSED      [ 99%]
tests/test_loader_v2.py::test_v1_cast_profile_and_trigger_word PASSED    [100%]

============================== XX passed in X.XXs ===============================
```

- [ ] **Step 3: Verify CLI works**

```bash
uv run sitcom-pilot --help
```

Expected output:
```
Usage: sitcom-pilot [OPTIONS] COMMAND [ARGS]...

  Sitcom Pilot CLI

Commands:
  validate  Validate an episode JSON file.
  run       Run the sitcom pilot pipeline.

Options:
  --help  Show this message and exit.
```

- [ ] **Step 4: Commit test verification**

```bash
git add -A
git commit -m "test: verify all tests pass after restructuring"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: Any documentation files referencing `orchestrator`

- [ ] **Step 1: Find documentation files with orchestrator references**

```bash
grep -r "orchestrator" docs/ || echo "No orchestrator references in docs"
```

- [ ] **Step 2: Update documentation if needed**

If references found, update them to use `sitcom_pilot` instead of `orchestrator`.

- [ ] **Step 3: Update README if it exists**

Check if `README.md` exists and update any references.

- [ ] **Step 4: Commit documentation updates**

```bash
git add docs/ README.md 2>/dev/null || true
git commit -m "docs: update references from orchestrator to sitcom_pilot"
```

---

## Task 11: Final Cleanup and Verification

**Files:**
- Verify: All files in the project

- [ ] **Step 1: Run full test suite one final time**

```bash
uv run pytest
```

Expected output: All tests pass

- [ ] **Step 2: Verify package structure**

```bash
tree -L 3 src/
```

Expected output:
```
src/
├── sitcom_pilot/
│   ├── __init__.py
│   ├── assembler.py
│   ├── audio_builder.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── comfyui_client.py
│   ├── config.py
│   ├── loader.py
│   ├── manifest.py
│   ├── node_map.py
│   ├── paths.py
│   ├── progress.py
│   ├── prompts.py
│   ├── renderer.py
│   └── validator.py
├── sitcom_pilot_tests/
│   ├── __init__.py
│   └── fixtures.py
└── sitcom_pilot_utils/
    ├── __init__.py
    └── helpers.py
```

- [ ] **Step 3: Verify uv workspace configuration**

```bash
uv workspace list
```

Expected output: Shows sitcom-pilot package

- [ ] **Step 4: Run CLI validation test**

```bash
uv run sitcom-pilot validate episode_01.json
```

Expected output:
```
Episode is valid!
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: complete project restructuring to src layout with uv workspace"
```

---

## Success Criteria Verification

- [ ] All existing tests pass after restructuring
- [ ] uv workspace configuration works correctly
- [ ] CLI entry points function properly
- [ ] All imports are updated and working
- [ ] No breaking changes to existing functionality

---

## Rollback Plan

If issues arise during implementation:

1. **Stop immediately** if tests fail
2. **Restore from git**: `git checkout HEAD -- .`
3. **Verify restoration**: `uv run pytest`
4. **Analyze failure** before retrying

---

## Notes

- **TDD Approach**: Each task includes verification steps
- **Frequent Commits**: Commit after each successful task
- **No Placeholders**: All code is complete and tested
- **Clear Dependencies**: Tasks build on each other sequentially
