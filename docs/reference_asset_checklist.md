# Reference Asset Checklist

Canonical checklist of all reference assets required by episode scripts.

## Cast Reference Images

Per character: 3 angles (front, three-quarter, profile). Generated or sourced once, reused across episodes.

| Character | ID | Front | Three-Quarter | Profile | Status |
|-----------|-----|-------|---------------|---------|--------|
| Maya Chen | maya | assets/cast/maya_ref_front.png | assets/cast/maya_ref_3q.png | assets/cast/maya_ref_profile.png | pending |
| Derek Thompson | derek | assets/cast/derek_ref_front.png | assets/cast/derek_ref_3q.png | assets/cast/derek_ref_profile.png | pending |
| Priya Sharma | priya | assets/cast/priya_ref_front.png | assets/cast/priya_ref_3q.png | assets/cast/priya_ref_profile.png | pending |
| Finn O'Brien | finn | assets/cast/finn_ref_front.png | assets/cast/finn_ref_3q.png | assets/cast/finn_ref_profile.png | pending |

## Cast Voice Clones

Per character: 1 reference audio clip for TTS voice cloning.

| Character | ID | Clone Source | Status |
|-----------|-----|-------------|--------|
| Maya Chen | maya | assets/voices/maya_clone.wav | pending |
| Derek Thompson | derek | assets/voices/derek_clone.wav | pending |
| Priya Sharma | priya | assets/voices/priya_clone.wav | pending |
| Finn O'Brien | finn | assets/voices/finn_clone.wav | pending |

## Environment Reference Images

Per environment: 1 reference image establishing the scene.

| Environment | ID | Reference | Used In | Status |
|-------------|-----|-----------|---------|--------|
| Living Room | living_room | assets/env/living_room_ref.png | S1E1, S1E2 | pending |
| Kitchen | kitchen | assets/env/kitchen_ref.png | S1E1, S1E2 | pending |
| Maya's Desk | maya_desk | assets/env/maya_desk_ref.png | S1E1, S1E2 | pending |
| Hallway | hallway | assets/env/hallway_ref.png | S1E1 | pending |
| Rooftop | rooftop | assets/env/rooftop_ref.png | S1E1, S1E2 | pending |

## LoRA Models (Optional)

All characters currently have `lora: null`. LoRA fine-tuning per character is deferred to E4 (Character Continuity System).

## Summary

| Category | Total | Pending |
|----------|-------|---------|
| Cast images | 12 | 12 |
| Voice clones | 4 | 4 |
| Environment images | 5 | 5 |
| LoRA models | 0 | 0 |
| **Total** | **21** | **21** |

## Notes

- Character IDs must match across episode_01.json, episode_02.json, and the template.
- Reference images should be generated at 1024x1024 minimum using text2image.
- Voice clone clips should be 10-30 seconds of clean speech.
- Environment images should match the `trigger_word` and `style` fields exactly.
