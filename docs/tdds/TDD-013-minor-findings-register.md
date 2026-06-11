# TDD-013: Minor findings register

- Status: Open
- Date: 2026-06-11
- Category: Mixed
- Severity: Low

Small items not worth individual TDDs (audit 2026-06-11):

1. **`node_map.py`** — ComfyUI workflow node-ID mapping (plus its test file) is pure backend infrastructure; platform candidate, delete with v1 path (see TDD-010).
2. **`schemas/beat_plan.py` cost constants** — hardcoded `0.01/0.05/0.02` per-second "estimated cost" with no user-facing meaning; future scriptforge scheduling will replace it.
3. **`ormsgpack>=1.12.2`** — listed under "Legacy audio pipeline deps" in `pyproject.toml`, used nowhere in `src/showrunner/`; remove.
4. **`aiservices_client.py` bool-positional hack** — `if isinstance(image_provider, bool): subprocess_fallback, image_provider = image_provider, "mlx-flux"` is an old-API compatibility shim; remove and fix callers.
5. **`test_loader.py` vs `test_loader_v2.py`** — 73 functions across two files testing the same `EpisodeLoader`; merge once TDD-002 unifies the schema.
6. **`coverage.xml` generated at repo root** by default pytest `addopts` (`--cov-report=xml`); not git-tracked (verified), but consider writing reports into a `reports/` dir to keep the root clean.
7. **`docs/*.original.md`** — `technical-due-diligence.original.md` and `docker-model-runner.original.md` are stale duplicates of their edited twins; delete (git history preserves originals).
8. **Golden-frame fixtures provenance** — `tests/fixtures/golden_frames/*.png` (4 committed PNGs) should document how to regenerate them from `episode_02.json`.
