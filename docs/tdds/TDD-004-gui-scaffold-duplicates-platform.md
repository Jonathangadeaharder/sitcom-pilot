# TDD-004: Tauri GUI scaffold in the content project duplicates scriptforge's role

- Status: Fixed (verified 2026-06-12: gui/ directory deleted)
- Date: 2026-06-11
- Category: Unnecessary complexity / Architecture
- Severity: Medium

## Finding

`gui/` contains a Tauri/Rust app scaffold (27 git-tracked files) with stub-level application logic. Per the v1.0 vision, the GUI IS scriptforge; a per-content-project GUI is the wrong layer. (Note: `gui/src-tauri/target/` build cache exists on disk but is NOT git-tracked — verified.)

## Why it matters

Any feature invested here must later be rebuilt in scriptforge's UI (SvelteKit); meanwhile it adds a Rust toolchain to a Python content repo.

## Recommendation

Delete `gui/` (or move concepts worth keeping into scriptforge's `packages/ui`). The content project should expose data, not windows.
