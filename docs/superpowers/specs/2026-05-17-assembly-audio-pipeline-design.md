---
id: SPEC-ASSEMBLY-AUD
kind: spec
title: Assembly & Audio Pipeline Design
status: draft
authors: []
reviewers: []
tags: []
supersedes: []
superseded_by: []
depends_on: []
blocks: []
implements: []
related: []
external: []
project: sitcom-pilot
checksum: 05f794fbda12163ea2b5dc73ef6ec56879fcad3787c747e8015c4dfd47308f3b
---

**Date:** 2026-05-17  

---

## 1. Overview

### 1.1 Problem Statement

After all beats are rendered as individual video clips (with optional audio), they must be concatenated into a single episode file with synchronized captions and a background music bed. FFmpeg handles the heavy lifting, but the pipeline must construct correct filter graphs, manage timing, and handle edge cases (silent beats, missing audio, variable durations).

### 1.2 Goals

1. **Lossless concat**: Join clips without re-encoding
2. **Accurate captions**: SRT aligned to beat timing
3. **Audio ducking**: Music bed lowers volume during dialogue
4. **SRT burn-in**: Optional hardcoded captions in output

### 1.3 Success Criteria

- 128-beat episode assembles in < 30 seconds
- SRT timestamps match beat durations within 100ms
- Audio ducking reduces music volume by -12dB during dialogue
- Same inputs produce bit-identical output (deterministic assembly)

---

## 2. Modules

### 2.1 `assembler.py`

Core assembly orchestration:

```python
class Assembler:
    def concat_clips(self, beat_paths: list[Path], output: Path) -> Path:
        """Concatenate beat clips using FFmpeg concat demuxer."""

    def generate_srt(self, beats: list[BeatJob], output: Path) -> Path:
        """Generate SRT subtitle file from beat text."""

    def burn_in_captions(self, video: Path, srt: Path, output: Path) -> Path:
        """Burn SRT into video using FFmpeg subtitles filter."""

    def mix_music_bed(self, video: Path, music: Path, output: Path,
                      duck_threshold: float = -12.0) -> Path:
        """Layer background music with dialogue ducking."""
```

### 2.2 `audio_builder.py`

Per-beat audio management:

```python
class AudioBuilder:
    def build_beat_audio(self, beat: BeatJob, tts_path: Path | None) -> Path:
        """Prepare audio for a single beat (TTS or silence)."""

    def apply_effect(self, audio: Path, effect: str) -> Path:
        """Apply voice effect (sigh, laugh, gasp)."""

    def get_duration(self, audio: Path) -> float:
        """Get audio file duration via ffprobe."""
```

### 2.3 `captions.py`

SRT generation:

```python
class CaptionGenerator:
    def generate_srt(self, beats: list[BeatJob]) -> str:
        """Generate SRT content from beat timing."""

    def align_timestamps(self, beats: list[BeatJob],
                         audio_durations: dict[str, float]) -> list[Caption]:
        """Align caption start/end times with actual audio duration."""
```

### 2.4 `plate_generator.py`

Title cards and end cards:

```python
class PlateGenerator:
    def generate_title_card(self, episode: dict) -> Path:
        """Generate episode title card image."""

    def generate_end_card(self, episode: dict) -> Path:
        """Generate end credits card."""
```

---

## 3. FFmpeg Commands

### Concat (demuxer, lossless)

```bash
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy episode_raw.mp4
```

### SRT Burn-In

```bash
ffmpeg -i episode_raw.mp4 -vf "subtitles=episode.srt" episode.mp4
```

### Audio Ducking

```bash
ffmpeg -i episode_raw.mp4 -i music_bed.mp3 \
  -filter_complex \
    "[1:a]volume=0.3[music];[0:a][music]amix=inputs=2:duration=first[out]" \
  -map 0:v -map "[out]" episode.mp4
```

---

## 4. Timing Model

- **Speech beats**: Duration = actual TTS audio length (via ffprobe)
- **Silent beats**: Duration = `duration_sec` field (default 2.0s)
- **SRT timing**: Cumulative offset from beat start times
- **Edge case**: If TTS audio is shorter than video clip, pad with silence

---

## 5. Output Structure

```
output/<run_id>/assembly/
  episode_raw.mp4          # concatenated video (no captions)
  episode.srt              # subtitle track
  episode.mp4              # final with captions
```

---

## 6. Key Design Decisions

1. **Concat demuxer over concat filter** → no re-encoding, faster, higher quality
2. **FFprobe for duration** → accurate timing from actual audio, not beat metadata
3. **SRT over ASS** → universally supported, simpler format, sufficient for captions
4. **Optional caption burn-in** → raw + captioned outputs for flexibility
5. **No crossfade transitions** → hard cuts between beats (sitcom convention)
