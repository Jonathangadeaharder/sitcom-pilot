# ADR-003: Quality Gates

**Status:** Accepted  
**Date:** 2026-05-17  
**Deciders:** Project owner  
**Tags:** ci/cd, github-actions, quality-gates, sonarcloud

---

## Context

The project requires automated quality enforcement on every pull request and merge. With vendored MLX providers, self-hosted runners, and a Python monorepo, the CI configuration must be precise and maintainable.

## Decision

### Three-Workflow CI Model

1. **pr-gate.yml** — Triggered on push to main + PR to main. Runs lint, typecheck, test+coverage, mutation testing, episode validation, and beat plan generation. Matrix across Python 3.11 and 3.12. Aggregator job `Required Checks (PR)` gates merge.

2. **merge-gate.yml** — Triggered on PR events (opened, sync, labeled). Same checks as PR gate plus a SonarCloud scan job. Designed as the authoritative gate for merging.

3. **pr-agent.yml** — Slash-command-only (issue_comment trigger). Runs PR-Agent via LM Studio (self-hosted, localhost:1234/v1). Only activates when `ENABLE_PR_AGENT` repo var is `true`.

### Self-Hosted macOS Runner

- All workflows run on `self-hosted` (macOS)
- Required because MLX providers are Apple Silicon-only
- The runner locally hosts LM Studio + Ollama for AI provider fallback

### SonarCloud Integration

- `sonar-project.properties` at repo root
- Project key: `Jonathangadeaharder_sitcom-pilot`
- Coverage XML from pytest-cov uploaded for quality gate analysis
- Scans only `src/showrunner/`; excludes `legacy/` and `aiservices/`

### Branch Protection

- Required check: `Required Checks (PR)`
- Requires pull request reviews before merging
- Dismiss stale reviews on push
- PR-Agent is a fallback review tool when CodeRabbit is rate-limited

## Consequences

**Positive:**
- Self-hosted runner avoids macOS CI cost while enabling Apple Silicon-specific builds
- Matrix testing across Python 3.11 and 3.12 catches version-specific issues
- SonarCloud provides continuous code quality tracking beyond CI pass/fail
- PR-Agent slash commands enable on-demand AI review without blocking merge

**Negative:**
- Self-hosted runner is a single point of failure; if the macOS machine is offline, CI blocks
- SonarCloud requires `SONAR_TOKEN` secret and `fetch-depth: 0` for blame data
- Two workflows (PR gate + merge gate) with near-identical steps creates duplication risk

**Neutral:**
- PR-Agent requires LM Studio running locally; model quality depends on local hardware
