# Retired Legacy Pipeline

All files previously in `legacy/` have been moved to `legacy/retired/`.
They are kept for historical reference only and must not be imported by any
active code under `src/`.

## Migration Map

| Retired file                  | Modern replacement                    |
|-------------------------------|---------------------------------------|
| `retired/pipeline.py`         | `src/sitcom_pilot/scene_render.py`    |
| `retired/orchestrator.py`     | `src/sitcom_pilot/cli/main.py`        |
| `retired/assembler.py`        | `src/sitcom_pilot/assembler.py`       |

Workflow templates `flux2_t2i_shot.json` and `flux2_i2i_refine.json` (in
`retired/workflows/`) have been retired alongside `flux2_generator.py`.

All other retired files (`voice_generator.py`, `script.py`,
`ltx_video_generator.py`, `setup_voices.py`, `flux2_generator.py`,
`video_generator_v2.py`, `utterance_pipeline.py`, `sitcom_generator.py`,
`voice_generator_v3.py`, `main.py`) have no direct replacement and are
retained as historical reference only.
