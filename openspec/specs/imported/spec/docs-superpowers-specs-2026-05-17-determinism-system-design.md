---
id: SPEC-DETERMINISM-
kind: spec
title: Determinism System Design
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
checksum: 063b0d6ccb7966d88332bd53dc58afb3aec56afe839657598e831f281fef6722
---

> Imported legacy SPEC artifact from `docs/superpowers/specs/2026-05-17-determinism-system-design.md`. Keep future lifecycle work in OpenSpec.

**Date:** 2026-05-17  

---

## 1. Overview

### 1.1 Problem Statement

AI-generated media is non-deterministic by default. The same prompt produces different outputs across runs. For a sitcom pipeline where character appearance, environment lighting, and scene composition must remain consistent across beats, deterministic seeding is essential.

### 1.2 Goals

1. **Reproducible renders**: Same episode JSON + same seeds → identical outputs
2. **Seed tracking**: Each beat knows its generation seed
3. **Regression testing**: SSIM comparison against golden frame references
4. **Minimal seed management**: Users should not need to hand-edit seeds

### 1.3 Success Criteria

- Re-rendering the same episode with the same seed set produces bit-identical images
- SSIM regression test detects meaningful visual changes (>0.05 delta)
- Seed auto-generation works from episode metadata alone

---

## 2. Architecture

### 2.1 Seed Convention

Pattern: `{episode_prefix}{scene_number}{beat_number}1`

| Episode | Prefix | Scene 1, Beat 0 | Scene 2, Beat 3 |
|---------|--------|-----------------|-----------------|
| S1E1 | `1` | `110001` | `120031` |
| S1E2 | (none) | `10001` | `20031` |

- Beat index: 3 digits zero-padded (000, 001, 002...)
- Suffix: always `1` (reserved for sub-beat variants)
- Seeds must be unique within an episode

### 2.2 Core Module: `determinism.py`

```python
class Determinist:
    """Manages deterministic seed generation and verification."""

    def seed_for_beat(self, scene_id: str, beat_id: str) -> int:
        """Generate or retrieve seed for a given beat."""

    def verify_episode_determinism(self, episode: dict) -> list[str]:
        """Check all seeds are unique and valid."""
```

### 2.3 SSIM Regression

The `golden_frame` system uses scikit-image's SSIM (structural similarity index) to detect regressions:

```python
from skimage.metrics import structural_similarity as ssim

score = ssim(golden_frame, rendered_frame, channel_axis=2)
if score < threshold:
    report_regression(beat_id, score)
```

### 2.4 Seed Propagation

- **Image generation**: seed → text2image provider (Flux2 seed parameter)
- **Video generation**: seed → image2video provider (LTX seed parameter)
- **TTS**: seed → text2speech provider (voice generation seed)
- **No cross-provider seed coupling**: each provider gets its own seed from the beat's seed + provider offset

---

## 3. Integration Points

| Module | How It Uses Determinism |
|--------|------------------------|
| `scene_render.py` | Passes seed from BeatJob to Renderer |
| `renderer.py` | Seeds each provider call with beat seed + offset |
| `beat_prompts.py` | Includes seed in generated prompts for reproducibility |
| `validator.py` | Validates seed uniqueness in strict mode |
| `continuity.py` | Uses seeds to verify character appearance consistency |

---

## 4. CLI Commands

```bash
# Verify determinism of episode
showrunner validate episode_02.json --strict

# Compare golden frame regression
python -m showrunner.determinism compare-scene 003 output/golden output/latest

# Regenerate golden frames
showrunner bootstrap episode_02.json --golden
```

---

## 5. Key Design Decisions

1. **Simple integer seeds** over UUIDs → human-readable, sortable, debuggable
2. **Per-beat seeds** over shared RNG state → each beat is independently reproducible
3. **SSIM for regression** over pixel-diff → SSIM matches human perception of structural change
4. **Optional seed field** → episodes without explicit seeds auto-generate from beat index
