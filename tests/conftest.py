import sys
from pathlib import Path

# Add legacy/ to sys.path so tests can import legacy root modules
# (e.g. voice_generator_v3, utterance_pipeline, pipeline)
_LEGACY_DIR = str(Path(__file__).resolve().parent.parent / "legacy")
if _LEGACY_DIR not in sys.path:
    sys.path.insert(0, _LEGACY_DIR)

collect_ignore = []
if "mutmut" in sys.modules:
    collect_ignore = ["test_cli.py", "test_e2e.py", "test_episode_01.py"]
