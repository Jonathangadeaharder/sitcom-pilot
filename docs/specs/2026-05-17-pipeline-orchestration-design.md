---
id: SPEC-PIPELINE-ORC
kind: spec
title: Pipeline Orchestration & Rendering Design
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
checksum: 6d401eb6a98b12ec7bba0c201e086f28629cff8afae18c699bb76d3dd8da46a6
---

**Date:** 2026-05-17  

---

## 1. Overview

### 1.1 Problem Statement

The sitcom-pilot pipeline must coordinate multiple MLX-based AI providers (text2image, image2video, text2speech) to transform episode JSON into beat-level video clips, then assemble them into a final episode. The orchestration layer must support parallel rendering, caching, partial re-renders, and crash recovery.

### 1.2 Goals

1. **Beat isolation**: Each beat renders independently for parallelism and caching
2. **Crash recovery**: Failed beats retry without re-rendering completed beats
3. **Partial re-render**: Re-render a single scene or beat without full pipeline rerun
4. **Progress visibility**: Real-time progress tracking per beat

### 1.3 Success Criteria

- Full episode of 128 beats renders with `-w 4` in under 30 minutes
- Re-rendering a single beat takes < 60 seconds
- Crashed pipeline resumes from last completed beat
- Progress indicator shows per-beat status (pending/running/done/failed)

---

## 2. Architecture

### 2.1 Core Modules

| Module | Responsibility |
|--------|---------------|
| `scene_render.py` | Orchestrates per-scene rendering: plan beats, dispatch render jobs, collect results |
| `renderer.py` | Single-beat render: image → audio → video sequence |
| `render_buffer.py` | Async buffer coordinating concurrent render jobs |
| `beat_clip_uniformiser.py` | Normalizes beat clips to consistent FPS/resolution |
| `progress.py` | Real-time progress tracking (total, completed, failed, pending) |
| `planner.py` | Converts episode JSON to ordered list of `BeatJob` objects |

### 2.2 Render Flow

```
plan_beats(episode, manifest, paths)
  │
  ▼
List[BeatJob] (one per beat)
  │
  ▼ (per scene, parallel)
scene_render.render_scene(scene, jobs, client, ...)
  ├── _render_image(beat_job)   → text2image → keyframe.png
  ├── _render_audio(beat_job)   → text2speech → dialogue.wav (speech beats only)
  └── _render_video(beat_job)   → image2video → beat.mp4
  │
  ▼
BeatClipUniformiser.uniformise(clips)
  │
  ▼
concat_clips(uniform_clips) → episode_raw.mp4
```

### 2.3 BeatJob Structure

```python
@dataclass
class BeatJob:
    scene_id: str
    beat_id: str
    kind: str            # "speech" | "silent"
    prompt: str          # generated image prompt
    seed: int
    duration_sec: float
    needs_audio: bool
    speaker: str = ""
    text: str = ""
    image_path: Path = field(default_factory=Path)
    audio_path: Path = field(default_factory=Path)
    video_path: Path = field(default_factory=Path)
    status: BeatStatus = BeatStatus.PENDING
    error: str = ""
```

### 2.4 Parallelism Model

- **Per-beat**: Independent (no shared state between beats)
- **Per-scene**: Beats within a scene share environment context but render independently
- **Workers**: Configurable via `-w` flag, defaults to 1
- **Cache**: Output file existence → skip render (idempotent)

### 2.5 Crash Recovery

1. Check output file existence before render
2. On crash: retry up to `SITCOM_MAX_CRASH_RETRIES` (default 3)
3. Cooldown between retries (`SITCOM_COOLDOWN_SECONDS`)
4. Failed beats reported in `render_report.json`

### 2.6 File Layout

```
output/<run_id>/
  beats/<scene_id>/<beat_id>.png
  beats/<scene_id>/<beat_id>.mp4
  audio/<scene_id>/<beat_id>.wav
  render_report.json
```

---

## 3. CLI Integration

```bash
# Full episode
showrunner render episode episode_02.json -o output -w 2

# Single scene
showrunner render scene episode_02.json 003 -o output -w 2

# Single beat
showrunner render beat episode_02.json 003_b05 -o output

# Dry run
showrunner plan episode_02.json -v
```

---

## 4. Key Design Decisions

1. **Per-beat output files** → cache invalidation by file deletion
2. **Concat demuxer** → no re-encoding during assembly
3. **Uniformiser pass** → prevents format mismatch errors during concat
4. **Progress tracking** → simple counter, not a progress bar library
