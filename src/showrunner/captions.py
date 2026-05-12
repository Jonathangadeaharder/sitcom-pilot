from __future__ import annotations

from showrunner.loader import BeatData


def timecode(seconds: float, fps: float = 24.0) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_text_for_subtitles(text: str, max_chars: int = 42) -> list[str]:
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text.strip())
            break
        split_at = text.rfind(" ", 0, max_chars + 1)
        if split_at == -1:
            chunks.append(text[:max_chars].strip())
            text = text[max_chars:]
        else:
            chunks.append(text[:split_at].strip())
            text = text[split_at + 1 :]
    return chunks


def generate_srt(
    beats: list[BeatData],
    fps: float = 24.0,
    max_chars: int = 42,
) -> str:
    lines: list[str] = []
    idx = 1
    current_time = 0.0
    for beat in beats:
        duration = beat.duration_sec
        if beat.kind == "speech" and beat.text:
            text = beat.text.replace("\n", " ").replace("\r", " ")
            chunks = split_text_for_subtitles(text, max_chars=max_chars)
            chunk_duration = duration / max(len(chunks), 1)
            for i, chunk in enumerate(chunks):
                start = timecode(current_time + i * chunk_duration, fps=fps)
                end = timecode(current_time + (i + 1) * chunk_duration, fps=fps)
                lines.append(str(idx))
                lines.append(f"{start} --> {end}")
                if beat.speaker and i == 0:
                    lines.append(f"{beat.speaker}: {chunk}")
                else:
                    lines.append(chunk)
                lines.append("")
                idx += 1
        current_time += duration
    return "\n".join(lines)
