---
id: SPEC-CAST-MANIFES
kind: spec
title: Cast Manifest & Character Consistency Design
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
checksum: f6f8cd8445d83403cdc5d984819d464d51cf407cd5f13b2cfff792be15792088
---

**Date:** 2026-05-17  

---

## 1. Overview

### 1.1 Problem Statement

Characters in a sitcom must look consistent across scenes, episodes, and renders. Without a system to track character metadata (reference images, voice configs, wardrobe), each render can produce visually different characters.

### 1.2 Goals

1. **Cast manifest**: Single source of truth for character metadata
2. **Reference images**: Front, three-quarter, and profile views per character
3. **Voice config**: Per-character TTS settings (voice ID, clone source, seed)
4. **Wardrobe tracking**: Per-episode costume descriptions
5. **Consistency notes**: Free-text continuity guidance for prompt engineering

### 1.3 Success Criteria

- Cast manifest serializes to `cast_manifest.json` in output directory
- Bootstrap generates reference images for all cast members
- Render pipeline reads manifest for character prompts and voice config
- Continuity checks flag appearance drift between scenes

---

## 2. Modules

### 2.1 `cast_manifest.py`

```python
@dataclass
class CharacterRef:
    front: str | None       # Path to front-facing reference
    three_quarter: str | None
    profile: str | None

@dataclass
class VoiceConfig:
    provider: str = "text2speech"
    voice_id: str | None = None
    clone_from: str | None = None
    seed: int | None = None
    temperature: float = 0.8
    language: str = "en"

@dataclass
class WardrobeEntry:
    episode: int
    costume: str
    accessories: list[str]

@dataclass
class CastManifest:
    characters: dict[str, CharacterEntry]
    schema_version: str = "1.0"

    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> CastManifest: ...
    def get_voice(self, character_id: str) -> VoiceConfig: ...
    def get_wardrobe(self, character_id: str, episode: int) -> WardrobeEntry | None: ...
```

### 2.2 `manifest.py`

Pipeline-level manifest tracking render metadata:

```python
@dataclass
class SceneManifest:
    scene_id: str
    beat_count: int
    duration_sec: float
    environment: str

@dataclass
class RenderManifest:
    episode: str
    run_id: str
    scenes: list[SceneManifest]
    status: str  # "pending" | "in_progress" | "complete" | "partial"
```

### 2.3 `continuity.py`

Cross-beat and cross-scene consistency checks:

```python
class ContinuityChecker:
    def check_character_appearance(self, manifest: CastManifest,
                                   scene_beats: list[BeatJob]) -> list[str]:
        """Verify character appearance is consistent across scene."""

    def check_environment_consistency(self, scene: dict) -> list[str]:
        """Check environment description doesn't drift across beats."""
```

---

## 3. Bootstrap Flow

> **Note:** The `showrunner bootstrap` CLI command creates a project scaffold, not reference images. Reference image generation happens inside `showrunner run` via `_pipeline_bootstrap()`.

The bootstrap pipeline step (invoked by `showrunner run`):

```
showrunner run episode_02.json -o output
  │
  ├── (bootstrap step) text2image → cast/<slug>/front.png
  ├── (bootstrap step) text2image → environments/<name>/reference.png
  └── ... render + assemble
```

### Output

```
output/bootstrap/
  cast/maya/
    front.png
    3q.png
    profile.png
  cast/derek/
    front.png
    3q.png
    profile.png
  environments/living_room/
    reference.png
  environments/kitchen/
    reference.png
  cast_manifest.json
```

---

## 4. Integration Points

| Module | Uses |
|--------|------|
| `scene_render.py` | Reads manifest for character visual prompts |
| `renderer.py` | Passes reference images as ControlNet input |
| `beat_prompts.py` | Includes character visual description + wardrobe in prompt |
| `assembler.py` | Reads scene manifest for assembly order |
| `continuity.py` | Compares generated frames against character references |

---

## 5. Key Design Decisions

1. **Manifest as JSON file** → human-readable, diffable, cacheable
2. **Three reference angles** → front/3q/profile covers typical sitcom camera setups
3. **Separate wardrobe tracking** → costumes change per episode, reference images don't
4. **Bootstrap generates references once** → cached across renders (unless deleted)
5. **Voice config in manifest** → TTS settings are per-character, not per-episode
