# TDD-005: `cli/main.py` is an 873-line god module with a half-finished refactor

- Status: Fixed (verified 2026-06-12: pipeline helpers extracted to cli/pipeline.py; suppress replaced with logger.warning)
- Date: 2026-06-11
- Category: Unnecessary complexity
- Severity: Medium-High

## Finding

`src/showrunner/cli/main.py` (873 lines, verified) holds 10 Typer commands plus 9 `_pipeline_*` orchestration helpers (`_pipeline_validate`, `_pipeline_determinism`, `_pipeline_load_plan`, `_pipeline_bootstrap`, `_pipeline_render`, `_pipeline_assemble`, `_pipeline_summary`) in the same file; `_setup_logging` is invoked inconsistently across commands; `contextlib.suppress(Exception)` (~line 711) silently ignores per-character `text2image` failures during bootstrap.

## Why it matters

Pipeline orchestration is platform logic living inside a content project's CLI, and the helpers-in-the-same-file pattern is a refactor that stopped halfway — hard to navigate, hard to test in isolation.

## Recommendation

Move `_pipeline_*` into a `pipeline.py` module (the natural seam for later migration to scriptforge); keep `cli/main.py` as thin command bindings; replace the bare suppress with a logged warning.
