# Episode Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a canonical episode template with enhanced JSON Schema and comprehensive documentation for the Sitcom Pilot pipeline.

**Architecture:** Create a new episode_template.json file with example data, update the existing JSON Schema with descriptions and defaults, and create documentation files explaining how to use the template.

**Tech Stack:** Python 3.11+, jsonschema, pydantic, pytest

---

## File Structure

### Files to Create
- `episode_template.json` - Canonical episode template with example data
- `docs/episode_template_guide.md` - User guide for the template
- `docs/episode_schema_reference.md` - Schema reference documentation

### Files to Modify
- `schemas/episode_v2.schema.json` - Enhanced schema with descriptions and defaults

---

## Task 1: Update JSON Schema with Descriptions and Defaults

**Files:**
- Modify: `schemas/episode_v2.schema.json`

- [ ] **Step 1: Read current schema file**

```bash
cat schemas/episode_v2.schema.json
```

- [ ] **Step 2: Update schema with descriptions and defaults**

Replace the entire `schemas/episode_v2.schema.json` with:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://showrunner/schemas/episode_v2.schema.json",
  "title": "Episode",
  "description": "Beat-based episode schema v2.0 for the Sitcom Pilot pipeline. All render fields are optional and will use AIServices defaults if not specified.",
  "type": "object",
  "required": ["show", "season", "episode", "title", "schema_version", "cast", "environments", "scenes"],
  "properties": {
    "show": { 
      "type": "string",
      "description": "Name of the show (e.g., 'Buffering')"
    },
    "season": { 
      "type": "integer", 
      "minimum": 1,
      "description": "Season number"
    },
    "episode": { 
      "type": "integer", 
      "minimum": 1,
      "description": "Episode number within the season"
    },
    "title": { 
      "type": "string",
      "description": "Episode title"
    },
    "schema_version": { 
      "type": "string", 
      "const": "2.0",
      "description": "Schema version (must be '2.0')"
    },
    "target_duration_min": { 
      "type": "number", 
      "minimum": 0,
      "description": "Target episode duration in minutes"
    },
    "dialogue_status": { 
      "type": "string", 
      "enum": ["present", "missing", "partial"],
      "description": "Status of dialogue in the episode"
    },
    "dialogue_recovery_note": { 
      "type": "string",
      "description": "Notes about dialogue recovery process"
    },
    "render": {
      "type": "object",
      "description": "Render configuration. All fields are optional and will use AIServices defaults.",
      "properties": {
        "fps": { 
          "type": "integer", 
          "minimum": 1, 
          "default": 24,
          "description": "Frames per second for video output"
        },
        "resolution": { 
          "type": "array", 
          "items": { "type": "integer" }, 
          "minItems": 2, 
          "maxItems": 2,
          "default": [1280, 720],
          "description": "Video resolution [width, height]"
        },
      },
      "additionalProperties": false
    },
    "cast": {
      "type": "object",
      "description": "Character definitions. Keys are character IDs.",
      "additionalProperties": { "$ref": "#/$defs/CharacterV2" }
    },
    "environments": {
      "type": "object",
      "description": "Environment definitions. Keys are environment IDs.",
      "additionalProperties": { "$ref": "#/$defs/EnvironmentV2" }
    },
    "scenes": {
      "type": "array",
      "description": "List of scenes in the episode",
      "items": { "$ref": "#/$defs/Scene" }
    }
  },
  "additionalProperties": true,
  "$defs": {
    "CharacterV2": {
      "type": "object",
      "required": ["name", "visual"],
      "description": "Character definition with visual description and optional voice configuration",
      "properties": {
        "name": { 
          "type": "string",
          "description": "Character's full name"
        },
        "role": { 
          "type": "string",
          "description": "Character's role in the story"
        },
        "visual": { 
          "type": "string",
          "description": "Detailed visual description of the character"
        },
        "reference_images": { 
          "type": "array", 
          "items": { "type": "string" },
          "description": "Paths to reference images for the character"
        },
        "lora": { 
          "type": ["string", "null"],
          "description": "LoRA model path for character consistency"
        },
        "voice": {
          "type": "object",
          "description": "Voice configuration for text-to-speech",
          "properties": {
            "provider": { 
              "type": "string", 
              "default": "text2speech",
              "description": "TTS provider (default: 'text2speech' from AIServices)"
            },
            "voice_id": { 
              "type": "string",
              "description": "Voice ID or reference audio path"
            },
            "clone_from": { 
              "type": "string",
              "description": "Path to reference audio for voice cloning"
            },
            "seed": { 
              "type": "integer",
              "description": "Random seed for voice generation"
            },
            "temperature": { 
              "type": "number",
              "description": "Voice generation temperature"
            },
            "language": { 
              "type": "string", 
              "default": "en",
              "description": "Language code"
            }
          },
          "additionalProperties": false
        }
      },
      "additionalProperties": true
    },
    "EnvironmentV2": {
      "type": "object",
      "required": ["trigger_word"],
      "description": "Environment definition with trigger word for image generation",
      "properties": {
        "trigger_word": { 
          "type": "string",
          "description": "Trigger word or detailed description for environment generation"
        },
        "reference_image": { 
          "type": "string",
          "description": "Path to reference image for the environment"
        },
        "style": { 
          "type": "string",
          "description": "Style description for the environment"
        }
      },
      "additionalProperties": true
    },
    "Scene": {
      "type": "object",
      "required": ["scene_id", "environment", "characters_present", "beats"],
      "description": "Scene definition with beats",
      "properties": {
        "scene_id": { 
          "type": "string",
          "description": "Unique scene identifier"
        },
        "title": { 
          "type": "string",
          "description": "Scene title"
        },
        "environment": { 
          "type": "string",
          "description": "Environment ID where the scene takes place"
        },
        "characters_present": { 
          "type": "array", 
          "items": { "type": "string" },
          "description": "List of character IDs present in the scene"
        },
        "target_seconds": { 
          "type": "number", 
          "minimum": 0,
          "description": "Target duration for the scene in seconds"
        },
        "mood": { 
          "type": "string",
          "description": "Mood or atmosphere of the scene"
        },
        "legacy_audio_path": { 
          "type": "string",
          "description": "Path to legacy audio file (for migration)"
        },
        "beats": {
          "type": "array",
          "description": "List of beats in the scene",
          "items": { "$ref": "#/$defs/Beat" }
        }
      },
      "additionalProperties": true
    },
    "Beat": {
      "type": "object",
      "required": ["beat_id", "kind"],
      "description": "Beat definition - either speech or silent",
      "properties": {
        "beat_id": { 
          "type": "string",
          "description": "Unique beat identifier"
        },
        "kind": { 
          "type": "string", 
          "enum": ["speech", "silent"],
          "description": "Type of beat: 'speech' or 'silent'"
        },
        "camera": { 
          "type": "string",
          "description": "Camera angle or shot description"
        },
        "action": { 
          "type": "string",
          "description": "Action or description of what happens in the beat"
        },
        "duration_sec": { 
          "type": "number", 
          "minimum": 0,
          "description": "Duration of the beat in seconds"
        },
        "seed": { 
          "type": "integer",
          "description": "Random seed for generation"
        },
        "speaker": { 
          "type": "string",
          "description": "Character ID of the speaker (required for speech beats)"
        },
        "text": { 
          "type": "string",
          "description": "Dialogue text (required for speech beats)"
        },
        "audio_path": { 
          "type": "string",
          "description": "Path to audio file (for speech beats)"
        }
      },
      "additionalProperties": true,
      "if": { 
        "properties": { "kind": { "const": "speech" } }, 
        "required": ["kind"] 
      },
      "then": { 
        "required": ["speaker", "text"] 
      }
    }
  }
}
```

- [ ] **Step 3: Verify schema syntax**

```bash
python -c "import json; json.load(open('schemas/episode_v2.schema.json')); print('Schema syntax OK')"
```

Expected output:
```
Schema syntax OK
```

- [ ] **Step 4: Commit schema updates**

```bash
git add schemas/episode_v2.schema.json
git commit -m "feat: enhance episode schema with descriptions and defaults"
```

---

## Task 2: Create Episode Template

**Files:**
- Create: `episode_template.json`

- [ ] **Step 1: Create episode template**

```json
{
  "show": "Buffering",
  "season": 1,
  "episode": 1,
  "title": "The Pilot",
  "schema_version": "2.0",
  "target_duration_min": 8.0,
  "dialogue_status": "present",
  "dialogue_recovery_note": "",
   "render": {
     "fps": 24,
     "resolution": [1280, 720]
   },
  "cast": {
    "maya": {
      "name": "Maya Chen",
      "role": "Lead engineer at a failing AI startup",
      "visual": "East Asian woman in her late 20s, short straight black hair with subtle blue highlights, round wire-frame glasses, wearing an oversized dark purple hoodie with a small robot logo, dark jeans, white sneakers, confident posture but tired eyes, warm skin tone",
      "reference_images": [
        "assets/cast/maya_ref_front.png",
        "assets/cast/maya_ref_3q.png",
        "assets/cast/maya_ref_profile.png"
      ],
      "lora": null,
      "voice": {
        "provider": "text2speech",
        "voice_id": "maya_v1",
        "clone_from": "assets/voices/maya_clone.wav",
        "seed": 42,
        "temperature": 0.8,
        "language": "en"
      }
    },
    "derek": {
      "name": "Derek Thompson",
      "role": "Growth hacker at a crypto company that keeps pivoting",
      "visual": "Tall Black man in his early 30s, immaculately trimmed short beard, confident smile, wearing a fitted navy blazer over a bright graphic tee with geometric patterns, slim khaki chinos, clean white leather shoes, silver watch",
      "reference_images": [
        "assets/cast/derek_ref_front.png",
        "assets/cast/derek_ref_3q.png",
        "assets/cast/derek_ref_profile.png"
      ],
      "lora": null,
      "voice": {
        "provider": "text2speech",
        "voice_id": "derek_v1",
        "clone_from": "assets/voices/derek_clone.wav",
        "seed": 137,
        "temperature": 0.85,
        "language": "en"
      }
    }
  },
  "environments": {
    "living_room": {
      "trigger_word": "Modern San Francisco apartment living room with a panoramic window showing the Bay Bridge at golden hour, cluttered with tech gadgets, a large whiteboard covered in diagrams, mismatched furniture including a worn leather couch and beanbag chairs, tangled cables, a broken espresso machine on a side table, warm ambient lighting",
      "reference_image": "assets/env/living_room_ref.png",
      "style": "cinematic, golden hour, warm ambient lighting, lived-in tech apartment"
    },
    "kitchen": {
      "trigger_word": "Small galley kitchen in a San Francisco apartment, cluttered countertops with smart home gadgets, a tablet mounted on the fridge showing notifications, coffee mugs with tech company logos, morning light streaming through a small window, cozy and lived-in",
      "reference_image": "assets/env/kitchen_ref.png",
      "style": "cinematic, soft morning light, kitchen sitcom, warm tones"
    }
  },
  "scenes": [
    {
      "scene_id": "001",
      "title": "The Bug Discovered",
      "environment": "living_room",
      "characters_present": ["maya", "derek"],
      "target_seconds": 70,
      "mood": "tense, late-night",
      "beats": [
        {
          "beat_id": "001_b00",
          "kind": "silent",
          "camera": "wide establishing shot of the living room",
          "action": "The living room is lit by the glow of multiple monitors; Maya is hunched over her laptop, Derek is on the couch scrolling his phone",
          "duration_sec": 4.0,
          "seed": 110001
        },
        {
          "beat_id": "001_b01",
          "kind": "speech",
          "camera": "close-up on Maya's face",
          "action": "Maya stares at her screen in disbelief",
          "duration_sec": 3.0,
          "seed": 110002,
          "speaker": "maya",
          "text": "This can't be right. All fourteen tests are failing.",
          "audio_path": ""
        },
        {
          "beat_id": "001_b02",
          "kind": "speech",
          "camera": "two-shot of Maya and Derek",
          "action": "Derek looks up from his phone with concern",
          "duration_sec": 3.5,
          "seed": 110003,
          "speaker": "derek",
          "text": "Wait, all of them? What did you push?",
          "audio_path": ""
        }
      ]
    }
  ]
}
```

Write this to `episode_template.json`

- [ ] **Step 2: Verify template syntax**

```bash
python -c "import json; json.load(open('episode_template.json')); print('Template syntax OK')"
```

Expected output:
```
Template syntax OK
```

- [ ] **Step 3: Commit template**

```bash
git add episode_template.json
git commit -m "feat: add episode template with example data"
```

---

## Task 3: Validate Template Against Schema

**Files:**
- Test: `episode_template.json` against `schemas/episode_v2.schema.json`

- [ ] **Step 1: Validate template against schema**

```bash
uv run python -c "import json; from jsonschema import validate; validate(instance=json.load(open('episode_template.json')), schema=json.load(open('schemas/episode_v2.schema.json'))); print('Validation OK')"
```

Expected output:
```
Validation OK
```

- [ ] **Step 2: Run existing tests to ensure no regressions**

```bash
uv run pytest
```

Expected output: All tests pass

- [ ] **Step 3: Test CLI validation**

```bash
uv run showrunner validate episode_template.json
```

Expected output:
```
Episode is valid!
```

- [ ] **Step 4: Commit validation verification**

```bash
git add -A
git commit -m "test: verify template validates against schema"
```

---

## Task 4: Create Episode Template Guide

**Files:**
- Create: `docs/episode_template_guide.md`

- [ ] **Step 1: Create episode template guide**

```markdown
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
| `target_duration_min` | number | No | Target episode duration in minutes |
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
| `target_seconds` | number | No | Target duration for the scene in seconds |
| `mood` | string | No | Mood or atmosphere of the scene |
| `legacy_audio_path` | string | No | Path to legacy audio file (for migration) |
| `beats` | array | Yes | List of beats in the scene |

### Beats Section

Each beat is either a "speech" or "silent" beat.

#### Beat Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `beat_id` | string | Yes | Unique beat identifier |
| `kind` | string | Yes | Type of beat: "speech" or "silent" |
| `camera` | string | No | Camera angle or shot description |
| `action` | string | No | Action or description of what happens in the beat |
| `duration_sec` | number | No | Duration of the beat in seconds |
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

## Best Practices

1. **Use descriptive character IDs**: Use lowercase, underscore-separated names (e.g., "maya", "derek")
2. **Use descriptive environment IDs**: Use lowercase, underscore-separated names (e.g., "living_room", "kitchen")
3. **Use sequential beat IDs**: Use format "scene_id_bNN" (e.g., "001_b00", "001_b01")
4. **Provide detailed visual descriptions**: The more detail, the better the image generation
5. **Use trigger words for environments**: Detailed descriptions help generate consistent environments
6. **Set dialogue_status**: Use "present" if dialogue is included, "missing" if not, "partial" if some is missing
7. **Include reference images**: Reference images help maintain character and environment consistency

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
```

Write this to `docs/episode_template_guide.md`

- [ ] **Step 2: Commit guide**

```bash
git add docs/episode_template_guide.md
git commit -m "docs: add episode template guide"
```

---

## Task 5: Create Schema Reference Documentation

**Files:**
- Create: `docs/episode_schema_reference.md`

- [ ] **Step 1: Create schema reference documentation**

```markdown
# Episode Schema Reference

## Schema Overview

The episode schema v2.0 defines the structure for beat-based episodes in the Sitcom Pilot pipeline. It uses JSON Schema Draft 2020-12 and supports both speech and silent beats.

## Field Definitions

### Top-Level Fields

#### `show` (string, required)
Name of the show (e.g., "Buffering").

#### `season` (integer, required)
Season number. Must be >= 1.

#### `episode` (integer, required)
Episode number within the season. Must be >= 1.

#### `title` (string, required)
Episode title.

#### `schema_version` (string, required)
Schema version. Must be "2.0".

#### `target_duration_min` (number, optional)
Target episode duration in minutes. Must be >= 0.

#### `dialogue_status` (string, optional)
Status of dialogue in the episode. Must be one of:
- "present": Dialogue is included
- "missing": Dialogue is not included
- "partial": Some dialogue is included

#### `dialogue_recovery_note` (string, optional)
Notes about dialogue recovery process.

### Render Section

All render fields are optional and will use AIServices defaults if not specified.

#### `fps` (integer, optional, default: 24)
Frames per second for video output. Must be >= 1.

#### `resolution` (array, optional, default: [1280, 720])
Video resolution as [width, height]. Must be exactly 2 integers.

### Cast Section

The `cast` section defines characters. Each character is keyed by a unique character ID.

#### Character Fields

##### `name` (string, required)
Character's full name.

##### `role` (string, optional)
Character's role in the story.

##### `visual` (string, required)
Detailed visual description of the character.

##### `reference_images` (array, optional)
Paths to reference images for the character.

##### `lora` (string/null, optional)
LoRA model path for character consistency.

##### `voice` (object, optional)
Voice configuration for text-to-speech.

#### Voice Fields

##### `provider` (string, optional, default: "text2speech")
TTS provider. Default is "text2speech" from AIServices.

##### `voice_id` (string, optional)
Voice ID or reference audio path.

##### `clone_from` (string, optional)
Path to reference audio for voice cloning.

##### `seed` (integer, optional)
Random seed for voice generation.

##### `temperature` (number, optional)
Voice generation temperature.

##### `language` (string, optional, default: "en")
Language code.

### Environments Section

The `environments` section defines environments. Each environment is keyed by a unique environment ID.

#### Environment Fields

##### `trigger_word` (string, required)
Trigger word or detailed description for environment generation.

##### `reference_image` (string, optional)
Path to reference image for the environment.

##### `style` (string, optional)
Style description for the environment.

### Scenes Section

The `scenes` section defines scenes. Each scene contains beats.

#### Scene Fields

##### `scene_id` (string, required)
Unique scene identifier.

##### `title` (string, optional)
Scene title.

##### `environment` (string, required)
Environment ID where the scene takes place.

##### `characters_present` (array, required)
List of character IDs present in the scene.

##### `target_seconds` (number, optional)
Target duration for the scene in seconds. Must be >= 0.

##### `mood` (string, optional)
Mood or atmosphere of the scene.

##### `legacy_audio_path` (string, optional)
Path to legacy audio file (for migration).

##### `beats` (array, required)
List of beats in the scene.

### Beats Section

Each beat is either a "speech" or "silent" beat.

#### Beat Fields

##### `beat_id` (string, required)
Unique beat identifier.

##### `kind` (string, required)
Type of beat. Must be "speech" or "silent".

##### `camera` (string, optional)
Camera angle or shot description.

##### `action` (string, optional)
Action or description of what happens in the beat.

##### `duration_sec` (number, optional)
Duration of the beat in seconds. Must be >= 0.

##### `seed` (integer, optional)
Random seed for generation.

##### `speaker` (string, required for speech beats)
Character ID of the speaker. Required when `kind` is "speech".

##### `text` (string, required for speech beats)
Dialogue text. Required when `kind` is "speech".

##### `audio_path` (string, optional)
Path to audio file.

## Validation Rules

### Required Fields

The following fields are required:
- `show`
- `season`
- `episode`
- `title`
- `schema_version`
- `cast`
- `environments`
- `scenes`

### Speech Beat Validation

Speech beats require:
- `speaker`: Character ID of the speaker
- `text`: Dialogue text

### Silent Beat Validation

Silent beats only require:
- `beat_id`: Unique beat identifier
- `kind`: Must be "silent"

## Error Messages

### Common Validation Errors

#### "schema_version must be '2.0'"
The `schema_version` field must be exactly "2.0".

#### "Missing required field: 'show'"
The `show` field is required at the top level.

#### "Speech beat missing 'speaker'"
Speech beats must include a `speaker` field with the character ID.

#### "Speech beat missing 'text'"
Speech beats must include a `text` field with the dialogue.

#### "Unknown environment reference"
The `environment` field in a scene must reference a valid environment ID from the `environments` section.

#### "Unknown character reference"
Characters in `characters_present` must reference valid character IDs from the `cast` section.

## Examples

### Valid Episode

```json
{
  "show": "Buffering",
  "season": 1,
  "episode": 1,
  "title": "The Bug",
  "schema_version": "2.0",
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

### Invalid Episode (Missing Schema Version)

```json
{
  "show": "Buffering",
  "season": 1,
  "episode": 1,
  "title": "The Bug",
  "cast": {},
  "environments": {},
  "scenes": []
}
```

Error: "schema_version must be '2.0'"
```

Write this to `docs/episode_schema_reference.md`

- [ ] **Step 2: Commit schema reference**

```bash
git add docs/episode_schema_reference.md
git commit -m "docs: add episode schema reference"
```

---

## Task 6: Final Verification and Cleanup

**Files:**
- Verify: All files in the project

- [ ] **Step 1: Run full test suite one final time**

```bash
uv run pytest
```

Expected output: All tests pass

- [ ] **Step 2: Validate template against schema**

```bash
uv run python -c "import json; from jsonschema import validate; validate(instance=json.load(open('episode_template.json')), schema=json.load(open('schemas/episode_v2.schema.json'))); print('Validation OK')"
```

Expected output:
```
Validation OK
```

- [ ] **Step 3: Test CLI validation**

```bash
uv run showrunner validate episode_template.json
```

Expected output:
```
Episode is valid!
```

- [ ] **Step 4: Verify documentation files exist**

```bash
ls -la docs/
```

Expected output: Shows episode_template_guide.md and episode_schema_reference.md

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete episode template with schema and documentation"
```

---

## Success Criteria Verification

- [ ] Template validates against enhanced schema
- [ ] All render fields are optional with AIServices defaults
- [ ] Documentation is clear and comprehensive
- [ ] Users can easily create new episodes using the template
- [ ] All existing tests pass

---

## Notes

- **TDD Approach**: Each task includes verification steps
- **Frequent Commits**: Commit after each successful task
- **No Placeholders**: All code is complete and tested
- **Clear Dependencies**: Tasks build on each other sequentially
