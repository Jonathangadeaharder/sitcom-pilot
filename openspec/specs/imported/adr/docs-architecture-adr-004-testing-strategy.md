---
id: ADR-004
kind: adr
title: Testing Strategy
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
checksum: 460f991cfd297fdbd7b74cae958ed6ff57a627d41bba9bc89d2444ce552f2e9d
---

> Imported legacy ADR artifact from `docs/architecture/ADR-004-testing-strategy.md`. Keep future lifecycle work in OpenSpec.

**Deciders:** Project owner  
**Tags:** testing, pytest, mutmut, coverage, sonarcloud

---

## Context

The sitcom-pilot pipeline involves AI provider calls (non-deterministic, slow, expensive), FFmpeg subprocesses, and complex data transformations. Testing strategy must balance thoroughness with pragmatism — mocking external providers while validating business logic with high confidence.

## Decision

### Test Framework: pytest

- All tests in `tests/` directory, mirroring `src/showrunner/` structure
- Fixtures in `tests/conftest.py` (shared) and `tests/*/conftest.py` (module-level)
- `showrunner_tests` package provides reusable test helpers (sample episodes, mock responses)

### Coverage Mandate: Branch Coverage >= 90%

- Enforced via `[tool.coverage.report] fail_under = 90`
- Branch coverage (not line coverage) is the metric — catches untaken conditional paths
- `[tool.coverage.run] branch = true`
- Reported as XML for SonarCloud ingestion

### Mutation Testing: mutmut on Core Modules

- Targets: `planner.py`, `manifest.py`, `determinism.py` — the modules with the most business logic
- Runner: `uv run pytest -x --no-header -q --no-cov` (fast, no coverage overhead)
- Also copies episode JSON files for integration-level mutation tests
- Mutation score thresholds are advisory (not CI-blocking) but failing mutants indicate weak tests

### Mocking Strategy

- **AI providers:** All provider clients (`AIServicesClient`, `ComfyUIClient`) are mocked at the boundary. Real provider calls never happen in unit tests.
- **FFmpeg:** Subprocess calls are mocked or use `subprocess.run` with canned return values.
- **Filesystem:** `tmp_path` fixture for output operations; JSON fixtures for episode data.
- **Determinism:** Seed-based modules are tested with known seed values and expected deterministic output.

### What Is NOT Tested (Intentionally)

- Actual AI model inference (tested upstream in aiservices packages)
- FFmpeg encoding correctness (tested upstream; our tests verify command construction)
- End-to-end render from JSON to video (tested manually per episode)

### Test Categories

| Category | Scope | Framework | CI Stage |
|----------|-------|-----------|----------|
| Unit | Single function/class, no I/O | pytest | PR gate |
| Integration | Module boundaries, mocked providers | pytest | PR gate |
| Mutation | Test suite quality | mutmut | PR gate (3.11 only) |
| Validation | Episode JSON conformity | pytest + jsonschema | PR gate |
| Plan generation | Beat plan correctness | pytest | PR gate |

## Consequences

**Positive:**
- Branch coverage >= 90% prevents untested conditional paths from reaching production
- Mutation testing catches test suites that pass but don't actually verify behavior
- Mocking AI providers keeps CI fast and deterministic
- Separate test categories allow fast unit test cycles without running slow mutation tests

**Negative:**
- Branch coverage is harder to achieve than line coverage (more work per module)
- Mocking AI providers means integration bugs (model API changes, prompt format drift) are caught later
- mutmut is slow on large files (5-10 minutes for current targets)

**Neutral:**
- Testing strategy assumes upstream aiservices packages have their own test coverage
- E2E testing is manual; no Playwright or browser automation needed (the output is a video file)
