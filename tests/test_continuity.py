from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from showrunner.continuity import (
    SimilarityResult,
    _ssim_fallback,
    batch_check,
    check_continuity,
)


class TestSimilarityResult:
    def test_passed(self):
        r = SimilarityResult("a.png", "b.png", 0.85, True)
        assert r.passed
        assert r.ssim_score == pytest.approx(0.85)


class TestCheckContinuity:
    def test_passes_above_threshold(self, tmp_path):
        img = Image.new("L", (64, 64), 128)
        ref = tmp_path / "ref.png"
        gen = tmp_path / "gen.png"
        img.save(ref)
        img.save(gen)
        result = check_continuity(ref, gen, threshold=0.7)
        assert result.passed
        assert result.ssim_score == pytest.approx(1.0)

    def test_fails_below_threshold(self, tmp_path):
        ref_img = Image.new("L", (64, 64), 0)
        gen_img = Image.new("L", (64, 64), 255)
        ref = tmp_path / "ref.png"
        gen = tmp_path / "gen.png"
        ref_img.save(ref)
        gen_img.save(gen)
        result = check_continuity(ref, gen, threshold=0.99)
        assert not result.passed

    def test_passes_at_exact_threshold(self, tmp_path):
        img = Image.new("L", (64, 64), 128)
        ref = tmp_path / "ref.png"
        gen = tmp_path / "gen.png"
        img.save(ref)
        img.save(gen)
        result = check_continuity(ref, gen, threshold=1.0)
        assert result.passed
        assert result.ssim_score == pytest.approx(1.0)

    def test_invalid_threshold_raises(self):
        import pytest

        with pytest.raises(ValueError, match="threshold"):
            check_continuity(Path("a.png"), Path("b.png"), threshold=1.5)

    def test_negative_threshold_raises(self):
        import pytest

        with pytest.raises(ValueError, match="threshold"):
            check_continuity(Path("a.png"), Path("b.png"), threshold=-0.1)


class TestSsimFallback:
    def test_identical_images(self):
        img = Image.new("L", (10, 10), 0)
        assert _ssim_fallback(img, img) == pytest.approx(1.0)

    def test_different_images(self):
        img_a = Image.new("L", (10, 10), 0)
        img_b = Image.new("L", (10, 10), 255)
        assert _ssim_fallback(img_a, img_b) == pytest.approx(0.0)

    def test_different_sizes_returns_zero(self):
        img_a = Image.new("L", (10, 10))
        img_b = Image.new("L", (20, 20))
        assert _ssim_fallback(img_a, img_b) == pytest.approx(0.0)


class TestBatchCheck:
    def test_batch(self, tmp_path):
        img = Image.new("L", (64, 64), 128)
        ref = tmp_path / "ref.png"
        gen = tmp_path / "gen.png"
        img.save(ref)
        img.save(gen)
        results = batch_check([(ref, gen)])
        assert len(results) == 1
        assert results[0].passed

    def test_exception_caught_oserror(self):
        results = batch_check([(Path("nonexistent_a.png"), Path("nonexistent_b.png"))])
        assert results == []

    def test_exception_caught_valueerror(self, tmp_path):
        img = Image.new("L", (64, 64), 128)
        ref = tmp_path / "ref.png"
        img.save(ref)
        results = batch_check([(ref, ref)], threshold=1.5)
        assert results == []


class TestLoadImageGray:
    def test_context_manager_usage(self, tmp_path):
        img_path = tmp_path / "test.png"
        Image.new("RGB", (10, 10), "red").save(img_path)

        from showrunner.continuity import _load_image_gray

        result = _load_image_gray(img_path)
        assert result.mode == "L"
        assert result.size == (10, 10)
        assert result.tobytes() is not None


@pytest.fixture
def golden_registry():
    from showrunner.continuity import GoldenFrameRegistry

    return GoldenFrameRegistry()


class TestGoldenFrameRegistry:
    def test_register_and_check(self, golden_registry):
        golden_registry.register("S02_beat01", threshold=0.8)
        result = golden_registry.check("S02_beat01")
        assert result.passed

    def test_unregistered_beat_raises(self, golden_registry):
        import pytest

        with pytest.raises(KeyError, match="S02_beat99"):
            golden_registry.check("S02_beat99")

    def test_ssim_regression_detected(self, golden_registry, tmp_path):
        golden_registry.register("S02_beat01", threshold=0.99)
        img = Image.new("RGB", (512, 512), color=0)
        gen_path = tmp_path / "gen.png"
        img.save(gen_path)
        result = golden_registry.check("S02_beat01", generated=gen_path)
        assert not result.passed

    def test_list_beats(self, golden_registry):
        golden_registry.register("a", threshold=0.7)
        golden_registry.register("b", threshold=0.8)
        assert set(golden_registry.list_beats()) == {"a", "b"}

    def test_check_all_returns_all_results(self, golden_registry, tmp_path):
        golden_registry.register("S02_beat01", threshold=0.1)
        golden_registry.register("S02_beat04", threshold=0.1)
        results = golden_registry.check_all(generated_dir=golden_registry.fixtures_dir)
        assert len(results) == 2

    def test_no_beats_registered_raises(self, golden_registry):
        import pytest

        with pytest.raises(RuntimeError, match="No golden frames registered"):
            golden_registry.check_all()

    def test_check_with_custom_generated(self, golden_registry, tmp_path):
        golden_registry.register("S02_beat01", threshold=0.8)
        gen_dir = tmp_path / "rendered"
        gen_dir.mkdir()
        from shutil import copy2

        copy2(golden_registry.fixtures_dir / "S02_beat01.png", gen_dir / "S02_beat01.png")
        result = golden_registry.check("S02_beat01", generated=gen_dir / "S02_beat01.png")
        assert result.passed

    def test_check_all_with_all_pass(self, golden_registry):
        golden_registry.register("S02_beat01", threshold=0.1)
        golden_registry.register("S02_beat02", threshold=0.1)
        results = golden_registry.check_all(generated_dir=golden_registry.fixtures_dir)
        assert all(r.passed for r in results)
