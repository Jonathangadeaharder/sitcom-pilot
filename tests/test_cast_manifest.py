from __future__ import annotations

from sitcom_pilot.cast_manifest import (
    CastManifest,
    CharacterProfile,
    CharacterRef,
    WardrobeEntry,
)
from sitcom_pilot.loader import VoiceConfig


class TestCharacterRef:
    def test_all_paths_core_only(self):
        ref = CharacterRef(front="a.png", three_quarter="b.png", profile="c.png")
        assert ref.all_paths == ("a.png", "b.png", "c.png")

    def test_all_paths_with_extras(self):
        ref = CharacterRef(front="a.png", extra=("d.png", "e.png"))
        assert ref.all_paths == ("a.png", "d.png", "e.png")

    def test_all_paths_empty(self):
        ref = CharacterRef()
        assert ref.all_paths == ()


class TestCharacterProfile:
    def test_has_refs_true(self):
        p = CharacterProfile(name="Maya", refs=CharacterRef(front="a.png"))
        assert p.has_refs

    def test_has_refs_false(self):
        p = CharacterProfile(name="Maya")
        assert not p.has_refs

    def test_has_lora_true(self):
        p = CharacterProfile(name="Maya", lora_path="maya.safetensors")
        assert p.has_lora

    def test_has_lora_false(self):
        p = CharacterProfile(name="Maya")
        assert not p.has_lora

    def test_has_lora_empty_string(self):
        p = CharacterProfile(name="Maya", lora_path="")
        assert not p.has_lora


class TestCastManifest:
    def _make_manifest(self):
        return CastManifest(
            characters={
                "maya": CharacterProfile(
                    name="Maya Chen",
                    slug="maya",
                    visual="East Asian woman, late 20s",
                    role="Lead engineer",
                    refs=CharacterRef(
                        front="assets/cast/maya_ref_front.png",
                        three_quarter="assets/cast/maya_ref_3q.png",
                    ),
                    voice=VoiceConfig(provider="mlx-audio", voice_id="maya_v1"),
                    wardrobe=(
                        WardrobeEntry(episode="s01e01", description="purple hoodie"),
                    ),
                ),
                "derek": CharacterProfile(
                    name="Derek Okafor",
                    slug="derek",
                    visual="Black man, early 30s",
                    role="CEO",
                ),
            },
        )

    def test_get_existing(self):
        m = self._make_manifest()
        assert m.get("maya") is not None
        assert m.get("maya").name == "Maya Chen"

    def test_get_missing(self):
        m = self._make_manifest()
        assert m.get("nonexistent") is None

    def test_slugs_sorted(self):
        m = self._make_manifest()
        assert m.slugs == ["derek", "maya"]

    def test_add_character(self):
        m = CastManifest()
        m.add(CharacterProfile(name="Finn", slug="finn"))
        assert m.get("finn") is not None

    def test_validate_refs_missing(self, tmp_path):
        m = self._make_manifest()
        missing = m.validate_refs(tmp_path)
        assert "maya" in missing
        assert len(missing["maya"]) == 2

    def test_validate_refs_exist(self, tmp_path):
        m = CastManifest(
            characters={
                "x": CharacterProfile(
                    slug="x", refs=CharacterRef(front="ref.png")
                ),
            },
        )
        (tmp_path / "ref.png").write_bytes(b"fake")
        missing = m.validate_refs(tmp_path)
        assert "x" not in missing

    def test_round_trip_json(self, tmp_path):
        m = self._make_manifest()
        path = tmp_path / "manifest.json"
        m.save(path)
        loaded = CastManifest.load(path)
        assert loaded.get("maya").name == "Maya Chen"
        assert loaded.get("maya").refs.front == "assets/cast/maya_ref_front.png"
        assert loaded.get("maya").voice.provider == "mlx-audio"
        assert loaded.get("derek").name == "Derek Okafor"

    def test_serialization_structure(self):
        m = self._make_manifest()
        d = m.to_dict()
        assert d["version"] == "1.0"
        assert "maya" in d["characters"]
        assert d["characters"]["maya"]["wardrobe"][0]["episode"] == "s01e01"
