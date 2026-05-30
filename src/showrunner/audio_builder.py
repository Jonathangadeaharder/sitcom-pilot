from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]")


def _safe_filename(name: str) -> str:
    return _SAFE_NAME_RE.sub("_", name)


VALID_EMOTIONS = frozenset(
    {
        "happy",
        "sad",
        "angry",
        "excited",
        "calm",
        "nervous",
        "confident",
        "surprised",
        "satisfied",
        "delighted",
        "scared",
        "worried",
        "upset",
        "frustrated",
        "depressed",
        "empathetic",
        "embarrassed",
        "disgusted",
        "moved",
        "proud",
        "relaxed",
        "grateful",
        "curious",
        "sarcastic",
        "disdainful",
        "unhappy",
        "anxious",
        "hysterical",
        "indifferent",
        "uncertain",
        "doubtful",
        "confused",
        "disappointed",
        "regretful",
        "guilty",
        "ashamed",
        "jealous",
        "envious",
        "hopeful",
        "optimistic",
        "pessimistic",
        "nostalgic",
        "lonely",
        "bored",
        "contemptuous",
        "sympathetic",
        "compassionate",
        "determined",
        "resigned",
    }
)

VALID_TONES = frozenset(
    {
        "in a hurry tone",
        "shouting",
        "screaming",
        "whispering",
        "soft tone",
    }
)

VALID_EFFECTS = frozenset(
    {
        "laughing",
        "chuckling",
        "sobbing",
        "crying loudly",
        "sighing",
        "groaning",
        "panting",
        "gasping",
        "yawning",
        "snoring",
    }
)


def build_fish_text_from_dialogue(line: dict) -> str:
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


def synthesize_dialogue_line(
    fish_text: str,
    character_id: str,
    output_path: Path,
    seed: int = 42,
    temperature: float = 0.8,
) -> bool:
    if output_path.exists():
        return True
    try:
        from aiservices.generate import AudioGenerator

        gen = AudioGenerator(seed=seed, temperature=temperature)
        gen.generate(
            text=fish_text,
            output=output_path,
            file_prefix="",
        )
        return output_path.exists()
    except Exception:
        logger.exception("TTS failed for '%s'", character_id)
        return False


def concatenate_wavs(wav_files: list[Path], output_path: Path, pause_sec: float = 0.4) -> bool:
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
    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_str,
        "-map",
        "[out]",
        "-ar",
        "44100",
        "-ac",
        "1",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0 and output_path.exists()
    except (subprocess.SubprocessError, OSError):
        logger.exception("ffmpeg concat failed")
        return False


def build_shot_audio(
    dialogue: list[dict],
    output_path: Path,
    voice_seed: int = 42,
    voice_temp: float = 0.8,
) -> bool:
    if not dialogue:
        return False
    if output_path.exists():
        return True
    line_files: list[Path] = []
    for i, line in enumerate(dialogue):
        fish_text = build_fish_text_from_dialogue(line)
        safe_spk = _safe_filename(line["speaker"])
        line_file = output_path.parent / f"{output_path.stem}_line_{i:03d}_{safe_spk}.wav"
        success = synthesize_dialogue_line(
            fish_text=fish_text,
            character_id=line["speaker"],
            output_path=line_file,
            seed=voice_seed,
            temperature=voice_temp,
        )
        if success:
            line_files.append(line_file)
        else:
            logger.error(
                "Dialogue line %d failed for speaker '%s'; aborting shot",
                i,
                line["speaker"],
            )
            return False
    if not line_files:
        return False
    return concatenate_wavs(line_files, output_path, pause_sec=0.4)
