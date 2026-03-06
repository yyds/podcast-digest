#!/usr/bin/env python3
"""
Manage podcast subscriptions.

Usage:
  python manage_podcasts.py list
  python manage_podcasts.py add <xiaoyuzhou_url | apple_podcasts_url | search_term>
  python manage_podcasts.py remove <name_or_number>
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

CHANNELS_FILE = "channels_xyz.json"
ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


def load():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE) as f:
            return json.load(f)
    return []


def save(channels):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(channels, f, indent=2, ensure_ascii=False)


def extract_search_term(raw):
    """
    Accept:
      - Xiaoyuzhou URL → fetch page title as search term
      - Apple Podcasts URL → extract podcast name from URL path
      - Free-text → use as-is
    Returns (search_term, source_label).
    """
    raw = raw.strip()

    # Xiaoyuzhou podcast URL
    if "xiaoyuzhoufm.com/podcast/" in raw:
        name = _scrape_xiaoyuzhou_name(raw)
        if name:
            return name, f"Xiaoyuzhou page: {name}"
        # fallback: can't get name, use URL as hint
        return None, None

    # Apple Podcasts URL — extract from path like /podcast/podcast-name/id123456
    m = re.search(r"podcasts\.apple\.com/.+?/podcast/([^/]+)", raw)
    if m:
        name = m.group(1).replace("-", " ")
        return name, f"Apple Podcasts URL: {name}"

    # Free-text search term
    return raw, f"search: {raw}"


def _scrape_xiaoyuzhou_name(url):
    """Fetch Xiaoyuzhou podcast page and extract the podcast name."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Try __NEXT_DATA__ JSON first
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
        if m:
            data = json.loads(m.group(1))
            # Navigate to podcast title in Next.js page props
            try:
                podcast = data["props"]["pageProps"]["podcast"]
                return podcast.get("title") or podcast.get("name")
            except (KeyError, TypeError):
                pass

        # Fallback: grab <title> tag
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            title = m.group(1).split("|")[0].strip()
            return title if title else None
    except Exception as e:
        print(f"[WARN] Could not fetch Xiaoyuzhou page: {e}")
    return None


def itunes_search(term, limit=5):
    """Search iTunes for podcasts. Returns list of {name, feed_url, artist}."""
    params = urllib.parse.urlencode({
        "term": term,
        "media": "podcast",
        "entity": "podcast",
        "limit": limit,
    })
    url = f"{ITUNES_SEARCH_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        results = []
        for item in data.get("results", []):
            feed_url = item.get("feedUrl", "")
            if not feed_url:
                continue
            results.append({
                "name": item.get("collectionName", ""),
                "artist": item.get("artistName", ""),
                "feed_url": feed_url,
            })
        return results
    except Exception as e:
        print(f"[ERROR] iTunes search failed: {e}")
        return []


def cmd_list():
    channels = load()
    if not channels:
        print("No podcasts subscribed yet.")
        return
    print(f"Subscribed podcasts ({len(channels)}):\n")
    for i, ch in enumerate(channels, 1):
        name = ch.get("name") or "(name unknown)"
        rss = ch.get("rss_url", "(no RSS URL)")
        print(f"  {i}. {name}")
        print(f"     RSS: {rss}")
        print()


def cmd_add(raw):
    search_term, label = extract_search_term(raw)
    if not search_term:
        print(f"[ERROR] Could not extract a podcast name from: {raw}")
        print("  Try passing the podcast name directly, e.g.:")
        print('  python manage_podcasts.py add "十字路口Crossing"')
        sys.exit(1)

    print(f"Searching iTunes for: {label}")
    results = itunes_search(search_term)

    if not results:
        print("[ERROR] No results found on iTunes. Try a different search term.")
        sys.exit(1)

    print(f"\nFound {len(results)} result(s):\n")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['name']}  —  {r['artist']}")
        print(f"     {r['feed_url']}")
        print()

    # Prompt user to pick one
    while True:
        choice = input(f"Enter number to add (1-{len(results)}), or 0 to cancel: ").strip()
        if choice == "0":
            print("Cancelled.")
            return
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            picked = results[int(choice) - 1]
            break
        print(f"  Please enter a number between 1 and {len(results)}.")

    channels = load()
    if any(ch.get("rss_url") == picked["feed_url"] for ch in channels):
        print(f"[SKIP] Already subscribed: {picked['name']}")
        return

    channels.append({"name": picked["name"], "rss_url": picked["feed_url"]})
    save(channels)
    print(f"\n[OK] Added: {picked['name']}")
    print(f"     RSS: {picked['feed_url']}")


def cmd_remove(ref):
    channels = load()
    if not channels:
        print("No podcasts to remove.")
        return

    # Match by list number
    if ref.isdigit():
        idx = int(ref) - 1
        if 0 <= idx < len(channels):
            removed = channels.pop(idx)
            save(channels)
            print(f"[OK] Removed: {removed.get('name', '(unknown)')}")
        else:
            print(f"[ERROR] No podcast at position {ref}. Run 'list' to see valid numbers.")
        return

    # Match by name substring
    ref_lower = ref.lower()
    matches = [i for i, ch in enumerate(channels)
               if ref_lower in ch.get("name", "").lower()]

    if len(matches) == 1:
        removed = channels.pop(matches[0])
        save(channels)
        print(f"[OK] Removed: {removed.get('name', '(unknown)')}")
    elif len(matches) == 0:
        print(f"[ERROR] No match for '{ref}'. Run 'list' to see subscribed podcasts.")
    else:
        print(f"[ERROR] '{ref}' matches multiple podcasts. Use the list number instead:")
        for i in matches:
            print(f"  {i+1}. {channels[i].get('name', '(unknown)')}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "list":
        cmd_list()
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: python manage_podcasts.py add <url_or_search_term>")
            sys.exit(1)
        cmd_add(sys.argv[2])
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: python manage_podcasts.py remove <name_or_number>")
            sys.exit(1)
        cmd_remove(sys.argv[2])
    else:
        print(f"[ERROR] Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
