# Test strategy: sitcom-pilot as a content project

- Date: 2026-06-12
- Status: Proposed
- Companion to `scriptforge/docs/specs/SPEC-quality-gates-testing.md`. No browser E2E here — the GUI is scriptforge's job (gui/ was deleted per TDD-004). sitcom-pilot's claim to prove is narrower: **episode JSON in → valid, deterministic, assembled episode out.**

## Layer 1 — Unit (exists: 698 fns / 37 files after the TDD-012 cleanup)

Keep the post-cleanup rule: assert behavior, not defaults. Additions:

- `ComfyUIClient` contract tests via `httpx.MockTransport` (no live server): retry-then-succeed returns prompt_id; persistent 500 raises after `max_retries`; poll timeout returns `False` without raising; connect error → `is_server_running() is False`; malformed JSON → logged, treated as recoverable. (The 2026-06-12 httpx rewrite was smoke-tested exactly this way — turn that smoke script into `tests/test_comfyui_client.py`.)
- Pydantic `Episode` negative fixtures: one fixture file per validation rule in `tests/fixtures/invalid/` (dangling environment ref, duplicate beat id, unknown speaker, bad beat kind) — each must fail with the *specific* error message. This pins the TDD-001 consolidation: if someone re-adds a second validator, these tests don't care; if validation weakens, they fail.

## Layer 2 — Integration (pytest, no network/GPU)

Fixture: `FakeAIServices` implementing the same client surface as `AIServicesClient` (deterministic: PNG with beat-id text, sine WAV sized to dialogue length, 1 s MP4). Injected through the existing constructor seam used by `MagicMock(spec=...)` tests today — but as a *behaving fake*, not a mock, so assembly code runs for real.

| Test | Proves |
|---|---|
| `showrunner run episode_02.json` (typer `CliRunner`) with FakeAIServices → exit 0; `run_dir` contains per-scene dirs, `render_report.json` validating against a report schema; assembled output exists with duration == Σ beat durations ± 0.1 s | the whole pipeline, no human eyes needed |
| Same command twice with the same seed → byte-identical manifests and report (hash compare) | determinism promise |
| FakeAIServices configured to fail one beat → exit ≠ 0, report names the failing beat, partial artifacts preserved | failures are loud and diagnosable |
| Golden frames: `test_golden_vs_altered_fails` stays; add one per registered fixture; regeneration procedure already in `tests/fixtures/golden_frames/README.md` | visual continuity with a real negative control |
| `validate` CLI on every committed episode JSON (`episode_01`, `episode_02`, template) | shipped content is always valid |

## Layer 3 — nightly real-backend smoke (optional, non-blocking)

One beat through real ComfyUI + AIServices on the workstation: asserts output file is a decodable video (ffprobe) with non-zero frames. This is the only test allowed to be slow or flaky, and it never gates merges.

## Meta-gates

mutmut (already a dev dep) ≥ 70% killed on `src/showrunner`; ruff `PT` rules; coverage stays a floor (90%) not a goal — the TDD-012 deletions already proved count ≠ value (793→698 tests with *more* meaning).

## Setup notes

`uv lock` still pending to register `httpx>=0.27.0` as a direct dep. `FakeAIServices` lives in `tests/fakes.py` (not `src/`) — content projects ship no test scaffolding to the platform.
