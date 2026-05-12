from __future__ import annotations

from pathlib import Path

from showrunner.determinism import compute_manifest_hash, compute_run_fingerprint, resolve_seed


class TestResolveSeed:
    def test_deterministic(self):
        a = resolve_seed("S01E02", "001", "001_b01", 42)
        b = resolve_seed("S01E02", "001", "001_b01", 42)
        assert a == b

    def test_different_components_different_seed(self):
        a = resolve_seed("S01E02", "001", "001_b01", 0)
        b = resolve_seed("S01E02", "002", "002_b01", 0)
        assert a != b

    def test_base_seed_affects_result(self):
        a = resolve_seed("S01E02", "001", "001_b01", 0)
        b = resolve_seed("S01E02", "001", "001_b01", 99)
        assert a != b

    def test_returns_positive_int(self):
        seed = resolve_seed("x", "y", "z", 0)
        assert isinstance(seed, int)
        assert seed > 0

    def test_empty_components_still_work(self):
        seed = resolve_seed("", "", "", 0)
        assert isinstance(seed, int)


class TestComputeManifestHash:
    def test_deterministic(self, episode_manifest):
        episode, manifest = episode_manifest
        h1 = compute_manifest_hash(episode, manifest)
        h2 = compute_manifest_hash(episode, manifest)
        assert h1 == h2

    def test_hex_length(self, episode_manifest):
        episode, manifest = episode_manifest
        h = compute_manifest_hash(episode, manifest)
        assert len(h) == 64

    def test_different_episode_title_changes_hash(self, episode_manifest):
        from showrunner.loader import EpisodeData

        episode, manifest = episode_manifest
        h1 = compute_manifest_hash(episode, manifest)
        modified = EpisodeData(
            title="Different Title",
            cast=episode.cast,
            environments=episode.environments,
            scenes=episode.scenes,
            show=episode.show,
            season=episode.season,
            episode_number=episode.episode_number,
        )
        h2 = compute_manifest_hash(modified, manifest)
        assert h1 != h2


class TestComputeRunFingerprint:
    def test_empty_paths(self):
        h = compute_run_fingerprint([])
        assert len(h) == 64

    def test_nonexistent_paths_skipped(self):
        h = compute_run_fingerprint([Path("/nonexistent/file.txt")])
        assert len(h) == 64

    def test_deterministic_with_files(self, tmp_path):
        a = tmp_path / "a.txt"
        a.write_text("hello")
        h1 = compute_run_fingerprint([a])
        h2 = compute_run_fingerprint([a])
        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("hello")
        b.write_text("world")
        h1 = compute_run_fingerprint([a])
        h2 = compute_run_fingerprint([b])
        assert h1 != h2

    def test_order_independent(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("x")
        b.write_text("y")
        h1 = compute_run_fingerprint([a, b])
        h2 = compute_run_fingerprint([b, a])
        assert h1 == h2
