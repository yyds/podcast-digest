"""Tests for get_videos module."""
import json

import pytest

from get_videos import load_processed, parse_duration_minutes, save_processed


class TestParseDurationMinutes:
    """Tests for parse_duration_minutes (ISO 8601 duration parser)."""

    def test_seconds_only(self):
        assert parse_duration_minutes("PT45S") == 0.75

    def test_minutes_only(self):
        assert parse_duration_minutes("PT5M") == 5

    def test_hours_minutes_seconds(self):
        assert parse_duration_minutes("PT1H23M45S") == 83.75

    def test_hours_only(self):
        assert parse_duration_minutes("PT2H") == 120

    def test_empty_or_invalid(self):
        assert parse_duration_minutes("") == 0
        assert parse_duration_minutes(None) == 0
        assert parse_duration_minutes("invalid") == 0

    def test_partial_format(self):
        assert parse_duration_minutes("PT30M") == 30
        assert parse_duration_minutes("PT1H30M") == 90


class TestLoadSaveProcessed:
    """Tests for load_processed and save_processed with temp files."""

    def test_load_missing_file_returns_empty_set(self, tmp_path, monkeypatch):
        monkeypatch.setattr("get_videos.PROCESSED_FILE", str(tmp_path / "nonexistent.json"))
        assert load_processed() == set()

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        proc_file = tmp_path / "processed.json"
        monkeypatch.setattr("get_videos.PROCESSED_FILE", str(proc_file))

        processed = {"vid1", "vid2", "vid3"}
        save_processed(processed)
        loaded = load_processed()
        assert loaded == processed

    def test_load_returns_set(self, tmp_path, monkeypatch):
        proc_file = tmp_path / "processed.json"
        monkeypatch.setattr("get_videos.PROCESSED_FILE", str(proc_file))
        proc_file.write_text(json.dumps(["a", "b"]))

        result = load_processed()
        assert result == {"a", "b"}
