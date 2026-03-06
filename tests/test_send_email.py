"""Tests for send_email module — parsing, rendering, HTML generation."""
import pytest

from send_email import (
    bold,
    build_email_html,
    build_toc,
    card_anchor,
    make_timestamp_link,
    parse_header,
    render_card,
    render_section_1,
    render_section_2,
    render_section_3,
    render_section_4,
    render_section_5,
    render_section_6,
    render_section_7,
    render_section_8,
    split_sections,
)


class TestBold:
    def test_converts_double_asterisks(self):
        assert bold("**hello**") == "<strong>hello</strong>"
        assert bold("**Host(s):** Lenny") == "<strong>Host(s):</strong> Lenny"

    def test_leaves_plain_text(self):
        assert bold("no bold here") == "no bold here"


class TestMakeTimestampLink:
    def test_youtube_converts_timestamp(self):
        url = "https://www.youtube.com/watch?v=abc"
        result = make_timestamp_link("Quote: [05:30] \"hello\"", url)
        assert "t=330s" in result
        assert 'href="https://www.youtube.com/watch?v=abc&t=330s"' in result

    def test_hhmmss_format(self):
        url = "https://youtube.com/watch?v=x"
        result = make_timestamp_link("[1:05:30] quote", url)
        assert "t=3930s" in result

    def test_multiple_timestamps(self):
        url = "https://youtube.com/watch?v=x"
        text = "[00:30] first [01:00] second"
        result = make_timestamp_link(text, url)
        assert "t=30s" in result
        assert "t=60s" in result


class TestParseHeader:
    def test_english_host_guest(self):
        digest = "**Host(s):** Lenny Rachitsky\n**Guest(s):** Bob Baxley\n\n### Part 1"
        hosts, guests = parse_header(digest)
        assert hosts == "Lenny Rachitsky"
        assert guests == "Bob Baxley"

    def test_chinese_host_guest(self):
        digest = "**主播：** 张三\n**嘉宾：** 李四\n\n### Part 1"
        hosts, guests = parse_header(digest)
        assert hosts == "张三"
        assert guests == "李四"

    def test_default_guests_na(self):
        digest = "**Host(s):** Lenny\n**Guest(s):** N/A\n\nrest"
        _, guests = parse_header(digest)
        assert guests == "N/A"


class TestSplitSections:
    def test_extracts_numbered_parts(self):
        digest = """**Host:** X

### Part 1: Overview
summary here

### Part 2: Themes
themes here
"""
        sections = split_sections(digest)
        assert 1 in sections
        assert 2 in sections
        assert "summary here" in sections[1]
        assert "themes here" in sections[2]

    def test_empty_digest(self):
        assert split_sections("") == {}

    def test_no_parts(self):
        assert split_sections("Just text\nno parts") == {}


class TestRenderSection1:
    def test_parses_overall_summary_and_conclusion(self):
        content = """**Overall Summary:** This is the core argument.
**Key Topics:**
1. Topic A: Description A
2. Topic B: Description B
**Conclusion:** The takeaway.
"""
        html = render_section_1(content, "https://youtube.com/watch?v=x")
        assert "This is the core argument" in html
        assert "The takeaway" in html
        assert "Topic A" in html

    def test_chinese_labels(self):
        content = """**总体摘要：** 核心论点。
**关键主题:**
1. 主题一：说明
**结论：** 总结。
"""
        html = render_section_1(content, "https://x.com", is_chinese=True)
        assert "核心论点" in html
        assert "结论" in html


class TestRenderSection2:
    def test_themes_with_quotes(self):
        content = """1. **Theme One**: Description
   Quote: [05:30] "exact words"
2. **Theme Two**: Another
   Quote: [10:00] "more words"
"""
        html = render_section_2(content, "https://youtube.com/watch?v=x")
        assert "Theme One" in html
        assert "Theme Two" in html
        assert "exact words" in html


class TestRenderSection3:
    def test_actionable_suggestions(self):
        content = """1. First suggestion
   - Why it matters: Important
   - How to apply: Do X
2. Second suggestion
   - Why it matters: Also important
   - How to apply: Do Y
"""
        html = render_section_3(content, "https://x.com")
        assert "First suggestion" in html
        assert "Important" in html
        assert "Do X" in html


class TestRenderSection5:
    def test_bullet_list(self):
        content = """- Lesson one
- Lesson two
- Lesson three
"""
        html = render_section_5(content, "https://x.com")
        assert "Lesson one" in html
        assert "Lesson two" in html


class TestRenderSection6:
    def test_entities_with_dash(self):
        content = """1. Company A — Context for A
2. Person B — Context for B
"""
        html = render_section_6(content, "https://x.com")
        assert "Company A" in html
        assert "Context for A" in html


class TestCardAnchor:
    def test_stable_id(self):
        video = {"video_id": "abc123"}
        assert card_anchor(video) == "vid-abc123"


class TestBuildToc:
    def test_generates_rows(self):
        digests = [
            {"video": {"video_id": "a", "title": "Video A", "channel": "Chan A"}, "digest": ""},
            {"video": {"video_id": "b", "title": "Video B", "channel": "Chan B"}, "digest": ""},
        ]
        html = build_toc(digests)
        assert "Video A" in html
        assert "Video B" in html
        assert "#vid-a" in html
        assert "#vid-b" in html


class TestBuildEmailHtml:
    def test_includes_toc_and_cards(self):
        digests = [
            {
                "video": {"video_id": "x", "title": "Test", "channel": "Chan", "url": "https://x.com"},
                "digest": "**Host(s):** Host\n**Guest(s):** N/A\n\n### Part 1: Overview\n**Overall Summary:** Summary.",
            }
        ]
        html = build_email_html(digests)
        assert "Daily Digest" in html
        assert "Test" in html
        assert "Chan" in html
