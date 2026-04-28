"""Test fixtures for Sitcom Pilot."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def sample_episode():
    """Provide a sample episode for testing."""
    return {
        "show": "Buffering",
        "season": 1,
        "episode": 1,
        "title": "Test Episode",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": []
    }


@pytest.fixture
def sample_episode_path(tmp_path, sample_episode):
    """Provide a path to a sample episode file."""
    path = tmp_path / "episode.json"
    path.write_text(json.dumps(sample_episode), encoding="utf-8")
    return path
