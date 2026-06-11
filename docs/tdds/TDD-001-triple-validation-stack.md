# TDD-001: Three parallel validation systems for the same episode structure

- Status: Open
- Date: 2026-06-11
- Category: Unnecessary complexity / Duplication
- Severity: High

## Finding

Episode validation exists three times (verified):

1. `src/showrunner/validator.py` (253 lines) — `EpisodeValidator` with hand-rolled `_check_scene_environment_refs`, `_check_scene_character_refs`, `_check_beat_ids_unique`, `_check_beat_speaker_refs`, plus BOTH a `_jsonschema_validate` path (line 71) and a `_structural_validate` fallback (line 86) for when `jsonschema` isn't installed.
2. `src/showrunner/schemas/episode.py` — Pydantic `Episode.validate_references()` (line 78) doing the same cross-reference checks.
3. `schemas/episode_v2.schema.json` — the JSON Schema consumed by path 1.

## Why it matters

Every schema change must be propagated to three places; they will drift. The Pydantic model alone covers everything more robustly. When sitcom-pilot becomes a scriptforge content project, this is triple the platform surface to migrate.

## Recommendation

Collapse onto the Pydantic `Episode` model; delete `validator.py` and the structural fallback; `commands/validate.py` becomes `Episode.model_validate(data)`. Keep the JSON Schema only if external tools need it — then generate it from the Pydantic model.
