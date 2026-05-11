"""One-shot generator for golden frame fixture images."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

base = Path(__file__).resolve().parent

Image.fromarray(np.full((512, 512, 3), 128, dtype=np.uint8)).save(base / "S02_beat01.png")
Image.fromarray(np.full((512, 512, 3), 200, dtype=np.uint8)).save(base / "S02_beat02.png")
Image.fromarray(np.full((512, 512, 3), 50, dtype=np.uint8)).save(base / "S02_beat03.png")

checker = np.zeros((512, 512, 3), dtype=np.uint8)
checker[:256, :256] = [255, 255, 255]
checker[256:, 256:] = [255, 255, 255]
Image.fromarray(checker).save(base / "S02_beat04.png")

print("Generated 4 golden frame fixtures")
