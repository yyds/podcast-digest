"""
One-off digest runner.
Accepts YouTube, xiaoyuzhou, and Apple Podcasts URLs, processes each,
and sends a single combined email.

Usage:
    python digest_url.py <url1> <url2> ...
    python digest_url.py --lang zh <url>   # Chinese transcript + output
"""
import os
import re
import sys
import json
import argparse
import datetime
import requests
from html import unescape
from dotenv import load_dotenv
from googleapiclient.discovery import build

from summarize import summarize_video
from summarize_podcast import summarize_episode
from send_combined_email import send_combined_digest

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


RETRY_QUEUE_PATH = "retry_queue.json"


def _add_to_retry_queue(metadata):
    """Add a YouTube video to the retry queue if not already present."""
    try:
        with open(RETRY_QUEUE_PATH) as f:
            queue = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        queue = []

    video_id = metadata["video_id"]
    if any(entry["video_id"] == video_id for entry in queue):
        print(f"[INFO] Already in retry queue: {metadata['title']}")
        return

    queue.append({
        "url": metadata["url"],
        "video_id": video_id,
        "title": metadata["title"],
        "channel": metadata.get("channel", ""),
        "description": metadata.get("description", ""),
        "lang": metadata.get("lang", "en"),
        "duration": metadata.get("duration"),
        "added_at": datetime.date.today().isoformat(),
        "last_attempted": datetime.date.today().isoformat(),
        "attempts": 1,
        "max_attempts": 7,
    })
    with open(RETRY_QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)
    print(f"[INFO] Added to retry queue: {metadata['title']} (will retry up to 7 daily runs)")


# ── Metadata fetchers ──────────────────────────────────────────────────────────

def _fetch_xiaoyuzhou(url):
    """Extract episode metadata from a xiaoyuzhou episode page."""
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        r.text, re.DOTALL
    )
    if not m:
        raise RuntimeError("Could not find __NEXT_DATA__ in xiaoyuzhou page")
    data = json.loads(m.group(1))
    ep = data["props"]["pageProps"]["episode"]
    print(f"[DEBUG] Xiaoyuzhou episode keys: {list(ep.keys())}")
    print(f"[DEBUG] Xiaoyuzhou duration field: {ep.get('duration')!r}")
    episode_id = ep.get("eid") or url.split("/")[-1]
    title = ep.get("title", "Untitled")
    channel = ep.get("podcast", {}).get("title", "Unknown Podcast")
    # shownotes is HTML — strip tags for the description
    raw_notes = ep.get("shownotes", "") or ep.get("description", "")
    description = re.sub(r"<[^>]+>", " ", raw_notes)
    description = unescape(description).strip()[:500]
    audio_url = ep["media"]["source"]["url"]
    duration_sec = ep.get("duration")
    return {
        "anchor_id": episode_id,
        "episode_id": episode_id,
        "title": title,
        "channel": channel,
        "description": description,
        "url": url,
        "audio_url": audio_url,
        "duration": duration_sec / 60 if duration_sec else None,
    }


def _fetch_apple_podcasts(url):
    """Extract episode metadata by scraping the Apple Podcasts web page directly."""
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()

    scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)

    # Script 0: schema.org JSON-LD — has description
    description = ""
    try:
        schema = json.loads(scripts[0])
        description = (schema.get("description", "") or "")[:500]
    except (IndexError, json.JSONDecodeError, KeyError):
        pass

    # Find the script with episodeOffer data
    ep_offer = None
    for script in scripts:
        if '"streamUrl"' in script and '"episodeOffer"' in script:
            try:
                data = json.loads(script)
                shelves = data["data"][0]["data"]["shelves"]
                for shelf in shelves:
                    for item in shelf.get("items", []):
                        offer = item.get("contextAction", {}).get("episodeOffer")
                        if offer and offer.get("streamUrl"):
                            ep_offer = offer
                            break
                    if ep_offer:
                        break
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
        if ep_offer:
            break

    if not ep_offer:
        raise RuntimeError(f"Could not extract episode data from Apple Podcasts page: {url}")

    episode_id = str(ep_offer.get("contentId", url.split("i=")[-1]))
    title = ep_offer.get("title", "Untitled")
    channel = ep_offer.get("showOffer", {}).get("title", "Unknown Podcast")
    audio_url = ep_offer["streamUrl"]
    duration_sec = ep_offer.get("duration")

    return {
        "anchor_id": episode_id,
        "episode_id": episode_id,
        "title": title,
        "channel": channel,
        "description": description,
        "url": url,
        "audio_url": audio_url,
        "duration": duration_sec / 60 if duration_sec else None,
    }


def _extract_youtube_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not m:
        raise RuntimeError(f"Cannot parse YouTube video ID from: {url}")
    return m.group(1)


def _load_channel_lang_map():
    """Return handle (lowercase, no @) → lang from channels_en.json."""
    try:
        with open("channels_en.json") as f:
            channels = json.load(f)
        return {ch["handle"].lstrip("@").lower(): ch.get("lang", "en") for ch in channels}
    except Exception:
        return {}


def _detect_channel_lang(channel_id, youtube_client):
    """Look up channel handle via YouTube API and return lang from channels_en.json."""
    handle_lang = _load_channel_lang_map()
    if not handle_lang:
        return None
    try:
        resp = youtube_client.channels().list(part="snippet", id=channel_id).execute()
        items = resp.get("items", [])
        if not items:
            return None
        custom_url = items[0]["snippet"].get("customUrl", "").lstrip("@").lower()
        return handle_lang.get(custom_url)
    except Exception:
        return None


def _parse_iso_duration(s):
    """Parse ISO 8601 duration (e.g. PT1H23M45S) to total minutes."""
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or "")
    if not m:
        return None
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 60 + minutes + seconds / 60


def _fetch_youtube_metadata(url, lang=None):
    video_id = _extract_youtube_id(url)
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    resp = youtube.videos().list(part="snippet,contentDetails", id=video_id).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError(f"No YouTube results for video: {video_id}")
    snippet = items[0]["snippet"]
    duration = _parse_iso_duration(items[0].get("contentDetails", {}).get("duration", ""))

    # Auto-detect lang from channels_en.json if not explicitly overridden
    if lang is None:
        channel_id = snippet.get("channelId", "")
        lang = _detect_channel_lang(channel_id, youtube) or "en"

    return {
        "video_id": video_id,
        "title": snippet["title"],
        "channel": snippet["channelTitle"],
        "description": snippet.get("description", "")[:500],
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "lang": lang,
        "duration": duration,
    }


def fetch_episode_metadata(url, lang=None):
    url = url.strip()
    if "youtube.com" in url or "youtu.be" in url:
        return ("youtube", _fetch_youtube_metadata(url, lang=lang))
    elif "xiaoyuzhoufm.com" in url:
        return ("podcast", _fetch_xiaoyuzhou(url))
    elif "podcasts.apple.com" in url:
        return ("podcast", _fetch_apple_podcasts(url))
    else:
        raise RuntimeError(f"Unsupported URL source: {url}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main(urls, lang=None):
    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for u in urls:
        u = u.strip()
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    print(f"[INFO] Processing {len(unique_urls)} URL(s)...")
    youtube_digests = []
    podcast_digests = []

    for url in unique_urls:
        print(f"\n[INFO] Fetching metadata: {url[:70]}...")
        try:
            kind, metadata = fetch_episode_metadata(url, lang=lang)
        except Exception as e:
            print(f"[ERROR] Metadata fetch failed: {e}")
            continue

        print(f"[INFO] {metadata['title']} ({metadata['channel']})")

        if kind == "youtube":
            digest = summarize_video(metadata)
            if digest:
                youtube_digests.append({"video": metadata, "digest": digest})
            else:
                print(f"[WARN] No digest produced for: {metadata['title']}")
                _add_to_retry_queue(metadata)
        else:
            digest = summarize_episode(metadata)
            if digest:
                podcast_digests.append({"episode": metadata, "digest": digest})
            else:
                print(f"[WARN] No digest produced for: {metadata['title']}")

    if not youtube_digests and not podcast_digests:
        print("[WARN] No digests produced — nothing to send.")
        return

    total = len(youtube_digests) + len(podcast_digests)
    print(f"\n[INFO] Sending email with {total} digest(s)...")
    send_combined_digest(youtube_digests=youtube_digests, podcast_digests=podcast_digests)
    print("[INFO] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="On-demand digest runner")
    parser.add_argument("urls", nargs="+", help="YouTube, Xiaoyuzhou, or Apple Podcasts URLs")
    parser.add_argument("--lang", default=None, choices=["en", "zh"],
                        help="Override transcript language (auto-detected from channels_en.json by default)")
    args = parser.parse_args()
    main(args.urls, lang=args.lang)
