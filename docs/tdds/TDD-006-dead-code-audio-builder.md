# TDD-006: `audio_builder.py` is dead code with a live 25-test suite

- Status: Fixed in working tree
- Date: 2026-06-11
- Category: Dead code / Meaningless tests
- Severity: High

## Finding

`src/showrunner/audio_builder.py` (218 lines: `build_shot_audio`, `synthesize_dialogue_line`, `concatenate_wavs`, 50-entry `VALID_EMOTIONS`) has ZERO callers in `src/` (verified by grep). Its only importers are `legacy/retired/pipeline.py` and `tests/test_audio_builder.py` (25 test functions). The live v2 pipeline uses `AIServicesClient.text2speech()`.

## Why it matters

~200 LOC of v1 platform code plus ~250 LOC of tests that validate code no user can reach — pure maintenance weight and coverage inflation, plus standing confusion about which TTS path is real.

## Recommendation

Delete `audio_builder.py` and `tests/test_audio_builder.py`. If the emotion/tone vocabularies matter, they belong with the `text2speech` provider in AIServices.
