# TDD-002: Two parallel object graphs for the domain (loader dataclasses vs Pydantic schemas)

- Status: Open
- Date: 2026-06-11
- Category: Unnecessary complexity
- Severity: High

## Finding

`src/showrunner/loader.py` defines `VoiceConfig`, `CharacterData`, `EnvironmentData`, `BeatData`, `ShotData`, `SceneData`, `EpisodeData` as plain dataclasses — while `src/showrunner/schemas/episode.py` defines the parallel `VoiceConfig`, `Character`, `Environment`, `Beat`, `Scene`, `Episode` as Pydantic models. The dataclasses also carry v1 legacy fields ("kept for backward compat") alongside v2 fields. The CLI validates via Pydantic, then re-loads the same JSON through the dataclass loader for rendering.

## Why it matters

Every consumer must choose between two incompatible representations of the same entity; field drift between them is undetectable. Two test suites (`test_loader.py`, `test_schema.py`, 100+ functions) exist mostly to pin both copies in place.

## Recommendation

Unify on the Pydantic models end-to-end; delete the dataclass layer and v1 compat fields once episode content is fully v2.
