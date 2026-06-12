# Golden Frame Fixtures

The PNG files in this directory are reference "golden frames" used by rendering tests.
They were generated from `episode_02.json` via the showrunner render pipeline.

To regenerate:

```bash
uv run showrunner render --episode tests/fixtures/episode_02.json --output-dir tests/fixtures/golden_frames
```
