---
id: SPEC-VALIDATION-S
kind: spec
title: Validation System Design
status: draft
authors: []
reviewers: []
tags: []
supersedes: []
superseded_by: []
depends_on: []
blocks: []
implements: []
related: []
external: []
project: sitcom-pilot
checksum: 54995499d36104ab95ecff5a14c691e5f9f58422ccf832c2117be06dd7553e16
---

**Date:** 2026-05-17  

---

## 1. Overview

### 1.1 Problem Statement

Episode JSON files are human-authored or AI-generated. They can contain structural errors (missing required fields, invalid references), semantic errors (speaker not in cast, scene environment doesn't exist), and business rule violations (duplicate beat IDs, seed conflicts).

### 1.2 Goals

1. **Schema validation**: Enforce JSON Schema Draft 2020-12 compliance
2. **Business rule checks**: Validate references, uniqueness, constraints
3. **Strict mode**: Optional deeper validation for production readiness
4. **Clear error messages**: Actionable feedback for episode authors

### 1.3 Success Criteria

- Schema catches all structural errors (missing fields, wrong types)
- Strict mode catches all reference errors (speaker not in cast, env not defined)
- Validation completes in < 1s for a full episode
- Error messages include file path, beat ID, and fix suggestion

---

## 2. Modules

### 2.1 `validator.py`

```python
class EpisodeValidator:
    def validate_file(self, path: Path, strict: bool = False) -> list[ValidationError]:
        """Validate an episode JSON file against schema + business rules."""

    def validate_episode(self, episode: dict, strict: bool = False) -> list[ValidationError]:
        """Validate a loaded episode dict."""

class ValidationError:
    path: str           # JSON path to error location
    message: str        # Human-readable error
    severity: str       # "error" | "warning"
    beat_id: str | None  # Associated beat, if applicable
```

### 2.2 `loader.py`

```python
class EpisodeLoader:
    def load(self, path: Path) -> dict:
        """Load and parse episode JSON file."""

    def load_with_schema(self, path: Path, schema_path: Path) -> dict:
        """Load with optional schema validation."""

    def resolve_references(self, episode: dict) -> Episode:
        """Resolve cast and environment references for validation."""
```

### 2.3 Schema: `schemas/episode_v2.schema.json`

JSON Schema Draft 2020-12 covering:
- Top-level fields (show, season, episode, title, schema_version)
- Cast objects with voice config
- Environment objects
- Scene array with beat sequences
- Per-field descriptions and default values

---

## 3. Validation Layers

### Layer 1: Schema Compliance

Checks enforced by `jsonschema.validate()`:
- Required fields present
- Field types match schema
- Enum values valid (e.g., `kind` is `"speech"` or `"silent"`)
- Array item types correct

### Layer 2: Reference Integrity (strict mode)

- All `speaker` values reference a key in `cast`
- All `environment` values reference a key in `environments`
- All `characters_present` slugs exist in `cast`
- No duplicate `beat_id` values within an episode

### Layer 3: Business Rules (strict mode)

- Speech beats must have non-empty `text`
- Speech beats must have `speaker` field
- Silent beats must not have `speaker` or `text`
- `schema_version` must be `"2.0"`
- Seed values must be unique within episode (if present)
- `scene_id` values must be unique

---

## 4. Error Format

```
Error: episode_02.json:003_b05: speaker 'bob' not found in cast
  Available: maya, derek, priya, finn
  Fix: Change speaker to one of the available cast members

Error: episode_02.json: beat_id '003_b05' is duplicated (also at scene 004)
  Fix: Change one of the duplicate beat_ids
```

---

## 5. CLI Integration

```bash
# Basic validation
showrunner validate episode_02.json

# Strict validation
showrunner validate episode_02.json --strict

# Programmatic
python -c "
from showrunner.validator import EpisodeValidator
v = EpisodeValidator()
errors = v.validate_file('episode_02.json', strict=True)
for e in errors:
    print(f'{e.path}: {e.message}')
"
```

---

## 6. Key Design Decisions

1. **Two-tier validation** (schema + strict) → fast structural checks in CI, deep checks on demand
2. **JSON Schema for structure** → declarative, well-specified, separates validation from code
3. **Python code for business rules** → some rules are too complex for JSON Schema (reference resolution, uniqueness across nested arrays)
4. **Error objects over exceptions** → collect all errors, report them together (not first-fail)
