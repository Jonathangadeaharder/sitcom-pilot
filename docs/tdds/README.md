# Technical Debt Documents (TDDs) — sitcom-pilot

Audit date: 2026-06-11. One file per finding; lens: sitcom-pilot is to become a mere content project of scriptforge — pipeline/infrastructure living here is platform debt by definition. Statuses: Open → Accepted/Fixed/Rejected.

| ID | Title | Category | Severity |
|----|-------|----------|----------|
| [TDD-001](TDD-001-triple-validation-stack.md) | Three parallel validation systems | Complexity | High |
| [TDD-002](TDD-002-dual-schema-representation.md) | Dual object graphs (dataclass vs Pydantic) | Complexity | High |
| [TDD-003](TDD-003-aiservices-platform-in-content-repo.md) | Nested aiservices platform clone | Architecture | High |
| [TDD-004](TDD-004-gui-scaffold-duplicates-platform.md) | Tauri GUI scaffold duplicates scriptforge | Architecture | Medium |
| [TDD-005](TDD-005-cli-main-god-module.md) | 873-line CLI god module | Complexity | Med-High |
| [TDD-006](TDD-006-dead-code-audio-builder.md) | Dead `audio_builder.py` + 25 tests | Dead code | High |
| [TDD-007](TDD-007-dead-code-silent-renderer.md) | Orphaned `silent_renderer.py` | Dead code | Medium |
| [TDD-008](TDD-008-unreachable-config-fallback.md) | Unreachable pydantic-settings fallback | Wheel | Medium |
| [TDD-009](TDD-009-save-report-copy-paste.md) | `_save_report` copy-paste ×2 | Duplication | Medium |
| [TDD-010](TDD-010-comfyui-client-hand-rolled-http.md) | Hand-rolled HTTP/retry/polling | Wheel | Medium |
| [TDD-011](TDD-011-legacy-retired-executable.md) | Executable "retired" code w/ sys.path hacks | Practice | Medium |
| [TDD-012](TDD-012-low-value-tests.md) | ~90 low-value tests in 793-fn suite | Tests | Medium |
| [TDD-013](TDD-013-minor-findings-register.md) | Minor findings register | Mixed | Low |
