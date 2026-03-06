[English](README.md) | [中文](README_zh.md)

# Podcast Digest

An AI-powered daily digest — monitors English YouTube channels and Chinese podcasts (Xiaoyuzhou / Apple Podcasts), transcribes and summarizes new content, and emails you a structured briefing.

## What You Get

Each digest email includes:
- **Overview** — Core argument and key takeaways
- **Key Themes** — Main discussion points with timestamped quotes (clickable on YouTube)
- **Actionable Suggestions** — Tailored to your background (PM, consumer AI, etc.)
- **Observations, Lessons, Entities** — Plus optional Twitter post ideas and blog angles

Short videos (under 20 min) appear in an "Also Updated Today" section without full digests.

**Weekly synthesis** (Sundays): extracts the overview from every digest in the past 7 days and emails a cross-content theme report — Converging Signals (cross-source patterns), Standout Takes (counterintuitive observations), and source links.

---

## Prerequisites

- Python 3.9 or later — [download here](https://www.python.org/downloads/)
- A terminal (Terminal.app on Mac, or any command-line interface)
- Free accounts for the API services listed below (most have generous free tiers)

Install dependencies:
```bash
pip3 install -r requirements.txt
```

---

## Quick Start

**Run all commands from inside the project folder** (open Terminal, `cd` to where you cloned this).

**1. Set up your config files:**
```bash
cp .env.example .env
cp config.example.json config.json
```

Open `.env` and fill in your API keys and email address.
Open `config.json` and add your name and background — this is used to personalize the AI summaries.

**2. Run the daily digest:**
```bash
python3 main_daily.py
```
This fetches new videos and episodes from the past 24 hours, summarizes them, and emails the digest.

**3. Get a digest for any URL on demand:**
```bash
python3 digest_url.py "https://www.youtube.com/watch?v=..."
python3 digest_url.py "https://www.xiaoyuzhoufm.com/episode/..."
python3 digest_url.py "https://podcasts.apple.com/..."
```

---

## API Keys

| Key | Required for | Where to get |
|-----|--------------|--------------|
| `YOUTUBE_API_KEY` | YouTube videos | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `GEMINI_API_KEY` | YouTube summaries | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` | Sending digest | [Google App Passwords](https://myaccount.google.com/apppasswords) |
| `RECIPIENT_EMAIL` | Who receives the digest | Your email |
| `GROQ_API_KEY` | Podcast transcription (optional) | [Groq Console](https://console.groq.com/keys) |
| `DEEPSEEK_API_KEY` | Chinese podcast summaries (optional) | [DeepSeek](https://platform.deepseek.com/api_keys) |

**YouTube-only setup:** Leave `GROQ_API_KEY` and `DEEPSEEK_API_KEY` unset. The pipeline skips podcasts and sends YouTube digests only. See [channels_xyz.json](channels_xyz.json) for podcast subscriptions — leave it empty if you only want YouTube.

---

## Config

| File | What it does |
|------|-------------|
| `channels_en.json` | YouTube channels to monitor |
| `channels_xyz.json` | Chinese podcast feeds (optional — leave empty for YouTube only) |
| `config.json` | Your name and background, used to personalize AI summaries |
| `.env` | API keys and email credentials (never committed to git) |

The `config.json` reader profile tailors what the AI highlights — for example, if you're a PM, it surfaces product insights. If you're an investor, it flags market signals. Edit `config.json` to match your background.

**Add or remove podcasts via the command line:**
```bash
python3 manage_podcasts.py list
python3 manage_podcasts.py add "podcast name or URL"
python3 manage_podcasts.py remove 2
```

---

## Scheduling (macOS)

To run the digest automatically on a schedule, macOS uses a built-in tool called **launchd** — it's like a task scheduler that runs in the background.

You'll create small config files (called plists) that tell macOS when to run each script.

**Three jobs to schedule:**

| Job | When | Script |
|-----|------|--------|
| Morning digest | 7:00 AM daily | `main_daily.py` |
| Afternoon digest | 12:00 PM daily | `main_daily.py` |
| Weekly synthesis | Sunday 9:00 PM | `main_weekly.py` |

**How to set it up:**

1. Create a file at `~/Library/LaunchAgents/com.yourname.podcastdigest.plist`
2. Paste the template below, replacing `/path/to/project` with your actual project path
3. Load it with: `launchctl load ~/Library/LaunchAgents/com.yourname.podcastdigest.plist`

**Template plist** (morning digest at 7 AM):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourname.podcastdigest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/project/main_daily.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/project</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>7</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>StandardOutPath</key>
    <string>/path/to/project/logs/daily.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/project/logs/daily.log</string>
</dict>
</plist>
```

Duplicate the file for afternoon and weekly runs — change the `Label`, `Hour`, and script path accordingly.

---

## Architecture

- **get_videos.py** — YouTube Data API, 24h window, 20-min filter
- **get_podcasts_xyz.py** — RSS feeds, 24h window
- **summarize.py** — YouTube transcript via youtube-transcript-api → Gemini
- **summarize_podcast.py** — Download audio → Groq Whisper → DeepSeek
- **send_combined_email.py** — HTML email builder and sender
- **main_daily.py** — Orchestrates full pipeline
- **main_weekly.py** — Weekly synthesis: scans archive, calls Gemini, sends theme report
- **synthesize.py** — Extracts Part 1 from digests, generates cross-content themes
- **digest_url.py** — On-demand for any YouTube / Xiaoyuzhou / Apple Podcasts URL

---

## Design Decisions & Lessons Learned

### Why two daily runs (7 AM and 12 PM)?
Two reasons, both discovered through real use:

1. **YouTube transcript lag** — When a video is published, auto-generated captions often aren't available for 1–3 hours. Running at 7 AM catches overnight uploads; the 12 PM run catches anything that published early morning but whose transcript wasn't ready yet.

2. **Groq free tier limits** — Podcast transcription uses Groq Whisper, which has a generous but finite free tier. Running twice a day spreads the transcription load across two sessions, reducing the chance of hitting the limit in a single batch.

### Why Groq Whisper + DeepSeek (two models for one podcast)?
Chinese podcast audio requires two separate steps:
- **Groq Whisper** — Fast, accurate audio-to-text transcription. Best free transcription API available. Outputs raw transcript.
- **DeepSeek** — Summarization and analysis of Chinese text. Significantly better than alternatives (including GPT-4) on Chinese language quality, nuance, and cultural context.

Trying to do both with one model (e.g., transcription + summarization in Gemini) produced noticeably worse results on Chinese content.

### Why email instead of an app or dashboard?
Zero friction. Email is searchable, works on every device, needs no installation, and integrates with notification systems you already use. A dashboard requires you to remember to check it. Email shows up where you already are.

### Why a 20-minute filter on YouTube videos?
Short videos (under 20 min) rarely have enough depth to warrant a full digest. They still appear in an "Also Updated Today" section so you don't miss them — they're just not summarized. This keeps the digest focused on substantive content.

### Why a 24-hour window?
Both YouTube and podcasts use a 24h lookback to avoid duplicate processing. A longer window would re-process old content on restarts; a shorter window risks gaps if a run fails.

### Why a reader profile in config instead of fine-tuning?
Personalization via a plain text config (your name, background, goals) is portable across any LLM, requires no training, and can be updated in seconds. Fine-tuning would lock you to one model and require retraining whenever your interests change.

### Why multiple LLMs instead of one?
Right tool for the job:
- **Gemini** (YouTube) — Fast, cheap, handles long transcripts well
- **Groq Whisper** (transcription) — Best free-tier audio transcription available
- **DeepSeek** (Chinese podcasts) — Highest quality Chinese language output

Using one model for everything produced consistently worse results on at least one of these tasks.
