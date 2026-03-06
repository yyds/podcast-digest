"""Tests for summarize_podcast module helpers."""
import pytest

from summarize_podcast import _parse_retry_seconds


class TestParseRetrySeconds:
    """Tests for Groq 429 rate limit retry parsing."""

    def test_minutes_and_seconds(self):
        msg = "Rate limit exceeded. try again in 2m29.5s"
        assert _parse_retry_seconds(msg) == 154  # 2*60 + 29 + 5 buffer

    def test_minutes_only(self):
        msg = "try again in 3m"
        assert _parse_retry_seconds(msg) == 185  # 3*60 + 5

    def test_seconds_only(self):
        msg = "try again in 45s"
        assert _parse_retry_seconds(msg) == 50  # 45 + 5

    def test_invalid_fallback(self):
        assert _parse_retry_seconds("unknown error") == 60
        assert _parse_retry_seconds("") == 60
