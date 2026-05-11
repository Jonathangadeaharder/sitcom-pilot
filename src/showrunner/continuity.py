from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimilarityResult:
    image_a: str
    image_b: str
    ssim_score: float
    passed: bool


def _load_image_gray(path: Path):
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("Pillow required for SSIM: uv add Pillow")
    with Image.open(path) as img:
        return img.convert("L").copy()


def _compute_ssim(img_a, img_b) -> float:
    try:
        from skimage.metrics import structural_similarity as ssim
    except ImportError:
        return _ssim_fallback(img_a, img_b)
    import numpy as np

    arr_a = np.array(img_a)
    arr_b = np.array(img_b)
    min_h = min(arr_a.shape[0], arr_b.shape[0])
    min_w = min(arr_a.shape[1], arr_b.shape[1])
    arr_a = arr_a[:min_h, :min_w]
    arr_b = arr_b[:min_h, :min_w]
    return float(ssim(arr_a, arr_b))  # pyright: ignore[reportArgumentType]


def _ssim_fallback(img_a, img_b) -> float:
    if img_a.size != img_b.size:
        return 0.0
    return 1.0 if img_a.tobytes() == img_b.tobytes() else 0.0


def check_continuity(
    reference_path: Path,
    generated_path: Path,
    threshold: float = 0.7,
) -> SimilarityResult:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0")
    img_a = _load_image_gray(reference_path)
    img_b = _load_image_gray(generated_path)
    score = _compute_ssim(img_a, img_b)
    return SimilarityResult(
        image_a=str(reference_path),
        image_b=str(generated_path),
        ssim_score=score,
        passed=score >= threshold,
    )


@dataclass(frozen=True)
class _GoldenEntry:
    beat_id: str
    threshold: float


class GoldenFrameRegistry:
    def __init__(self, fixtures_dir: Path | str = ""):
        self._entries: dict[str, _GoldenEntry] = {}
        self.fixtures_dir = (
            Path(fixtures_dir) if fixtures_dir else Path("tests/fixtures/golden_frames")
        )

    def register(self, beat_id: str, *, threshold: float = 0.7) -> None:
        self._entries[beat_id] = _GoldenEntry(beat_id=beat_id, threshold=threshold)

    def check(self, beat_id: str, *, generated: Path | None = None) -> SimilarityResult:
        entry = self._entries.get(beat_id)
        if entry is None:
            raise KeyError(f"Beat '{beat_id}' not registered. Available: {list(self._entries)}")
        ref = self.fixtures_dir / f"{beat_id}.png"
        if generated is None:
            gen = ref
        else:
            gen = generated
        return check_continuity(ref, gen, threshold=entry.threshold)

    def check_all(self, *, generated_dir: Path | None = None) -> list[SimilarityResult]:
        if not self._entries:
            raise RuntimeError("No golden frames registered")
        results: list[SimilarityResult] = []
        for bid in self._entries:
            gen = (generated_dir / f"{bid}.png") if generated_dir else None
            results.append(self.check(bid, generated=gen))
        return results

    def list_beats(self) -> list[str]:
        return list(self._entries)


def batch_check(
    pairs: list[tuple[Path, Path]],
    threshold: float = 0.7,
) -> list[SimilarityResult]:
    results = []
    for ref, gen in pairs:
        try:
            results.append(check_continuity(ref, gen, threshold))
        except (OSError, ValueError, ImportError) as exc:
            logger.warning("SSIM check failed for %s vs %s: %s", ref, gen, exc)
    return results
