import os
import re
import json
import feedparser
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

PROCESSED_FILE = "processed_podcasts.json"
CHANNELS_FILE = "channels_xyz.json"


def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE) as f:
            return json.load(f)
    return []


def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed), f, indent=2)


def _safe_anchor_id(channel_name, episode_id):
    """Generate a safe HTML anchor ID from channel name + episode identifier."""
    slug = episode_id.split("/")[-1] if episode_id.startswith("http") else episode_id
    slug = re.sub(r"[^a-zA-Z0-9-]", "", slug)[:40]
    prefix = re.sub(r"[^a-zA-Z0-9]", "", channel_name)[:10]
    return f"{prefix}-{slug}"


def get_new_episodes():
    processed = load_processed()
    new_episodes = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    for channel in load_channels():
        name = channel.get("name", "Unknown")
        rss_url = channel.get("rss_url", "")
        if not rss_url:
            print(f"[WARN] No RSS URL for channel: {name}")
            continue

        print(f"[INFO] Fetching RSS for {name}...")

        try:
            feed = feedparser.parse(rss_url)
        except Exception as e:
            print(f"[ERROR] Failed to fetch RSS for {name}: {e}")
            continue

        if feed.bozo and not feed.entries:
            print(f"[WARN] RSS parse error for {name}: {feed.bozo_exception}")
            continue

        podcast_name = feed.feed.get("title", name)

        for entry in feed.entries:
            episode_id = entry.get("id") or entry.get("guid", "")
            if not episode_id:
                continue

            if episode_id in processed:
                continue

            # Filter to last 24 hours (matches YouTube pipeline)
            published = entry.get("published_parsed")
            if published:
                pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue

            # Get audio URL from enclosures
            audio_url = None
            for enc in entry.get("enclosures", []):
                if enc.get("type", "").startswith("audio/"):
                    audio_url = enc.get("href") or enc.get("url")
                    break

            if not audio_url:
                print(f"[WARN] No audio URL for: {entry.get('title', 'Unknown')}")
                continue

            title = entry.get("title", "Untitled")
            episode_url = entry.get("link", "")

            new_episodes.append({
                "anchor_id": _safe_anchor_id(podcast_name, episode_id),
                "episode_id": episode_id,
                "title": title,
                "channel": podcast_name,
                "description": entry.get("summary", "")[:500],
                "url": episode_url,
                "audio_url": audio_url,
            })
            print(f"[INFO] New episode: {title}")

    return new_episodes, processed


if __name__ == "__main__":
    episodes, _ = get_new_episodes()
    print(f"\nFound {len(episodes)} new episodes:")
    for e in episodes:
        print(f"  [{e['channel']}] {e['title']}")
        print(f"  {e['url']}")
        print(f"  Audio: {e['audio_url']}")
