"""Shared pytest fixtures."""
import json
import os

import pytest


@pytest.fixture
def temp_processed_file(tmp_path):
    """Temporary processed_videos.json for get_videos tests."""
    path = tmp_path / "processed_videos.json"
    return path


@pytest.fixture
def temp_channels_file(tmp_path):
    """Temporary channels file for tests that need it."""
    path = tmp_path / "channels.json"
    path.write_text(json.dumps([{"handle": "@test", "lang": "en"}]))
    return path
