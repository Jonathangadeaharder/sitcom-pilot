from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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
        assert r.ssim_score == 0.85


class TestCheckContinuity:
    @patch("showrunner.continuity._compute_ssim", return_value=0.9)
    @patch("showrunner.continuity._load_image_gray")
    def test_passes_above_threshold(self, mock_load, mock_ssim):
        mock_load.return_value = MagicMock()
        result = check_continuity(Path("ref.png"), Path("gen.png"), threshold=0.7)
        assert result.passed
        assert result.ssim_score == 0.9

    @patch("showrunner.continuity._compute_ssim", return_value=0.3)
    @patch("showrunner.continuity._load_image_gray")
    def test_fails_below_threshold(self, mock_load, mock_ssim):
        mock_load.return_value = MagicMock()
        result = check_continuity(Path("ref.png"), Path("gen.png"), threshold=0.7)
        assert not result.passed

    @patch("showrunner.continuity._compute_ssim", return_value=0.7)
    @patch("showrunner.continuity._load_image_gray")
    def test_passes_at_exact_threshold(self, mock_load, mock_ssim):
        mock_load.return_value = MagicMock()
        result = check_continuity(Path("ref.png"), Path("gen.png"), threshold=0.7)
        assert result.passed
        assert result.ssim_score == 0.7

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
        img = MagicMock()
        img.tobytes.return_value = b"\x00\x01\x02"
        assert _ssim_fallback(img, img) == 1.0

    def test_different_images(self):
        img_a = MagicMock()
        img_a.tobytes.return_value = b"\x00\x01\x02"
        img_b = MagicMock()
        img_b.tobytes.return_value = b"\x03\x04\x05"
        assert _ssim_fallback(img_a, img_b) == 0.0

    def test_different_sizes_returns_zero(self):
        img_a = MagicMock()
        img_a.size = (10, 10)
        img_b = MagicMock()
        img_b.size = (20, 20)
        assert _ssim_fallback(img_a, img_b) == 0.0


class TestBatchCheck:
    @patch("showrunner.continuity.check_continuity")
    def test_batch(self, mock_check):
        mock_check.return_value = SimilarityResult("a", "b", 0.8, True)
        results = batch_check([(Path("a"), Path("b"))])
        assert len(results) == 1
        assert results[0].passed

    @patch("showrunner.continuity._load_image_gray", side_effect=OSError("missing"))
    def test_oserror_caught(self, mock_load):
        results = batch_check([(Path("a"), Path("b"))])
        assert results == []

    @patch("showrunner.continuity._load_image_gray", side_effect=ValueError("bad"))
    def test_valueerror_caught(self, mock_load):
        results = batch_check([(Path("a"), Path("b"))])
        assert results == []

    @patch("showrunner.continuity._load_image_gray", side_effect=ImportError("nope"))
    def test_importerror_caught(self, mock_load):
        results = batch_check([(Path("a"), Path("b"))])
        assert results == []

    @patch("showrunner.continuity._load_image_gray", side_effect=RuntimeError("boom"))
    def test_runtimeerror_propagates(self, mock_load):
        import pytest

        with pytest.raises(RuntimeError, match="boom"):
            batch_check([(Path("a"), Path("b"))])


class TestLoadImageGray:
    def test_context_manager_usage(self, tmp_path):
        pytest = __import__("pytest")
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        img_path = tmp_path / "test.png"
        Image.new("RGB", (10, 10), "red").save(img_path)

        from showrunner.continuity import _load_image_gray

        result = _load_image_gray(img_path)
        assert result.mode == "L"
        assert result.size == (10, 10)
        assert result.tobytes() is not None
