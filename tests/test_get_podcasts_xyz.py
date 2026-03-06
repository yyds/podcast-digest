"""Tests for get_podcasts_xyz module."""
import json

import pytest

from get_podcasts_xyz import _safe_anchor_id, load_processed, load_channels, save_processed


class TestSafeAnchorId:
    def test_simple_ids(self):
        assert _safe_anchor_id("My Podcast", "ep-123") == "MyPodcast-ep-123"

    def test_strips_special_chars(self):
        result = _safe_anchor_id("Podcast Name", "ep/with/slash")
        assert "/" not in result
        assert "epwithslash" in result or "withslash" in result

    def test_truncates_long_ids(self):
        long_id = "a" * 50
        result = _safe_anchor_id("Pod", long_id)
        assert len(result) <= 50  # prefix + slug, both truncated

    def test_http_url_id(self):
        result = _safe_anchor_id("Chan", "https://example.com/ep/xyz")
        assert "xyz" in result or "ep" in result


class TestLoadSaveProcessed:
    def test_load_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("get_podcasts_xyz.PROCESSED_FILE", str(tmp_path / "missing.json"))
        assert load_processed() == set()

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        path = tmp_path / "processed.json"
        monkeypatch.setattr("get_podcasts_xyz.PROCESSED_FILE", str(path))

        processed = {"ep1", "ep2"}
        save_processed(processed)
        assert load_processed() == processed


class TestLoadChannels:
    def test_load_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("get_podcasts_xyz.CHANNELS_FILE", str(tmp_path / "missing.json"))
        assert load_channels() == []
