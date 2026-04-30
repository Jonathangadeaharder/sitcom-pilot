from __future__ import annotations

from sitcom_pilot.cast_manifest import CastManifest, CharacterProfile
from sitcom_pilot.loader import BeatData, EpisodeData, SceneData


def build_character_prompt(
    character: CharacterProfile,
    *,
    include_wardrobe: bool = True,
    episode_id: str = "",
) -> str:
    parts = [character.visual]
    if include_wardrobe and episode_id and character.wardrobe:
        for w in character.wardrobe:
            if w.episode == episode_id and w.description:
                parts.append(f"Wardrobe: {w.description}")
                break
    if character.consistency_notes:
        parts.append(character.consistency_notes)
    return ", ".join(parts)


def build_scene_prompt(
    scene: SceneData,
    episode: EpisodeData,
    manifest: CastManifest,
    *,
    episode_id: str = "",
) -> str:
    env = episode.environments.get(scene.environment)
    env_desc = env.trigger_word if env else scene.environment
    char_parts = []
    for name in scene.characters_present:
        char = manifest.get(name)
        if char:
            char_parts.append(build_character_prompt(char, episode_id=episode_id))
        else:
            raw = episode.cast.get(name)
            if raw:
                char_parts.append(raw.visual or raw.name)
    parts = [p for p in [env_desc] + char_parts if p]
    return ", ".join(parts)


def build_beat_prompt(
    beat: BeatData,
    scene: SceneData,
    episode: EpisodeData,
    manifest: CastManifest,
    *,
    episode_id: str = "",
) -> str:
    scene_prompt = build_scene_prompt(scene, episode, manifest, episode_id=episode_id)
    action = beat.action or beat.dialogue or ""
    quality = "RAW photo, 8k resolution, cinematic lighting"
    parts = [p for p in [scene_prompt, action, quality] if p]
    return ", ".join(parts)
