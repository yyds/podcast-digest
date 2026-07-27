import re
from bs4 import BeautifulSoup
from trending_utils import http_get_with_retry, filter_consecutive

GITHUB_TRENDING_URL = "https://github.com/trending/{language}?since=daily"
PROCESSED_FILE = "processed_github_trending.json"
TOP_N = 5


def _parse_star_count(text):
    text = text.strip().replace(",", "")
    if text.isdigit():
        return int(text)
    m = re.match(r'([\d.]+)\s*([kKmM])', text)
    if m:
        num = float(m.group(1))
        suffix = m.group(2).lower()
        return int(num * 1000) if suffix == 'k' else int(num * 1000000)
    return 0


def fetch_github_trending(language="typescript"):
    url = GITHUB_TRENDING_URL.format(language=language)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    try:
        resp = http_get_with_retry(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch GitHub trending: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")
    repos = []

    for idx, article in enumerate(articles[:TOP_N * 2]):
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        repo_path = h2.get("href", "").strip("/")
        if not repo_path:
            continue

        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        star_el = article.select_one("a[href$='/stargazers']")
        total_stars = _parse_star_count(star_el.get_text(strip=True)) if star_el else 0

        today_star_el = article.select_one("span.d-inline-block.float-sm-right")
        today_stars_text = today_star_el.get_text(strip=True) if today_star_el else "0"
        today_stars = _parse_star_count(today_stars_text.replace("stars today", "").strip())

        lang_el = article.select_one("span[itemprop='programmingLanguage']")
        language_name = lang_el.get_text(strip=True) if lang_el else ""

        repos.append({
            "rank": idx + 1,
            "repo": repo_path,
            "description": description,
            "url": f"https://github.com/{repo_path}",
            "total_stars": total_stars,
            "today_stars": today_stars,
            "language": language_name,
        })

    return repos[:TOP_N]


def _fetch_readme_snippet(repo_path, max_chars=1500):
    api_url = f"https://api.github.com/repos/{repo_path}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    try:
        resp = http_get_with_retry(api_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return ""
        content = resp.text[:max_chars * 3]
        lines = content.split("\n")
        clean_lines = []
        in_code_block = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if stripped.startswith("#"):
                clean_lines.append(stripped.lstrip("#").strip())
                continue
            if stripped.startswith("![") or stripped.startswith("<img"):
                continue
            if stripped and not stripped.startswith("---") and not stripped.startswith("==="):
                clean_lines.append(stripped)
            if sum(len(l) for l in clean_lines) > max_chars:
                break
        return "\n".join(clean_lines)[:max_chars]
    except Exception as e:
        print(f"[WARN] Failed to fetch README for {repo_path}: {e}")
        return ""


def _fetch_topics(repo_path):
    api_url = f"https://api.github.com/repos/{repo_path}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        resp = http_get_with_retry(api_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("topics", [])
    except Exception:
        return []


def enrich_repo_details(repos):
    print(f"[INFO] Enriching {len(repos)} repos with README details...")
    for repo in repos:
        readme = _fetch_readme_snippet(repo["repo"])
        if readme:
            repo["readme_snippet"] = readme
        topics = _fetch_topics(repo["repo"])
        if topics:
            repo["topics"] = topics
    return repos


def get_new_trending(language="typescript"):
    print(f"[INFO] Fetching GitHub Trending ({language}, daily)...")
    all_repos = fetch_github_trending(language)
    if not all_repos:
        print("[WARN] No repos found on GitHub trending")
        return []

    print(f"[INFO] Found {len(all_repos)} repos on trending")
    filtered = filter_consecutive(all_repos, "repo", PROCESSED_FILE)
    if filtered:
        filtered = enrich_repo_details(filtered)
    print(f"[INFO] {len(filtered)} new repos after consecutive filter")
    return filtered


if __name__ == "__main__":
    repos = get_new_trending("typescript")
    for r in repos:
        print(f"  #{r['rank']} {r['repo']} (+{r['today_stars']} today)")
        print(f"    {r['description'][:80]}")
