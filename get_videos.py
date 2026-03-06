import os
import re
import json
import requests
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
PROCESSED_FILE = "processed_videos.json"

with open("channels_en.json") as _f:
    CHANNELS = json.load(_f)


def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed), f, indent=2)


MIN_DURATION_MINUTES = 20


def parse_duration_minutes(iso_duration):
    """Parse ISO 8601 duration (e.g. PT1H23M45S) to total minutes."""
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration or "")
    if not m:
        return 0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 60 + minutes + seconds / 60


def get_duration_minutes(youtube, video_id):
    try:
        resp = youtube.videos().list(part="contentDetails", id=video_id).execute()
        items = resp.get("items", [])
        if not items:
            return None
        return parse_duration_minutes(items[0]["contentDetails"]["duration"])
    except Exception as e:
        print(f"[WARN] Could not fetch duration for {video_id}: {e}")
        return None


def is_short(video_id):
    url = f"https://www.youtube.com/shorts/{video_id}"
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return "/shorts/" in response.url
    except Exception:
        return False


def get_uploads_playlist_id(youtube, handle):
    try:
        response = youtube.channels().list(
            part="contentDetails",
            forHandle=handle.lstrip("@")
        ).execute()

        items = response.get("items", [])
        if not items:
            print(f"[WARN] Channel not found: {handle}")
            return None

        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except Exception as e:
        print(f"[ERROR] Failed to get playlist for {handle}: {e}")
        return None


def get_new_videos():
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    processed = load_processed()
    new_videos = []
    short_videos = []

    for channel in CHANNELS:
        handle = channel["handle"]
        print(f"[INFO] Checking {handle}...")

        playlist_id = get_uploads_playlist_id(youtube, handle)
        if not playlist_id:
            continue

        try:
            response = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=5
            ).execute()
        except Exception as e:
            print(f"[ERROR] Failed to fetch videos for {handle}: {e}")
            continue

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for item in response.get("items", []):
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]

            if video_id in processed:
                continue

            published_at = snippet.get("publishedAt", "")
            if published_at:
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue

            if is_short(video_id):
                print(f"[INFO] Skipping Short: {snippet['title']}")
                continue

            video_data = {
                "video_id": video_id,
                "title": snippet["title"],
                "description": snippet.get("description", "")[:500],
                "channel": snippet["channelTitle"],
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "lang": channel["lang"],
            }

            duration = get_duration_minutes(youtube, video_id)
            if duration is not None and duration < MIN_DURATION_MINUTES:
                print(f"[INFO] Short video ({duration:.0f} min), will mention only: {snippet['title']}")
                short_videos.append(video_data)
            else:
                new_videos.append(video_data)
                print(f"[INFO] New video found ({duration:.0f} min): {snippet['title']}")
            break  # one per channel

    return new_videos, short_videos, processed


if __name__ == "__main__":
    videos, short_videos, _ = get_new_videos()
    print(f"\nFound {len(videos)} new videos, {len(short_videos)} short:")
    for v in videos:
        print(f"  [{v['channel']}] {v['title']}")
        print(f"  {v['url']}")
