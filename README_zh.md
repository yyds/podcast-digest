[English](README.md) | [中文](README_zh.md)

# Podcast Digest — 双语内容 AI 摘要系统

我订阅了一堆英文 YouTube 频道和中文播客，每天根本看不完。

于是我做了这个工具：每天自动抓取新内容，转录音频，用 AI 提炼重点，然后直接发到我邮箱。不用打开任何 App，不用记得去刷，内容自己找到你。

支持：**英文 YouTube 频道** + **中文播客（小宇宙 / Apple Podcasts）**

---

## 每天能收到什么

每封摘要邮件包含：
- **内容概览** — 核心论点和关键结论
- **主要议题** — 重点讨论内容 + 带时间戳的原文引用（YouTube 可直接点击跳转）
- **行动建议** — 根据你的背景（产品、投资、研究等）定制化
- **观察 / 教训 / 关键实体** — 以及可选的推文灵感和博客写作角度

不到 20 分钟的短视频不做完整摘要，但会出现在"今日更新"列表里，不会漏掉。

**每周日晚上**还会发一封周报：把本周所有内容的要点汇总起来，找出跨内容的共同规律（Converging Signals）和反直觉洞察（Standout Takes），并附上原始链接。

---

## 前置条件

- Python 3.9 或以上版本 — [点这里下载](https://www.python.org/downloads/)
- 终端工具（Mac 自带的 Terminal.app 就行）
- 下面列出的 API 服务账号（大多数都有免费额度，够个人用）

安装依赖：
```bash
pip3 install -r requirements.txt
```

---

## 快速上手

**所有命令都需要在项目文件夹内运行**（打开 Terminal，`cd` 进项目目录）。

**第一步：初始化配置文件**
```bash
cp .env.example .env
cp config.example.json config.json
```

打开 `.env`，填入你的 API Key 和邮箱地址。
打开 `config.json`，填入你的名字和背景介绍 — AI 会根据这个来定制摘要内容。

**第二步：跑一次每日摘要**
```bash
python3 main_daily.py
```
会自动抓取过去 24 小时的新内容，生成摘要，发送到你邮箱。

**第三步：对任意链接生成摘要（随时可用）**
```bash
python3 digest_url.py "https://www.youtube.com/watch?v=..."
python3 digest_url.py "https://www.xiaoyuzhoufm.com/episode/..."
python3 digest_url.py "https://podcasts.apple.com/..."
```

---

## API Key 配置

| Key | 用途 | 获取地址 |
|-----|------|---------|
| `YOUTUBE_API_KEY` | 抓取 YouTube 视频 | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `GEMINI_API_KEY` | YouTube 内容摘要 | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` | 发送摘要邮件 | [Google App Passwords](https://myaccount.google.com/apppasswords) |
| `RECIPIENT_EMAIL` | 收件人邮箱 | 你自己的邮箱 |
| `GROQ_API_KEY` | 播客音频转录（可选） | [Groq Console](https://console.groq.com/keys) |
| `DEEPSEEK_API_KEY` | 中文播客摘要（可选） | [DeepSeek](https://platform.deepseek.com/api_keys) |

**只用 YouTube？** 可以不填 `GROQ_API_KEY` 和 `DEEPSEEK_API_KEY`，系统会自动跳过播客处理，只发 YouTube 摘要。

---

## 配置说明

| 文件 | 作用 |
|------|------|
| `channels_en.json` | 要监控的 YouTube 频道列表 |
| `channels_xyz.json` | 中文播客订阅（可选，不用可留空） |
| `config.json` | 你的名字和背景，用于 AI 个性化摘要 |
| `.env` | API Key 和邮箱凭证（不会提交到 git） |

`config.json` 里的个人背景会直接影响 AI 的分析角度 — 比如你是产品经理，它会着重提炼产品洞察；你是投资人，它会标出市场信号。按你自己的情况填就好。

**通过命令行管理播客订阅：**
```bash
python3 manage_podcasts.py list
python3 manage_podcasts.py add "播客名称或链接"
python3 manage_podcasts.py remove 2
```

---

## 定时运行（macOS）

macOS 有个内置的任务调度工具叫 **launchd**，可以让脚本按计划自动跑。

你需要创建几个小配置文件（plist 格式），告诉系统什么时候运行哪个脚本。

**三个定时任务：**

| 任务 | 时间 | 脚本 |
|------|------|------|
| 早间摘要 | 每天早上 7:00 | `main_daily.py` |
| 午间摘要 | 每天中午 12:00 | `main_daily.py` |
| 每周汇总 | 周日晚上 9:00 | `main_weekly.py` |

**配置步骤：**

1. 在 `~/Library/LaunchAgents/` 创建一个 plist 文件（参考英文 README 中的模板）
2. 把 `/path/to/project` 替换成你的实际项目路径
3. 执行加载命令：`launchctl load ~/Library/LaunchAgents/com.yourname.podcastdigest.plist`

具体 plist 模板见 [English README](README.md#scheduling-macos)。

---

## 技术架构

- **get_videos.py** — YouTube Data API，24h 时间窗口，过滤 20 分钟以下短视频
- **get_podcasts_xyz.py** — RSS 抓取，24h 时间窗口
- **summarize.py** — YouTube 字幕获取 → Gemini 摘要
- **summarize_podcast.py** — 音频下载 → Groq Whisper 转录 → DeepSeek 摘要
- **send_combined_email.py** — HTML 邮件构建和发送
- **main_daily.py** — 每日主流程
- **main_weekly.py** — 每周汇总：扫描 archive，调用 Gemini，发送主题报告
- **synthesize.py** — 提取各篇摘要要点，生成跨内容主题分析
- **digest_url.py** — 按需处理任意 YouTube / 小宇宙 / Apple Podcasts 链接

---

## 设计决策与踩坑记录

### 为什么每天跑两次（早上 7 点 + 中午 12 点）？
两个原因，都是实际用下来发现的：

1. **YouTube 字幕生成有延迟** — 视频发布后，自动生成的字幕通常要 1-3 小时才可用。早上 7 点抓一次，中午 12 点再抓一次，可以捕捉到那些早上字幕还没准备好的内容。

2. **Groq 免费额度限制** — 播客转录用的是 Groq Whisper，免费额度够用但有上限。分两次跑，把转录量分散到两个时段，避免单次触达限制。

### 为什么中文播客要用两个模型（Groq Whisper + DeepSeek）？
处理中文播客需要两个独立步骤：
- **Groq Whisper** — 音频转文字。目前最好的免费转录 API，速度快，准确度高。
- **DeepSeek** — 中文内容理解和摘要。在中文语言质量、语感和文化语境上，明显优于 GPT-4 等其他模型。

用单一模型同时做转录和摘要（比如全用 Gemini）效果差很多，特别是中文内容。

### 为什么用邮件而不是做个 App 或者 Dashboard？
零摩擦。邮件可搜索、任何设备都能看、不用安装任何东西、跟你已有的通知系统天然集成。Dashboard 要你主动去打开；邮件出现在你本来就在的地方。

### 为什么过滤 20 分钟以下的短视频？
短视频通常没有足够的深度值得做完整摘要。它们会出现在"今日更新"列表里，不会消失——只是不做全文分析。这样保证摘要里的内容都是值得细读的。

### 为什么用 24 小时时间窗口？
YouTube 和播客统一用 24h 回溯，避免重复处理。窗口太长会重复抓旧内容；窗口太短，某次运行失败了就可能漏内容。

### 为什么用配置文件做个性化，而不是微调模型？
把个人背景（名字、职业、关注点）写进一个文本配置文件，可以换任何 LLM 都生效、不需要重新训练、随时修改。微调会把你绑定在某个模型上，每次兴趣变了还得重新来一遍。

### 为什么用多个 LLM 而不是统一用一个？
用最合适的工具做最合适的事：
- **Gemini**（YouTube）— 速度快、成本低、处理长文本效果好
- **Groq Whisper**（音频转录）— 免费额度最慷慨的转录 API
- **DeepSeek**（中文播客）— 中文语言输出质量最高

用一个模型包办所有任务，至少在其中某个环节上效果会明显变差。
