from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class _CharData:
    profile: str
    trigger_word: str


@dataclass(frozen=True)
class _EnvData:
    profile: str
    trigger_word: str


@dataclass(frozen=True)
class _ShotData:
    shot_id: str
    camera_angle: str
    action_start: str
    action_end: str
    audio_path: str
    seed: int


@dataclass(frozen=True)
class _SceneData:
    scene_id: str
    environment: str
    characters_present: list
    shots: list


@dataclass(frozen=True)
class _EpisodeData:
    title: str
    cast: dict
    environments: dict
    scenes: list


@pytest.fixture
def sample_episode():
    return _EpisodeData(
        title="Test",
        cast={
            "Jerry": _CharData("jerry_v2", "jry_guy, wearing a puffy shirt"),
            "George": _CharData("george_v1", "grg_man, wearing a red jacket"),
        },
        environments={
            "Apt": _EnvData("apt_v1", "90s apartment, couch, daylight"),
        },
        scenes=[
            _SceneData(
                "S01",
                "Apt",
                ["Jerry", "George"],
                [
                    _ShotData(
                        "S01_SH01",
                        "wide shot of Jerry and George talking",
                        "Jerry standing, George sitting",
                        "Jerry pointing, George nodding",
                        "audio/s1.wav",
                        42,
                    ),
                ],
            ),
        ],
    )


def test_build_start_prompt_combines_all_elements(sample_episode):
    from sitcom_pilot.prompts import PromptBuilder

    builder = PromptBuilder()
    scene = sample_episode.scenes[0]
    shot = scene.shots[0]
    prompt = builder.build_start_prompt(shot, scene, sample_episode)
    assert "90s apartment, couch, daylight" in prompt
    assert "jry_guy, wearing a puffy shirt" in prompt
    assert "grg_man, wearing a red jacket" in prompt
    assert "wide shot of Jerry and George talking" in prompt
    assert "Jerry standing, George sitting" in prompt
    assert "RAW photo, 8k" in prompt


def test_build_end_prompt_uses_action_end(sample_episode):
    from sitcom_pilot.prompts import PromptBuilder

    builder = PromptBuilder()
    scene = sample_episode.scenes[0]
    shot = scene.shots[0]
    prompt = builder.build_end_prompt(shot, scene, sample_episode)
    assert "Jerry pointing, George nodding" in prompt
    assert "RAW photo, 8k" in prompt


def test_build_start_prompt_no_characters():
    from sitcom_pilot.prompts import PromptBuilder

    builder = PromptBuilder()
    episode = _EpisodeData(
        title="T",
        cast={},
        environments={"Rooftop": _EnvData("roof", "rooftop at dusk")},
        scenes=[
            _SceneData(
                "S1",
                "Rooftop",
                [],
                [_ShotData("S1_SH1", "establishing shot", "empty", "empty", "a.wav", 1)],
            ),
        ],
    )
    prompt = builder.build_start_prompt(
        episode.scenes[0].shots[0], episode.scenes[0], episode
    )
    assert "rooftop at dusk" in prompt


def test_start_and_end_prompts_differ(sample_episode):
    from sitcom_pilot.prompts import PromptBuilder

    builder = PromptBuilder()
    scene = sample_episode.scenes[0]
    shot = scene.shots[0]
    start = builder.build_start_prompt(shot, scene, sample_episode)
    end = builder.build_end_prompt(shot, scene, sample_episode)
    assert start != end


def test_build_end_prompt_contains_action_end_not_start(sample_episode):
    from sitcom_pilot.prompts import PromptBuilder
    builder = PromptBuilder()
    scene = sample_episode.scenes[0]
    shot = scene.shots[0]
    prompt = builder.build_end_prompt(shot, scene, sample_episode)
    assert "Jerry pointing, George nodding" in prompt
    assert "Jerry standing, George sitting" not in prompt


def test_build_start_prompt_contains_action_start_not_end(sample_episode):
    from sitcom_pilot.prompts import PromptBuilder
    builder = PromptBuilder()
    scene = sample_episode.scenes[0]
    shot = scene.shots[0]
    prompt = builder.build_start_prompt(shot, scene, sample_episode)
    assert "Jerry standing, George sitting" in prompt
    assert "Jerry pointing, George nodding" not in prompt


def test_build_end_prompt_contains_env_and_chars(sample_episode):
    from sitcom_pilot.prompts import PromptBuilder
    builder = PromptBuilder()
    scene = sample_episode.scenes[0]
    shot = scene.shots[0]
    prompt = builder.build_end_prompt(shot, scene, sample_episode)
    assert "90s apartment, couch, daylight" in prompt
    assert "jry_guy, wearing a puffy shirt" in prompt
