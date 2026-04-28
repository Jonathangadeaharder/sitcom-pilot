from pathlib import Path
from sitcom_pilot.loader import EpisodeLoader


def test_episode_01_loads():
    path = Path(__file__).parent.parent / "episode_01.json"
    loader = EpisodeLoader()
    episode = loader.load(path)
    assert episode.title == "The Bug"
    assert episode.schema_version == "2.0"
    assert len(episode.scenes) == 6
    assert "maya" in episode.cast
    assert "derek" in episode.cast
    # v2.0 uses beats, not shots
    total_beats = sum(len(s.beats) for s in episode.scenes)
    assert total_beats > 0


def test_episode_01_cast_has_v2_fields():
    path = Path(__file__).parent.parent / "episode_01.json"
    episode = EpisodeLoader().load(path)
    maya = episode.cast["maya"]
    assert maya.name == "Maya Chen"
    assert "East Asian" in maya.visual
    assert maya.voice is not None
    assert maya.voice.voice_id == "maya_v1"


def test_episode_01_environments_have_trigger_words():
    path = Path(__file__).parent.parent / "episode_01.json"
    episode = EpisodeLoader().load(path)
    assert "living_room" in episode.environments
    env = episode.environments["living_room"]
    assert "San Francisco" in env.trigger_word


def test_episode_01_beats_have_correct_kinds():
    path = Path(__file__).parent.parent / "episode_01.json"
    episode = EpisodeLoader().load(path)
    # All beats in episode_01 are silent (no dialogue recovered yet)
    for scene in episode.scenes:
        for beat in scene.beats:
            assert beat.kind in ("speech", "silent")
            assert beat.beat_id
            assert beat.seed > 0


def test_episode_01_render_config_loaded():
    path = Path(__file__).parent.parent / "episode_01.json"
    episode = EpisodeLoader().load(path)
    assert episode.render_config.get("fps") == 24
    assert episode.render_config.get("image_provider") == "mlx-flux"
