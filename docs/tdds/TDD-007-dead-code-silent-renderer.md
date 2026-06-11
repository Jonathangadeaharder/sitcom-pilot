# TDD-007: `silent_renderer.py` is fully orphaned (zero callers, even the CLI)

- Status: Fixed in working tree
- Date: 2026-06-11
- Category: Dead code / Meaningless tests
- Severity: Medium

## Finding

`src/showrunner/silent_renderer.py` (31 lines): one function chaining `build_beat_prompt` → `ensure_scene_dirs` → `client.text2image`, duplicating what `scene_render._render_image` already does. Verified: the ONLY reference anywhere in `src/`, `tests/`, `legacy/` is its own test file `tests/test_silent_renderer.py` (6 tests, 254 lines) — not even the CLI imports it.

## Why it matters

A one-function module whose entire reason to exist is its own test suite: 8× more test code than product code, all guarding an unreachable path.

## Recommendation

Delete `silent_renderer.py` and `tests/test_silent_renderer.py`.
