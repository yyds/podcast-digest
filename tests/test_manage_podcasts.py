"""Tests for manage_podcasts module."""
import json

import pytest

from manage_podcasts import extract_search_term, load, save


class TestExtractSearchTerm:
    def test_apple_podcasts_url(self):
        url = "https://podcasts.apple.com/us/podcast/some-podcast-name/id123456789"
        term, label = extract_search_term(url)
        assert term == "some podcast name"
        assert "Apple" in label

    def test_free_text(self):
        term, label = extract_search_term("  Lenny's Podcast  ")
        assert term == "Lenny's Podcast"
        assert "search" in label

    def test_free_text_single_word(self):
        term, label = extract_search_term("Lex Fridman")
        assert term == "Lex Fridman"
        assert label == "search: Lex Fridman"


class TestLoadSave:
    def test_load_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("manage_podcasts.CHANNELS_FILE", str(tmp_path / "missing.json"))
        assert load() == []

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        path = tmp_path / "channels.json"
        monkeypatch.setattr("manage_podcasts.CHANNELS_FILE", str(path))

        channels = [{"name": "Test", "rss_url": "https://example.com/feed"}]
        save(channels)
        loaded = load()
        assert loaded == channels
