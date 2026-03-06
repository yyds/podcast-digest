# Podcast Digest — Project Context

## What This Is
A personal AI-powered daily digest system. Monitors YouTube channels and Xiaoyuzhou (Chinese podcast platform), transcribes/summarizes new content using LLMs, and emails a formatted HTML digest. Also supports on-demand digests for any URL.

**Owner:** Jackie Yuan — PM/data background, non-engineer, builds via vibe coding.

---

## Architecture

```
get_videos.py          → Fetch new YouTube videos via YouTube Data API
get_podcasts_xyz.py    → Fetch new Xiaoyuzhou episodes via RSS
summarize.py           → Transcribe + summarize YouTube videos (Gemini)
summarize_podcast.py   → Download + transcribe + summarize podcasts (Groq Whisper + DeepSeek)
send_email.py          → HTML email renderer (CSS, card components, section renderers)
send_combined_email.py → Sends the combined daily digest email + weekly digest
main_daily.py          → Daily entry point — runs the full pipeline
main_weekly.py         → Weekly entry point — synthesizes themes from past 7 days
synthesize.py          → Extract Part 1 from digests, generate weekly synthesis (Gemini)
digest_url.py          → On-demand entry point — accepts any URL, emails digest immediately
manage_podcasts.py     → CLI to add/remove Xiaoyuzhou subscriptions
```

---

## Config Files

| File | Purpose | Committed? |
|------|---------|-----------|
| `.env` | API keys and email credentials | No — gitignored |
| `config.json` | Reader profile (name, background) for LLM personalization | No — gitignored |
| `channels_en.json` | YouTube channels to monitor | Yes |
| `channels_xyz.json` | Xiaoyuzhou podcast RSS feeds | Yes |
| `.env.example` | Template for `.env` | Yes |
| `config.example.json` | Template for `config.json` | Yes |

---

## Services / API Keys Required

| Key | Used for |
|-----|---------|
| `YOUTUBE_API_KEY` | Fetching YouTube channel/video metadata |
| `GEMINI_API_KEY` | Summarizing YouTube videos (gemini-2.5-flash-lite) |
| `GROQ_API_KEY` | Transcribing podcast audio (Whisper large v3) |
| `DEEPSEEK_API_KEY` | Summarizing Chinese podcasts (deepseek-chat) |
| `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` | Sending digest email via SMTP |
| `RECIPIENT_EMAIL` / `RECIPIENT_EMAIL_2` | Who receives the digest |

---

## How to Run

```bash
# Daily digest (launchd: 7am + 2pm)
python3 main_daily.py

# Weekly digest (launchd: Sunday 9am)
python3 main_weekly.py

# On-demand digest for any URL
python3 digest_url.py "https://www.youtube.com/watch?v=..."
python3 digest_url.py "https://www.xiaoyuzhoufm.com/episode/..."
python3 digest_url.py "https://podcasts.apple.com/..."  # Apple Podcasts also supported

# Manage podcast subscriptions
python3 manage_podcasts.py list
python3 manage_podcasts.py add "podcast name or URL"
python3 manage_podcasts.py remove 2
```

---

## Scheduler (macOS launchd)

Three plist files in `~/Library/LaunchAgents/`:
- `com.jackie.podcastdigest.plist` — morning run (7am) → `main_daily.py`
- `com.jackie.podcastdigest.afternoon.plist` — afternoon run (2pm) → `main_daily.py`
- `com.jackie.podcastdigest.weekly.plist` — Sunday 9pm → `main_weekly.py`

Daily logs: `logs/daily.log`. Weekly logs: `logs/weekly.log`.

To reload after editing a plist:
```bash
launchctl unload ~/Library/LaunchAgents/<plist-name>.plist
launchctl load ~/Library/LaunchAgents/<plist-name>.plist
```

---

## Outstanding Tasks

### Done
- Part 3 label loads reader name from `config.json` (fallback: "You")
- Dead files removed (`main.py`, `main_xyz.py`, `send_podcast_email.py`); helpers inlined in `send_combined_email.py`
- `_get_recipients()` and SMTP consolidated in `send_email._send_html_email()`
- Podcast IDs saved on discovery, not just on success
- Podcast cutoff: 24 hours (matches YouTube)
- Part 3 (actionable) rendered last with label ⑧; parts 4–8 renumbered ③–⑦
- README.md written
- Podcast pipeline skips gracefully when Groq/DeepSeek keys missing

### Optional / future
- **Path assumptions** — Document "run from project root"; path refactor optional
- **Parts 7 + 8** — Twitter/Blog sections; consider making optional per user
- **Silent failure visibility** — Summary of skipped videos/episodes
- **SETUP.md** — Detailed setup guide for semi-technical users

---

## Key Design Decisions (rationale)

- **Email delivery** — zero friction, no app to install, searchable in inbox, works on any device
- **Reader profile in config** — personalization without fine-tuning; portable across LLMs
- **Multiple LLMs** — Gemini for English YouTube (cheap + fast), Groq Whisper for transcription (generous free tier), DeepSeek for Chinese podcasts (best quality on Chinese text)
- **20-min video filter** — short videos rarely have depth worth digesting; they appear in a separate "Also Updated Today" section instead of being silently dropped
- **24h window** — Both YouTube and podcasts use 24h to avoid duplicate processing
- **On-demand via `digest_url.py`** — handles content outside your subscription list (shared links, discoveries) without touching the daily automation
- **Weekly synthesis** — Runs Sunday 9pm; extracts Part 1 from all digests in past 7 days; identifies 3–5 common themes + top insights; links to original source URLs

---

## Code Conventions

- Logging: `[INFO]`, `[WARN]`, `[ERROR]` prefix on all print statements
- Archive: digests saved to `archive/YYYY-MM-DD/<slug>.md`; daily HTML saved as `digest.html`; weekly HTML saved as `weekly_digest.html`
- Transcript cache: stored in `archive/transcripts/` during processing, deleted after digest is complete
- Language detection: `is_chinese` flag passed to all section renderers, inferred from digest header (`**主播**` vs `**Host**`)
