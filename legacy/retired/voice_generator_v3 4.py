from __future__ import annotations

"""
Fish-Speech Voice Generator V3 — reads unified episode JSON and generates
emotion-tagged audio for each dialogue line via Fish-Speech API.

Emotion tags use Fish Audio's native syntax:
  S1: (emotion)(tone)(effect) text
  S2: [emotion][tone][effect] text

This module uses S1 (parenthesis) syntax for maximum compatibility.
"""

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

FISH_API_URL = "http://127.0.0.1:8090"
TTS_TIMEOUT_SEC = 300

VALID_EMOTIONS = frozenset({
    "happy", "sad", "angry", "excited", "calm", "nervous", "confident",
    "surprised", "satisfied", "delighted", "scared", "worried", "upset",
    "frustrated", "depressed", "empathetic", "embarrassed", "disgusted",
    "moved", "proud", "relaxed", "grateful", "curious", "sarcastic",
    "disdainful", "unhappy", "anxious", "hysterical", "indifferent",
    "uncertain", "doubtful", "confused", "disappointed", "regretful",
    "guilty", "ashamed", "jealous", "envious", "hopeful", "optimistic",
    "pessimistic", "nostalgic", "lonely", "bored", "contemptuous",
    "sympathetic", "compassionate", "determined", "resigned",
})

VALID_TONES = frozenset({
    "in a hurry tone", "shouting", "screaming", "whispering", "soft tone",
})

VALID_EFFECTS = frozenset({
    "laughing", "chuckling", "sobbing", "crying loudly", "sighing",
    "groaning", "panting", "gasping", "yawning", "snoring",
})


def load_episode(path: Path) -> dict:
    with open(path) as f:
        data = json.load(f)
    if data.get("schema_version") == "2.0":
        print(
            "This script only supports v1 (shot-based) episode files. "
            "For v2 beat-based episodes, use the src/showrunner pipeline.",
            file=sys.stderr,
        )
        sys.exit(1)
    for required in ("scenes", "cast", "environments"):
        if required not in data:
            raise ValueError(f"Missing required field: {required}")
    return data


def build_fish_text(line: dict) -> str:
    parts = []
    emotion = line.get("emotion")
    if emotion and emotion in VALID_EMOTIONS:
        parts.append(f"({emotion})")
    tone = line.get("tone")
    if tone and tone in VALID_TONES:
        parts.append(f"({tone})")
    effect = line.get("effect")
    if effect and effect in VALID_EFFECTS:
        parts.append(f"({effect})")
    tags = "".join(parts)
    text = line.get("text", "").strip()
    if tags:
        return f"{tags} {text}"
    return text


def get_scene_dialogue(scene: dict) -> list[dict]:
    lines = []
    for shot in scene.get("shots", []):
        for line in shot.get("dialogue", []):
            lines.append(line)
    return lines


def generate_fish_payload(
    fish_text: str,
    character_id: str,
    seed: int = 42,
    temperature: float = 0.8,
) -> dict[str, Any]:
    return {
        "text": fish_text,
        "references": [],
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
        "use_memory_cache": "on",
    }


def synthesize_line(
    fish_text: str,
    character_id: str,
    output_path: Path,
    seed: int = 42,
    temperature: float = 0.8,
) -> bool:
    if output_path.exists():
        return True

    try:
        import ormsgpack
    except ImportError:
        return False

    payload = generate_fish_payload(fish_text, character_id, seed, temperature)

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
        return True

    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def concatenate_audio(wav_files: list[Path], output_path: Path, pause_sec: float = 0.4) -> bool:
    if not wav_files:
        return False
    if len(wav_files) == 1:
        import shutil
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wav_files[0], output_path)
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

    inputs = []
    for i, wav in enumerate(wav_files):
        inputs.extend(["-i", str(wav)])

    n = len(wav_files)
    pad_parts = []
    for i in range(n):
        if i < n - 1:
            pad_parts.append(f"[{i}:a]apad=pad_dur={pause_sec}[p{i}];")
        else:
            pad_parts.append(f"[{i}:a]acopy[p{i}];")
    pad_str = "".join(pad_parts)
    concat_refs = "".join(f"[p{i}]" for i in range(n))
    filter_str = f"{pad_str}{concat_refs}concat=n={n}:v=0:a=1[out]"

    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_str, "-map", "[out]", "-ar", "44100", "-ac", "1", str(output_path)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0 and output_path.exists()
    except Exception:
        return False


def check_fish_api() -> bool:
    try:
        resp = urllib.request.urlopen(f"{FISH_API_URL}/v1/health", timeout=5)
        return resp.status == 200
    except Exception:
        return False


def generate_episode_audio(episode: dict, output_dir: Path) -> dict[str, dict]:
    cast = episode["cast"]
    results: dict[str, dict] = {}

    for scene in episode["scenes"]:
        sid = scene["scene_id"]
        voice_dir = output_dir / "voices" / f"scene_{sid}"
        voice_dir.mkdir(parents=True, exist_ok=True)

        line_files: list[Path] = []
        line_idx = 0

        for shot in scene.get("shots", []):
            for dialogue_line in shot.get("dialogue", []):
                speaker = dialogue_line["speaker"]
                char = cast.get(speaker, {})
                fish_text = build_fish_text(dialogue_line)
                line_file = voice_dir / f"line_{line_idx:03d}_{speaker}.wav"

                success = synthesize_line(
                    fish_text=fish_text,
                    character_id=speaker,
                    output_path=line_file,
                    seed=char.get("voice_seed", 42),
                    temperature=char.get("voice_temp", 0.8),
                )

                if success:
                    line_files.append(line_file)
                line_idx += 1

        scene_audio = voice_dir / f"scene_{sid}_full.wav"
        if line_files:
            concatenate_audio(line_files, scene_audio, pause_sec=0.4)

        results[sid] = {
            "lines_generated": len(line_files),
            "scene_audio": scene_audio if scene_audio.exists() else None,
        }

    return results


def main(episode_path: Path, output_dir: Path) -> dict:
    print(f"Buffering Voice Generator V3 — {episode_path.name}")

    if not check_fish_api():
        print("ERROR: Fish-Speech API not running on", FISH_API_URL)
        raise RuntimeError("Fish-Speech API unavailable")

    print("Fish-Speech API connected")

    episode = load_episode(episode_path)
    print(f"  Scenes: {len(episode['scenes'])}")
    total_lines = sum(
        len(dl)
        for s in episode["scenes"]
        for sh in s.get("shots", [])
        for dl in sh.get("dialogue", [])
    )
    print(f"  Dialogue lines: {total_lines}")

    results = generate_episode_audio(episode, output_dir)

    print("\nResults:")
    for sid, r in results.items():
        print(f"  Scene {sid}: {r['lines_generated']} lines, audio={r['scene_audio']}")
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python voice_generator_v3.py <episode.json> [output_dir]")
        sys.exit(1)

    ep = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")
    main(ep, out)
