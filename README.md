# sitcom-pilot

Beat-based AI sitcom pilot pipeline. Turns JSON episode scripts into animated video via local MLX providers — text-to-image, image-to-video, text-to-speech, and ffmpeg assembly.

Built for **Buffering S01**.

Package name: **`showrunner`** | CLI entry point: **`showrunner`**

## Architecture

```
Episode JSON (v2.0)
       │
       ▼
   validate ──► plan (dry run)
       │
       ▼
   bootstrap ──► reference images + voice samples
       │
       ▼
   render ──► per-beat: image → audio → video
       │              │
       │              └── scene / episode granularity
       ▼
   assemble ──► concat clips + SRT → final .mp4
```

The pipeline is **beat-based**: each scene contains ordered beats (speech or silent), and every beat is an independent render unit — a keyframe image, optional TTS audio, and an image-to-video clip. Beats are assembled in order to produce the final episode.

## Installation

Requires **Python 3.11+**, [uv](https://docs.astral.sh/uv/), and [ffmpeg](https://ffmpeg.org/).

```bash
git clone git@github.com:Jonathangadeaharder/sitcom-pilot.git && cd sitcom-pilot
uv sync
```

MLX provider packages (text2image, image2video, text2speech, etc.) are installed via AIServices git dependencies.

Verify dependencies:

```bash
showrunner doctor
```

## Quick Start

### Render episode_02 ("The Demo Day")

`episode_02.json` is a full 8-scene episode. These steps walk through the entire pipeline:

```bash
# 1. Validate the episode file
showrunner validate episode_02.json --strict

# 2. Preview the beat plan (128 beats across 8 scenes)
showrunner plan episode_02.json

# 3. Bootstrap reference images + voice samples (via the run command)
showrunner run episode_02.json -o output --skip-validate

# 4. Render a single beat (e.g., cold open first beat)
showrunner render beat episode_02.json 001_b00 -o output

# 5. Render a single scene
showrunner render scene episode_02.json 001 -o output -w 2

# 6. Render the full episode (all 128 beats)
showrunner render episode episode_02.json -o output -w 2

# 7. Assemble final video with captions
showrunner assemble episode_02.json -o output --captions
```

Output lands in `output/<run_id>/assembly/episode.mp4`.

### Common workflows

**Iterate on a scene**: render a scene, review, tweak the JSON, re-render:

```bash
showrunner render scene episode_02.json 003 -o output -w 2
```

**Reboot**: clean everything and start fresh:

```bash
rm -rf output && showrunner run episode_02.json -o output
```

### Scene reference

| Scene | Title | Environment | Beats |
|-------|-------|-------------|-------|
| 001 | Cold Open — The Email | maya_desk | 10 |
| 002 | The War Room | kitchen | 18 |
| 003 | The Pivot Pitch | living_room | 17 |
| 004 | The Rehearsal | living_room | 19 |
| 005 | The All-Nighter | maya_desk | 17 |
| 006 | The Demo — Part 1 | living_room | 16 |
| 007 | The Demo — Part 2 / Climax | living_room | 14 |
| 008 | Tag — The Aftermath | rooftop | 17 |

## CLI Reference

All commands are under the `showrunner` entrypoint.

### `validate`

Validate an episode JSON against the v2 schema.

```bash
showrunner validate <episode.json> [--strict]
```

| Flag | Description |
|------|-------------|
| `--strict` | Enable business-rule checks beyond schema (speaker refs, dialogue text presence) |

### `plan`

Output beat plan as JSON (dry run — no rendering).

```bash
showrunner plan <episode.json>
```

Outputs a JSON array of beat plan objects with beat number, type, description, duration, estimated cost, and rendering strategy.

### `bootstrap`

Create a new episode project scaffold with a template episode.json, scenes/, output/, and assets/ directories.

```bash
showrunner bootstrap <project_name> [--force] [--no-assets]
```

| Flag | Description |
|------|-------------|
| `--force` | Overwrite existing project directory |
| `--no-assets` | Skip creating assets directory |

### `render beat`

Render a single beat.

```bash
showrunner render beat <episode.json> <beat_id> [-s <scene_id>] [-o <dir>]
```

| Flag | Description |
|------|-------------|
| `-s, --scene` | Scene ID (auto-detected if omitted) |
| `-o, --output-dir` | Output root directory (default: `output`) |

### `render scene`

Render all beats in a scene.

```bash
showrunner render scene <episode.json> <scene_id> [-o <dir>] [-w <workers>] [--json]
```

| Flag | Description |
|------|-------------|
| `-o, --output-dir` | Output root directory (default: `output`) |
| `-w, --workers` | Parallel render threads (default: 1) |
| `--json` | Output structured JSON logs |

### `render episode`

Render all beats across all scenes.

```bash
showrunner render episode <episode.json> [-o <dir>] [-w <workers>] [--json] [-b <N>]
```

| Flag | Description |
|------|-------------|
| `-o, --output-dir` | Output root directory (default: `output`) |
| `-w, --workers` | Parallel render threads (default: 1) |
| `--json` | Output structured JSON logs |
| `-b, --buffer` | Buffer N beats ahead (default: sequential) |

### `assemble`

Concatenate rendered clips into a final video with subtitles.

```bash
showrunner assemble <episode.json> [-o <dir>] [--run-id <id>] [--captions]
```

| Flag | Description |
|------|-------------|
| `-o, --output-dir` | Output root directory (default: `output`) |
| `--run-id` | Specific run to assemble (defaults to latest) |
| `--captions` | Burn SRT subtitles into video |

Outputs `output/<run_id>/assembly/episode_raw.mp4`, `episode.srt`, and (with `--captions`) `episode.mp4`.

### `showcase`

Extract a scene clip + thumbnail from a render run.

```bash
showrunner showcase <episode.json> [--scene <id>] [-o <dir>] [--run-id <id>]
```

| Flag | Description |
|------|-------------|
| `--scene` | Scene ID or 1-based index (default: `007`) |
| `-o, --output-dir` | Output root directory (default: `output`) |
| `--run-id` | Specific run ID |

Outputs `output/<run_id>/showcase/<scene_id>.mp4` and `<scene_id>.jpg`.

### `run`

Run the full pipeline: validate → plan → bootstrap → render → assemble.

```bash
showrunner run <episode.json> [-o <dir>] [-w <workers>] [--captions] [--seed <N>] [--deterministic] [-v]
```

| Flag | Description |
|------|-------------|
| `-o, --output-dir` | Output root directory (default: `output`) |
| `-w, --workers` | Parallel render workers (default: 1) |
| `--captions` | Burn in captions |
| `--skip-bootstrap` | Skip bootstrap (character refs) step |
| `--skip-validate` | Skip schema validation step |
| `--seed` | Override seed for deterministic generation |
| `--deterministic` | Enable strict deterministic mode |
| `-v, --verbose` | Verbose logging |

### `doctor`

Check system prerequisites (Python, ffmpeg, uv, disk space, RAM).

```bash
showrunner doctor [--json] [-v]
```

| Flag | Description |
|------|-------------|
| `--json` | Output results as JSON |
| `-v, --verbose` | Show details for passing checks |

## Episode Format (v2.0)

Episodes are JSON files using the beat-based schema. The authoritative schema is defined by the pydantic models in `src/showrunner/schemas/episode.py`.

### Minimal Example

```json
{
  "show": "Buffering",
  "season": 1,
  "episode": 1,
  "title": "Pilot",
  "schema_version": "2.0",
  "cast": {
    "maya": {
      "name": "Maya Chen",
      "visual": "East Asian woman in her late 20s, black hair, casual clothes"
    }
  },
  "environments": {
    "living_room": {
      "trigger_word": "Modern apartment living room, warm lighting, sitcom set"
    }
  },
  "scenes": [
    {
      "scene_id": "001",
      "title": "Cold Open",
      "environment": "living_room",
      "characters_present": ["maya"],
      "mood": "comedic",
      "beats": [
        {
          "beat_id": "001_b00",
          "kind": "speech",
          "camera": "medium shot",
          "action": "Maya stares at her laptop in disbelief",
          "speaker": "maya",
          "text": "You have got to be kidding me."
        },
        {
          "beat_id": "001_b01",
          "kind": "silent",
          "camera": "close-up",
          "action": "Laptop screen shows a critical error",
          "duration_sec": 2.0
        }
      ]
    }
  ]
}
```

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `show` | string | yes | Show name |
| `season` | integer | yes | Season number (>= 1) |
| `episode` | integer | yes | Episode number (>= 1) |
| `title` | string | yes | Episode title |
| `schema_version` | string | yes | Must be `"2.0"` |
| `dialogue_status` | string | no | `"present"`, `"missing"`, or `"partial"` |
| `render` | object | no | Per-episode render overrides (fps, resolution) |

### Cast

Each character is keyed by a slug (e.g., `"maya"`):

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Full name |
| `role` | string | Character role description |
| `visual` | string | Detailed visual description for image generation |
| `lora` | string \| null | LoRA model path for consistency |
| `voice` | object | TTS config (see below) |
| `reference_images` | array | Paths to reference images |

#### Voice Config

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | string | `"text2speech"` | TTS provider |
| `voice_id` | string | — | Voice ID or reference audio path |
| `clone_from` | string | — | Path to audio for voice cloning |
| `seed` | integer | — | Random seed |
| `temperature` | float | `0.8` | Generation temperature |
| `language` | string | `"en"` | Language code |

### Environments

| Field | Type | Description |
|-------|------|-------------|
| `trigger_word` | string | Description for environment generation |
| `style` | string | Style description |
| `reference_image` | string | Path to reference image |

### Scenes

| Field | Type | Description |
|-------|------|-------------|
| `scene_id` | string | Unique identifier |
| `environment` | string | References an environment key |
| `characters_present` | array | Character slugs in this scene |
| `beats` | array | Ordered list of beats |
| `title` | string | Scene title |
| `mood` | string | Mood/atmosphere |
| `target_seconds` | number | Target duration |

### Beats

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `beat_id` | string | yes | Unique identifier (e.g., `"001_b00"`) |
| `kind` | string | yes | `"speech"`, `"silent"`, or `"transition"` |
| `camera` | string | no | Camera angle/shot description |
| `action` | string | no | Visual action description |
| `duration_sec` | float | no | Beat duration (default: 3.0) |
| `seed` | integer | no | Reproducibility seed |
| `speaker` | string | speech | Character slug of speaker |
| `text` | string | speech | Dialogue text |
| `audio_path` | string | no | Path to audio file |

## Cast Manifest

The `CastManifest` tracks per-character metadata across the pipeline. Built internally by the `run` command and consumed by the render pipeline for:

- **Reference images** (`CharacterRef`): front, three-quarter, profile views
- **Voice config** (`VoiceConfig`): provider, voice ID, clone source
- **Wardrobe tracking** (`WardrobeEntry`): per-episode costume descriptions
- **Consistency notes**: free-text for cross-scene continuity

Stored as `cast_manifest.json` and loadable via `CastManifest.load()`.

## Pipeline Stages

### 1. Validate (`commands/validate.py`)

Validates episode JSON against the pydantic models in `src/showrunner/schemas/episode.py`. Strict mode adds business-rule checks (e.g., all referenced characters/environments must exist, speech beats have speaker + text).

### 2. Plan (`scene_render.py:plan_beats`)

Converts every beat in every scene into a `BeatJob` — a renderable unit with a generated image prompt (from `beat_prompts.py`), output paths (from `paths.py`), and status tracking. The `plan` CLI command outputs beat plans as JSON.

### 3. Bootstrap (`cli/main.py:_pipeline_bootstrap`)

Called by the `run` command. Uses `AIServicesClient.text2image` to generate character reference sheets and environment establishing shots. Can be skipped with `--skip-bootstrap`.

### 4. Render (`scene_render.py`)

For each `BeatJob`:
1. **Image**: `text2image` generates a keyframe from the beat prompt
2. **Audio**: `text2speech` generates dialogue audio (speech beats only)
3. **Video**: `image2video` animates the keyframe, muxing in audio if present

Supports parallel rendering via `--workers`. Caches results — skips if output already exists.

### 5. Assemble (`assembler.py`)

Post-render assembly via ffmpeg:
- `concat_clips` — joins all beat videos in order
- `generate_srt` — creates subtitles from speech beat text and durations
- `burn_in_captions` — optionally burns SRT into video
- `mux_audio` / `mix_music_bed` — audio mixing utilities

## Configuration

Per-episode render config in JSON (`episode.json` → `render` block) controls output:

```json
"render": {
  "fps": 24,
  "resolution": [1280, 720]
}
```

## Output Structure

```
output/
  <run_id>/
    beats/<scene_id>/<beat_id>.png   # keyframe images
    beats/<scene_id>/<beat_id>.mp4   # video clips
    audio/<scene_id>/<beat_id>.wav   # TTS audio
    assembly/
      episode_raw.mp4                # concatenated video
      episode.srt                    # subtitle track
      episode.mp4                    # final (with captions)
    render_report.json               # per-scene stats
```

## Project Structure

```
sitcom-pilot/
├── docs/                # Guides, references, and architecture docs
│   ├── architecture/    # ADRs (architecture decision records)
│   ├── specs/           # Design specs
│   ├── plans/           # Implementation plans
│   ├── episode_template_guide.md
│   ├── episode_schema_reference.md
│   ├── writers_guide.md
│   └── reference_asset_checklist.md
├── src/
│   └── showrunner/      # Main package
│       ├── cli/         # Typer CLI entry point
│       ├── commands/    # Subcommand implementations (doctor, validate)
│       ├── schemas/     # Pydantic models (episode, beat_plan, cast)
│       ├── loader.py    # EpisodeLoader — parses episode JSON (v1 + v2)
│       ├── prompts.py   # PromptBuilder (v1 legacy, ComfyUI workflows)
│       ├── beat_prompts.py  # Beat-based prompt generation (v2)
│       ├── scene_render.py  # BeatJob orchestration, render_scene/episode
│       ├── renderer.py  # ShotRenderer (v1 legacy, ComfyUI driver)
│       ├── assembler.py # FFmpeg assembly (concat, SRT, captions, music)
│       ├── planner.py   # Plan episode beats with cost estimation
│       ├── paths.py     # RunPaths — output directory layout
│       ├── config.py    # PipelineConfig (pydantic-settings + fallback)
│       ├── determinism.py   # Seed strategy and manifest hashing
│       ├── cast_manifest.py # CastManifest tracking
│       ├── manifest.py  # Episode manifest utilities
│       ├── continuity.py    # Cross-scene continuity checks
│       ├── node_map.py  # ComfyUI workflow node mapping
│       ├── progress.py  # Progress callback system
│       ├── render_buffer.py # Buffered concurrent render
│       ├── beat_clip_uniformiser.py # Normalize clips before concat
│       ├── captions.py  # SRT/caption generation
│       ├── plate_generator.py # Plate/background generation
│       ├── comfyui_client.py  # ComfyUI API client
│       └── aiservices_client.py # AIServices unified facade
├── scripts/             # Utility scripts (build_refs.py, build_voices.py)
├── tests/               # pytest test suite
├── episode_01.json      # S01E01 "Pilot"
├── episode_02.json      # S01E02 "The Demo Day"
└── episode_template.json
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest tests/

# Lint
uvx ruff check src/
uvx ruff format src/

# Type check
uvx pyright src/

# Mutation testing
uv run mutmut run
```

### Test Configuration

- Test runner: **pytest** with `pytest-cov`
- Linting: **ruff** (line-length 100, target Python 3.11)
- Type checking: **pyright**
- Mutation testing: **mutmut**

## Documentation

- `docs/episode_template_guide.md` — How to write episode JSON files
- `docs/episode_schema_reference.md` — Full schema field reference
- `docs/reference_asset_checklist.md` — Asset preparation guide
- `docs/architecture/` — Deep-dive architecture docs
- `src/showrunner/schemas/episode.py` — Pydantic models defining the episode schema

## License

Private project. All rights reserved.
