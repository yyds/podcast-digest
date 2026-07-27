import os
import json
import time
from datetime import date
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
MODEL = "deepseek-v4-flash"
MAX_RETRIES = 3

GITHUB_PROMPT = """You are a senior tech analyst specializing in open source projects. Below are today's GitHub TypeScript trending repos.

For each repo, produce a bilingual (English + Chinese) summary. Output JSON with these fields per item:

**en_title:** 8-12 word English one-liner capturing the core value
**cn_title:** 10-18字中文一句话标题，精准概括核心价值
**en_what:** One English sentence — what it does, what problem it solves
**cn_what:** 一句中文 — 做什么的、解决什么问题
**features:** 2-3 key features/tech highlights (short phrases, use English tech terms)
**en_value:** 2-3 English sentences covering: who this is for, use cases, and why it's notable/interesting right now. Do NOT mention star counts or trending rank — focus on substance.
**cn_value:** 2-3句中文，内容和 en_value 对应：适用人群、使用场景、为什么值得关注。不要提 star 数或排名，讲实质性原因。

You have the repo's description, README snippet, and topics as reference.

Requirements:
- Direct, concise, high information density
- No filler phrases like "this project"
- features: short phrases separated by semicolons
- Keep bilingual content aligned in meaning

Repo list:
{items_json}

Output ONLY a raw JSON array (no markdown code fences):
[
  {{
    "index": 1,
    "en_title": "...",
    "cn_title": "...",
    "en_what": "...",
    "cn_what": "...",
    "features": "...",
    "en_value": "...",
    "cn_value": "..."
  }}
]
"""

HN_PROMPT = """You are a senior tech news analyst specializing in Hacker News trending topics. Below are today's top HN stories.

For each story, produce a bilingual (English + Chinese) summary. Output JSON with these fields per item:

**cn_title:** 10-18字中文一句话标题，精准概括核心话题
**en_summary:** 2-3 English sentences covering: what the story is about, why it's trending (controversy / insight / breakthrough), and what's notable about it.
**cn_summary:** 2-3句中文，和 en_summary 对应：讲了什么、为什么热门（争议/洞见/技术突破）、值得关注的点。

Requirements:
- Direct, concise, high information density
- For tech stories: highlight technical points. For business/startup stories: highlight core arguments.
- Objective analysis — no personalized "for you" type endings
- Keep bilingual content aligned in meaning

Story list:
{items_json}

Output ONLY a raw JSON array (no markdown code fences):
[
  {{
    "index": 1,
    "cn_title": "...",
    "en_summary": "...",
    "cn_summary": "..."
  }}
]
"""


def _call_deepseek(prompt):
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = deepseek_client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()
            content = content.strip("```json").strip("```").strip()
            return json.loads(content)
        except Exception as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"[WARN] DeepSeek call failed (attempt {attempt+1}/{MAX_RETRIES}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
    print(f"[ERROR] DeepSeek API call failed after {MAX_RETRIES} attempts: {last_exc}")
    return None


def summarize_github_repos(repos):
    if not repos:
        return []

    items = []
    for i, repo in enumerate(repos, 1):
        items.append({
            "index": i,
            "repo": repo["repo"],
            "description": repo["description"],
            "url": repo["url"],
            "today_stars": repo["today_stars"],
            "readme_snippet": repo.get("readme_snippet", ""),
            "topics": repo.get("topics", []),
        })

    prompt = GITHUB_PROMPT.format(
        items_json=json.dumps(items, ensure_ascii=False, indent=2),
    )

    print(f"[INFO] Summarizing {len(repos)} GitHub repos with DeepSeek...")
    results = _call_deepseek(prompt)
    if not results:
        return repos

    for item in results:
        idx = item.get("index", 0) - 1
        if 0 <= idx < len(repos):
            repos[idx]["en_title"] = item.get("en_title", "")
            repos[idx]["cn_title"] = item.get("cn_title", "")
            repos[idx]["en_what"] = item.get("en_what", "")
            repos[idx]["cn_what"] = item.get("cn_what", "")
            repos[idx]["features"] = item.get("features", "")
            repos[idx]["en_value"] = item.get("en_value", "")
            repos[idx]["cn_value"] = item.get("cn_value", "")

    today = date.today().isoformat()
    archive_dir = os.path.join("archive", today, "trending")
    os.makedirs(archive_dir, exist_ok=True)
    with open(os.path.join(archive_dir, "github_summaries.json"), "w") as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)

    return repos


def summarize_hn_stories(stories):
    if not stories:
        return []

    items = []
    for i, story in enumerate(stories, 1):
        items.append({
            "index": i,
            "title": story["title"],
            "url": story["url"],
            "score": story["score"],
            "comments": story["comments"],
        })

    prompt = HN_PROMPT.format(
        items_json=json.dumps(items, ensure_ascii=False, indent=2),
    )

    print(f"[INFO] Summarizing {len(stories)} HN stories with DeepSeek...")
    results = _call_deepseek(prompt)
    if not results:
        return stories

    for item in results:
        idx = item.get("index", 0) - 1
        if 0 <= idx < len(stories):
            stories[idx]["cn_title"] = item.get("cn_title", "")
            stories[idx]["en_summary"] = item.get("en_summary", "")
            stories[idx]["cn_summary"] = item.get("cn_summary", "")

    today = date.today().isoformat()
    archive_dir = os.path.join("archive", today, "trending")
    os.makedirs(archive_dir, exist_ok=True)
    with open(os.path.join(archive_dir, "hn_summaries.json"), "w") as f:
        json.dump(stories, f, indent=2, ensure_ascii=False)

    return stories
