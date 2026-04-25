from pathlib import Path
from orchestrator.loader import EpisodeLoader


def test_episode_01_loads():
    path = Path(__file__).parent.parent / "episode_01.json"
    loader = EpisodeLoader()
    episode = loader.load(path)
    assert episode.title
    assert len(episode.scenes) == 6
    assert "maya" in episode.cast
    assert "derek" in episode.cast
    total_shots = sum(len(s.shots) for s in episode.scenes)
    assert total_shots > 0
