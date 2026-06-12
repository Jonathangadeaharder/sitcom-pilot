# Technical Debt Documents (TDDs) — sitcom-pilot

Audit date: 2026-06-11. Re-verified against working tree: 2026-06-12. One file per finding; lens: sitcom-pilot is to become a mere content project of scriptforge — pipeline/infrastructure living here is platform debt by definition.

**Score: 13 fixed, 0 partial, 0 open** (updated 2026-06-12).

| ID | Title | Severity | Status (verified 2026-06-12) |
|----|-------|----------|------------------------------|
| [TDD-001](TDD-001-triple-validation-stack.md) | Three parallel validation systems | High | ✅ Fixed — Pydantic only |
| [TDD-002](TDD-002-dual-schema-representation.md) | Dual object graphs (dataclass vs Pydantic) | High | ✅ Fixed — unified on Pydantic models (2026-06-12) |
| [TDD-003](TDD-003-aiservices-platform-in-content-repo.md) | Nested aiservices platform clone | High | ✅ Fixed — aiservices/ directory deleted (2026-06-12) |
| [TDD-004](TDD-004-gui-scaffold-duplicates-platform.md) | Tauri GUI scaffold duplicates scriptforge | Medium | ✅ Fixed — gui/ directory deleted (2026-06-12) |
| [TDD-005](TDD-005-cli-main-god-module.md) | 873-line CLI god module | Med-High | ✅ Fixed — pipeline helpers extracted to cli/pipeline.py (2026-06-12) |
| [TDD-006](TDD-006-dead-code-audio-builder.md) | Dead `audio_builder.py` + 25 tests | High | ✅ Fixed — deleted with tests |
| [TDD-007](TDD-007-dead-code-silent-renderer.md) | Orphaned `silent_renderer.py` | Medium | ✅ Fixed — deleted with tests |
| [TDD-008](TDD-008-unreachable-config-fallback.md) | Unreachable pydantic-settings fallback | Medium | ✅ Fixed — single `PipelineConfig` |
| [TDD-009](TDD-009-save-report-copy-paste.md) | `_save_report` copy-paste ×2 | Medium | ✅ Fixed — shared `reporting.py` |
| [TDD-010](TDD-010-comfyui-client-hand-rolled-http.md) | Hand-rolled HTTP/retry/polling | Medium | ✅ Fixed — rewritten on httpx (v1 kept by decision); run `uv lock` |
| [TDD-011](TDD-011-legacy-retired-executable.md) | Executable "retired" code w/ sys.path hacks | Medium | ✅ Fixed — `legacy/` reduced to README |
| [TDD-012](TDD-012-low-value-tests.md) | ~90 low-value tests in 793-fn suite | Medium | ✅ Fixed — all 5 categories resolved (2026-06-12) |
| [TDD-013](TDD-013-minor-findings-register.md) | Minor findings register | Low | ✅ Fixed — all 8 items resolved (2026-06-12) |
