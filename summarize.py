import os
import re
import json
from datetime import date
from google import genai
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

with open("config.json") as _f:
    _reader = json.load(_f)["reader"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash-lite"

client = genai.Client(api_key=GEMINI_API_KEY)

_yta = YouTubeTranscriptApi()

def get_transcript(video_id, lang='en'):
    """Fetch transcript. Uses lang hint to prioritize English or Chinese."""
    en = ('en', 'en-US', 'en-orig')
    zh = ('zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW')
    lang_groups = [zh, en] if lang == 'zh' else [en, zh]
    for langs in lang_groups:
        try:
            snippets = list(_yta.fetch(video_id, languages=langs))
            if snippets:
                lines = []
                for s in snippets:
                    start = int(s.start)
                    text = s.text.strip()
                    if text and text != "\n":
                        lines.append(f"[{start//60:02d}:{start%60:02d}] {text}")
                return "\n".join(lines) if lines else None
        except Exception:
            continue
    print(f"[WARN] No transcript found for {video_id}")
    return None

PROMPT_TEMPLATE = """You are an expert research analyst and content strategist.

You will receive a YouTube video. Use the title and description below to correct any transcription errors, especially names, companies, and technical terms.

VIDEO TITLE: {title}
CHANNEL: {channel}
DESCRIPTION: {description}

Write in clear, direct prose. Never say "In this video" or "The host discusses." Each section should stand alone — the reader has not watched the video.

LANGUAGE RULE: If the transcript is in Chinese, write the entire digest in Chinese — do not translate. Keep the section headers (### Part 1:, ### Part 2:, etc.) exactly as shown. For Chinese responses, use Chinese sub-labels: 总体摘要, 关键点, 关键主题, 结论, 引用, 重要性, 如何应用, 核心论点, 锚点引用.

READER CONTEXT:
The reader is {reader_name} — {reader_profile}

PRIVACY: Never mention the reader's employer or company by name in the output. Use generic terms like "your company", "consumer AI", "your product" instead. This applies to all sections, especially Part 3.

---

OUTPUT FORMAT (markdown, compact — no extra blank lines between items):

**Host(s):** [names]
**Guest(s):** [names, or N/A]

### Part 1: Podcast Overview & Key Recommendations
**Overall Summary:** [2–3 sentences — core argument and why it matters]
**Key Topics:**
1. [Topic]: [2–3 sentence description]
2. [repeat for all major topics]
**Conclusion:** [1–2 sentences on the closing argument or takeaway]

### Part 2: Key Themes, Technological Insights & Core Discussion Points
[Extract exactly 5 themes. Format timestamps as [MM:SS] exactly — they will be converted to clickable links.]
1. [Theme]: [Description]
   Quote: [MM:SS] "[exact words from speaker]"
2. [Theme]: [Description]
   Quote: [MM:SS] "[exact words from speaker]"
3. [Theme]: [Description]
   Quote: [MM:SS] "[exact words from speaker]"
4. [Theme]: [Description]
   Quote: [MM:SS] "[exact words from speaker]"
5. [Theme]: [Description]
   Quote: [MM:SS] "[exact words from speaker]"

### Part 3: Actionable Suggestions & Theses for {reader_name}
[Tailored to {reader_name}'s background: {reader_background}. Minimum 3 suggestions.]
1. [Suggestion or thesis]
   - Why it matters: ...
   - How to apply: ...
2. [Suggestion or thesis]
   - Why it matters: ...
   - How to apply: ...
3. [Suggestion or thesis]
   - Why it matters: ...
   - How to apply: ...

### Part 4: Noteworthy Observations & Unique Perspectives
[Surprising, contrarian, or non-obvious takes. Include direct quotes with timestamps.]
1. [Observation]
   Quote: [MM:SS] "[quote]"

### Part 5: Lessons Learned & Success Factors
[What made them successful. If they describe a tutorial, project, or process — list the exact steps so {reader_name} can replicate it.]
- [Lesson or step]

### Part 6: Companies & Entities Mentioned
[Every company, product, person, or institution actually discussed — exclude the podcast channel itself and any sponsors. No URLs. Just name and context.]
1. [Name] — [1 sentence context]
2. [repeat]

### Part 7: Tweet-sized Takeaways
[5 tweet-sized takeaways. Each: strong quote or insight + hook line + hashtags. Under 280 characters each.]
1. "[Quote]" — [Speaker]. [Hook]. #[tag] #[tag]

### Part 8: Essay Angles
[3 ideas. Each: title, core argument (2 sentences), anchor quote with optional timestamp for jump-to.]
1. Title: "[Title]"
   Core Argument: [2 sentences]
   Anchor Quote: [MM:SS] "[quote]"   (include [MM:SS] timestamp if available, like Part 2)
"""

BRIEF_PROMPT_TEMPLATE = """You are an expert content analyst.

You will receive a short YouTube video (under 20 minutes). Use the title and description below to correct any transcription errors, especially names, companies, and technical terms.

VIDEO TITLE: {title}
CHANNEL: {channel}
DESCRIPTION: {description}

Write in clear, direct prose. Never say "In this video" or "The host discusses." The reader has not watched the video.

LANGUAGE RULE: If the transcript is in Chinese, write the entire output in Chinese and use these labels: **快速摘要：** and **关键点：**

OUTPUT FORMAT (markdown, compact):

**Quick Take:** [2–3 sentences — core argument and why it matters]
**Key Points:**
- [Most important single-sentence insight]
- [Second key point]
- [Third key point]
- [Additional point if warranted]
"""


def summarize_video(video):
    transcript = get_transcript(video["video_id"], video.get("lang", "en"))
    if not transcript:
        print(f"[WARN] No transcript available for: {video['title']}")
        return None

    prompt = PROMPT_TEMPLATE.format(
        title=video["title"],
        channel=video["channel"],
        description=video["description"],
        url=video["url"],
        reader_name=_reader["name"],
        reader_profile=_reader["profile"],
        reader_background=_reader["background"],
    )

    full_prompt = f"{prompt}\n\n---\n\nTRANSCRIPT:\n{transcript}"

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=full_prompt
        )

        digest = response.text

        # Save to archive
        today = date.today().isoformat()
        archive_dir = os.path.join("archive", today)
        os.makedirs(archive_dir, exist_ok=True)

        slug = re.sub(r"[^a-z0-9]+", "-", video["title"].lower())[:50]
        filepath = os.path.join(archive_dir, f"{slug}.md")

        with open(filepath, "w") as f:
            f.write(f"# {video['title']}\n")
            f.write(f"**Channel:** {video['channel']}\n")
            f.write(f"**URL:** {video['url']}\n\n")
            f.write(digest)

        print(f"[INFO] Saved digest to {filepath}")
        return digest

    except Exception as e:
        print(f"[ERROR] Failed to summarize {video['title']}: {e}")
        return None


def summarize_video_brief(video):
    """Generate a compact Quick Take digest for short videos (under 20 min)."""
    transcript = get_transcript(video["video_id"], video.get("lang", "en"))
    if not transcript:
        print(f"[WARN] No transcript available for: {video['title']}")
        return None

    prompt = BRIEF_PROMPT_TEMPLATE.format(
        title=video["title"],
        channel=video["channel"],
        description=video["description"],
    )
    full_prompt = f"{prompt}\n\n---\n\nTRANSCRIPT:\n{transcript}"

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=full_prompt
        )
        digest = response.text

        today = date.today().isoformat()
        archive_dir = os.path.join("archive", today)
        os.makedirs(archive_dir, exist_ok=True)

        slug = re.sub(r"[^a-z0-9]+", "-", video["title"].lower())[:50]
        filepath = os.path.join(archive_dir, f"brief-{slug}.md")

        with open(filepath, "w") as f:
            f.write(f"# {video['title']}\n")
            f.write(f"**Channel:** {video['channel']}\n")
            f.write(f"**URL:** {video['url']}\n\n")
            f.write(digest)

        print(f"[INFO] Saved brief digest to {filepath}")
        return digest

    except Exception as e:
        print(f"[ERROR] Failed to brief-summarize {video['title']}: {e}")
        return None


if __name__ == "__main__":
    # Quick test with a sample video
    test_video = {
        "video_id": "test",
        "title": "Test Video",
        "channel": "Test Channel",
        "description": "A test video",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
    result = summarize_video(test_video)
    if result:
        print("\n--- DIGEST ---")
        print(result[:500], "...")
