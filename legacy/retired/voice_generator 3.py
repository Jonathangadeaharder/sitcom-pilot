from __future__ import annotations

"""
Fish-Speech Voice Generator V2 — synthesizes character dialogue audio with
reference voices for consistent character identity and emotional delivery.
Uses Fish-Speech's API server (ormsgpack protocol) for TTS generation.
"""

import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from script import CHARACTERS, SCENES

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
FISH_ROOT = Path("/Users/jonathangadeaharder/Documents/projects/fish-speech")
FISH_VENV_PYTHON = FISH_ROOT / ".venv" / "bin" / "python"

# Fish-Speech API runs on port 8090 (8080 is taken by Plane)
FISH_API_URL = "http://127.0.0.1:8090"

# Timeout for individual TTS requests (long lines can take ~3 min on MPS)
TTS_TIMEOUT_SEC = 300


def check_fish_api() -> bool:
    """Check if Fish-Speech API server is running."""
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"{FISH_API_URL}/v1/health", timeout=5)
        return resp.status == 200
    except Exception:
        return False


def clean_dialogue_text(text: str) -> str:
    """Clean dialogue text for TTS — preserve emotion cues as they help
    Fish-Speech s2-pro add expressiveness."""
    # Strip leading emotion cue from parens — keep rest as natural speech
    # E.g. "(panicked) No no no" → just send the full text including the cue
    # Fish-Speech can interpret stage directions like (excited), (angry), etc.
    return text.strip()


def synthesize_line(text: str, character_id: str, output_path: Path,
                    seed: int = 42, temperature: float = 0.8) -> bool:
    """Synthesize a single dialogue line using Fish-Speech API with
    character reference voice (msgpack protocol)."""
    if output_path.exists():
        print(f"    [SKIP] {output_path.name} already exists")
        return True

    try:
        import ormsgpack
    except ImportError:
        print("    [WARN] ormsgpack not available, skipping API call")
        return False

    import urllib.request
    import urllib.error

    # Clean the text but keep emotion cues
    clean_text = clean_dialogue_text(text)

    payload = {
        "text": clean_text,
        "references": [],
        # Use character-specific reference voice
        "reference_id": character_id,
        "seed": seed,
        "temperature": temperature,
        "top_p": 0.8,
        "repetition_penalty": 1.1,
        "chunk_length": 200,
        "max_new_tokens": 1024,
        "streaming": False,
        "format": "wav",
        "latency": "normal",
        "normalize": True,
        "use_memory_cache": "on",  # Cache ref voice encoding for speed
    }

    try:
        data = ormsgpack.packb(payload)
        req = urllib.request.Request(
            f"{FISH_API_URL}/v1/tts",
            data=data,
            headers={"Content-Type": "application/msgpack"},
        )
        resp = urllib.request.urlopen(req, timeout=TTS_TIMEOUT_SEC)
        audio_data = resp.read()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        print(f"    [TTS] ✓ {output_path.name} ({len(audio_data)} bytes)")
        return True

    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        print(f"    [TTS] ✗ HTTP {e.code}: {body}")
        return False
    except Exception as e:
        print(f"    [TTS] ✗ Error: {e}")
        return False


def generate_silence(duration_sec: float, output_path: Path,
                     sample_rate: int = 44100) -> bool:
    """Generate a silent WAV file for pauses or scenes with no dialogue."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = int(duration_sec * sample_rate)
    with wave.open(str(output_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return True


def concatenate_scene_audio(wav_files: list[Path], output_path: Path,
                            pause_sec: float = 0.5) -> bool:
    """Concatenate individual line WAVs into a single scene audio file,
    with pauses between lines for natural pacing."""
    if not wav_files:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use ffmpeg to concatenate with silence gaps
    filter_parts = []
    inputs = []
    for i, wav in enumerate(wav_files):
        inputs.extend(["-i", str(wav)])
        filter_parts.append(f"[{i}:a]")

    # Create silence filter for gaps
    n = len(wav_files)
    if n == 1:
        # Single file, just copy
        import shutil
        shutil.copy2(wav_files[0], output_path)
        return True

    # Build complex filter: interleave audio with silence gaps
    # Generate a silence pad and concat all
    concat_filter = ""
    pad_parts = []
    for i in range(n):
        if i < n - 1:
            pad_parts.append(f"[{i}:a]apad=pad_dur={pause_sec}[p{i}];")
        else:
            pad_parts.append(f"[{i}:a]acopy[p{i}];")
    pad_str = "".join(pad_parts)
    concat_refs = "".join(f"[p{i}]" for i in range(n))
    filter_str = f"{pad_str}{concat_refs}concat=n={n}:v=0:a=1[out]"

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-ar", "44100",
        "-ac", "1",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and output_path.exists():
            print(f"  [CONCAT] ✓ {output_path.name}")
            return True
        else:
            print(f"  [CONCAT] ✗ ffmpeg failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  [CONCAT] ✗ Error: {e}")
        return False


def generate_scene_audio(scene: dict) -> dict:
    """Generate all dialogue audio for a scene and concatenate into a scene WAV."""
    sid = scene["id"]
    voice_dir = OUTPUT_DIR / "voices" / f"scene_{sid}"
    voice_dir.mkdir(parents=True, exist_ok=True)

    results = {"lines": [], "scene_audio": None}

    if not scene["dialogue"]:
        # Generate silence for scenes without dialogue
        silence_path = voice_dir / "silence.wav"
        generate_silence(5.0, silence_path)
        results["scene_audio"] = silence_path
        return results

    line_files = []
    for i, (char_id, line) in enumerate(scene["dialogue"]):
        char = CHARACTERS.get(char_id, {})
        line_file = voice_dir / f"line_{i:03d}_{char_id}.wav"

        # Display the line (truncated for readability)
        display = line[:60] + "..." if len(line) > 60 else line
        print(f"  [{char_id}] \"{display}\"")

        success = synthesize_line(
            text=line,
            character_id=char_id,
            output_path=line_file,
            seed=char.get("voice_seed", 42),
            temperature=char.get("voice_temp", 0.8),
        )

        if success:
            results["lines"].append(line_file)
            line_files.append(line_file)

    # Concatenate all lines into a single scene audio WAV
    if line_files:
        scene_audio = voice_dir / f"scene_{sid}_full.wav"
        if scene_audio.exists():
            print(f"  [SKIP] {scene_audio.name} already exists")
        else:
            concatenate_scene_audio(line_files, scene_audio, pause_sec=0.4)
        results["scene_audio"] = scene_audio

    return results


def generate_all_voices() -> dict[str, dict]:
    """Generate voice audio for all scenes."""
    print("╔══════════════════════════════════════════════╗")
    print("║  Fish-Speech Voice Gen V2 — Buffering S01     ║")
    print("║  With character reference voices               ║")
    print("╚══════════════════════════════════════════════╝")

    if not check_fish_api():
        print("✗ Fish-Speech API not running!")
        print(f"  Start: cd {FISH_ROOT} && .venv/bin/python tools/api_server.py --listen 127.0.0.1:8090 --device mps --half")
        sys.exit(1)
    print("✓ Fish-Speech API server is running")

    # Check references exist
    refs_dir = FISH_ROOT / "references"
    for char_id in CHARACTERS:
        ref_dir = refs_dir / char_id
        if ref_dir.exists():
            print(f"  ✓ Reference voice: {char_id}")
        else:
            print(f"  ⚠ No reference for {char_id} — will use default voice")

    results = {}
    total_lines = sum(len(s["dialogue"]) for s in SCENES)
    generated = 0

    for scene in SCENES:
        sid = scene["id"]
        print(f"\n─── Scene {sid}: {scene['title']} ({len(scene['dialogue'])} lines) ───")
        scene_results = generate_scene_audio(scene)
        results[sid] = scene_results
        generated += len(scene_results["lines"])

    print("\n═══ Voice Generation Summary ═══")
    print(f"  Total dialogue lines: {total_lines}")
    print(f"  Audio files generated: {generated}")

    # List scene audio files
    print("\n  Scene audio files:")
    for sid, r in results.items():
        if r.get("scene_audio") and r["scene_audio"].exists():
            size = r["scene_audio"].stat().st_size
            print(f"    Scene {sid}: {r['scene_audio'].name} ({size / 1024:.0f} KB)")

    return results


if __name__ == "__main__":
    generate_all_voices()
