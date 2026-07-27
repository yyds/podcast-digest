from get_github_trending import get_new_trending
from get_hackernews import get_new_stories
from summarize_trending import summarize_github_repos, summarize_hn_stories
from send_trending_email import send_trending_digest


def main():
    print("[INFO] Starting GitHub & HN Trending Digest...\n")

    print("[INFO] --- GitHub Trending ---")
    github_repos = get_new_trending("typescript")
    if github_repos:
        github_repos = summarize_github_repos(github_repos)

    print("\n[INFO] --- Hacker News ---")
    hn_stories = get_new_stories()
    if hn_stories:
        hn_stories = summarize_hn_stories(hn_stories)

    if not github_repos and not hn_stories:
        print("\n[INFO] No new content today. Email not sent.")
        return

    print("\n[INFO] Sending trending digest email...")
    send_trending_digest(github_repos, hn_stories)
    gh_count = len(github_repos)
    hn_count = len(hn_stories)
    print(f"[INFO] Done. Sent {gh_count} GitHub repos + {hn_count} HN stories.")


if __name__ == "__main__":
    main()
