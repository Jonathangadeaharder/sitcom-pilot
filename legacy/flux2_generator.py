from __future__ import annotations

"""
Flux2 Image Generator — drives ComfyUI API to generate character, scene, and shot images.
Includes image-to-image refinement for character/scene consistency.
"""

import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Add script module
sys.path.insert(0, str(Path(__file__).parent))
from script import CHARACTERS, LOCATIONS, SCENES, get_shot_prompt

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_OUTPUT = Path(os.environ.get(
    "COMFYUI_OUTPUT",
    "/Users/jonathangadeaharder/Documents/projects/ComfyUI/ComfyUI/output",
))
PROJECT_ROOT = Path(__file__).parent
WORKFLOWS_DIR = PROJECT_ROOT / "workflows"
OUTPUT_DIR = PROJECT_ROOT / "output"


def load_workflow(name: str) -> dict:
    with open(WORKFLOWS_DIR / name) as f:
        return json.load(f)


def queue_prompt(prompt: dict) -> str:
    """Queue a prompt to ComfyUI and return the prompt_id."""
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=payload,
                                headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    return result.get("prompt_id", "")


def wait_for_completion(prompt_id: str, timeout: int = 600) -> bool:
    """Poll ComfyUI history until the prompt completes."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def find_output_images(prefix: str) -> list[Path]:
    """Find generated images in ComfyUI output directory matching prefix."""
    results = []
    for f in sorted(COMFYUI_OUTPUT.iterdir()):
        if f.name.startswith(prefix) and f.suffix in (".png", ".jpg", ".webp"):
            results.append(f)
    return results


def copy_to_input(src_path: Path) -> str:
    """Copy an image to ComfyUI's input folder and return the filename."""
    input_dir = COMFYUI_OUTPUT.parent / "input"
    input_dir.mkdir(exist_ok=True)
    dest = input_dir / src_path.name
    shutil.copy2(src_path, dest)
    return src_path.name


def generate_t2i(prompt_text: str, prefix: str, seed: int = 42,
                 width: int = 1024, height: int = 1024) -> Path | None:
    """Generate a text-to-image using Flux2 via ComfyUI."""
    workflow = load_workflow("flux2_t2i_shot.json")
    workflow["6"]["inputs"]["text"] = prompt_text
    workflow["9"]["inputs"]["filename_prefix"] = prefix
    workflow["25"]["inputs"]["noise_seed"] = seed
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    workflow["17"]["inputs"]["width"] = width
    workflow["17"]["inputs"]["height"] = height

    print(f"  [T2I] Queuing: {prefix}")
    prompt_id = queue_prompt(workflow)
    if not prompt_id:
        print(f"  [T2I] ERROR: Failed to queue prompt for {prefix}")
        return None

    print(f"  [T2I] Waiting for {prompt_id}...")
    if not wait_for_completion(prompt_id):
        print(f"  [T2I] ERROR: Timeout waiting for {prefix}")
        return None

    time.sleep(1)  # Brief delay for file system
    images = find_output_images(prefix)
    if images:
        print(f"  [T2I] Done: {images[-1].name}")
        return images[-1]
    print(f"  [T2I] WARNING: No output image found for {prefix}")
    return None


def generate_i2i(prompt_text: str, input_image: Path, prefix: str,
                 seed: int = 42, denoise: float = 0.4) -> Path | None:
    """Generate an image-to-image refinement using Flux2 via ComfyUI."""
    workflow = load_workflow("flux2_i2i_refine.json")
    img_name = copy_to_input(input_image)
    workflow["1"]["inputs"]["image"] = img_name
    workflow["6"]["inputs"]["text"] = prompt_text
    workflow["9"]["inputs"]["filename_prefix"] = prefix
    workflow["25"]["inputs"]["noise_seed"] = seed
    workflow["17"]["inputs"]["denoise"] = denoise

    print(f"  [I2I] Queuing: {prefix} (denoise={denoise})")
    prompt_id = queue_prompt(workflow)
    if not prompt_id:
        print(f"  [I2I] ERROR: Failed to queue prompt for {prefix}")
        return None

    print(f"  [I2I] Waiting for {prompt_id}...")
    if not wait_for_completion(prompt_id):
        print(f"  [I2I] ERROR: Timeout waiting for {prefix}")
        return None

    time.sleep(1)
    images = find_output_images(prefix)
    if images:
        print(f"  [I2I] Done: {images[-1].name}")
        return images[-1]
    print(f"  [I2I] WARNING: No output image found for {prefix}")
    return None


# ─── Pipeline stages ─────────────────────────────────────────────────────────

def generate_character_portraits() -> dict[str, Path]:
    """Generate portrait images for each character."""
    print("\n═══ Generating Character Portraits ═══")
    results = {}
    for cid, char in CHARACTERS.items():
        out_dir = OUTPUT_DIR / "characters"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{cid}.png"
        if dest.exists():
            print(f"  [SKIP] {cid}.png already exists")
            results[cid] = dest
            continue

        img = generate_t2i(
            prompt_text=char["portrait_prompt"],
            prefix=f"char_{cid}",
            seed=char["voice_seed"],
        )
        if img:
            shutil.copy2(img, dest)
            results[cid] = dest
    return results


def generate_scene_backgrounds() -> dict[str, Path]:
    """Generate background images for each location."""
    print("\n═══ Generating Scene Backgrounds ═══")
    results = {}
    for loc_id, loc_desc in LOCATIONS.items():
        out_dir = OUTPUT_DIR / "scenes"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{loc_id}.png"
        if dest.exists():
            print(f"  [SKIP] {loc_id}.png already exists")
            results[loc_id] = dest
            continue

        img = generate_t2i(
            prompt_text=loc_desc,
            prefix=f"scene_{loc_id}",
            seed=100 + hash(loc_id) % 1000,
        )
        if img:
            shutil.copy2(img, dest)
            results[loc_id] = dest
    return results


def generate_shot_images(scene_bgs: dict[str, Path]) -> dict[str, Path]:
    """Generate composed shot images for each scene, then refine via i2i."""
    print("\n═══ Generating Shot Images ═══")
    results = {}
    for scene in SCENES:
        sid = scene["id"]
        out_dir = OUTPUT_DIR / "shots"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"shot_{sid}.png"
        if dest.exists():
            print(f"  [SKIP] shot_{sid}.png already exists")
            results[sid] = dest
            continue

        # Step 1: Generate initial shot via text-to-image
        shot_prompt = get_shot_prompt(scene)
        initial = generate_t2i(
            prompt_text=shot_prompt,
            prefix=f"shot_{sid}_raw",
            seed=200 + int(sid),
            width=1024,
            height=768,
        )
        if not initial:
            continue

        # Step 2: Refine via image-to-image for consistency
        # Use the scene background + character descriptions as the refinement prompt
        refine_prompt = (
            f"Photorealistic cinematic still from a TV sitcom. {shot_prompt} "
            f"Consistent lighting, sharp focus, natural skin tones, film grain."
        )
        refined = generate_i2i(
            prompt_text=refine_prompt,
            input_image=initial,
            prefix=f"shot_{sid}_refined",
            seed=200 + int(sid),
            denoise=0.35,
        )
        final_img = refined or initial
        shutil.copy2(final_img, dest)
        results[sid] = dest

    return results


def run_all():
    """Run the complete image generation pipeline."""
    print("╔══════════════════════════════════════════╗")
    print("║  Flux2 Image Generator — Buffering S01   ║")
    print("╚══════════════════════════════════════════╝")

    # Check ComfyUI is running
    try:
        urllib.request.urlopen(f"{COMFYUI_URL}/system_stats")
        print("✓ ComfyUI is running")
    except Exception:
        print("✗ ComfyUI is not running at", COMFYUI_URL)
        print("  Start it with: cd ComfyUI && python main.py --force-fp16")
        return {}

    chars = generate_character_portraits()
    scenes = generate_scene_backgrounds()
    shots = generate_shot_images(scenes)

    print(f"\n═══ Summary ═══")
    print(f"  Characters: {len(chars)}")
    print(f"  Scenes: {len(scenes)}")
    print(f"  Shots: {len(shots)}")
    return {"characters": chars, "scenes": scenes, "shots": shots}


if __name__ == "__main__":
    run_all()
