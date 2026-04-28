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

#### `pause_between_speech_sec` (number, optional, default: 0.4)
Pause between speech beats in seconds. Must be >= 0.

#### `pause_between_scenes_sec` (number, optional, default: 1.2)
Pause between scenes in seconds. Must be >= 0.

#### `default_silent_beat_duration` (number, optional, default: 3.0)
Default duration for silent beats in seconds. Must be >= 0.

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
