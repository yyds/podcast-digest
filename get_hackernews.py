from trending_utils import http_get_with_retry, filter_consecutive

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
PROCESSED_FILE = "processed_hn.json"
TOP_N = 10


def fetch_story(story_id):
    try:
        resp = http_get_with_retry(HN_ITEM_URL.format(id=story_id), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[WARN] Failed to fetch story {story_id}: {e}")
        return None


def fetch_hn_top_stories(top_n=TOP_N):
    try:
        resp = http_get_with_retry(HN_TOP_STORIES_URL, timeout=15)
        resp.raise_for_status()
        story_ids = resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch HN top stories: {e}")
        return []

    stories = []
    for i, story_id in enumerate(story_ids[:top_n * 2]):
        if len(stories) >= top_n:
            break
        story = fetch_story(story_id)
        if not story or story.get("type") != "story":
            continue

        url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
        stories.append({
            "rank": len(stories) + 1,
            "id": story_id,
            "title": story.get("title", ""),
            "url": url,
            "score": story.get("score", 0),
            "comments": story.get("descendants", 0),
            "by": story.get("by", ""),
            "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
        })

    return stories


def get_new_stories():
    print("[INFO] Fetching Hacker News top stories...")
    all_stories = fetch_hn_top_stories(TOP_N)
    if not all_stories:
        print("[WARN] No stories found on HN")
        return []

    print(f"[INFO] Found {len(all_stories)} top stories on HN")
    filtered = filter_consecutive(all_stories, "id", PROCESSED_FILE)
    print(f"[INFO] {len(filtered)} new stories after consecutive filter")
    return filtered


if __name__ == "__main__":
    stories = get_new_stories()
    for s in stories:
        print(f"  #{s['rank']} {s['title'][:70]} ({s['score']} pts)")
        print(f"    {s['url'][:70]}")
