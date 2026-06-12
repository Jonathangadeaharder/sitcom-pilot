# TDD-012: Low-value test patterns inflating a 793-function suite

- Status: Fixed (verified 2026-06-12: all 5 item categories resolved — dead code tests deleted, golden-self removed, open-set assertions gone, loader tests merged via TDD-002, default-value change-detectors gone)
- Date: 2026-06-11
- Category: Meaningless tests
- Severity: Medium

## Finding

The suite is large (verified: 793 test functions, 42 files) but includes patterns with no failure power:

1. **Default-value change-detectors** — `tests/test_schema.py` (54 tests) asserts frozen-dataclass defaults: `v = VoiceConfig(); assert v.provider == ""; assert v.voice_id == ""; assert v.seed == 0`. Repeated across `TestCharacterData`, `TestEnvironmentData`, `TestBeatData`. These pin TDD-002's duplicate object graph in place.
2. **Golden-vs-itself** — `tests/test_golden_frames.py::test_golden_vs_identical_passes` (verified ~line 148) registers `S02_beat01` and checks it against itself: SSIM 1.0 vs threshold 0.9, guaranteed pass. (The adjacent `test_golden_vs_altered_fails` is a real test.)
3. **Open-set assertion** — `tests/test_episode_01.py` ~line 43: `assert beat.kind in ("speech", "silent")` — documents instead of constrains; schema-level `pattern` already enforces this.
4. **Tests of dead code** — `test_audio_builder.py` (25 tests) and `test_silent_renderer.py` (6 tests) cover unreachable modules (TDD-006/007).
5. **Pass-through triviality** — `tests/test_loader.py` cases like `test_load_empty_scenes_returns_empty_list`, `test_load_missing_title_defaults_empty` re-verify dict-get defaults already exercised by every other loader test.

## Why it matters

~90+ of 793 tests assert things that cannot meaningfully fail or guard dead paths — they cost runtime and maintenance, inflate coverage, and dilute trust in the suite.

## Recommendation

Delete tests of dead code with their modules; drop default-value and self-comparison tests; let `test_golden_vs_altered_fails`-style behavioral tests be the pattern.
