# TDD-009: `_save_report` is copy-pasted between `scene_render.py` and `render_buffer.py`

- Status: Open
- Date: 2026-06-11
- Category: Duplication
- Severity: Medium

## Finding

Verified: `src/showrunner/scene_render.py:306` and `src/showrunner/render_buffer.py:211` both define `def _save_report(paths: RunPaths, reports: list[SceneReport]) -> None:` with identical bodies, both writing `render_report.json` to `paths.run_dir` — the footprint of `render_buffer` having been created by copy-paste from `scene_render`.

## Why it matters

Report-format fixes must be made twice; the copies will diverge silently and two different writers race on the same output file name.

## Recommendation

Extract to one shared function (e.g. `reporting.py`) and import it from both; while there, check the rest of `render_buffer.py` for further copied blocks.
