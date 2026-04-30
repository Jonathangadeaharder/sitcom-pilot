from __future__ import annotations

from pathlib import Path

import pytest

from sitcom_pilot.beat_prompts import build_beat_prompt, build_scene_prompt
from sitcom_pilot.cast_manifest import CastManifest, CharacterProfile, CharacterRef
from sitcom_pilot.continuity import SimilarityResult, batch_check
from sitcom_pilot.determinism import compute_manifest_hash
from sitcom_pilot.loader import EpisodeLoader

EPISODE_02 = Path(__file__).resolve().parent.parent / "episode_02.json"


@pytest.fixture
def episode_02():
    return EpisodeLoader().load(EPISODE_02)


@pytest.fixture
def manifest_02(episode_02):
    m = CastManifest()
    for slug, char in episode_02.cast.items():
        m.add(
            CharacterProfile(
                name=char.name,
                slug=slug,
                visual=char.visual,
                role=getattr(char, "role", ""),
                refs=CharacterRef(),
            )
        )
    return m


def _collect_beat_prompts(episode, manifest):
    prompts = []
    for scene in episode.scenes:
        for beat in scene.beats:
            p = build_beat_prompt(beat, scene, episode, manifest, episode_id="002")
            prompts.append({"beat_id": beat.beat_id, "prompt": p})
    return prompts


class TestGoldenFrameDeterminism:
    def test_prompts_deterministic(self, episode_02, manifest_02):
        run_a = _collect_beat_prompts(episode_02, manifest_02)
        run_b = _collect_beat_prompts(episode_02, manifest_02)
        for a, b in zip(run_a, run_b):
            assert a["prompt"] == b["prompt"], f"Determinism failure at {a['beat_id']}"

    def test_manifest_hash_deterministic(self, episode_02, manifest_02):
        h1 = compute_manifest_hash(episode_02, manifest_02)
        h2 = compute_manifest_hash(episode_02, manifest_02)
        assert h1 == h2
        assert len(h1) == 64

    def test_manifest_hash_changes_on_edit(self, episode_02, manifest_02):
        h1 = compute_manifest_hash(episode_02, manifest_02)
        manifest_02.add(CharacterProfile(name="Extra", slug="extra", visual="tall person"))
        h2 = compute_manifest_hash(episode_02, manifest_02)
        assert h1 != h2

    def test_scene_prompts_nonempty(self, episode_02, manifest_02):
        for scene in episode_02.scenes:
            prompt = build_scene_prompt(scene, episode_02, manifest_02, episode_id="002")
            assert len(prompt) > 0, f"Empty prompt for scene {scene.scene_id}"

    def test_beat_prompts_contain_quality_tag(self, episode_02, manifest_02):
        prompts = _collect_beat_prompts(episode_02, manifest_02)
        for entry in prompts:
            assert "cinematic" in entry["prompt"].lower(), f"Missing quality in {entry['beat_id']}"

    def test_beat_prompts_unique_across_beats(self, episode_02, manifest_02):
        prompts = _collect_beat_prompts(episode_02, manifest_02)
        texts = [p["prompt"] for p in prompts]
        assert len(texts) == len(set(texts)), "Duplicate prompts detected"

    def test_ssim_identical_images_pass(self, tmp_path):
        from PIL import Image

        img = Image.new("L", (64, 64), color=128)
        a = tmp_path / "a.png"
        b = tmp_path / "b.png"
        img.save(a)
        img.save(b)
        from sitcom_pilot.continuity import check_continuity

        result = check_continuity(a, b, threshold=0.9)
        assert result.passed

    def test_ssim_different_images_fail(self, tmp_path):
        from PIL import Image

        a = tmp_path / "a.png"
        b = tmp_path / "b.png"
        Image.new("L", (64, 64), color=0).save(a)
        Image.new("L", (64, 64), color=255).save(b)
        from sitcom_pilot.continuity import check_continuity

        result = check_continuity(a, b, threshold=0.9)
        assert not result.passed

    def test_batch_check_returns_results(self, tmp_path):
        from PIL import Image

        pairs = []
        for i in range(3):
            a = tmp_path / f"a{i}.png"
            b = tmp_path / f"b{i}.png"
            Image.new("L", (32, 32), color=i * 80).save(a)
            Image.new("L", (32, 32), color=i * 80).save(b)
            pairs.append((a, b))
        results = batch_check(pairs)
        assert len(results) == 3
        assert all(isinstance(r, SimilarityResult) for r in results)

    def test_episode_02_all_beats_have_seeds(self, episode_02):
        for scene in episode_02.scenes:
            for beat in scene.beats:
                assert beat.seed != 0, f"Beat {beat.beat_id} has zero seed"

    def test_episode_02_beat_ids_unique(self, episode_02):
        ids = []
        for scene in episode_02.scenes:
            for beat in scene.beats:
                ids.append(beat.beat_id)
        assert len(ids) == len(set(ids)), "Duplicate beat IDs"
