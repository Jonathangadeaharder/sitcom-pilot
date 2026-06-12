# TDD-003: Full `aiservices` platform clone nested inside the content project

- Status: Fixed (verified 2026-06-12: aiservices/ directory deleted)
- Date: 2026-06-11
- Category: Unnecessary complexity / Architecture
- Severity: High

## Finding

`aiservices/` is a complete nested git repo (own `.git`, own CI + release workflows, own uv workspace, 11 packages: text2image, text2speech, image2video, video2audio, audio2subtitle, subtitle-filter, subtitle-translate, text2video, image2image, text2audio, video2subtitle; ~240 test functions). It is correctly gitignored (`.gitignore` lines 7, 21–22 — "Local aiservices symlink") and `pyproject.toml` line 34 consumes it properly as `aiservices-core = { git = "https://github.com/.../AIServices.git" }` — so the working tree hosts a full second platform that the repo doesn't actually depend on locally.

## Why it matters

This is exactly the layer scriptforge is supposed to own. The local clone invites editing the dependency in place (changes invisible to the locked git ref), confuses tooling/search, and blurs the platform/content boundary the GarageBand vision requires.

## Recommendation

Develop AIServices in its own checkout outside this repo; if a local override is genuinely needed, use an explicit `[tool.uv.sources] path=` override documented in the README rather than a shadow clone.
