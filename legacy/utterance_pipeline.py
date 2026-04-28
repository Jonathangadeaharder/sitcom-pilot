from __future__ import annotations

"""
Utterance-Driven Pipeline — generates video synced to speech.

Pipeline:
  1. Generate per-line audio via Fish-Speech
  2. Concatenate with pauses → full scene audio + timing map
  3. Run mlx-whisper → word-level timestamps per segment
  4. Generate one LTX clip per utterance (short, character-focused)
  5. Stitch clips onto timeline, add subtitles, encode final video
"""

import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from voice_generator_v3 import (
    build_fish_text,
    check_fish_api,
    synthesize_line,
)

V2_EPISODE_GUARD = (
    "This script only supports v1 (shot-based) episode files. "
    "For v2 beat-based episodes, use the src/sitcom_pilot pipeline."
)

FISH_API_URL = "http://127.0.0.1:8090"
LTX_ROOT = Path("/Users/jonathangadeaharder/Documents/projects/ltx-2-mlx")
LTX_CLI = str(LTX_ROOT / ".venv" / "bin" / "ltx-2-mlx")
MODEL_DIR = LTX_ROOT / "weights" / "q8"
GEMMA_DIR = LTX_ROOT / "weights" / "gemma-3-12b-it-4bit"

FRAME_RATE = 24
WIDTH = 768
HEIGHT = 512
PAUSE_BETWEEN_LINES = 0.5
PAUSE_BETWEEN_SHOTS = 1.0


@dataclass
class Utterance:
    line_idx: int
    shot_id: str
    speaker: str
    emotion: str
    text: str
    audio_path: Path = field(default=None, repr=False)
    start_sec: float = 0.0
    end_sec: float = 0.0


@dataclass
class TimingMap:
    utterances: list[Utterance] = field(default_factory=list)
    total_duration: float = 0.0
    full_audio_path: Path = field(default=None, repr=False)


def load_scene(episode_path: Path, scene_id: str) -> dict:
    with open(episode_path) as f:
        episode = json.load(f)
    if episode.get("schema_version") == "2.0":
        raise SystemExit(V2_EPISODE_GUARD)
    for scene in episode["scenes"]:
        if scene["scene_id"] == scene_id:
            return {"scene": scene, "cast": episode["cast"], "environments": episode["environments"]}
    raise ValueError(f"Scene {scene_id} not found")


def extract_utterances(scene_data: dict) -> list[Utterance]:
    scene = scene_data["scene"]
    utterances: list[Utterance] = []
    idx = 0
    for shot in scene.get("shots", []):
        for line in shot.get("dialogue", []):
            utterances.append(Utterance(
                line_idx=idx,
                shot_id=shot["shot_id"],
                speaker=line["speaker"],
                emotion=line.get("emotion", "neutral"),
                text=line.get("text", ""),
            ))
            idx += 1
    return utterances


def generate_audio(
    utterances: list[Utterance],
    cast: dict,
    audio_dir: Path,
) -> list[Path]:
    audio_dir.mkdir(parents=True, exist_ok=True)
    wav_paths: list[Path] = []

    for utt in utterances:
        char = cast.get(utt.speaker, {})
        fish_text = build_fish_text({
            "speaker": utt.speaker,
            "emotion": utt.emotion,
            "text": utt.text,
        })
        wav_path = audio_dir / f"utt_{utt.line_idx:03d}_{utt.speaker}.wav"
        success = synthesize_line(
            fish_text=fish_text,
            character_id=utt.speaker,
            output_path=wav_path,
            seed=char.get("voice_seed", 42),
            temperature=char.get("voice_temp", 0.8),
        )
        if success:
            utt.audio_path = wav_path
            wav_paths.append(wav_path)
            print(f"  [TTS] utt_{utt.line_idx:03d} ({utt.speaker}): OK ({wav_path.stat().st_size / 1024:.0f}KB)")
        else:
            print(f"  [TTS] utt_{utt.line_idx:03d} ({utt.speaker}): FAILED")

    return wav_paths


def build_timing_map(
    utterances: list[Utterance],
    scene: dict,
    audio_dir: Path,
) -> TimingMap:
    shot_boundaries: dict[str, int] = {}
    shot_idx = 0
    for shot in scene.get("shots", []):
        shot_boundaries[shot["shot_id"]] = shot_idx
        shot_idx += 1

    current_time = 0.0
    prev_shot_id: str | None = None

    for utt in utterances:
        if prev_shot_id is not None and utt.shot_id != prev_shot_id:
            current_time += PAUSE_BETWEEN_SHOTS

        if utt.audio_path and utt.audio_path.exists():
            duration = get_audio_duration(utt.audio_path)
        else:
            duration = 2.0

        utt.start_sec = current_time
        utt.end_sec = current_time + duration
        current_time = utt.end_sec + PAUSE_BETWEEN_LINES
        prev_shot_id = utt.shot_id

    return TimingMap(
        utterances=utterances,
        total_duration=current_time - PAUSE_BETWEEN_LINES,
    )


def concatenate_scene_audio(
    utterances: list[Utterance],
    output_path: Path,
) -> Path | None:
    valid = [u for u in utterances if u.audio_path and u.audio_path.exists()]
    if not valid:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(valid) == 1:
        import shutil
        shutil.copy2(valid[0].audio_path, output_path)
        return output_path

    inputs = []
    for i, utt in enumerate(valid):
        inputs.extend(["-i", str(utt.audio_path)])

    n = len(valid)
    filter_parts = []
    for i in range(n):
        if i < n - 1:
            pad = PAUSE_BETWEEN_LINES
        else:
            pad = 0.0
        filter_parts.append(f"[{i}:a]apad=pad_dur={pad}[p{i}];")
    concat_refs = "".join(f"[p{i}]" for i in range(n))
    filter_str = "".join(filter_parts) + f"{concat_refs}concat=n={n}:v=0:a=1[out]"

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_str,
        "-map", "[out]", "-ar", "44100", "-ac", "1",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and output_path.exists():
        return output_path
    return None


def run_whisper(audio_path: Path, output_dir: Path) -> list[dict]:
    json_path = output_dir / "whisper_segments.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    import mlx_whisper
    result = mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        language="en",
        word_timestamps=True,
        verbose=False,
    )

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
            "words": [
                {"start": w["start"], "end": w["end"], "word": w["word"].strip()}
                for w in seg.get("words", [])
            ],
        })

    with open(json_path, "w") as f:
        json.dump(segments, f, indent=2)

    print(f"  [Whisper] {len(segments)} segments, {sum(len(s['words']) for s in segments)} words")
    for s in segments:
        print(f"    {s['start']:.2f}-{s['end']:.2f}: {s['text'][:60]}")

    return segments


def align_whisper_to_utterances(
    whisper_segments: list[dict],
    timing_map: TimingMap,
) -> list[Utterance]:
    for utt in timing_map.utterances:
        overlapping = []
        for seg in whisper_segments:
            overlap_start = max(utt.start_sec, seg["start"])
            overlap_end = min(utt.end_sec, seg["end"])
            if overlap_end - overlap_start > 0:
                overlapping.append(seg)

        if overlapping:
            utt.start_sec = min(s["start"] for s in overlapping)
            utt.end_sec = max(s["end"] for s in overlapping)

    return timing_map.utterances


def build_utterance_prompt(
    utt: Utterance,
    cast: dict,
    environments: dict,
    scene: dict,
) -> str:
    char = cast.get(utt.speaker, {})
    char_visual = char.get("visual", utt.speaker)
    env_key = scene.get("environment", "")
    env = environments.get(env_key, {})
    env_visual = env.get("trigger_word", "")

    return (
        f"{env_visual}, {char_visual}, "
        f"{utt.emotion} expression, speaking, looking slightly off-camera, "
        f"medium close-up, cinematic lighting, 8k resolution"
    )


def generate_utterance_clips(
    utterances: list[Utterance],
    cast: dict,
    environments: dict,
    scene: dict,
    video_dir: Path,
) -> list[Path]:
    video_dir.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []

    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{LTX_ROOT / 'packages' / 'ltx-core-mlx' / 'src'}:"
        f"{LTX_ROOT / 'packages' / 'ltx-pipelines-mlx' / 'src'}:"
        f"{env.get('PYTHONPATH', '')}"
    )

    for utt in utterances:
        duration = max(utt.end_sec - utt.start_sec, 1.0)
        num_frames = calc_frames(duration)
        clip_path = video_dir / f"utt_{utt.line_idx:03d}.mp4"

        if clip_path.exists() and clip_path.stat().st_size > 1000:
            print(f"  [LTX] utt_{utt.line_idx:03d}: SKIP (exists)")
            clips.append(clip_path)
            continue

        prompt = build_utterance_prompt(utt, cast, environments, scene)
        print(f"  [LTX] utt_{utt.line_idx:03d} ({duration:.1f}s, {num_frames}f): {utt.text[:50]}...")

        cmd = [
            LTX_CLI, "generate",
            "--model", str(MODEL_DIR),
            "--gemma", str(GEMMA_DIR),
            "--prompt", prompt,
            "--output", str(clip_path),
            "--seed", str(2000 + utt.line_idx),
            "--frames", str(num_frames),
            "--height", str(HEIGHT),
            "--width", str(WIDTH),
        ]

        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
            if result.returncode == 0 and clip_path.exists() and clip_path.stat().st_size > 1000:
                size_kb = clip_path.stat().st_size / 1024
                print(f"  [LTX] OK ({size_kb:.0f}KB)")
                clips.append(clip_path)
            else:
                stderr = result.stderr[-300:] if result.stderr else "(no stderr)"
                print(f"  [LTX] FAIL: {stderr}")
                clips.append(clip_path if clip_path.exists() else Path())
        except subprocess.TimeoutExpired:
            print(f"  [LTX] TIMEOUT")
            clips.append(Path())
        except Exception as e:
            print(f"  [LTX] ERROR: {e}")
            clips.append(Path())

    return clips


def calc_frames(duration_sec: float) -> int:
    target = int(duration_sec * FRAME_RATE)
    remainder = target % 8
    if remainder > 0:
        target += 8 - remainder
    return max(17, min(target, 161))


def get_audio_duration(audio_path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-hide_banner", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio_path)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 3.0


def generate_srt(utterances: list[Utterance], srt_path: Path) -> Path:
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(srt_path, "w") as f:
        for i, utt in enumerate(utterances):
            start_ts = _fmt_srt_time(utt.start_sec)
            end_ts = _fmt_srt_time(utt.end_sec)
            f.write(f"{i + 1}\n{start_ts} --> {end_ts}\n{utt.text}\n\n")
    return srt_path


def _fmt_srt_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def stitch_scene(
    utterances: list[Utterance],
    video_dir: Path,
    audio_path: Path,
    srt_path: Path,
    output_path: Path,
    total_duration: float,
) -> Path | None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    valid_clips = []
    for utt in utterances:
        clip = video_dir / f"utt_{utt.line_idx:03d}.mp4"
        if clip.exists() and clip.stat().st_size > 1000:
            valid_clips.append((utt, clip))

    if not valid_clips:
        return None

    concat_dir = video_dir / "concat_segments"
    concat_dir.mkdir(parents=True, exist_ok=True)
    for f in concat_dir.glob("*.ts"):
        f.unlink()

    segment_list: list[Path] = []
    current_time = 0.0

    for utt, clip in valid_clips:
        if utt.start_sec > current_time:
            gap_dur = utt.start_sec - current_time
            gap_path = concat_dir / f"gap_{len(segment_list):03d}.ts"
            _make_black_segment(gap_dur, gap_path)
            segment_list.append(gap_path)

        seg_path = concat_dir / f"seg_{utt.line_idx:03d}.ts"
        clip_dur = utt.end_sec - utt.start_sec
        _reencode_clip(clip, clip_dur, seg_path)
        if seg_path.exists():
            segment_list.append(seg_path)

        current_time = utt.end_sec

    if current_time < total_duration:
        gap_dur = total_duration - current_time
        gap_path = concat_dir / f"gap_end.ts"
        _make_black_segment(gap_dur, gap_path)
        segment_list.append(gap_path)

    concat_file = concat_dir / "list.txt"
    with open(concat_file, "w") as f:
        for seg in segment_list:
            f.write(f"file '{seg}'\n")

    temp_video = output_path.with_suffix(".noaudio.mp4")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "h264_videotoolbox",
        "-b:v", "8M",
        "-r", str(FRAME_RATE),
        str(temp_video),
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if not temp_video.exists():
        return None

    cmd = [
        "ffmpeg", "-y",
        "-i", str(temp_video),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode == 0 and output_path.exists():
        temp_video.unlink(missing_ok=True)
        return output_path
    return None


def _make_black_segment(duration: float, output: Path) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:d={duration}:r={FRAME_RATE}",
        "-c:v", "h264_videotoolbox",
        "-b:v", "2M",
        "-bsf:v", "h264_mp4toannexb",
        "-f", "mpegts",
        str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def _reencode_clip(clip: Path, target_dur: float, output: Path) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", str(clip),
        "-t", str(target_dur),
        "-c:v", "h264_videotoolbox",
        "-b:v", "8M",
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        "-r", str(FRAME_RATE),
        "-an",
        "-bsf:v", "h264_mp4toannexb",
        "-f", "mpegts",
        str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def burn_subtitles(video_path: Path, srt_path: Path, output_path: Path) -> Path | None:
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Alignment=2'",
        "-c:v", "h264_videotoolbox",
        "-b:v", "8M",
        "-c:a", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0 and output_path.exists():
        return output_path
    return None


def run_scene(episode_path: Path, scene_id: str, output_dir: Path) -> Path | None:
    print(f"\n{'='*60}")
    print(f"Utterance Pipeline — Scene {scene_id}")
    print(f"{'='*60}")

    scene_data = load_scene(episode_path, scene_id)
    scene = scene_data["scene"]
    cast = scene_data["cast"]
    envs = scene_data["environments"]

    audio_dir = output_dir / "audio"
    video_dir = output_dir / "video"
    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Step 1: Extract utterances ---")
    utterances = extract_utterances(scene_data)
    print(f"  {len(utterances)} utterances extracted")
    for u in utterances:
        print(f"    utt_{u.line_idx:03d} [{u.shot_id}] {u.speaker}/{u.emotion}: {u.text[:50]}...")

    print(f"\n--- Step 2: Generate audio ---")
    if not check_fish_api():
        print("ERROR: Fish-Speech not running at", FISH_API_URL)
        print("Start: cd fish-speech && .venv/bin/python tools/api_server.py ...")
        return None
    print("Fish-Speech API connected")
    wav_paths = generate_audio(utterances, cast, audio_dir)
    if not wav_paths:
        print("ERROR: No audio generated")
        return None
    print(f"  {len(wav_paths)}/{len(utterances)} lines synthesized")

    print(f"\n--- Step 3: Build full scene audio ---")
    full_audio = audio_dir / f"scene_{scene_id}_full.wav"
    concat_result = concatenate_scene_audio(utterances, full_audio)
    if not concat_result:
        print("ERROR: Failed to concatenate audio")
        return None
    full_dur = get_audio_duration(full_audio)
    print(f"  Full audio: {full_dur:.1f}s")

    print(f"\n--- Step 4: Build timing map ---")
    timing_map = build_timing_map(utterances, scene, audio_dir)
    timing_map.full_audio_path = full_audio
    for u in timing_map.utterances:
        dur = u.end_sec - u.start_sec
        print(f"    utt_{u.line_idx:03d}: {u.start_sec:.2f}-{u.end_sec:.2f} ({dur:.1f}s)")

    print(f"\n--- Step 5: Whisper alignment ---")
    whisper_segs = run_whisper(full_audio, audio_dir)
    if whisper_segs:
        utterances = align_whisper_to_utterances(whisper_segs, timing_map)
        print("  Aligned utterances to Whisper segments:")
        for u in utterances:
            dur = u.end_sec - u.start_sec
            print(f"    utt_{u.line_idx:03d}: {u.start_sec:.2f}-{u.end_sec:.2f} ({dur:.1f}s)")
    else:
        print("  No Whisper segments, using timing map as-is")

    print(f"\n--- Step 6: Generate utterance video clips ---")
    clips = generate_utterance_clips(utterances, cast, envs, scene, video_dir)
    valid = [c for c in clips if c and c.exists()]
    print(f"  {len(valid)}/{len(utterances)} clips generated")

    print(f"\n--- Step 7: Generate subtitles ---")
    srt_path = final_dir / f"scene_{scene_id}.srt"
    generate_srt(utterances, srt_path)
    print(f"  Subtitles: {srt_path}")

    print(f"\n--- Step 8: Stitch video ---")
    stitched_path = final_dir / f"scene_{scene_id}_stitched.mp4"
    result = stitch_scene(
        utterances, video_dir, full_audio, srt_path,
        stitched_path, timing_map.total_duration,
    )
    if not result:
        print("ERROR: Stitching failed")
        return None
    size_mb = result.stat().st_size / (1024 * 1024)
    dur = get_audio_duration(result)
    print(f"  Stitched: {result.name} ({size_mb:.1f}MB, {dur:.1f}s)")

    print(f"\n--- Step 9: Burn subtitles ---")
    final_path = final_dir / f"scene_{scene_id}_final.mp4"
    sub_result = burn_subtitles(stitched_path, srt_path, final_path)
    if sub_result:
        size_mb = sub_result.stat().st_size / (1024 * 1024)
        print(f"  Final: {sub_result.name} ({size_mb:.1f}MB)")
        return sub_result
    else:
        print("  Subtitle burn failed, returning stitched version")
        return stitched_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Utterance-driven video pipeline")
    parser.add_argument("episode", help="Path to episode JSON")
    parser.add_argument("--scene", default="001", help="Scene ID to process")
    parser.add_argument("--output-dir", default="output/s01e02")
    args = parser.parse_args()

    result = run_scene(Path(args.episode), args.scene, Path(args.output_dir))
    if result:
        print(f"\nDone! Output: {result}")
    else:
        print(f"\nPipeline failed!")
        sys.exit(1)
