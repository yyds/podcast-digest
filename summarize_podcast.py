import os
import re
import json
import time
import shutil
import subprocess
import tempfile
import requests
from datetime import date
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

with open("config.json") as _f:
    _reader = json.load(_f)["reader"]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

PROMPT_TEMPLATE = """你是一位专业的内容分析师和播客研究员。你将收到以下中文播客转录文字。请根据以下格式生成摘要。使用标题和描述信息纠正转录中的错误，特别是人名、公司名和专业术语。

播客名称：{channel}
单集标题：{title}
节目描述：{description}

写作要求：直接、清晰、使用流畅的中文散文体。不要写"在本期节目中"或"主播讨论了"。每个部分应独立完整，读者未收听原音频。

读者背景：{reader_name}，{reader_profile}

隐私要求：输出中切勿提及读者所在公司或雇主名称。请使用"你的公司"、"消费级AI"、"你的产品"等泛化表述。此要求适用于所有部分，尤其是 Part 3。

---

输出格式（Markdown，紧凑排版，条目之间不要添加多余空行）：

**主播：** [姓名]
**嘉宾：** [姓名，如无则填 N/A]

### Part 1: Podcast Overview & Key Recommendations
**总体摘要：** [2-3句话，核心论点及其重要性]
**关键点：**
- [最重要的单句结论或洞察]
- [第二个关键点]
- [第三个关键点，如有]
**关键主题：**
1. [话题名称]：[1-2句说明]
2. [以此类推，涵盖所有主要话题]
**结论：** [1-2句话，总结核心观点或收听要点]

### Part 2: Key Themes, Technological Insights & Core Discussion Points
[提炼恰好5个主题。每个主题：先写描述，然后另起一行写引用，格式严格为"   引用：[HH:MM:SS] "原话""，时间戳将被转换为可点击链接。]
1. **[主题名称]**
   [描述：2-3句话说明该主题的核心内容和意义]
   引用：[HH:MM:SS] "[说话人原话]"
2. **[主题名称]**
   [描述]
   引用：[HH:MM:SS] "[说话人原话]"
3. **[主题名称]**
   [描述]
   引用：[HH:MM:SS] "[说话人原话]"
4. **[主题名称]**
   [描述]
   引用：[HH:MM:SS] "[说话人原话]"
5. **[主题名称]**
   [描述]
   引用：[HH:MM:SS] "[说话人原话]"

### Part 3: Actionable Suggestions & Theses for {reader_name}
[结合{reader_name}的背景：{reader_background}。至少3条建议。]
1. [建议或论点]
   - 重要性：...
   - 如何应用：...
2. [建议或论点]
   - 重要性：...
   - 如何应用：...
3. [建议或论点]
   - 重要性：...
   - 如何应用：...

### Part 4: Noteworthy Observations & Unique Perspectives
[令人惊讶、反直觉或非显而易见的观点。包含原话和时间戳。]
1. [观察]
   引用：[HH:MM:SS] "[引用]"

### Part 5: Lessons Learned & Success Factors
[成功经验。如果节目描述了教程、项目或流程——列出具体步骤，让{reader_name}可以复现。]
- [经验或步骤]

### Part 6: Companies & Entities Mentioned
[所有实际讨论过的公司、产品、人物或机构——排除播客频道本身和赞助商。无需URL，只需名称和背景。]
1. [名称] — [一句话背景]
2. [以此类推]

### Part 7: Tweet-sized Takeaways
[5条推文式要点。每条：有力引用或洞察 + 钩子句 + 话题标签。每条不超过280字符。]
1. "[引用]" — [说话人]. [钩子句]. #[标签] #[标签]

### Part 8: Essay Angles
[3个角度。每个：标题、核心论点（2句话）、锚点引用（含可选时间戳）。]
1. 标题："[标题]"
   核心论点：[2句话]
   锚点引用：[HH:MM:SS] "[引用]"   （如有，加入时间戳，格式同 Part 2）

---

转录文字：
{transcript}
"""


def download_audio(audio_url):
    """Download audio to a temp file, return the path."""
    suffix = ".m4a" if ".m4a" in audio_url else ".mp3"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        print(f"[INFO] Downloading audio from {audio_url[:60]}...")
        with requests.get(audio_url, stream=True, timeout=300) as r:
            r.raise_for_status()
            downloaded = 0
            for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):
                tmp.write(chunk)
                downloaded += len(chunk)
                print(f"[INFO] Downloaded {downloaded / 1024 / 1024:.1f} MB...", end="\r")
        tmp.close()
        print(f"\n[INFO] Audio saved to {tmp.name}")
        return tmp.name
    except Exception as e:
        tmp.close()
        os.unlink(tmp.name)
        raise RuntimeError(f"Audio download failed: {e}")


GROQ_MAX_MB = 24  # stay under 25MB hard limit


def _split_audio(tmp_path, chunk_minutes=15):
    """Split audio into MP3 chunks using ffmpeg. Returns list of temp file paths."""
    chunk_dir = tempfile.mkdtemp()
    chunk_pattern = os.path.join(chunk_dir, "chunk_%03d.mp3")
    result = subprocess.run(
        [
            "ffmpeg", "-i", tmp_path,
            "-f", "segment",
            "-segment_time", str(chunk_minutes * 60),
            "-codec:a", "libmp3lame",
            "-b:a", "64k",   # 64kbps is plenty for speech transcription
            "-vn",            # strip video track
            "-reset_timestamps", "1",
            chunk_pattern, "-y",
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg split failed: {result.stderr.decode()[-500:]}")
    chunks = [
        os.path.join(chunk_dir, f)
        for f in sorted(os.listdir(chunk_dir))
        if f.startswith("chunk_")
    ]
    return chunks, chunk_dir


def _parse_retry_seconds(error_msg):
    """Extract wait seconds from Groq 429 message like 'try again in 2m29.5s'."""
    m = re.search(r"try again in\s+(?:(\d+)m)?(?:([\d.]+)s)?", str(error_msg))
    if not m:
        return 60
    minutes = int(m.group(1) or 0)
    seconds = float(m.group(2) or 0)
    return int(minutes * 60 + seconds) + 5  # +5s buffer


def _transcribe_file(path):
    for attempt in range(3):
        try:
            with open(path, "rb") as f:
                result = groq_client.audio.transcriptions.create(
                    file=(os.path.basename(path), f),
                    model="whisper-large-v3",
                    language="zh",
                )
            return result.text
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = _parse_retry_seconds(e)
                print(f"[WARN] Groq rate limit hit — waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Groq transcription failed after retries: {path}")


def transcribe_audio(tmp_path, cache_path=None):
    """Transcribe audio via Groq Whisper. Splits files > 24 MB into chunks."""
    file_size_mb = os.path.getsize(tmp_path) / 1024 / 1024
    print(f"[INFO] Transcribing with Groq Whisper ({file_size_mb:.1f} MB)...")

    if file_size_mb <= GROQ_MAX_MB:
        text = _transcribe_file(tmp_path)
        print(f"[INFO] Transcription complete ({len(text)} chars)")
        return text

    print(f"[INFO] File exceeds {GROQ_MAX_MB} MB — splitting into 15-min chunks...")
    chunk_paths, chunk_dir = _split_audio(tmp_path)
    print(f"[INFO] Split into {len(chunk_paths)} chunk(s)")

    parts = []
    try:
        for i, chunk_path in enumerate(chunk_paths, 1):
            chunk_mb = os.path.getsize(chunk_path) / 1024 / 1024
            print(f"[INFO] Transcribing chunk {i}/{len(chunk_paths)} ({chunk_mb:.1f} MB)...")
            parts.append(_transcribe_file(chunk_path))
            # Save progress after each chunk so retries resume from here
            if cache_path:
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(parts))
    finally:
        shutil.rmtree(chunk_dir, ignore_errors=True)

    full_text = "\n".join(parts)
    print(f"[INFO] Transcription complete ({len(full_text)} chars across {len(parts)} chunks)")
    return full_text


def _transcript_cache_path(episode):
    slug = re.sub(r"[^a-z0-9]+", "-", episode["title"].lower())[:50]
    cache_dir = os.path.join("archive", "transcripts")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{slug}.txt")


def summarize_episode(episode):
    tmp_path = None
    cache_path = _transcript_cache_path(episode)

    try:
        # Use cached transcript if available — avoids re-transcribing on retry
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                transcript = f.read()
            print(f"[INFO] Loaded transcript from cache ({len(transcript)} chars)")
        else:
            tmp_path = download_audio(episode["audio_url"])
            transcript = transcribe_audio(tmp_path, cache_path=cache_path)
            if not os.path.exists(cache_path):  # single-chunk case: save now
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(transcript)
            print(f"[INFO] Transcript cached to {cache_path}")

        prompt = PROMPT_TEMPLATE.format(
            title=episode["title"],
            channel=episode["channel"],
            description=episode["description"],
            transcript=transcript,
            reader_name=_reader["name"],
            reader_profile=_reader["profile"],
            reader_background=_reader["background"],
        )

        print(f"[INFO] Generating digest with DeepSeek...")
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
        )
        digest = response.choices[0].message.content

        # Save to archive
        today = date.today().isoformat()
        archive_dir = os.path.join("archive", today)
        os.makedirs(archive_dir, exist_ok=True)

        slug = re.sub(r"[^a-z0-9]+", "-", episode["title"].lower())[:50]
        filepath = os.path.join(archive_dir, f"xyz-{slug}.md")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {episode['title']}\n")
            f.write(f"**播客：** {episode['channel']}\n")
            f.write(f"**链接：** {episode['url']}\n\n")
            f.write(digest)

        print(f"[INFO] Saved digest to {filepath}")

        # Clean up transcript cache now that digest is complete
        if os.path.exists(cache_path):
            os.unlink(cache_path)

        return digest

    except Exception as e:
        print(f"[ERROR] Failed to summarize {episode['title']}: {e}")
        return None

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
            print(f"[INFO] Cleaned up temp audio file")


if __name__ == "__main__":
    # Quick test — replace with a real episode to verify the pipeline
    test_episode = {
        "anchor_id": "test",
        "episode_id": "test",
        "title": "测试单集",
        "channel": "测试播客",
        "description": "这是一个测试单集。",
        "url": "https://www.xiaoyuzhoufm.com/",
        "audio_url": "",  # set a real URL to test
    }
    if not test_episode["audio_url"]:
        print("[ERROR] Set audio_url to a real episode URL before testing.")
    else:
        result = summarize_episode(test_episode)
        if result:
            print("\n--- 摘要预览 ---")
            print(result[:800], "...")
