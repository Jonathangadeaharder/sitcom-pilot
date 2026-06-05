---
id: ADR-001
kind: adr
title: Project Architecture
status: accepted
date: 2026-05-17T00:00:00.000Z
authors: [Jonathan Gadea Harder]
reviewers: [Jonathan Gadea Harder]
tags: []
supersedes: []
superseded_by: []
depends_on: []
blocks: []
implements: []
related: []
external: []
project: sitcom-pilot
checksum: 4336f2e301bf7e63199154ff6e3cbeff4cca147998d8083f4d74ed9de085f9f6
---

**Deciders:** Project owner  
**Tags:** architecture, python, monorepo, uv, ffmpeg

---

## Context

The sitcom-pilot project transforms JSON episode scripts into animated video. It needs to coordinate multiple MLX-based AI providers (text-to-image, image-to-video, text-to-speech), an FFmpeg assembly pipeline, and a deterministic rendering system — all while maintaining reproducibility and debuggability.

The project grew from a flat `orchestrator/` directory without workspace isolation, making it hard to add new packages or manage dependencies cleanly.

## Decision

### Python Monorepo with uv Workspace

Use `uv` workspace at the project root with `src/` layout:

```
src/
  showrunner/       # Core package (CLI, renderer, validator, assembler)
aiservices/
  packages/         # Vendored MLX provider packages (text2image, image2video, text2speech, etc.)
```

- **Build system:** hatchling
- **Package name:** `showrunner`
- **CLI entry point:** `showrunner.cli.main:app` (Typer)
- **Dependency management:** `uv sync` / `uv add`
- **Python:** >=3.11

### Beat-Based Media Pipeline

The pipeline processes episodes as ordered beat units:

```
Episode JSON ─► validate ─► plan ─► bootstrap ─► render ─► assemble ─► .mp4
```

Each beat is an independent render unit: keyframe image → optional TTS audio → image-to-video clip. Beats assemble via FFmpeg concat.

### Deterministic by Default

Every render operation is seeded. The determinism system (`determinism.py`) tracks seeds across beats, scenes, and full episodes so that identical inputs produce identical outputs.

### AI Provider Abstraction

All AI providers (image, video, TTS, ASR) are behind a client interface (`aiservices_client.py`, `comfyui_client.py`). Provider selection is env-driven (`SITCOM_IMAGE_PROVIDER`, `SITCOM_VIDEO_PROVIDER`, `SITCOM_TTS_PROVIDER`) with CLI fallback when Python APIs unavailable.

## Consequences

**Positive:**
- Clean package boundaries; new packages slot into `src/` or `aiservices/packages/` without restructuring
- uv workspace enables monorepo-local dependencies and `--dev` groups
- Beat isolation enables parallel rendering, caching, and partial re-renders
- Deterministic seeds make renders reproducible and regression-testable
- Provider abstraction allows swapping models without pipeline changes
- Docker Model Runner with vllm-metal provides an OpenAI-compatible LLM inference endpoint (port 12434) for text-based tasks, eliminating the need for a separate Ollama or LM Studio setup for text LLM inference during CI.

**Negative:**
- Vendored aiservices packages must stay in sync with upstream
- Beat independence means cross-beat continuity (character appearance, lighting) must be managed via prompts and seed chains, not shared state
- FFmpeg assembly is a single-threaded bottleneck at the end of the pipeline

**Neutral:**
- Test fixtures and helpers live in `tests/conftest.py` rather than a separate package
