from __future__ import annotations

import pytest
from pydantic import ValidationError

from showrunner.schemas.cast import (
    CastCharacter,
    CastManifest,
    VisualReference,
    VoiceProfile,
)


class TestVisualReference:
    def test_defaults(self):
        v = VisualReference()
        assert v.front == ""
        assert v.extra == []

    def test_with_paths(self):
        v = VisualReference(
            front="f.png", three_quarter="3q.png", profile="p.png", extra=["e1.png"]
        )
        assert v.front == "f.png"
        assert "e1.png" in v.extra


class TestVoiceProfile:
    def test_default_pitch_speed(self):
        v = VoiceProfile(voice_id="v1")
        assert v.pitch == pytest.approx(1.0)
        assert v.speed == pytest.approx(1.0)

    def test_valid_pitch_range(self):
        v = VoiceProfile(voice_id="v1", pitch=0.5)
        assert v.pitch == pytest.approx(0.5)
        v2 = VoiceProfile(voice_id="v1", pitch=2.0)
        assert v2.pitch == pytest.approx(2.0)

    @pytest.mark.parametrize("bad_pitch", [0.4, 2.1, -1.0])
    def test_invalid_pitch(self, bad_pitch):
        with pytest.raises(ValidationError):
            VoiceProfile(voice_id="v1", pitch=bad_pitch)

    @pytest.mark.parametrize("bad_speed", [0.4, 2.1, -1.0])
    def test_invalid_speed(self, bad_speed):
        with pytest.raises(ValidationError):
            VoiceProfile(voice_id="v1", speed=bad_speed)


class TestCastCharacter:
    def test_minimal(self):
        c = CastCharacter(name="Maya Chen", slug="maya")
        assert c.name == "Maya Chen"
        assert c.slug == "maya"

    @pytest.mark.parametrize("bad_name", [""])
    def test_invalid_name(self, bad_name):
        with pytest.raises(ValidationError):
            CastCharacter(name=bad_name, slug="maya")

    @pytest.mark.parametrize("bad_slug", ["", "   ", "Maya", "maya chen", "123abc"])
    def test_invalid_slug(self, bad_slug):
        with pytest.raises(ValidationError):
            CastCharacter(name="Maya", slug=bad_slug)

    def test_full_character(self):
        c = CastCharacter(
            name="Maya Chen",
            slug="maya",
            description="Lead engineer at startup",
            age="late 20s",
            gender="female",
            ethnicity="East Asian",
            visual_refs=VisualReference(front="cast/maya/front.png"),
            voice=VoiceProfile(voice_id="maya_v1", pitch=1.1, speed=0.95),
            lora="models/lora/maya.safetensors",
        )
        assert c.description == "Lead engineer at startup"
        assert c.age == "late 20s"
        assert c.gender == "female"
        assert c.ethnicity == "East Asian"
        assert c.visual_refs.front == "cast/maya/front.png"
        assert c.voice.voice_id == "maya_v1"
        assert c.lora == "models/lora/maya.safetensors"

    def test_no_voice_or_lora(self):
        c = CastCharacter(name="Derek Okafor", slug="derek")
        assert c.voice is None
        assert c.lora is None


class TestCastManifest:
    def test_empty_manifest(self):
        m = CastManifest()
        assert m.characters == {}
        assert m.version == "1.0"

    def test_add_characters(self):
        m = CastManifest(
            characters={
                "maya": CastCharacter(name="Maya Chen", slug="maya"),
                "derek": CastCharacter(name="Derek Okafor", slug="derek"),
            }
        )
        assert len(m.characters) == 2
        assert m.characters["maya"].name == "Maya Chen"

    def test_serialization_round_trip(self):
        m = CastManifest(
            characters={
                "maya": CastCharacter(
                    name="Maya Chen",
                    slug="maya",
                    age="late 20s",
                    ethnicity="East Asian",
                    visual_refs=VisualReference(front="ref.png"),
                    voice=VoiceProfile(voice_id="mv1", pitch=1.2),
                    lora="maya.safetensors",
                ),
            }
        )
        data = m.model_dump()
        restored = CastManifest.model_validate(data)
        assert restored.characters["maya"].name == "Maya Chen"
        assert restored.characters["maya"].voice.voice_id == "mv1"
        assert restored.characters["maya"].voice.pitch == pytest.approx(1.2)
        assert restored.characters["maya"].lora == "maya.safetensors"
