# Deleted Legacy Pipeline

The executable `legacy/retired/` tree was removed. Git history is the archive;
retired pipeline code must not live in the working tree or import active
`src/showrunner` modules.

## Migration Map

| Deleted file                  | Modern replacement                    |
|-------------------------------|---------------------------------------|
| `retired/pipeline.py`         | `src/showrunner/scene_render.py`      |
| `retired/orchestrator.py`     | `src/showrunner/cli/main.py`          |
| `retired/assembler.py`        | `src/showrunner/assembler.py`         |

Workflow templates `flux2_t2i_shot.json` and `flux2_i2i_refine.json` were
deleted alongside `flux2_generator.py`.

All other deleted files (`voice_generator.py`, `script.py`,
`ltx_video_generator.py`, `setup_voices.py`, `flux2_generator.py`,
`video_generator_v2.py`, `utterance_pipeline.py`, `sitcom_generator.py`,
`voice_generator_v3.py`, `main.py`) have no direct replacement.
