---
id: ADR-005
kind: adr
title: Media Processing Architecture
status: accepted
date: 2026-05-17T00:00:00.000Z
authors: [Jonathan Gadea Harder]
reviewers: [Jonathan Gadea Harder]
tags: []
supersedes: []
superseded_by: []
depends_on: []
blocks: []
implements: []
related: []
external: []
project: sitcom-pilot
checksum: b64c4d01758b8c512f451c9c243ab0492e92d2fc026615163f03980001b1a365
---

**Deciders:** Project owner  
**Tags:** ffmpeg, media-pipeline, audio, video, assembly

---

## Context

The final output of the sitcom-pilot pipeline is an `.mp4` file with synchronized audio, captions, and a music bed. Each beat produces an independent image and optional audio file that must be assembled into a coherent video with consistent timing, transitions, and audio mixing.

## Decision

### FFmpeg-Centric Assembly

All post-render media processing uses FFmpeg subprocess calls. No Python media libraries (moviepy, opencv, etc.).

**Assembly pipeline:**

1. **concat_clips** — Concatenate beat video clips in order using FFmpeg's concat demuxer (avoids re-encoding). Produces `episode_raw.mp4`.
2. **generate_srt** — Create SRT subtitle track from speech beat text and timing data. Uses beat duration_sec for timing alignment.
3. **burn_in_captions** — Optional: burn SRT into video using FFmpeg subtitles filter. Produces `episode.mp4`.
4. **mux_audio** — Merge generated TTS audio tracks with beat video clips.
5. **mix_music_bed** — Layer a background music track under dialogue audio with ducking.

### Per-Beat Render Unit

Each beat is rendered independently:

```
text2image ─► keyframe.png
text2speech ─► dialogue.wav  (speech beats only)
image2video ─► beat.mp4      (keyframe + optional audio, animated)
```

- Image: `output/<run_id>/beats/<scene_id>/<beat_id>.png`
- Audio: `output/<run_id>/audio/<scene_id>/<beat_id>.wav`
- Video: `output/<run_id>/beats/<scene_id>/<beat_id>.mp4`

### Beat Clip Uniformization

All beat clips are normalized to the same FPS and resolution before assembly via `beat_clip_uniformiser.py`. This ensures consistent playback when concatenating clips that may have been rendered at slightly different settings.

### Audio Architecture

- **Speech beats:** TTS generates `.wav` files per beat. Duration derived from audio length (not fixed).
- **Silent beats:** No audio. Video runs for `duration_sec` at configured FPS.
- **Music bed:** Optional background track mixed via FFmpeg amix filter with volume ducking so dialogue stays audible.
- **Audio effects:** Each speech beat can specify `effect` (sighing, laughing, etc.) applied as post-processing.

### Output Structure

```
output/<run_id>/
  beats/<scene_id>/<beat_id>.png   # keyframe images
  beats/<scene_id>/<beat_id>.mp4   # video clips
  audio/<scene_id>/<beat_id>.wav   # TTS audio
  assembly/
    episode_raw.mp4                # concatenated video (no captions)
    episode.srt                    # subtitle track
    episode.mp4                    # final with captions burned in
  render_report.json               # per-scene timing and status
```

### Configuration

Per-episode render overrides in JSON (`render` block):
```json
"render": {
  "fps": 24,
  "resolution": [1280, 720]
}
```

Environment variables (prefix `SITCOM_`):
- `SITCOM_OUTPUT_DIR` — root output directory (default: `output`)
- `SITCOM_RUN_ID` — run identifier (default: auto-generated timestamp)
- `SITCOM_COOLDOWN_SECONDS` — pause between shots (default: 0.0)
- `SITCOM_MAX_CRASH_RETRIES` — retries on render failure (default: 3)

## Consequences

**Positive:**
- FFmpeg concat demuxer avoids re-encoding, preserving quality and speeding assembly
- Per-beat independence enables parallel rendering, cache invalidation, and partial re-renders
- SRT generation from beat data is lossless and editable
- Uniformization step prevents format mismatches during concat

**Negative:**
- FFmpeg command construction is error-prone (filter graph syntax, stream specifiers)
- Concat demuxer requires exact codec/format match across all clips (uniformization is mandatory)
- Music bed ducking requires tuning the ducking threshold per episode

**Neutral:**
- No Python media library dependency reduces surface area but shifts complexity to FFmpeg CLI args
- Audio effects are placeholders; actual effect processing (sigh detection, laughter overlay) is future work
