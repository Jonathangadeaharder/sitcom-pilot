---
id: TDD-SITP
kind: tdd
title: sitcom-pilot (showrunner)
description: Beat-based AI sitcom pilot pipeline (Buffering S01) — Episode JSON → MLX render → assembled video
status: draft
date: 2026-05-17T00:00:00.000Z
authors: []
reviewers: []
risk_level: high
scope_type: project
tags:
  - mlx
  - python
  - ai-pipeline
  - video
  - typer
related:
  - TDD-GRET
  - TDD-SCFG
---

> Imported legacy TDD artifact from `docs/technical-due-diligence.md`. Keep future lifecycle work in OpenSpec.

## Executive Summary

sitcom-pilot (package `showrunner`, CLI `sitcom-pilot`) is a Python 3.11+ beat-based AI video pipeline targeting Buffering S01E01 + S01E02 final renders. It composes MLX provider packages vendored under `aiservices/packages/` (text2image, image2image, image2video, text2speech, audio2subtitle) into a CLI flow: validate → plan → bootstrap → render → assemble. Foundation (E0) and Script Authoring (E1) epics are done; AIServices integration (E2), MLX providers (E3), character continuity (E4), scene render (E5), assembly (E6), CLI (E7), quality (E8), and pilot release (E9) epics remain open. 76 issues open across 9 active epics + a v1.0 GUI/showrunner-MVP track + a property-based-testing track. High risk: render path not yet end-to-end, urgent provider plugins and beat-renderer issues are still backlog, and there is no test gate on the planner/renderer yet.

## Scope

Assessed the `showrunner` package, vendored `aiservices/packages/*` uv workspace, episode JSON v2.0 schema, CLI entry points, all 76 open GitHub issues across active epics (E0, E2–E9) and the v1.0 release track, the rebrand from sitcom-pilot → showrunner, and the relationship to the shared [[project-scriptforge]] monorepo. Excluded: detailed MLX model performance benchmarks, GUI/Tauri wrapper (issue #115 — out of TDD scope until E7 lands).

## Architecture

Pipeline: Episode JSON (v2.0) → `validate` → `plan` (dry run) → `bootstrap` (reference images + voice samples) → `render` (per-beat: image → audio → video) → `assemble` (concat clips + SRT → final .mp4). Beat-based granularity: each scene contains ordered beats (speech or silent), and every beat is an independent render unit. AIServicesClient facade (issue SITP-30, open) is the planned integration boundary between showrunner and the MLX provider packages, with subprocess fallback (SITP-34) when Python APIs are unavailable. Reference-image plumbing (SITP-31) and audio-conditioned image2video for lip sync (SITP-32) feed character-continuity (E4) and scene-render (E5) stages.

## Tech Stack

- **Runtime:** Python 3.11+, Apple Silicon (MLX) only.
- **Data/config:** pydantic 2, pydantic-settings, jsonschema 4.
- **Image:** pillow 12, scikit-image (SSIM continuity checks).
- **Audio/legacy:** ormsgpack.
- **CLI/logging:** typer 0.24, rich 15, structlog 25.
- **Providers (vendored uv workspace under `aiservices/packages/`):** text2image, image2image, image2video, text2speech, audio2subtitle. text2video is excluded from the workspace.
- **Build:** uv workspace, package name `showrunner`, CLI entry `sitcom-pilot`.
- **Testing:** pytest 9, pytest-cov 7 (branch coverage), mutmut 3.5, pyright, ruff.
- **External:** ffmpeg (concat + mux + SRT burn-in optional).

## Code Quality

E0 foundation is solid: schema (SITP-14), pydantic models (SITP-15), uv workspace layout (SITP-16), pydantic-settings config (SITP-17), output-dir contract (SITP-18), run manifest (SITP-19), validator CLI (SITP-20), architecture doc (SITP-21) all CLOSED. E1 (script authoring) fully done including template, both episodes rewritten into beat schema, voice profiles, cast/env reference asset checklist, writer's guide. Test coverage gaps: unit tests for schema/planner/ffmpeg wrappers (SITP-76) CLOSED, integration render of scene 001 (SITP-77) CLOSED, CI lint+type+validate+plan on push (SITP-78) CLOSED, golden-frame SSIM fixtures (SITP-75) CLOSED. Still open: determinism + seed strategy + manifest hashing (SITP-74), mutmut on planner+manifest (SITP-79), property-based testing rollout (SITP-88 through SITP-95). Repo hygiene: iCloud `* 2*` duplicate files cleaned (SITP-112 CLOSED), rebrand sitcom-pilot → showrunner tracked (#113 CLOSED), legacy `.py` files moved to `legacy/` (SITP-86 CLOSED), legacy pipeline retirement still open (SITP-84).

## Security

Local-only render pipeline; no external API calls in steady state, no credential management, no user-facing surface yet. Supply-chain risk inherits from MLX ecosystem and shared scriptforge providers (see [[TDD-GRET]] for the ltx-* Git-source pin risk applicable here too). No secret scanning workflow yet documented in this repo (compare with [[TDD-OBST]] which runs Gitleaks + Trivy).

## Scalability & Performance

Beat-level parallelism is planned but explicitly low-priority (SITP-58). Single-active-job constraint inherits from MLX memory ceilings (shared with scriptforge — see [[project-scriptforge]] scheduler design). Cache & resume per beat (SITP-56, high priority) is the dominant performance lever for iteration loops. Beat duration budget logic (SITP-55, high), failure isolation per beat (SITP-57, medium), per-scene render report (SITP-59) round out the runtime story. Cost/time estimator (SITP-37) already CLOSED. No load testing; the target workload is two episodes, not throughput.

## Operations & DevOps

CI: lint + type + validate + plan on push is in place (SITP-78 CLOSED). `sitcom-pilot doctor` (SITP-72) still open for environment verification. Run manifest format (SITP-19) and output-directory contract (SITP-18) are CLOSED — this is the operations backbone. No production deployment surface yet; GUI/Tauri wrapper (#115) is the planned v1.0 distribution path. No observability beyond structlog + rich progress (SITP-73 CLOSED).

## Dependencies & Third-Party Risk

Critical path: MLX provider packages are vendored under `aiservices/packages/` as a uv workspace and consumed via `tool.uv.sources` workspace links — this isolates sitcom-pilot from upstream churn but means provider updates require manual sync. text2video is explicitly excluded from the workspace (build instability). The AIServicesClient facade (SITP-30, open) is still the missing seam — until it lands, provider swaps touch the renderer. Subprocess fallback layer (SITP-34) and provider capability discovery (SITP-36) are still open. ComfyUI vs direct MLX providers decided in favour of direct MLX (SITP-85 CLOSED, future-branch). MLX-only opinionated default for v1.0 (#116 CLOSED) removes provider-switching UI complexity.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Beat planner + speech/silent beat renderers (SITP-52, 53, 54) are urgent-priority and still open — render path not end-to-end | High | Critical | Land E5.1–E5.3 before any further provider work |
| MLX text2image/image2image/image2video provider plugins (SITP-38, 39, 40) urgent/high and still open | High | Critical | Land E3.1–E3.3 in parallel with E5 |
| AIServicesClient facade (SITP-30) not yet built — renderer touches providers directly | Medium | High | Land SITP-30 before SITP-52–54 to avoid rework |
| Cast manifest schema (SITP-44) urgent and still open — character continuity blocked | High | High | Land E4.1 + E4.5 (beat plate generator) before E5 render lockdown |
| Determinism / seed strategy (SITP-74) open — golden-frame SSIM regression brittle | Medium | High | Land seed strategy before golden-frame fixtures graduate to CI gate |
| Episode concat + caption SRT (SITP-61, 62, 83 — high) open — no E2E render output | Medium | High | Land E6.1–E6.3 once a single scene renders |
| Showrunner MVP (#110, v1.0 p1) gates v1.0 release — depends on E2–E9 closure | High | Critical | Treat #110 as roll-up tracking issue; sequence dependent epics |
| GUI wrapper Tauri (#115) p1 — scope creep against MVP CLI | Medium | Medium | Defer until CLI MVP renders both episodes end-to-end |
| Property-based testing track (SITP-88–95) backlogged — schema/CLI regressions not covered | Low | Medium | Sequence after E5/E6 land; hypothesis 1000 max_examples in CI is the long-term gate |
| Legacy pipeline retirement (SITP-84) open — duplicate code paths confuse contributors | Medium | Low | Close after showrunner MVP renders S01E02 |

## Recommendations

1. **Sequence the critical path:** AIServicesClient facade (SITP-30) → cast manifest (SITP-44) + beat planner (SITP-52) → speech/silent beat renderers (SITP-53, 54) → MLX provider plugins (SITP-38, 39, 40). This is the minimum to get one scene of episode_02 rendering end-to-end.
2. **Close E6 (assembly) before opening more E4/E5 polish:** beat clip uniformiser (SITP-60), episode concat (SITP-61), caption SRT (SITP-62), final mux + thumbnail (SITP-65). Without assembly the renderer cannot prove correctness.
3. **Land determinism (SITP-74) before promoting golden-frame fixtures to CI gates** — without seed strategy + manifest hashing, SSIM regressions are noise.
4. **Treat showrunner MVP (#110) as the v1.0 roll-up.** Sub-issues #114 (condense scope) and #111 (future-branch graduation criteria) should be enforced — anything not on the MVP path goes to `future-branch` label.
5. **Defer GUI/Tauri (#115) until CLI MVP renders both episodes.** This is the highest scope-creep risk against v1.0.
6. **Migrate shared infrastructure to scriptforge** (see [[project-scriptforge]]) once the renderer is stable. sitcom-pilot is one of three downstream consumers — duplicate scheduler/HITL logic should move to `packages/core` rather than ship in showrunner.
7. **Sequence property-based testing (SITP-88–95) after E5/E6 land.** Install hypothesis (SITP-89), then schema round-trip (SITP-90), then CLI args (SITP-91), then CI integration (SITP-95) with 1000 max_examples.
8. **Close legacy pipeline retirement (SITP-84)** after S01E02 renders. Two pipelines in one repo confuses contributors and bloats `legacy/`.
