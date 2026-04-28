from sitcom_pilot.node_map import NodeMap


def test_default_node_map_has_required_fields():
    nm = NodeMap()
    assert nm.start_prompt == "6"
    assert nm.end_prompt == "12"
    assert nm.audio == "25"
    assert nm.seed == "3"
    assert nm.env_profile == "40"
    assert nm.char_profiles == ["41", "42", "43"]


def test_custom_node_map_overrides():
    nm = NodeMap(start_prompt="10", end_prompt="20", audio="30", seed="1", env_profile="50", char_profiles=["51", "52"])
    assert nm.start_prompt == "10"
    assert nm.end_prompt == "20"
    assert nm.audio == "30"
    assert nm.seed == "1"
    assert nm.env_profile == "50"
    assert nm.char_profiles == ["51", "52"]


def test_from_dict_creates_node_map():
    data = {"start_prompt": "99", "end_prompt": "88", "audio": "77", "seed": "1", "env_profile": "55", "char_profiles": ["60", "61"]}
    nm = NodeMap.from_dict(data)
    assert nm.start_prompt == "99"
    assert nm.char_profiles == ["60", "61"]


def test_from_dict_uses_defaults_for_missing_keys():
    nm = NodeMap.from_dict({})
    assert nm.start_prompt == "6"
    assert nm.char_profiles == ["41", "42", "43"]


def test_from_dict_partial_override():
    nm = NodeMap.from_dict({"start_prompt": "100"})
    assert nm.start_prompt == "100"
    assert nm.end_prompt == "12"
