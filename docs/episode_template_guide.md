# Episode Template Guide

## Introduction

The episode template is a canonical JSON file that defines the structure for creating new episodes in the Sitcom Pilot pipeline. It uses the beat-based schema v2.0 format and integrates with AIServices packages for model configuration.

## Quick Start

1. **Copy the template**: Copy `episode_template.json` to your new episode file
2. **Update metadata**: Change `show`, `season`, `episode`, and `title` fields
3. **Define characters**: Add your characters to the `cast` section
4. **Define environments**: Add your environments to the `environments` section
5. **Create scenes**: Add your scenes with beats to the `scenes` section
6. **Validate**: Run `showrunner validate your_episode.json` to check for errors

## Field Reference

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `show` | string | Yes | Name of the show (e.g., "Buffering") |
| `season` | integer | Yes | Season number (minimum: 1) |
| `episode` | integer | Yes | Episode number within the season (minimum: 1) |
| `title` | string | Yes | Episode title |
| `schema_version` | string | Yes | Schema version (must be "2.0") |
| `dialogue_status` | string | No | Status of dialogue: "present", "missing", or "partial" |
| `dialogue_recovery_note` | string | No | Notes about dialogue recovery process |

### Render Section

All render fields are optional and will use AIServices defaults if not specified.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `fps` | integer | 24 | Frames per second for video output |
| `resolution` | array | [1280, 720] | Video resolution [width, height] |

### Cast Section

The `cast` section defines characters. Each character is keyed by a unique character ID.

#### Character Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Character's full name |
| `role` | string | No | Character's role in the story |
| `visual` | string | Yes | Detailed visual description of the character |
| `reference_images` | array | No | Paths to reference images for the character |
| `lora` | string/null | No | LoRA model path for character consistency |
| `voice` | object | No | Voice configuration for text-to-speech |

#### Voice Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | string | "text2speech" | TTS provider (default: "text2speech" from AIServices) |
| `voice_id` | string | - | Voice ID or reference audio path |
| `clone_from` | string | - | Path to reference audio for voice cloning |
| `seed` | integer | - | Random seed for voice generation |
| `temperature` | number | - | Voice generation temperature |
| `language` | string | "en" | Language code |

### Environments Section

The `environments` section defines environments. Each environment is keyed by a unique environment ID.

#### Environment Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trigger_word` | string | Yes | Trigger word or detailed description for environment generation |
| `reference_image` | string | No | Path to reference image for the environment |
| `style` | string | No | Style description for the environment |

### Scenes Section

The `scenes` section defines scenes. Each scene contains beats.

#### Scene Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scene_id` | string | Yes | Unique scene identifier |
| `title` | string | No | Scene title |
| `environment` | string | Yes | Environment ID where the scene takes place |
| `characters_present` | array | Yes | List of character IDs present in the scene |
| `mood` | string | No | Mood or atmosphere of the scene |
| `legacy_audio_path` | string | No | Path to legacy audio file (for migration) |
| `beats` | array | Yes | List of beats in the scene |

### Beats Section

Each beat is either a "speech" or "silent" beat.

#### Beat Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `beat_id` | string | Yes | Unique beat identifier |
| `kind` | string | Yes | Type of beat: "speech", "silent", or "transition" |
| `camera` | string | No | Camera angle or shot description |
| `action` | string | No | Action or description of what happens in the beat |
| `seed` | integer | No | Random seed for generation |
| `speaker` | string | Yes (speech) | Character ID of the speaker |
| `text` | string | Yes (speech) | Dialogue text |
| `audio_path` | string | No | Path to audio file |

## Examples

### Minimal Episode

```json
{
  "show": "My Show",
  "season": 1,
  "episode": 1,
  "title": "Pilot",
  "schema_version": "2.0",
  "cast": {},
  "environments": {},
  "scenes": []
}
```

### Episode with Dialogue

```json
{
  "show": "Buffering",
  "season": 1,
  "episode": 1,
  "title": "The Bug",
  "schema_version": "2.0",
  "dialogue_status": "present",
  "cast": {
    "maya": {
      "name": "Maya Chen",
      "visual": "East Asian woman in her late 20s"
    }
  },
  "environments": {
    "living_room": {
      "trigger_word": "Modern apartment living room"
    }
  },
  "scenes": [
    {
      "scene_id": "001",
      "environment": "living_room",
      "characters_present": ["maya"],
      "beats": [
        {
          "beat_id": "001_b00",
          "kind": "speech",
          "speaker": "maya",
          "text": "Hello, world!"
        }
      ]
    }
  ]
}
```

## Beat Seed Allocation Convention

Seeds ensure deterministic image/video generation per beat. The convention is:

**Pattern:** `{episode_prefix}{scene_number}{beat_number}1`

| Episode | Prefix | Example seed for scene 1, beat 0 | Example for scene 2, beat 3 |
|---------|--------|----------------------------------|------------------------------|
| S1E1 | `1` | `110001` (1 + 1 + 000 + 1) | `120031` (1 + 2 + 003 + 1) |
| S1E2 | (none) | `10001` (1 + 000 + 1) | `20031` (2 + 003 + 1) |

**Rules:**
- Episode prefix: single digit matching episode number (omit if seeds stay unique without it)
- Scene number: 1-2 digits matching `scene_id` numeric part
- Beat index: 3 digits zero-padded matching beat position within scene (000, 001, 002...)
- Suffix: always `1` (reserved for future sub-beat variants)
- Silent beats follow the same convention as speech beats
- Seeds must be unique within an episode to guarantee determinism

**Reference asset seeds** (cast voices, environment refs) use the character/environment config `seed` field, not beat seeds.

## Best Practices

1. **Use descriptive character IDs**: Use lowercase, underscore-separated names (e.g., "maya", "derek")
2. **Use descriptive environment IDs**: Use lowercase, underscore-separated names (e.g., "living_room", "kitchen")
3. **Use sequential beat IDs**: Use format "scene_id_bNN" (e.g., "001_b00", "001_b01")
4. **Follow the seed allocation convention**: See "Beat Seed Allocation Convention" above
5. **Provide detailed visual descriptions**: The more detail, the better the image generation
6. **Use trigger words for environments**: Detailed descriptions help generate consistent environments
7. **Set dialogue_status**: Use "present" if dialogue is included, "missing" if not, "partial" if some is missing
8. **Include reference images**: Reference images help maintain character and environment consistency

## Validation

Validate your episode file using the CLI:

```bash
showrunner validate your_episode.json
```

Or using Python:

```python
import json
from jsonschema import validate

episode = json.load(open('your_episode.json'))
schema = json.load(open('schemas/episode_v2.schema.json'))
validate(instance=episode, schema=schema)
```
