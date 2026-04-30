import sys
from pathlib import Path

import pytest

from sitcom_pilot.cast_manifest import CastManifest, CharacterProfile, CharacterRef
from sitcom_pilot.loader import EpisodeLoader

sys.path  # ensure imported before use below

_LEGACY_DIR = str(Path(__file__).resolve().parent.parent / "legacy")
if _LEGACY_DIR not in sys.path:
    sys.path.insert(0, _LEGACY_DIR)

collect_ignore = []
if "mutmut" in sys.modules:
    collect_ignore = ["test_cli.py", "test_e2e.py", "test_episode_01.py"]

_EPISODE_02 = str(Path(__file__).resolve().parent.parent / "episode_02.json")


@pytest.fixture
def episode_manifest():
    loader = EpisodeLoader()
    episode = loader.load(Path(_EPISODE_02))
    manifest = CastManifest()
    for slug, char in episode.cast.items():
        manifest.add(
            CharacterProfile(
                name=char.name,
                slug=slug,
                visual=char.visual,
                refs=CharacterRef(),
            )
        )
    return episode, manifest
