import os
from get_videos import get_new_videos, save_processed as save_yt_processed
from summarize import summarize_video, summarize_video_brief
from get_podcasts_xyz import get_new_episodes, save_processed as save_pod_processed
from summarize_podcast import summarize_episode
from send_combined_email import send_combined_digest


def main():
    print("[INFO] Starting Combined Daily Digest...\n")

    # --- YouTube pipeline ---
    print("[INFO] --- YouTube Pipeline ---")
    yt_videos, yt_short_videos, yt_processed = get_new_videos()

    yt_digests = []
    if yt_videos:
        print(f"[INFO] Processing {len(yt_videos)} new video(s)...\n")
        for video in yt_videos:
            print(f"[INFO] Summarizing: {video['title']}")
            digest = summarize_video(video)
            if digest:
                yt_digests.append({"video": video, "digest": digest})
                yt_processed.add(video["video_id"])
    else:
        print("[INFO] No new YouTube videos today.")

    # Short videos → brief Quick Take digests
    yt_brief_digests = []
    if yt_short_videos:
        print(f"[INFO] Generating Quick Takes for {len(yt_short_videos)} short video(s)...\n")
        for video in yt_short_videos:
            print(f"[INFO] Quick Take: {video['title']}")
            digest = summarize_video_brief(video)
            if digest:
                yt_brief_digests.append({"video": video, "digest": digest})
            yt_processed.add(video["video_id"])

    # --- Podcast pipeline ---
    print("\n[INFO] --- Podcast Pipeline ---")
    if not os.getenv("GROQ_API_KEY") or not os.getenv("DEEPSEEK_API_KEY"):
        print("[INFO] Podcast API keys not configured — skipping podcast pipeline.")
        pod_episodes, pod_processed = [], set()
    else:
        pod_episodes, pod_processed = get_new_episodes()

    pod_digests = []
    if pod_episodes:
        print(f"[INFO] Processing {len(pod_episodes)} new episode(s)...\n")
        for episode in pod_episodes:
            print(f"[INFO] 正在生成摘要: {episode['title']}")
            pod_processed.add(episode["episode_id"])  # Mark on discovery so failed ones aren't retried
            digest = summarize_episode(episode)
            if digest:
                pod_digests.append({"episode": episode, "digest": digest})
    else:
        print("[INFO] No new podcast episodes today.")

    # --- Send combined email ---
    if yt_digests or pod_digests or yt_brief_digests:
        print("\n[INFO] Sending combined digest email...")
        send_combined_digest(yt_digests, pod_digests, yt_brief_digests=yt_brief_digests)
        save_yt_processed(yt_processed)
        if pod_episodes:
            save_pod_processed(pod_processed)  # Save all discovered episodes, not just successful digests
        print(f"[INFO] Done. Sent {len(yt_digests)} full + {len(yt_brief_digests)} quick take + {len(pod_digests)} podcast digest(s).")
    else:
        print("\n[INFO] No new content today. Email not sent.")


if __name__ == "__main__":
    main()
