from pathlib import Path
from unittest.mock import MagicMock, patch

from showrunner.aiservices_client import AIServicesClient
from showrunner.cast_manifest import CastManifest, CharacterProfile, CharacterRef
from showrunner.loader import BeatData, CharacterData, EnvironmentData, EpisodeData, SceneData
from showrunner.silent_renderer import render_silent_beat


def _make_manifest(episode: EpisodeData) -> CastManifest:
    manifest = CastManifest()
    for slug, char in episode.cast.items():
        manifest.add(
            CharacterProfile(
                name=char.name or slug,
                slug=slug,
                visual=char.visual or char.trigger_word,
            )
        )
    return manifest


def test_render_silent_beat_calls_text2image(tmp_path):
    episode = EpisodeData(
        title="Test",
        cast={"Maya": CharacterData(name="Maya", visual="maya young woman", trigger_word="maya")},
        environments={"Kitchen": EnvironmentData(trigger_word="kitchen")},
        scenes=[
            SceneData(
                scene_id="S01",
                environment="Kitchen",
                characters_present=["Maya"],
                beats=[
                    BeatData(
                        beat_id="B01",
                        kind="silent",
                        camera="wide shot",
                        action="Maya stares out the window",
                        duration_sec=4.0,
                        seed=42,
                    )
                ],
            )
        ],
    )
    manifest = _make_manifest(episode)
    client = MagicMock(spec=AIServicesClient)
    client.text2image.return_value = tmp_path / "output" / "beats" / "S01" / "B01.png"

    result = render_silent_beat(
        beat=episode.scenes[0].beats[0],
        scene=episode.scenes[0],
        episode=episode,
        manifest=manifest,
        client=client,
        output_dir=str(tmp_path / "output"),
        run_id="test-run",
    )

    assert client.text2image.call_count == 1
    prompt_arg = client.text2image.call_args[0][0]
    assert "kitchen" in prompt_arg
    assert "maya" in prompt_arg
    assert "window" in prompt_arg
    assert result.endswith("B01.png")


def test_render_silent_beat_without_action_text(tmp_path):
    episode = EpisodeData(
        title="Test",
        cast={"Finn": CharacterData(name="Finn", visual="finn man", trigger_word="finn")},
        environments={"Rooftop": EnvironmentData(trigger_word="rooftop")},
        scenes=[
            SceneData(
                scene_id="S02",
                environment="Rooftop",
                characters_present=["Finn"],
                beats=[
                    BeatData(
                        beat_id="B02",
                        kind="silent",
                        camera="close up",
                        action="",
                        duration_sec=2.0,
                        seed=7,
                    )
                ],
            )
        ],
    )
    manifest = _make_manifest(episode)
    client = MagicMock(spec=AIServicesClient)
    client.text2image.return_value = tmp_path / "output" / "beats" / "S02" / "B02.png"

    result = render_silent_beat(
        beat=episode.scenes[0].beats[0],
        scene=episode.scenes[0],
        episode=episode,
        manifest=manifest,
        client=client,
        output_dir=str(tmp_path / "output"),
        run_id="test-run",
    )

    assert client.text2image.call_count == 1
    assert result.endswith("B02.png")


def test_render_silent_beat_returns_clip_path(tmp_path):
    episode = EpisodeData(
        title="Test",
        cast={"Priya": CharacterData(name="Priya", visual="priya woman", trigger_word="priya")},
        environments={"Office": EnvironmentData(trigger_word="office")},
        scenes=[
            SceneData(
                scene_id="S03",
                environment="Office",
                characters_present=["Priya"],
                beats=[
                    BeatData(
                        beat_id="B03",
                        kind="silent",
                        camera="medium shot",
                        action="Priya types on keyboard",
                        duration_sec=3.0,
                        seed=99,
                    )
                ],
            )
        ],
    )
    manifest = _make_manifest(episode)
    client = MagicMock(spec=AIServicesClient)
    expected = str(tmp_path / "output" / "beats" / "S03" / "B03.png")
    client.text2image.return_value = Path(expected)

    result = render_silent_beat(
        beat=episode.scenes[0].beats[0],
        scene=episode.scenes[0],
        episode=episode,
        manifest=manifest,
        client=client,
        output_dir=str(tmp_path / "output"),
        run_id="test-run",
    )

    assert isinstance(result, str)
    assert result == expected


def test_render_silent_beat_creates_output_directory(tmp_path):
    episode = EpisodeData(
        title="Test",
        cast={"Maya": CharacterData(name="Maya", visual="maya", trigger_word="maya")},
        environments={"Room": EnvironmentData(trigger_word="room")},
        scenes=[
            SceneData(
                scene_id="S04",
                environment="Room",
                characters_present=["Maya"],
                beats=[
                    BeatData(beat_id="B04", kind="silent", camera="wide", action="Waiting", seed=1)
                ],
            )
        ],
    )
    manifest = _make_manifest(episode)
    client = MagicMock(spec=AIServicesClient)
    out = tmp_path / "renders"
    beat_path = out / "test-run" / "beats" / "S04" / "B04.png"
    beat_path.parent.mkdir(parents=True, exist_ok=True)
    beat_path.write_text("fake-image")
    client.text2image.return_value = beat_path

    render_silent_beat(
        beat=episode.scenes[0].beats[0],
        scene=episode.scenes[0],
        episode=episode,
        manifest=manifest,
        client=client,
        output_dir=str(out),
        run_id="test-run",
    )

    assert beat_path.exists()


def test_render_silent_beat_passes_seed(tmp_path):
    episode = EpisodeData(
        title="Test",
        cast={"X": CharacterData(name="X", visual="x", trigger_word="x")},
        environments={"E": EnvironmentData(trigger_word="e")},
        scenes=[
            SceneData(
                scene_id="S05",
                environment="E",
                characters_present=["X"],
                beats=[
                    BeatData(beat_id="B05", kind="silent", camera="shot", action="foo", seed=123)
                ],
            )
        ],
    )
    manifest = _make_manifest(episode)
    client = MagicMock(spec=AIServicesClient)
    client.text2image.return_value = tmp_path / "out.png"

    render_silent_beat(
        beat=episode.scenes[0].beats[0],
        scene=episode.scenes[0],
        episode=episode,
        manifest=manifest,
        client=client,
        output_dir=str(tmp_path),
        run_id="r",
    )

    _kwargs = client.text2image.call_args[1]
    assert _kwargs.get("seed") == 123


def test_render_silent_beat_missing_character_in_manifest(tmp_path):
    episode = EpisodeData(
        title="Test",
        cast={"Ghost": CharacterData(name="Ghost", visual="ghost", trigger_word="ghost")},
        environments={"Hall": EnvironmentData(trigger_word="hall")},
        scenes=[
            SceneData(
                scene_id="S06",
                environment="Hall",
                characters_present=["Ghost"],
                beats=[
                    BeatData(beat_id="B06", kind="silent", camera="shot", action="glide", seed=0)
                ],
            )
        ],
    )
    manifest = CastManifest()
    client = MagicMock(spec=AIServicesClient)
    client.text2image.return_value = tmp_path / "out.png"

    result = render_silent_beat(
        beat=episode.scenes[0].beats[0],
        scene=episode.scenes[0],
        episode=episode,
        manifest=manifest,
        client=client,
        output_dir=str(tmp_path),
        run_id="r",
    )

    assert client.text2image.call_count == 1
    assert result.endswith(".png")
