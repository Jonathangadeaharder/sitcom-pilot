# TDD-011: `legacy/retired/` is "archived" yet executable, with `sys.path` hacks importing live code

- Status: Fixed in working tree
- Date: 2026-06-11
- Category: Bad practice
- Severity: Medium

## Finding

`legacy/retired/orchestrator.py` lines 9–10 do `sys.path.insert(0, str(_PROJECT_ROOT / "src"))` + `sys.path.insert(0, str(Path(__file__).parent))` and then import `showrunner.*` from live `src/` (pattern repeated across ~9 retired files). `legacy/retired/pipeline.py:16` imports `showrunner.audio_builder` — itself dead code (TDD-006). `legacy/README.md` claims these files "must not be imported by any active code", but they actively import the live tree and remain runnable.

## Why it matters

Retired code that mutates `sys.path` and reaches into `src/` isn't archived — it's a loaded trap that also keeps dead modules (audio_builder) looking "referenced".

## Recommendation

Delete `legacy/retired/` (the README migration map + git history suffice), or strip executability (rename to `.py.txt`).
