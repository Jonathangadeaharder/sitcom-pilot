from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from aiservices import generate_image2image, generate_text2image
from showrunner.loader import CharacterData, VoiceConfig

logger = logging.getLogger(__name__)


class AIServicesClient:
    """Unified facade over AIServices provider packages.

    Wraps text2image, image2image, image2video, text2speech (TTS),
    and audio2subtitle into a single interface consumed by the render
    pipeline.  Falls back to CLI subprocess when the Python API is
    unavailable.
    """

    def __init__(
        self,
        image_provider: str = "mlx-flux",
        image_edit_provider: str | None = None,  # deprecated
        video_provider: str = "mlx-ltx",
        tts_provider: str = "mlx-audio",
        asr_provider: str | None = None,
        subprocess_fallback: bool = True,
    ):
        if isinstance(image_provider, bool):
            subprocess_fallback, image_provider = image_provider, "mlx-flux"
        self._image_provider = image_provider
        self._image_edit_provider = image_edit_provider  # deprecated
        self._video_provider = video_provider
        self._tts_provider = tts_provider
        self._asr_provider = asr_provider
        self._subprocess_fallback = subprocess_fallback

    def text2image(
        self,
        prompt: str,
        output_path: str | Path,
        *,
        seed: int | None = None,
        **kwargs: Any,
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = generate_text2image(
                prompt=prompt,
                out_path=output,
                seed=seed or 42,
                steps=4,
            )
            return result.path
        except Exception as exc:
            logger.error("text2image failed: %s", exc)
            raise RuntimeError("text2image failed") from exc

    def image2image(
        self,
        image_path: str | Path,
        prompt: str,
        output_path: str | Path,
        *,
        seed: int | None = None,
        **kwargs: Any,
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = generate_image2image(
                prompt=prompt,
                base_image=Path(image_path),
                out_path=output,
                seed=seed or 42,
                steps=4,
            )
            return result.path
        except Exception as exc:
            logger.error("image2image failed: %s", exc)
            raise RuntimeError("image2image failed") from exc

    def image2video(
        self,
        image_path: str | Path,
        prompt: str,
        output_path: str | Path,
        *,
        audio_path: str | Path | None = None,
        seed: int | None = None,
        width: int = 640,
        height: int = 640,
        num_frames: int = 81,
        num_inference_steps: int = 4,
        fps: int = 16,
    ) -> Path:
        from aiservices.generate import VideoGenerator

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        gen = VideoGenerator(seed=seed or 0, fps=fps, num_inference_steps=num_inference_steps)
        result = gen.generate(
            prompt=prompt,
            output=output_path,
            image=str(image_path),
            width=width,
            height=height,
            num_frames=num_frames,
        )

        # optionally attach audio
        if audio_path and Path(audio_path).exists():
            self._attach_audio(result, audio_path)

        return result

    @staticmethod
    def _resolve_voice_config(
        voice: VoiceConfig | None,
        character: CharacterData | None,
    ) -> VoiceConfig | None:
        if voice:
            return voice
        if character and character.voice:
            return character.voice
        return None

    def text2speech(
        self,
        text: str,
        output_path: str | Path,
        *,
        voice: VoiceConfig | None = None,
        emotion: str | None = None,
        tone: str | None = None,
        effect: str | None = None,
        character: CharacterData | None = None,
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        voice = self._resolve_voice_config(voice, character)
        voice_id = voice.voice_id if voice else None
        tags = _build_speech_tags(emotion, tone, effect)
        tagged_text = f"{tags} {text}".strip() if tags else text

        try:
            from text2speech.client import generate

            return generate(
                text,
                output,
                voice_id=voice_id,
                emotion=emotion,
                tone=tone,
                effect=effect,
                reference_audio=voice.clone_from if voice else None,
                provider_name=self._tts_provider,
            )
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("text2speech Python API failed: %s", exc)

        if self._subprocess_fallback:
            return self._cli_text2speech(
                text=tagged_text,
                output_path=output,
                voice_id=voice_id,
                clone_from=voice.clone_from if voice else None,
                seed=voice.seed if voice else None,
                temperature=voice.temperature if voice else 0.8,
            )
        raise RuntimeError("text2speech failed: no provider available")

    def audio2subtitle(
        self,
        audio_path: str | Path,
        output_path: str | Path,
        *,
        language: str | None = None,
        output_format: str = "srt",
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if self._asr_provider:
            try:
                from audio2subtitle.client import generate

                return generate(
                    audio_path,
                    output,
                    language=language,
                    output_format=output_format,
                    provider_name=self._asr_provider,
                )
            except ImportError:
                pass
            except Exception as exc:
                logger.warning("audio2subtitle Python API failed: %s", exc)

        if self._subprocess_fallback:
            return self._cli_audio2subtitle(
                audio_path=str(audio_path),
                output_path=output,
            )
        raise RuntimeError("audio2subtitle failed: no provider available")

    def estimate_cost(self, operation: str, **kwargs) -> dict[str, Any]:
        duration_sec = kwargs.get("duration_seconds", 5.0)
        num_frames = kwargs.get("num_frames", 81)
        steps = kwargs.get("num_inference_steps", 50)
        estimates: dict[str, dict[str, float]] = {
            "text2image": {"time_sec": steps * 0.3, "memory_gb": 4.0},
            "image2image": {"time_sec": steps * 0.3, "memory_gb": 4.0},
            "image2video": {"time_sec": num_frames * steps * 0.05, "memory_gb": 8.0},
            "text2speech": {"time_sec": duration_sec * 0.5, "memory_gb": 2.0},
            "audio2subtitle": {"time_sec": duration_sec * 0.3, "memory_gb": 1.0},
        }
        return estimates.get(
            operation, {"time_sec": 0.0, "memory_gb": 0.0, "note": "unknown operation"}
        )

    def _attach_audio(self, video_path: Path, audio_path: str | Path) -> Path:
        return _mux_audio(video_path, audio_path, video_path)

    def discover_capabilities(self) -> dict[str, list[str]]:
        caps: dict[str, list[str]] = {}
        for op, reg_name in [
            ("text2image", self._image_provider),
            ("image2image", self._image_edit_provider),
            ("image2video", self._video_provider),
            ("text2speech", self._tts_provider),
        ]:
            caps[op] = [reg_name]
        if self._asr_provider:
            caps["audio2subtitle"] = [self._asr_provider]
        elif self._subprocess_fallback:
            caps["audio2subtitle"] = ["cli-fallback"]
        return caps

    # ------------------------------------------------------------------
    # CLI subprocess fallbacks
    # ------------------------------------------------------------------

    def _cli_text2speech(self, *, text, output_path, voice_id, clone_from, seed, temperature):
        cmd = [
            "text2speech",
            "generate",
            "--text",
            text,
            "--output",
            str(output_path),
            "--provider",
            self._tts_provider,
        ]
        if voice_id:
            cmd += ["--voice-id", voice_id]
        if clone_from:
            cmd += ["--reference-audio", clone_from]
        if seed is not None:
            cmd += ["--seed", str(seed)]
        if temperature is not None:
            cmd += ["--temperature", str(temperature)]
        _run_cli(cmd)
        return Path(output_path)

    def _cli_audio2subtitle(self, *, audio_path, output_path):
        cmd = [
            "audio2subtitle",
            "transcribe",
            "--input",
            audio_path,
            "--output",
            str(output_path),
        ]
        if self._asr_provider:
            cmd += ["--provider", self._asr_provider]
        _run_cli(cmd)
        return Path(output_path)


def _mux_audio(video_path: Path, audio_path: str | Path, output_path: Path) -> Path:
    tmp = output_path.with_suffix(".tmp.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        str(tmp),
    ]
    _run_cli(cmd)
    tmp.replace(output_path)
    return output_path


def _run_cli(cmd: list[str]) -> subprocess.CompletedProcess:
    logger.debug("CLI fallback command: %s", cmd[0] if cmd else "<empty>")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        stderr_preview = (result.stderr or "")[:500]
        stdout_preview = (result.stdout or "")[:500]
        error_msg = (
            f"CLI command failed (rc={result.returncode}) for `{cmd[0] if cmd else '<empty>'}`\n"
            f"stderr: {stderr_preview}"
        )
        if stdout_preview.strip():
            error_msg += f"\nstdout: {stdout_preview}"
        raise RuntimeError(error_msg)
    return result


def _build_speech_tags(
    emotion: str | None,
    tone: str | None,
    effect: str | None,
) -> str:
    parts = []
    if emotion:
        parts.append(f"({emotion})")
    if tone:
        parts.append(f"({tone})")
    if effect:
        parts.append(f"({effect})")
    return "".join(parts)
