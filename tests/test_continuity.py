from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from sitcom_pilot.continuity import SimilarityResult, batch_check, check_continuity


class TestSimilarityResult:
    def test_passed(self):
        r = SimilarityResult("a.png", "b.png", 0.85, True)
        assert r.passed
        assert r.ssim_score == 0.85


class TestCheckContinuity:
    @patch("sitcom_pilot.continuity._compute_ssim", return_value=0.9)
    @patch("sitcom_pilot.continuity._load_image_gray")
    def test_passes_above_threshold(self, mock_load, mock_ssim):
        mock_load.return_value = MagicMock()
        result = check_continuity(Path("ref.png"), Path("gen.png"), threshold=0.7)
        assert result.passed
        assert result.ssim_score == 0.9

    @patch("sitcom_pilot.continuity._compute_ssim", return_value=0.3)
    @patch("sitcom_pilot.continuity._load_image_gray")
    def test_fails_below_threshold(self, mock_load, mock_ssim):
        mock_load.return_value = MagicMock()
        result = check_continuity(Path("ref.png"), Path("gen.png"), threshold=0.7)
        assert not result.passed


class TestBatchCheck:
    @patch("sitcom_pilot.continuity.check_continuity")
    def test_batch(self, mock_check):
        mock_check.return_value = SimilarityResult("a", "b", 0.8, True)
        results = batch_check([(Path("a"), Path("b"))])
        assert len(results) == 1
        assert results[0].passed
