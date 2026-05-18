---
id: ADR-002
kind: adr
title: Toolchain
status: draft
date: 2026-05-17T00:00:00.000Z
authors: []
reviewers: []
tags: []
supersedes: []
superseded_by: []
depends_on: []
blocks: []
implements: []
related: []
external: []
project: sitcom-pilot
checksum: 87029b554e9b81d5cdd878d13c372c30f358b302d93a08e2adf054c4f2d6adfc
---

**Deciders:** Project owner  
**Tags:** toolchain, uv, ruff, pyright, pytest

---

## Context

The project needs a consistent, modern Python toolchain for package management, linting, formatting, type checking, and testing. Multiple tools exist for each concern; the decision standardizes on a single stack to avoid configuration drift and cognitive overhead.

## Decision

### Package Manager: uv

- Install: `uv sync`
- Add deps: `uv add <package>`
- Dev deps in `[dependency-groups] dev`
- Workspace members in `[tool.uv.workspace]`
- No pip, pipx, poetry, conda, or virtualenv

### Linting + Formatting: ruff

- Line length: 100
- Target: Python 3.11
- Rules: E, F, I, UP (pycodestyle, pyflakes, isort, pyupgrade)
- Execute: `uvx ruff check` / `uvx ruff format`
- No black, flake8, isort, pylint, or autopep8

### Type Checking: pyright

- Mode: standard
- Include: `src/`
- Exclude: `**/__pycache__`, `legacy`, `output`, `aiservices`
- Execute: `uvx pyright src/`
- No mypy

### Testing: pytest + pytest-cov

- Config in `[tool.pytest.ini_options]`: `--cov=showrunner --cov-branch --cov-report=term-missing`
- Threshold: `fail_under = 90` branch coverage
- No unittest (framework), nose, or doctests as primary strategy

### Mutation Testing: mutmut

- Targets: `planner.py`, `manifest.py`, `determinism.py`
- Runner: `uv run pytest -x --no-header -q --no-cov`
- Verifies test suite quality beyond line/coverage metrics

## Consequences

**Positive:**
- uv is 10-100x faster than pip for installs and syncs
- ruff combines lint + format + import sorting in one tool (no config conflicts)
- pyright catches real type errors that mypy would miss or flag differently
- mutmut prevents test suites that pass but assert nothing meaningful

**Negative:**
- Team must learn uv-specific commands (no pip familiarity)
- pyright occasionally flags valid patterns as errors, requiring `# type: ignore` or type:ignore
- mutmut is slow on large mutation targets (mitigated by targeting only core files)

**Neutral:**
- All tools configurable from `pyproject.toml` (single source of truth)
