from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sitcom_pilot.loader import VoiceConfig


@dataclass(frozen=True)
class CharacterRef:
    front: str = ""
    three_quarter: str = ""
    profile: str = ""
    extra: tuple[str, ...] = ()

    @property
    def all_paths(self) -> tuple[str, ...]:
        core = tuple(p for p in (self.front, self.three_quarter, self.profile) if p)
        return core + self.extra


@dataclass(frozen=True)
class WardrobeEntry:
    episode: str = ""
    description: str = ""
    notes: str = ""


@dataclass(frozen=True)
class CharacterProfile:
    name: str = ""
    slug: str = ""
    visual: str = ""
    role: str = ""
    refs: CharacterRef = field(default_factory=CharacterRef)
    lora_path: str | None = None
    voice: VoiceConfig | None = None
    wardrobe: tuple[WardrobeEntry, ...] = ()
    consistency_notes: str = ""

    @property
    def has_refs(self) -> bool:
        return len(self.refs.all_paths) > 0

    @property
    def has_lora(self) -> bool:
        return self.lora_path is not None and self.lora_path != ""


@dataclass
class CastManifest:
    characters: dict[str, CharacterProfile] = field(default_factory=dict)
    version: str = "1.0"

    def get(self, slug: str) -> CharacterProfile | None:
        return self.characters.get(slug)

    def add(self, profile: CharacterProfile) -> None:
        if not profile.slug:
            raise ValueError("CharacterProfile.slug must be non-empty")
        self.characters[profile.slug] = profile

    @property
    def slugs(self) -> list[str]:
        return sorted(self.characters.keys())

    def validate_refs(self, base_dir: Path) -> dict[str, list[str]]:
        missing: dict[str, list[str]] = {}
        for slug, char in self.characters.items():
            for p in char.refs.all_paths:
                full = base_dir / p
                if not full.exists():
                    missing.setdefault(slug, []).append(p)
        return missing

    def to_dict(self) -> dict:
        return _manifest_to_dict(self)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def from_dict(cls, data: dict) -> CastManifest:
        return _manifest_from_dict(data)

    @classmethod
    def load(cls, path: Path) -> CastManifest:
        return cls.from_dict(json.loads(path.read_text()))


def _manifest_to_dict(manifest: CastManifest) -> dict:
    chars = {}
    for slug, char in manifest.characters.items():
        chars[slug] = {
            "name": char.name,
            "slug": char.slug,
            "visual": char.visual,
            "role": char.role,
            "refs": {
                "front": char.refs.front,
                "three_quarter": char.refs.three_quarter,
                "profile": char.refs.profile,
                "extra": list(char.refs.extra),
            },
            "lora_path": char.lora_path,
            "voice": _voice_to_dict(char.voice) if char.voice else None,
            "wardrobe": [
                {"episode": w.episode, "description": w.description, "notes": w.notes}
                for w in char.wardrobe
            ],
            "consistency_notes": char.consistency_notes,
        }
    return {"version": manifest.version, "characters": chars}


def _manifest_from_dict(data: dict) -> CastManifest:
    manifest = CastManifest(version=data.get("version", "1.0"))
    for slug, cdata in data.get("characters", {}).items():
        refs_data = cdata.get("refs", {})
        refs = CharacterRef(
            front=refs_data.get("front", ""),
            three_quarter=refs_data.get("three_quarter", ""),
            profile=refs_data.get("profile", ""),
            extra=tuple(refs_data.get("extra", [])),
        )
        voice_data = cdata.get("voice")
        voice = _voice_from_dict(voice_data) if voice_data else None
        wardrobe = tuple(
            WardrobeEntry(
                episode=w.get("episode", ""),
                description=w.get("description", ""),
                notes=w.get("notes", ""),
            )
            for w in cdata.get("wardrobe", [])
        )
        profile = CharacterProfile(
            name=cdata.get("name", ""),
            slug=cdata.get("slug") or slug,
            visual=cdata.get("visual", ""),
            role=cdata.get("role", ""),
            refs=refs,
            lora_path=cdata.get("lora_path"),
            voice=voice,
            wardrobe=wardrobe,
            consistency_notes=cdata.get("consistency_notes", ""),
        )
        manifest.characters[profile.slug] = profile
    return manifest


def _voice_to_dict(voice: VoiceConfig) -> dict:
    return {
        "provider": voice.provider,
        "voice_id": voice.voice_id,
        "clone_from": voice.clone_from,
        "seed": voice.seed,
        "temperature": voice.temperature,
        "language": voice.language,
    }


def _voice_from_dict(data: dict) -> VoiceConfig:
    return VoiceConfig(
        provider=data.get("provider", ""),
        voice_id=data.get("voice_id", ""),
        clone_from=data.get("clone_from", ""),
        seed=data.get("seed", 0),
        temperature=data.get("temperature", 0.8),
        language=data.get("language", "en"),
    )
