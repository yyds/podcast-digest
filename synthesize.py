"""Weekly synthesis: extract Part 1 from digests and generate cross-content themes."""

import os
import re
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash-lite"

client = genai.Client(api_key=GEMINI_API_KEY)


def _load_reader():
    try:
        with open("config.json") as f:
            return json.load(f).get("reader", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def extract_part1(digest_text: str) -> str:
    """Extract Part 1 content from a digest markdown file.
    
    Returns the text between '### Part 1:' and '### Part 2:'.
    """
    lines = digest_text.split("\n")
    in_part1 = False
    part1_lines = []

    for line in lines:
        if re.match(r"### Part 1:", line):
            in_part1 = True
            continue
        if re.match(r"### Part 2:", line):
            break
        if in_part1:
            part1_lines.append(line)

    return "\n".join(part1_lines).strip()


def parse_digest_metadata(digest_text: str) -> dict:
    """Extract title, channel, and URL from digest header."""
    title, channel, url = "", "", ""
    
    for line in digest_text.split("\n")[:10]:
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("**Channel:**"):
            channel = line.replace("**Channel:**", "").strip()
        elif line.startswith("**播客：**"):
            channel = line.replace("**播客：**", "").strip()
        elif line.startswith("**URL:**"):
            url = line.replace("**URL:**", "").strip()
        elif line.startswith("**链接：**"):
            url = line.replace("**链接：**", "").strip()
    
    return {"title": title, "channel": channel, "url": url}


SYNTHESIS_PROMPT = """You are a research analyst synthesizing a week's worth of content digests.

Below are {count} content summaries numbered [1]–[{count}] from podcasts and YouTube videos.

Your task:
1. Identify 3–5 NON-OBVIOUS underlying trends, theses, or tensions that emerge across multiple pieces of content.
   DO NOT name surface-level topic categories. If all content is about AI, don't say "AI is transforming work" — that's already known. Instead look for:
   - Shifts in conventional wisdom or reversals of prior assumptions
   - Tensions between competing approaches or schools of thought
   - A thesis that multiple sources are building toward, even if they don't say it explicitly
   - Cross-domain patterns that apply beyond the obvious category
   - Emerging risks, inflection points, or underappreciated opportunities
2. For each theme, write 2–3 sentences explaining the insight. Cite contributing sources inline using [N] notation.
3. Highlight 2–3 top observations that were counterintuitive, surprising, or unusually actionable — things you wouldn't conclude from just reading the headline. Cite with [N].

{reader_context}

Style rules (strictly follow):
- Short sentences. One idea per sentence. Max 20 words per sentence.
- Theme description: 2 sentences max. Write like you're explaining it to a smart friend, not writing a report.
- Source lines: max 10 words. State the specific angle, nothing more.
- Insights: one sentence. Direct. State the finding, not the context.
- No filler: cut "it is worth noting", "this suggests that", "in today's landscape", and similar padding.

Follow the output format exactly. Use [N] citations inline — do not list sources separately.

---

OUTPUT FORMAT:

## Converging Signals

- **[Specific insight or thesis, not a topic name]:** [2-3 sentences explaining the pattern and why it matters.]
  - [N] [Exact source title] — [one-line paraphrased takeaway showing this source's specific angle]
  - [N] [Exact source title] — [one-line paraphrased takeaway showing this source's specific angle]
- **[Specific insight or thesis]:** [2-3 sentences.]
  - [N] [Exact source title] — [one-line paraphrased takeaway]
  - [N] [Exact source title] — [one-line paraphrased takeaway]

## Standout Takes

- [Counterintuitive or surprising observation.] [N]
  - [N] [Exact source title]
- [Counterintuitive or surprising observation.] [N]
  - [N] [Exact source title]

---

CONTENT SUMMARIES:

{summaries}
"""


BACKFILL_PROMPT = """For each citation below, write ONE concise line (under 15 words) showing how that source specifically supports the theme it was cited in.

{context}

OUTPUT FORMAT (one line per citation, no extra text):
[N] takeaway text
[N] takeaway text"""


def _backfill_missing_sources(synthesis_md: str, items: list[tuple[str, str]]) -> str:
    """Inject source lines for any [N] citations Gemini cited but forgot to list."""
    lines = synthesis_md.split("\n")

    # Pass 1: collect theme blocks (need LLM) and insight blocks (title-only)
    theme_blocks = []
    current_theme_idx = None
    current_theme_text = ""
    current_cited = set()
    current_sourced = set()
    current_last_idx = None
    in_themes = False
    in_insights = False

    insight_blocks = []
    current_insight_idx = None
    current_insight_cited = set()
    current_insight_sourced = set()
    current_insight_last_idx = None

    for i, line in enumerate(lines):
        s = line.strip()
        is_indented = line.startswith((' ', '\t'))

        if "## Converging Signals" in s:
            in_themes = True
            in_insights = False
            continue
        if "## Standout Takes" in s:
            if current_theme_idx is not None:
                theme_blocks.append((current_theme_text, current_cited.copy(),
                                     current_sourced.copy(), current_last_idx))
            in_themes = False
            in_insights = True
            current_theme_idx = None
            continue

        if in_themes:
            if re.match(r'[-*]\s+\*\*', s) and not is_indented:
                if current_theme_idx is not None:
                    theme_blocks.append((current_theme_text, current_cited.copy(),
                                         current_sourced.copy(), current_last_idx))
                current_theme_idx = i
                current_last_idx = i
                current_theme_text = s
                current_cited = set(int(m.group(1)) for m in re.finditer(r'\[(\d+)\]', s))
                current_sourced = set()
            elif is_indented and current_theme_idx is not None:
                for m in re.finditer(r'\[(\d+)\]', s):
                    current_cited.add(int(m.group(1)))
                if re.match(r'[-*]\s+\[', s):
                    for m in re.finditer(r'\[(\d+)\]', s):
                        current_sourced.add(int(m.group(1)))
                    current_last_idx = i

        elif in_insights:
            if re.match(r'[-*]\s+', s) and not is_indented:
                if current_insight_idx is not None:
                    insight_blocks.append((current_insight_cited.copy(),
                                           current_insight_sourced.copy(),
                                           current_insight_last_idx))
                current_insight_idx = i
                current_insight_last_idx = i
                current_insight_cited = set(int(m.group(1)) for m in re.finditer(r'\[(\d+)\]', s))
                current_insight_sourced = set()
            elif is_indented and current_insight_idx is not None:
                if re.match(r'[-*]\s+\[', s):
                    for m in re.finditer(r'\[(\d+)\]', s):
                        current_insight_sourced.add(int(m.group(1)))
                    current_insight_last_idx = i

    # Save last blocks
    if in_themes and current_theme_idx is not None:
        theme_blocks.append((current_theme_text, current_cited.copy(),
                             current_sourced.copy(), current_last_idx))
    if current_insight_idx is not None:
        insight_blocks.append((current_insight_cited.copy(),
                               current_insight_sourced.copy(),
                               current_insight_last_idx))

    # Pass 2: collect missing citations
    missing = {}  # {n: theme_text} — for LLM takeaway generation
    inject_after = {}  # {line_idx: [n, ...]} — themes (needs LLM)
    inject_after_insights = {}  # {line_idx: [n, ...]} — insights (title-only)

    for theme_text, cited, sourced, last_idx in theme_blocks:
        gap = sorted(cited - sourced)
        if gap:
            for n in gap:
                if 1 <= n <= len(items):
                    missing[n] = theme_text
            inject_after[last_idx] = inject_after.get(last_idx, []) + gap

    for cited, sourced, last_idx in insight_blocks:
        gap = sorted(cited - sourced)
        if gap:
            valid_gap = [n for n in gap if 1 <= n <= len(items)]
            if valid_gap:
                inject_after_insights[last_idx] = inject_after_insights.get(last_idx, []) + valid_gap

    if not missing and not inject_after_insights:
        return synthesis_md

    # Pass 3: one LLM call to generate takeaways for missing theme citations
    new_takeaways = {}
    if missing:
        context_parts = []
        for n, theme_text in sorted(missing.items()):
            title, part1 = items[n - 1]
            context_parts.append(
                f"[{n}] Theme: {theme_text[:200]}\n"
                f"    Title: {title}\n"
                f"    Summary: {part1[:300]}"
            )
        try:
            prompt = BACKFILL_PROMPT.format(context="\n\n".join(context_parts))
            resp = client.models.generate_content(model=MODEL, contents=prompt)
            for line in resp.text.strip().split("\n"):
                m = re.match(r'\[(\d+)\]\s+(.+)', line.strip())
                if m:
                    new_takeaways[int(m.group(1))] = m.group(2).strip()
        except Exception as e:
            print(f"[WARN] Citation backfill failed: {e}")

    # Pass 4: inject missing source lines at the right positions
    result = []
    for i, line in enumerate(lines):
        result.append(line)
        if i in inject_after:
            for n in inject_after[i]:
                title = items[n - 1][0]
                takeaway = new_takeaways.get(n, title)
                result.append(f"  - [{n}] {title} — {takeaway}")
        if i in inject_after_insights:
            for n in inject_after_insights[i]:
                title = items[n - 1][0]
                result.append(f"  - [{n}] {title}")

    return "\n".join(result)


def synthesize_weekly(items: list[tuple[str, str]]) -> str:
    """Generate weekly synthesis from a list of (title, part1) tuples.
    
    Args:
        items: List of (title, part1_content) tuples
        
    Returns:
        Markdown string with common themes and top insights
    """
    if len(items) < 2:
        return ""

    reader = _load_reader()
    reader_context = ""
    if reader.get("name") and reader.get("profile"):
        reader_context = f"The reader is {reader['name']} — {reader['profile']}"

    summaries = ""
    for i, (title, part1) in enumerate(items, 1):
        summaries += f"### [{i}] {title}\n{part1}\n\n"

    prompt = SYNTHESIS_PROMPT.format(
        count=len(items),
        reader_context=reader_context,
        summaries=summaries.strip()
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        synthesis = response.text.strip()
        return _backfill_missing_sources(synthesis, items)
    except Exception as e:
        print(f"[ERROR] Failed to generate weekly synthesis: {e}")
        return ""


if __name__ == "__main__":
    test_items = [
        ("Test Video 1", "This is a summary about AI trends and data quality."),
        ("Test Video 2", "This discusses bootstrapping and startup strategies."),
    ]
    result = synthesize_weekly(test_items)
    if result:
        print("--- SYNTHESIS ---")
        print(result)
