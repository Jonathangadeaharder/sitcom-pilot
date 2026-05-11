# Golden-Frame Fixtures + SSIM Regression

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store reference golden frame images in the repo and detect SSIM regression when rendered output diverges from them.

**Architecture:** Add a `GoldenFrameRegistry` to `continuity.py` that maps beat IDs to golden frame paths + SSIM thresholds. Generate golden frames as deterministic synthetic images stored in `tests/fixtures/golden_frames/`. Tests render beats via `scene_render.plan_beats` pipeline and compare output frames against golden references.

**Tech Stack:** scikit-image (SSIM), Pillow (image I/O), pytest (fixtures/tests)

---

### Task 1: Create golden frame fixture images

**Files:**
- Create: `tests/fixtures/golden_frames/S02_beat01.png` (solid-gray 512x512)
- Create: `tests/fixtures/golden_frames/S02_beat02.png` (solid-light 512x512)
- Create: `tests/fixtures/golden_frames/S02_beat03.png` (solid-dark 512x512)
- Create: `tests/fixtures/golden_frames/S02_beat04.png` (checkerboard 512x512)
- Script: Run a one-shot generator at the end

- [ ] **Step 1: Generate fixture images**

```bash
mkdir -p tests/fixtures/golden_frames
```

- [ ] **Step 2: Run generator script**

```python
from PIL import Image
import numpy as np

base = Path("tests/fixtures/golden_frames")

# S02_beat01 — solid gray (128)
Image.fromarray(np.full((512, 512, 3), 128, dtype=np.uint8)).save(base / "S02_beat01.png")

# S02_beat02 — solid light (200)
Image.fromarray(np.full((512, 512, 3), 200, dtype=np.uint8)).save(base / "S02_beat02.png")

# S02_beat03 — solid dark (50)
Image.fromarray(np.full((512, 512, 3), 50, dtype=np.uint8)).save(base / "S02_beat03.png")

# S02_beat04 — checkerboard
checker = np.zeros((512, 512, 3), dtype=np.uint8)
checker[:256, :256] = [255, 255, 255]
checker[256:, 256:] = [255, 255, 255]
Image.fromarray(checker).save(base / "S02_beat04.png")
```

- [ ] **Step 3: Verify files exist**

Run: `ls -la tests/fixtures/golden_frames/`
Expected: 4 PNG files, each ~2-3 KB (solid color compresses well)

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/golden_frames/
git commit -m "feat: add golden frame fixture images for E8.2"
```

---

### Task 2: Add GoldenFrameRegistry to continuity module

**Files:**
- Modify: `src/showrunner/continuity.py`
- Test: `tests/test_continuity.py`

- [ ] **Step 1: Write the failing test for GoldenFrameRegistry**

```python
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
        img = Image.new("RGB", (512, 512), color=0)  # differs from gray golden frame
        gen_path = tmp_path / "gen.png"
        img.save(gen_path)
        result = golden_registry.check("S02_beat01", generated=gen_path)
        assert not result.passed

    def test_list_beats(self, golden_registry):
        golden_registry.register("a", threshold=0.7)
        golden_registry.register("b", threshold=0.8)
        assert set(golden_registry.list_beats()) == {"a", "b"}

    def test_check_all_returns_all_results(self, golden_registry, tmp_path):
        golden_registry.register("a", threshold=0.1)
        golden_registry.register("b", threshold=0.1)
        results = golden_registry.check_all()
        assert len(results) == 2

    def test_no_beats_registered_raises(self, golden_registry):
        import pytest
        with pytest.raises(RuntimeError, match="No golden frames registered"):
            golden_registry.check_all()

    def test_check_uses_default_generated_path(self, golden_registry, tmp_path):
        golden_registry.register("S02_beat01", threshold=0.8)
        gen_dir = tmp_path / "rendered"
        gen_dir.mkdir()
        img = Image.fromarray(np.full((512, 512, 3), 128, dtype=np.uint8))
        img.save(gen_dir / "S02_beat01.png")
        golden_registry.generated_dir = gen_dir
        result = golden_registry.check("S02_beat01")
        assert result.passed

    def test_check_all_with_all_pass(self, golden_registry, tmp_path):
        golden_registry.register("a", threshold=0.1)
        golden_registry.register("b", threshold=0.1)
        results = golden_registry.check_all()
        assert all(r.passed for r in results)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_continuity.py::TestGoldenFrameRegistry -v 2>&1 | head -40`
Expected: All 8 tests fail with `GoldenFrameRegistry` / `register` / `check` not defined

- [ ] **Step 3: Add GoldenFrameRegistry to continuity.py**

```python
class GoldenFrameRegistry:
    def __init__(self, fixtures_dir: Path | str = "", generated_dir: Path | str = ""):
        self._entries: dict[str, _GoldenEntry] = {}
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else Path("tests/fixtures/golden_frames")
        self.generated_dir = Path(generated_dir) if generated_dir else Path()

    def register(self, beat_id: str, *, threshold: float = 0.7) -> None:
        self._entries[beat_id] = _GoldenEntry(beat_id=beat_id, threshold=threshold)

    def check(self, beat_id: str, *, generated: Path | None = None) -> SimilarityResult:
        entry = self._entries.get(beat_id)
        if entry is None:
            raise KeyError(f"Beat '{beat_id}' not registered. Available: {list(self._entries)}")
        ref = self.fixtures_dir / f"{beat_id}.png"
        gen = generated or (self.generated_dir / f"{beat_id}.png")
        return check_continuity(ref, gen, threshold=entry.threshold)

    def check_all(self) -> list[SimilarityResult]:
        if not self._entries:
            raise RuntimeError("No golden frames registered")
        return [self.check(bid) for bid in self._entries]

    def list_beats(self) -> list[str]:
        return list(self._entries)
```

Also add `_GoldenEntry` dataclass:

```python
@dataclass(frozen=True)
class _GoldenEntry:
    beat_id: str
    threshold: float
```

- [ ] **Step 4: Add fixture conftest imports**

Add to `tests/conftest.py`:
```python
@pytest.fixture
def golden_registry():
    from showrunner.continuity import GoldenFrameRegistry
    from pathlib import Path
    base = Path(__file__).resolve().parent
    return GoldenFrameRegistry(
        fixtures_dir=base / "fixtures" / "golden_frames",
    )
```

- [ ] **Step 5: Add numpy/PIL imports to test file**

```python
import numpy as np
from PIL import Image
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_continuity.py::TestGoldenFrameRegistry -v`
Expected: All 8 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/showrunner/continuity.py tests/test_continuity.py tests/conftest.py
git commit -m "feat: add GoldenFrameRegistry for SSIM regression detection"
```

---

### Task 3: Golden frame regression test for episode_02

**Files:**
- Modify: `tests/test_golden_frames.py`

- [ ] **Step 1: Write the failing test**

```python
def test_golden_registry_fixtures_exist(episode_02):
    from showrunner.continuity import GoldenFrameRegistry
    registry = GoldenFrameRegistry()
    assert registry.fixtures_dir.exists()
    golden_files = list(registry.fixtures_dir.glob("*.png"))
    assert len(golden_files) >= 4

def test_ssim_golden_vs_identical_passes(episode_02, golden_registry):
    golden_registry.register("S02_beat01", threshold=0.9)
    result = golden_registry.check("S02_beat01")
    assert result.passed
    assert result.ssim_score >= 0.9

def test_ssim_golden_vs_altered_fails(golden_registry, tmp_path):
    golden_registry.register("S02_beat01", threshold=0.99)
    inverted = tmp_path / "S02_beat01.png"
    from PIL import Image
    import numpy as np
    img = Image.fromarray(np.full((512, 512, 3), 255, dtype=np.uint8))
    img.save(inverted)
    result = golden_registry.check("S02_beat01", generated=inverted)
    assert not result.passed
    assert result.ssim_score < 0.99

def test_check_all_against_copy(golden_registry, tmp_path):
    golden_registry.register("S02_beat01", threshold=0.5)
    golden_registry.register("S02_beat02", threshold=0.5)
    golden_registry.register("S02_beat03", threshold=0.5)
    golden_registry.register("S02_beat04", threshold=0.5)
    results = golden_registry.check_all()
    assert len(results) == 4
    assert all(r.passed for r in results)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_golden_frames.py::test_ssim_golden_vs_identical_passes tests/test_golden_frames.py::test_ssim_golden_vs_altered_fails tests/test_golden_frames.py::test_check_all_against_copy tests/test_golden_frames.py::test_golden_registry_fixtures_exist -v`
Expected: Tests fail because golden_registry fixture not available in this file

- [ ] **Step 3: Fix — add golden_registry fixture import to test_golden_frames.py**

The `golden_registry` fixture is already in conftest.py, but `test_golden_frames.py` doesn't import `golden_registry`. Pytest discovers fixtures from conftest.py automatically. The test should work once we add the correct directory path.

Actually let me check — the conftest.py fixture creates `GoldenFrameRegistry(fixtures_dir=...)` pointing to `tests/fixtures/golden_frames/`. This should work.

Let me verify the tests actually fail and fix as needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_golden_frames.py::test_golden_registry_fixtures_exist tests/test_golden_frames.py::test_ssim_golden_vs_identical_passes tests/test_golden_frames.py::test_ssim_golden_vs_altered_fails tests/test_golden_frames.py::test_check_all_against_copy -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_golden_frames.py
git commit -m "feat: add golden frame regression tests for episode 02"
```

---

### Task 4: Run full lint/typecheck/test suite

- [ ] **Step 1: Run all tests**

Run: `uv run pytest -v 2>&1 | tail -30`
Expected: All tests pass (0 failed)

- [ ] **Step 2: Run ruff check**

Run: `uvx ruff check`
Expected: No linting errors (0)

- [ ] **Step 3: Run ruff format check**

Run: `uvx ruff format --check`
Expected: No formatting issues

- [ ] **Step 4: Run pyright**

Run: `uvx pyright`
Expected: No type errors

- [ ] **Step 5: Fix any issues found in steps 1-4, re-run until clean**

```bash
uv run pytest -v && uvx ruff check && uvx ruff format --check && uvx pyright
```

Expected: All exit 0

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: fix lint/type/test issues for golden frame fixtures"
```

---

### Task 5: Push and create PR

- [ ] **Step 1: Push branch**

```bash
git push origin chore/sitp-75-golden-frames
```

- [ ] **Step 2: Create PR**

```bash
gh pr create \
  --title "[SITP-75] E8.2 — Golden-frame fixtures + SSIM regression" \
  --body "## Summary

- Add golden frame fixture images (4 reference PNGs) in \`tests/fixtures/golden_frames/\`
- Add \`GoldenFrameRegistry\` to \`continuity.py\` for SSIM regression detection
- Add 12 new tests covering registry registration, check, check_all, regression detection, and fixture existence
- All existing tests continue to pass

Closes #97" \
  --base main
```

- [ ] **Step 3: Return PR URL**

Run: `gh pr view --json url --jq '.url'`
