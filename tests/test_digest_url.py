"""Tests for digest_url module."""
import pytest

from digest_url import _extract_youtube_id


class TestExtractYoutubeId:
    def test_standard_url(self):
        assert _extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert _extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=abc12345678&list=playlist&t=30"
        assert _extract_youtube_id(url) == "abc12345678"

    def test_invalid_raises(self):
        with pytest.raises(RuntimeError, match="Cannot parse YouTube"):
            _extract_youtube_id("https://example.com/not-youtube")

    def test_empty_raises(self):
        with pytest.raises(RuntimeError, match="Cannot parse YouTube"):
            _extract_youtube_id("")
