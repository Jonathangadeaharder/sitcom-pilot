from __future__ import annotations

"""
Setup character reference voices for Fish-Speech.
Generates distinctive voice samples per character and registers them
as reference voices in the Fish-Speech server's references/ directory.
"""

import sys
import time
from pathlib import Path

# Fish-Speech config
FISH_ROOT = Path("/Users/jonathangadeaharder/Documents/projects/fish-speech")
FISH_API_URL = "http://127.0.0.1:8090"

# Reference lines — chosen to be emotionally representative of each character
# These become the "voice identity" anchors for all future TTS
VOICE_BOOTSTRAP = {
    "maya": {
        "seed": 42,
        "temperature": 0.8,
        "text": "No no no no no. The deployment is in twelve hours and everything is broken. I wrote this bug myself three weeks ago at two in the morning. Past Maya is the worst engineer I've ever worked with.",
        "lab_text": "No no no no no. The deployment is in twelve hours and everything is broken. I wrote this bug myself three weeks ago at two in the morning. Past Maya is the worst engineer I've ever worked with.",
    },
    "derek": {
        "seed": 137,
        "temperature": 0.85,
        "text": "Good morning team! Big news, our new pivot is going to be absolutely huge. We're doing blockchain for pets. Plants don't have wallets. Pets have owners, owners have wallets. It's simple economics.",
        "lab_text": "Good morning team! Big news, our new pivot is going to be absolutely huge. We're doing blockchain for pets. Plants don't have wallets. Pets have owners, owners have wallets. It's simple economics.",
    },
    "priya": {
        "seed": 256,
        "temperature": 0.75,
        "text": "You know what has zero bugs? A pencil. A pencil has never crashed. It doesn't need a firmware update. It doesn't send your data to three different servers. I'm going to the roof. With a pencil.",
        "lab_text": "You know what has zero bugs? A pencil. A pencil has never crashed. It doesn't need a firmware update. It doesn't send your data to three different servers. I'm going to the roof. With a pencil.",
    },
    "finn": {
        "seed": 389,
        "temperature": 0.8,
        "text": "Has anyone else noticed that the thermostat just reported our living room temperature to three different servers? One of them is in a country I cannot find on any map. I've checked four maps. Physical maps.",
        "lab_text": "Has anyone else noticed that the thermostat just reported our living room temperature to three different servers? One of them is in a country I cannot find on any map. I've checked four maps. Physical maps.",
    },
}


def generate_reference_audio(char_id: str, config: dict, output_path: Path) -> bool:
    """Generate a reference audio clip using Fish-Speech API (msgpack)."""
    try:
        import ormsgpack
        import urllib.request
        import urllib.error
    except ImportError:
        print("  [ERROR] ormsgpack not installed")
        return False

    payload = {
        "text": config["text"],
        "references": [],
        "reference_id": None,
        "seed": config["seed"],
        "temperature": config["temperature"],
        "top_p": 0.8,
        "repetition_penalty": 1.1,
        "chunk_length": 200,
        "max_new_tokens": 1024,
        "streaming": False,
        "format": "wav",
        "latency": "normal",
        "normalize": True,
        "use_memory_cache": "off",
    }

    try:
        data = ormsgpack.packb(payload)
        req = urllib.request.Request(
            f"{FISH_API_URL}/v1/tts",
            data=data,
            headers={"Content-Type": "application/msgpack"},
        )
        resp = urllib.request.urlopen(req, timeout=300)
        audio_data = resp.read()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        print(f"  [✓] {char_id}: {output_path.name} ({len(audio_data)} bytes)")
        return True

    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        print(f"  [✗] HTTP {e.code}: {body}")
        return False
    except Exception as e:
        print(f"  [✗] Error: {e}")
        return False


def register_reference(char_id: str, audio_path: Path, lab_text: str) -> bool:
    """Register a voice reference in Fish-Speech's references/ directory."""
    ref_dir = FISH_ROOT / "references" / char_id
    ref_dir.mkdir(parents=True, exist_ok=True)

    import shutil

    # Copy audio as sample.wav
    target_audio = ref_dir / "sample.wav"
    shutil.copy2(audio_path, target_audio)

    # Write lab file with matching text
    lab_path = ref_dir / "sample.lab"
    with open(lab_path, "w", encoding="utf-8") as f:
        f.write(lab_text)

    print(f"  [REG] {char_id}: registered at {ref_dir}")
    return True


def main():
    print("╔══════════════════════════════════════════╗")
    print("║  Voice Bootstrap — Buffering Characters   ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # Check API
    import urllib.request
    try:
        urllib.request.urlopen(f"{FISH_API_URL}/v1/health", timeout=5)
        print("✓ Fish-Speech API is running")
    except Exception:
        print("✗ Fish-Speech API not running! Start it first:")
        print(f"  cd {FISH_ROOT} && .venv/bin/python tools/api_server.py --listen 127.0.0.1:8090 --device mps --half")
        sys.exit(1)

    output_dir = Path(__file__).parent / "output" / "voice_refs"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n── Generating Reference Audio ──\n")
    for char_id, config in VOICE_BOOTSTRAP.items():
        audio_path = output_dir / f"{char_id}_ref.wav"
        if audio_path.exists():
            print(f"  [SKIP] {char_id}: reference already exists")
        else:
            print(f"  Generating {char_id} ({config['seed']})...")
            success = generate_reference_audio(char_id, config, audio_path)
            if not success:
                print(f"  [WARN] Failed to generate {char_id} reference, will use no reference")
                continue
            # Small delay between generations
            time.sleep(1)

    print("\n── Registering References ──\n")
    for char_id, config in VOICE_BOOTSTRAP.items():
        audio_path = output_dir / f"{char_id}_ref.wav"
        if audio_path.exists():
            register_reference(char_id, audio_path, config["lab_text"])
        else:
            print(f"  [SKIP] {char_id}: no audio to register")

    print("\n✓ Voice setup complete!")
    print(f"  References dir: {FISH_ROOT / 'references'}")


if __name__ == "__main__":
    main()
