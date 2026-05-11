from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from showrunner.loader import CharacterData, VoiceConfig

logger = logging.getLogger(__name__)


# MLX-optimized providers — hardcoded for v1.0
_IMAGE_PROVIDER = "text2image.mlx"
_IMAGE_EDIT_PROVIDER = "image2image.mlx"
_VIDEO_PROVIDER = "image2video.mlx"
_TTS_PROVIDER = "text2speech.fish_mlx"
_ASR_PROVIDER = "audio2subtitle.mlx"


class AIServicesClient:
    """Unified facade over AIServices provider packages.

    Wraps text2image, image2image, image2video, text2speech (TTS),
    and audio2subtitle into a single interface consumed by the render
    pipeline.  Falls back to CLI subprocess when the Python API is
    unavailable.
    """

    def __init__(self, subprocess_fallback: bool = True):
        self._subprocess_fallback = subprocess_fallback

    def text2image(
        self,
        prompt: str,
        output_path: str | Path,
        *,
        seed: int | None = None,
        width: int = 1024,
        height: int = 720,
        negative_prompt: str | None = None,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 50,
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        try:
            from text2image.client import generate

            return generate(
                prompt,
                output,
                seed=seed,
                width=width,
                height=height,
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
                provider_name=_IMAGE_PROVIDER,
            )
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("text2image Python API failed: %s", exc)

        if self._subprocess_fallback:
            return self._cli_text2image(
                prompt=prompt,
                output_path=output,
                seed=seed,
                width=width,
                height=height,
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale,
                steps=num_inference_steps,
            )
        raise RuntimeError("text2image failed: no provider available")

    def image2image(
        self,
        image_path: str | Path,
        prompt: str,
        output_path: str | Path,
        *,
        seed: int | None = None,
        strength: float = 0.5,
        negative_prompt: str | None = None,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 50,
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        inp = str(image_path)

        try:
            from image2image.client import generate

            return generate(
                inp,
                prompt,
                output,
                seed=seed,
                strength=strength,
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
                provider_name=_IMAGE_EDIT_PROVIDER,
            )
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("image2image Python API failed: %s", exc)

        if self._subprocess_fallback:
            return self._cli_image2image(
                input_path=inp,
                prompt=prompt,
                output_path=output,
                seed=seed,
                strength=strength,
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale,
                steps=num_inference_steps,
            )
        raise RuntimeError("image2image failed: no provider available")

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
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        inp = str(image_path)

        result: Path | None = None
        try:
            from image2video.client import generate

            result = generate(
                inp,
                prompt,
                output,
                seed=seed,
                width=width,
                height=height,
                num_frames=num_frames,
                num_inference_steps=num_inference_steps,
                fps=fps,
                provider_name=_VIDEO_PROVIDER,
            )
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("image2video Python API failed: %s", exc)

        if result is None and self._subprocess_fallback:
            result = self._cli_image2video(
                image_path=inp,
                prompt=prompt,
                output_path=output,
                seed=seed,
                width=width,
                height=height,
                num_frames=num_frames,
                steps=num_inference_steps,
                fps=fps,
            )

        if result is None:
            raise RuntimeError("image2video failed: no provider available")

        if audio_path and result.suffix == ".mp4":
            return _mux_audio(result, audio_path, output)

        return result

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

        voice = voice or (character.voice if character and character.voice else None)
        tags = _build_speech_tags(emotion, tone, effect)
        tagged_text = f"{tags} {text}".strip() if tags else text

        try:
            from text2speech.client import generate

            return generate(
                text,
                output,
                voice_id=voice.voice_id if voice else None,
                emotion=emotion,
                tone=tone,
                effect=effect,
                reference_audio=voice.clone_from if voice else None,
                provider_name=_TTS_PROVIDER,
            )
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("text2speech Python API failed: %s", exc)

        if self._subprocess_fallback:
            return self._cli_text2speech(
                text=tagged_text,
                output_path=output,
                voice_id=voice.voice_id if voice else None,
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

        try:
            from audio2subtitle.client import generate

            return generate(
                audio_path,
                output,
                language=language,
                output_format=output_format,
                provider_name=_ASR_PROVIDER,
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

    def discover_capabilities(self) -> dict[str, list[str]]:
        caps: dict[str, list[str]] = {}
        for op, reg_name in [
            ("text2image", _IMAGE_PROVIDER),
            ("image2image", _IMAGE_EDIT_PROVIDER),
            ("image2video", _VIDEO_PROVIDER),
            ("text2speech", _TTS_PROVIDER),
        ]:
            caps[op] = [reg_name]
        caps["audio2subtitle"] = [_ASR_PROVIDER]
        return caps

    # ------------------------------------------------------------------
    # CLI subprocess fallbacks
    # ------------------------------------------------------------------

    def _cli_text2image(
        self, *, prompt, output_path, seed, width, height, negative_prompt, guidance_scale, steps
    ):
        cmd = [
            "text2image",
            "generate",
            "--prompt",
            prompt,
            "--output",
            str(output_path),
            "--width",
            str(_div8(width)),
            "--height",
            str(_div8(height)),
            "--guidance-scale",
            str(guidance_scale),
            "--steps",
            str(steps),
        ]
        if seed is not None:
            cmd += ["--seed", str(seed)]
        if negative_prompt:
            cmd += ["--negative-prompt", negative_prompt]
        _run_cli(cmd)
        return Path(output_path)

    def _cli_image2image(
        self,
        *,
        input_path,
        prompt,
        output_path,
        seed,
        strength,
        negative_prompt,
        guidance_scale,
        steps,
    ):
        cmd = [
            "image2image",
            "--input",
            input_path,
            "--prompt",
            prompt,
            "--output",
            str(output_path),
            "--strength",
            str(strength),
            "--guidance",
            str(guidance_scale),
            "--steps",
            str(steps),
        ]
        if seed is not None:
            cmd += ["--seed", str(seed)]
        if negative_prompt:
            cmd += ["--negative-prompt", negative_prompt]
        _run_cli(cmd)
        return Path(output_path)

    def _cli_image2video(
        self, *, image_path, prompt, output_path, seed, width, height, num_frames, steps, fps
    ):
        cmd = [
            "image2video",
            "generate",
            "--image",
            image_path,
            "--prompt",
            prompt,
            "--output",
            str(output_path),
            "--width",
            str(_div8(width)),
            "--height",
            str(_div8(height)),
            "--frames",
            str(num_frames),
            "--steps",
            str(steps),
            "--fps",
            str(fps),
        ]
        if seed is not None:
            cmd += ["--seed", str(seed)]
        _run_cli(cmd)
        return Path(output_path)

    def _cli_text2speech(self, *, text, output_path, voice_id, clone_from, seed, temperature):
        cmd = [
            "text2speech",
            "generate",
            "--text",
            text,
            "--output",
            str(output_path),
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
        _run_cli(cmd)
        return Path(output_path)


def _div8(n: int) -> int:
    return max(512, (n // 8) * 8)


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
