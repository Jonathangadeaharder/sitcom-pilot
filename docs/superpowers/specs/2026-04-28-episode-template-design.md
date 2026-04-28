# Episode Template Design

**Date:** 2026-04-28  
**Epic:** E1 - Script Authoring  
**Item:** E1.1 - Author episode_template.json  
**Status:** Design Complete - Ready for Implementation

---

## 1. Overview

### 1.1 Problem Statement

The Sitcom Pilot project needs a canonical episode template that:
- Defines the beat-based episode schema structure
- Provides example data for users to understand the format
- Integrates with AIServices packages for model configuration
- Includes comprehensive documentation for users

### 1.2 Goals

1. **Create Template**: Provide a working template that users can copy and modify
2. **Enhance Schema**: Update the JSON Schema with better documentation and defaults
3. **Documentation**: Create comprehensive documentation for using the template
4. **AIServices Integration**: Use AIServices package names instead of custom provider names

### 1.3 Success Criteria

- Template validates against the enhanced schema
- All render fields are optional with AIServices defaults
- Documentation is clear and comprehensive
- Users can easily create new episodes using the template

---

## 2. Template Structure

### 2.1 Final Template Structure

```
episode_template.json
├── show (string, required)
├── season (integer, required)
├── episode (integer, required)
├── title (string, required)
├── schema_version (string: "2.0", required)
├── target_duration_min (number, optional)
├── dialogue_status (string: "present" | "missing" | "partial", optional)
├── dialogue_recovery_note (string, optional)
├── render (object, all optional)
│   ├── fps (integer, default: 24)
│   └── resolution (array of 2 integers, default: [1280, 720])
├── cast (object of CharacterV2, required)
│   └── character_id (object)
│       ├── name (string, required)
│       ├── role (string, optional)
│       ├── visual (string, required)
│       ├── reference_images (array of strings, optional)
│       ├── lora (string or null, optional)
│       └── voice (object, optional)
│           ├── provider (string, optional, default: "text2speech")
│           ├── voice_id (string, optional)
│           ├── clone_from (string, optional)
│           ├── seed (integer, optional)
│           ├── temperature (number, optional)
│           └── language (string, optional, default: "en")
├── environments (object of EnvironmentV2, required)
│   └── environment_id (object)
│       ├── trigger_word (string, required)
│       ├── reference_image (string, optional)
│       └── style (string, optional)
└── scenes (array of Scene, required)
    └── scene (object)
        ├── scene_id (string, required)
        ├── title (string, optional)
        ├── environment (string, required)
        ├── characters_present (array of strings, required)
        ├── target_seconds (number, optional)
        ├── mood (string, optional)
        ├── legacy_audio_path (string, optional)
        └── beats (array of Beat, required)
            └── beat (object)
                ├── beat_id (string, required)
                ├── kind (string: "speech" | "silent", required)
                ├── camera (string, optional)
                ├── action (string, optional)
                ├── duration_sec (number, optional)
                ├── seed (integer, optional)
                ├── speaker (string, required for speech)
                ├── text (string, required for speech)
                └── audio_path (string, optional)
```

### 2.2 Key Design Decisions

1. **Minimal render section**: Only fps, resolution, and timing fields
2. **All render fields optional**: AIServices provides defaults
3. **Voice provider defaults to "text2speech"**: Uses AIServices package name
4. **Removed image/video/subtitle providers from render**: Inferred from AIServices
5. **All render fields have defaults**: Users can omit the entire render section

---

## 3. Template Content

### 3.1 Final Template Content

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

### 3.2 Key Changes from Current Episodes

1. **Minimal render section**: Only 5 fields instead of 14
2. **Voice provider**: "text2speech" instead of "mlx-audio"
3. **Removed image/video/subtitle providers**: Inferred from AIServices
4. **All render fields optional**: Can be omitted for defaults

---

## 4. JSON Schema Enhancements

### 4.1 Enhanced Schema Features

1. **Added descriptions** to all fields
2. **Added default values** for render fields
3. **Updated voice provider default** to "text2speech"
4. **Removed image/video/subtitle providers** from render section
5. **Added "additionalProperties": false** to render section to prevent extra fields

### 4.2 Schema Validation Rules

- **Required fields**: show, season, episode, title, schema_version, cast, environments, scenes
- **Render section**: All fields optional with defaults
- **Voice provider**: Defaults to "text2speech"
- **Speech beats**: Require speaker and text fields
- **Silent beats**: Only require beat_id and kind

---

## 5. Documentation Structure

### 5.1 Documentation Files

```
docs/
├── episode_template_guide.md
└── episode_schema_reference.md
```

### 5.2 episode_template_guide.md

1. **Introduction**: What the template is and how to use it
2. **Quick Start**: Copy and modify the template
3. **Field Reference**: Detailed explanation of each field
4. **Examples**: Complete examples for different scenarios
5. **Best Practices**: Tips for creating episodes

### 5.3 episode_schema_reference.md

1. **Schema Overview**: JSON Schema structure
2. **Field Definitions**: All fields with types and constraints
3. **Validation Rules**: How to validate episode files
4. **Error Messages**: Common validation errors and fixes

---

## 6. File Locations

### 6.1 File Structure

```
sitcom_pilot/
├── episode_template.json          # New template file
├── schemas/
│   └── episode_v2.schema.json     # Enhanced schema (update existing)
└── docs/
    ├── episode_template_guide.md  # New documentation
    └── episode_schema_reference.md # New documentation
```

### 6.2 Key Points

1. **episode_template.json**: New file at project root
2. **episode_v2.schema.json**: Update existing schema file
3. **Documentation**: New files in docs/ directory

---

## 7. AIServices Integration

### 7.1 Available AIServices Packages

1. **text2image**: ComfyUI with Flux2 workflow
2. **text2speech**: Fish S2 Pro MLX
3. **speech2text**: MLX Whisper
4. **image2image**: ComfyUI with Flux2 image-edit workflow
5. **text2video**: MLX with ltx-2-mlx implementation

### 7.2 Provider Mapping

| Current Provider | AIServices Package |
|------------------|-------------------|
| mlx-flux | text2image |
| mlx-flux-img2img | image2image |
| mlx-ltx | text2video |
| mlx-audio | text2speech |
| mlx-whisper | speech2text |

### 7.3 Default Models

- **text2image**: Flux2 (via ComfyUI)
- **text2speech**: Fish S2 Pro MLX
- **speech2text**: mlx-community/whisper-large-v3-mlx
- **image2image**: Flux2 image-edit (via ComfyUI)
- **text2video**: ltx-2-mlx

---

## 8. Implementation Plan

### 8.1 Tasks

1. **Create episode_template.json**: New template file with example data
2. **Update episode_v2.schema.json**: Enhance schema with descriptions and defaults
3. **Create documentation files**: episode_template_guide.md and episode_schema_reference.md
4. **Validate template**: Ensure template validates against enhanced schema
5. **Test integration**: Verify template works with existing pipeline

### 8.2 Success Metrics

- Template validates against enhanced schema
- All render fields are optional with AIServices defaults
- Documentation is clear and comprehensive
- Users can easily create new episodes using the template

---

## 9. Approval

**Design Approved:** 2026-04-28  
**Approved By:** User  
**Next Step:** Implementation Planning

---

## Appendix A: File Checklist

### Files to Create
- [ ] `episode_template.json`
- [ ] `docs/episode_template_guide.md`
- [ ] `docs/episode_schema_reference.md`

### Files to Modify
- [ ] `schemas/episode_v2.schema.json`

---

## Appendix B: Commands Reference

### Validation Commands
```bash
# Validate template against schema
uv run python -c "import json; from jsonschema import validate; validate(instance=json.load(open('episode_template.json')), schema=json.load(open('schemas/episode_v2.schema.json')))"

# Run existing tests
uv run pytest

# Check CLI
uv run sitcom-pilot validate episode_template.json
```
