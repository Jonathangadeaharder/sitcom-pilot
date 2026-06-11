# TDD-008: `config.py` ships a hand-rolled fallback for a dependency that is always present

- Status: Fixed in working tree
- Date: 2026-06-11
- Category: Reinvented wheel / Dead code
- Severity: Medium

## Finding

`src/showrunner/config.py` defines `PipelineConfig` twice (verified lines 22 and 69): the real `BaseSettings` class behind `if _PYDANTIC_AVAILABLE:`, and a manual `os.environ.get()` re-implementation of all fields in the `else:` branch — but `pyproject.toml` line 9 lists `pydantic-settings>=2.0.0` as a hard dependency, so the fallback is unreachable. `tests/test_config.py` spends ~50 lines of `sys.modules` manipulation to cover the dead branch, and the double definition forces `pyright: ignore[reportRedeclaration]` / `type: ignore[no-redef]` comments.

## Why it matters

Defensive code for an impossible environment: maintenance burden, type-checker suppressions, and test complexity, all for zero benefit.

## Recommendation

Delete the `else:` class, `_PYDANTIC_AVAILABLE`, and `TestFallbackPipelineConfig`.
