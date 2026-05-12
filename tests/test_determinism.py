from __future__ import annotations

from pathlib import Path

import pytest

from showrunner.determinism import (
    DeterminismConfig,
    SeedStrategy,
    _file_hash,
    compute_manifest_hash,
    compute_manifest_hash_from_dict,
    compute_run_fingerprint,
    derive_seed,
    resolve_seed,
)


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


class TestSeedStrategy:
    def test_requires_episode_id(self):
        with pytest.raises(ValueError, match="^episode_id must be non-empty$"):
            SeedStrategy("")

    def test_default_base_seed_is_zero(self):
        s = SeedStrategy("S01E02")
        assert s.base_seed == 0

    def test_for_beat_deterministic(self):
        s = SeedStrategy("S01E02", base_seed=42)
        a = s.for_beat("001", "001_b01", 10)
        b = s.for_beat("001", "001_b01", 10)
        assert a == b

    def test_for_beat_different_beats_different_seed(self):
        s = SeedStrategy("S01E02")
        a = s.for_beat("001", "001_b01", 10)
        b = s.for_beat("002", "002_b01", 20)
        assert a != b

    def test_for_beat_uses_beat_seed(self):
        s = SeedStrategy("S01E02")
        a = s.for_beat("001", "001_b01", 10)
        b = s.for_beat("001", "001_b01", 99)
        assert a != b

    def test_for_beat_zero_beat_seed_still_works(self):
        s = SeedStrategy("S01E02", base_seed=42)
        a = s.for_beat("001", "001_b01", 0)
        b = s.for_beat("001", "001_b01", 0)
        assert a == b
        assert isinstance(a, int)
        assert a > 0

    def test_for_beat_integrates_base_seed(self):
        s0 = SeedStrategy("S01E02", base_seed=0)
        s1 = SeedStrategy("S01E02", base_seed=99)
        a = s0.for_beat("001", "001_b01", 10)
        b = s1.for_beat("001", "001_b01", 10)
        assert a != b

    def test_for_scene_deterministic(self):
        s = SeedStrategy("S01E02", base_seed=7)
        a = s.for_scene("001")
        b = s.for_scene("001")
        assert a == b

    def test_for_scene_different_scenes_different(self):
        s = SeedStrategy("S01E02")
        assert s.for_scene("001") != s.for_scene("002")

    def test_for_episode_deterministic(self):
        s = SeedStrategy("S01E02", base_seed=1)
        a = s.for_episode()
        b = s.for_episode()
        assert a == b

    def test_for_episode_changes_with_base_seed(self):
        s0 = SeedStrategy("S01E02", base_seed=0)
        s1 = SeedStrategy("S01E02", base_seed=1)
        assert s0.for_episode() != s1.for_episode()

    def test_with_base_seed_immutable(self):
        s = SeedStrategy("S01E02", base_seed=0)
        s2 = s.with_base_seed(99)
        assert s.base_seed == 0
        assert s2.base_seed == 99
        assert s2.episode_id == s.episode_id

    def test_beat_scene_episode_seeds_differ(self):
        s = SeedStrategy("S01E02", base_seed=42)
        beat = s.for_beat("001", "001_b01", 0)
        scene = s.for_scene("001")
        ep = s.for_episode()
        assert len({beat, scene, ep}) == 3

    def test_properties(self):
        s = SeedStrategy("S01E02", base_seed=42)
        assert s.episode_id == "S01E02"
        assert s.base_seed == 42


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

    def test_render_config_changes_hash(self, episode_manifest):
        episode, manifest = episode_manifest
        h1 = compute_manifest_hash(episode, manifest)
        h2 = compute_manifest_hash(episode, manifest, render_config={"fps": 30})
        assert h1 != h2

    def test_render_config_none_same_as_empty(self, episode_manifest):
        episode, manifest = episode_manifest
        h1 = compute_manifest_hash(episode, manifest, render_config=None)
        h2 = compute_manifest_hash(episode, manifest, render_config={})
        assert h1 == h2

    def test_episode_path_missing_skipped(self, episode_manifest):
        episode, manifest = episode_manifest
        h = compute_manifest_hash(episode, manifest, episode_path="/nonexistent/path.json")
        assert len(h) == 64

    def test_file_hash_returns_empty_for_missing_file(self):
        assert _file_hash("/nonexistent/path.json") == ""

    def test_episode_path_default_is_empty(self, episode_manifest):
        episode, manifest = episode_manifest
        h_default = compute_manifest_hash(episode, manifest)
        h_explicit = compute_manifest_hash(episode, manifest, episode_path="")
        assert h_default == h_explicit
        episode, manifest = episode_manifest
        h1 = compute_manifest_hash(episode, manifest, episode_path="")
        h2 = compute_manifest_hash(episode, manifest, episode_path="")
        assert h1 == h2

    def test_episode_path_with_file_changes_hash(self, episode_manifest, tmp_path):
        episode, manifest = episode_manifest
        ep = tmp_path / "episode.json"
        ep.write_text('{"title": "test"}')
        h1 = compute_manifest_hash(episode, manifest)
        h2 = compute_manifest_hash(episode, manifest, episode_path=str(ep))
        assert h1 != h2

    def test_different_manifest_content_changes_hash(self, episode_manifest):
        episode, manifest = episode_manifest
        from showrunner.cast_manifest import CharacterProfile, CharacterRef

        h1 = compute_manifest_hash(episode, manifest)
        manifest.add(
            CharacterProfile(name="Extra", slug="extra", visual="extra person", refs=CharacterRef())
        )
        h2 = compute_manifest_hash(episode, manifest)
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

    def test_continues_after_nonexistent_path(self, tmp_path):
        a = tmp_path / "a.txt"
        a.write_text("content")
        h = compute_run_fingerprint([Path("/nonexistent/file.txt"), a])
        assert len(h) == 64
        assert h == compute_run_fingerprint([a])

    def test_does_not_break_on_nonexistent_path(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("first")
        b.write_text("second")
        all_files = compute_run_fingerprint([a, Path("/nonexistent/file.txt"), b])
        middle_skipped = compute_run_fingerprint([a, b])
        assert all_files == middle_skipped


class TestDeterminismConfig:
    def test_create_with_seed_only(self):
        cfg = DeterminismConfig(seed=42)
        assert cfg.seed == 42
        assert cfg.deterministic is False

    def test_create_with_deterministic(self):
        cfg = DeterminismConfig(seed=99, deterministic=True)
        assert cfg.seed == 99
        assert cfg.deterministic is True

    def test_frozen(self):
        cfg = DeterminismConfig(seed=1)
        with pytest.raises(AttributeError):
            cfg.seed = 2  # type: ignore  # testing frozen constraint

    def test_different_seeds_not_equal(self):
        a = DeterminismConfig(seed=1)
        b = DeterminismConfig(seed=2)
        assert a != b


class TestDeriveSeed:
    def test_reproducible(self):
        h = "abcdef1234567890"
        assert derive_seed(h) == derive_seed(h)

    def test_returns_positive_int(self):
        h = "0000000000000000"
        s = derive_seed(h)
        assert isinstance(s, int)
        assert s >= 0

    def test_different_hashes_give_different_seeds(self):
        a = derive_seed("aaaaaaaaaaaaaaaa")
        b = derive_seed("bbbbbbbbbbbbbbbb")
        assert a != b

    def test_first_8_hex_digits_used(self):
        h = "deadbeefcafebabe"
        assert derive_seed(h) == int("deadbeef", 16)

    def test_short_hash_works(self):
        h = "ff"
        assert derive_seed(h) == 255


class TestComputeManifestHashFromDict:
    def test_deterministic(self):
        ep = {"title": "Test", "scenes": []}
        h1 = compute_manifest_hash_from_dict(ep)
        h2 = compute_manifest_hash_from_dict(ep)
        assert h1 == h2

    def test_different_episodes_different_hash(self):
        a = compute_manifest_hash_from_dict({"title": "Alpha"})
        b = compute_manifest_hash_from_dict({"title": "Beta"})
        assert a != b

    def test_key_order_independent(self):
        ep1 = {"title": "X", "scenes": []}
        ep2 = {"scenes": [], "title": "X"}
        assert compute_manifest_hash_from_dict(ep1) == compute_manifest_hash_from_dict(ep2)

    def test_returns_hex_string(self):
        h = compute_manifest_hash_from_dict({"title": "T"})
        assert isinstance(h, str)
        assert len(h) == 64
        int(h, 16)

    def test_empty_dict_works(self):
        h = compute_manifest_hash_from_dict({})
        assert len(h) == 64
