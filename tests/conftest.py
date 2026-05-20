import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from showrunner.assembler import EpisodeAssembler
from showrunner.cast_manifest import CastManifest, CharacterProfile, CharacterRef
from showrunner.loader import EpisodeLoader

collect_ignore = []
if "mutmut" in sys.modules:
    collect_ignore = ["test_e2e.py", "test_episode_01.py"]

_EPISODE_02 = str(Path(__file__).resolve().parent.parent / "episode_02.json")


@pytest.fixture
def episode_manifest():
    loader = EpisodeLoader()
    episode = loader.load(Path(_EPISODE_02))
    manifest = CastManifest()
    for slug, char in episode.cast.items():
        refs = tuple(char.reference_images or ())
        manifest.add(
            CharacterProfile(
                name=char.name,
                slug=slug,
                visual=char.visual,
                refs=CharacterRef(
                    front=refs[0] if len(refs) > 0 else "",
                    three_quarter=refs[1] if len(refs) > 1 else "",
                    profile=refs[2] if len(refs) > 2 else "",
                    extra=refs[3:] if len(refs) > 3 else (),
                ),
                lora_path=char.lora,
                voice=char.voice,
            )
        )
    return episode, manifest


@pytest.fixture
def assembler(tmp_path):
    with patch.object(EpisodeAssembler, "_detect_videotoolbox", return_value=False):
        return EpisodeAssembler(output_dir=tmp_path / "output")


@pytest.fixture
def golden_registry():
    from showrunner.continuity import GoldenFrameRegistry

    base = Path(__file__).resolve().parent
    return GoldenFrameRegistry(
        fixtures_dir=base / "fixtures" / "golden_frames",
    )
