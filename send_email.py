import json
import os
import re
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def _load_actionable_label():
    """Load actionable section label from config. Forkers can customize via reader.actionable_label."""
    try:
        with open("config.json") as f:
            return json.load(f).get("reader", {}).get("actionable_label", "For You")
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return "For You"


def _get_recipients():
    return [r for r in [os.getenv("RECIPIENT_EMAIL"), os.getenv("RECIPIENT_EMAIL_2")] if r]


def _send_html_email(subject, html_body):
    """Send HTML email to configured recipients via Gmail SMTP."""
    recipients = _get_recipients()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())
        print(f"[INFO] Email sent to {', '.join(recipients)}")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f0efeb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; color: #111; }
.email { max-width: 680px; margin: 24px auto; }
.header { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 18px 26px; margin-bottom: 12px; }
.header-title { font-size: 19px; font-weight: 700; letter-spacing: -0.4px; }
.header-sub { font-size: 11px; color: #666; margin-top: 2px; }
.header-date { font-size: 13px; color: #333; text-align: right; }
.header-count { font-size: 11px; color: #666; text-align: right; margin-top: 2px; }
.card { background: #fff; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 12px; overflow: hidden; }
.card-top { padding: 18px 26px 13px; border-bottom: 1px solid #f0efe9; }
.card-channel { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #555; margin-bottom: 4px; }
.card-title { font-size: 18px; font-weight: 700; line-height: 1.3; letter-spacing: -0.3px; margin-bottom: 7px; color: #111; }
.card-byline { font-size: 12px; color: #444; }
.watch-link { color: #c0392b; font-weight: 700; text-decoration: none; margin-left: 10px; }
.card-body { padding: 16px 26px 20px; }
.section { margin-bottom: 16px; }
.section-label { display: inline-block; vertical-align: middle; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.7px; padding: 3px 9px; border-radius: 4px; margin-bottom: 9px; }
.label-1 { background: #dbeafe; color: #1e40af; }
.label-2 { background: #ede9fe; color: #5b21b6; }
.label-3 { background: #d1fae5; color: #065f46; }
.label-4 { background: #fef3c7; color: #78350f; }
.label-5 { background: #fee2e2; color: #7f1d1d; }
.label-6 { background: #e5e7eb; color: #1f2937; }
.label-7 { background: #cffafe; color: #0e4f60; }
.label-8 { background: #fce7f3; color: #831843; }
.summary { font-size: 14px; line-height: 1.7; color: #222; margin-bottom: 9px; }
.topic-list { list-style: none; border-top: 1px solid #e8e8e4; }
.topic-list li { padding: 6px 0; border-bottom: 1px solid #e8e8e4; font-size: 13px; line-height: 1.5; color: #222; }
.conclusion { background: #f3f4f6; border-radius: 6px; padding: 8px 12px; font-size: 13px; color: #333; line-height: 1.6; margin-top: 8px; }
.theme-row { padding: 9px 0; border-bottom: 1px solid #ebebeb; }
.theme-row:last-child { border-bottom: none; }
.theme-title { font-size: 13px; font-weight: 700; color: #111; margin-bottom: 3px; }
.theme-body { font-size: 13px; color: #333; line-height: 1.6; }
.quote-block { margin-top: 5px; font-style: italic; color: #555; font-size: 13px; line-height: 1.5; }
.ts { font-style: normal; font-size: 11px; font-weight: 700; color: #1d4ed8; text-decoration: none; background: #dbeafe; padding: 1px 5px; border-radius: 3px; }
.action-row { padding: 8px 11px; background: #f3f4f6; border-radius: 6px; margin-bottom: 6px; }
.action-title { font-size: 13px; font-weight: 700; color: #111; margin-bottom: 3px; }
.action-body { font-size: 12px; color: #333; line-height: 1.6; }
.action-label { font-weight: 700; color: #111; }
.obs-row { padding: 8px 11px; border-left: 3px solid #d97706; background: #fef9ec; border-radius: 0 6px 6px 0; margin-bottom: 6px; }
.entity-grid { width: 100%; border-collapse: collapse; }
.entity-pill { background: #f0efeb; border-radius: 4px; padding: 6px 9px; }
.entity-name { font-weight: 700; color: #111; font-size: 12px; }
.entity-ctx { color: #555; font-size: 11px; margin-top: 1px; }
.tweet-box { background: #e8f4fd; border-radius: 6px; padding: 8px 11px; margin-bottom: 5px; font-size: 13px; line-height: 1.5; color: #0c2d4e; }
.blog-row { padding: 8px 0; border-bottom: 1px solid #e8e8e4; }
.blog-row:last-child { border-bottom: none; }
.blog-title { font-size: 13px; font-weight: 700; color: #111; margin-bottom: 3px; }
.blog-arg { font-size: 12px; color: #333; line-height: 1.5; margin-bottom: 3px; }
.blog-quote { font-size: 12px; font-style: italic; color: #666; }
.plain-item { font-size: 13px; color: #222; line-height: 1.6; padding: 3px 0; }
.toc { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 16px 26px; margin-bottom: 12px; }
.toc-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #555; margin-bottom: 10px; }
.toc-row { border-bottom: 1px solid #e8e8e4; }
.toc-row:last-child { border-bottom: none; }
.toc-num { font-size: 11px; color: #777; min-width: 22px; }
.toc-channel { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #555; min-width: 140px; }
.toc-link { font-size: 13px; color: #1d4ed8; text-decoration: none; line-height: 1.4; }
.toc-link:hover { text-decoration: underline; }
"""

def _section_config():
    label = _load_actionable_label()
    return {
        1: ("label-1", "① Overview"),
        2: ("label-2", "② Key Themes & Insights"),
        3: ("label-3", f"⑧ {label}"),
        4: ("label-4", "③ Noteworthy Observations"),
        5: ("label-5", "④ Lessons Learned"),
        6: ("label-6", "⑤ Entities Mentioned"),
        7: ("label-7", "⑥ Tweet-sized takeaways"),
        8: ("label-8", "⑦ Essay angles"),
    }


SECTION_CONFIG = _section_config()


def make_timestamp_link(text, video_url):
    is_youtube = "youtube.com" in video_url or "youtu.be" in video_url

    def replace(m):
        t = m.group(1)
        parts = t.split(":")
        if len(parts) == 3:
            secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            secs = int(parts[0]) * 60 + int(parts[1])
        if is_youtube:
            href = f"{video_url}&t={secs}s"
        else:
            href = video_url  # podcast: link to episode page, no timestamp param
        return f'<a class="ts" href="{href}">{t}</a>'

    return re.sub(r'\[(\d{1,3}:\d{2}(?::\d{2})?)\]', replace, text)


def bold(text):
    result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'\*\*', '', result)


def parse_header(digest):
    """Extract host/guest from digest header lines (English or Chinese)."""
    hosts, guests = "", "N/A"
    for line in digest.split("\n")[:6]:
        if line.startswith("**Host") or line.startswith("**主播"):
            hosts = re.sub(r'\*\*(Host\(s\)|主播)[:：]\*\*\s*', '', line).strip()
        if line.startswith("**Guest") or line.startswith("**嘉宾"):
            guests = re.sub(r'\*\*(Guest\(s\)|嘉宾)[:：]\*\*\s*', '', line).strip()
    return hosts, guests


def split_sections(digest):
    """Split digest into numbered sections."""
    sections = {}
    current_num = 0
    current_lines = []

    for line in digest.split("\n"):
        m = re.match(r'### Part (\d+):', line)
        if m:
            if current_num:
                sections[current_num] = "\n".join(current_lines).strip()
            current_num = int(m.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    if current_num:
        sections[current_num] = "\n".join(current_lines).strip()
    return sections


def _parse_section_1(content):
    """Parse Part 1 (Overview) into summary, key_points, topics, conclusion."""
    summary, key_points, topics, conclusion = "", [], [], ""
    mode = None

    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue

        if s.startswith("**Overall Summary") or s.startswith("**总体摘要"):
            summary = re.sub(r"\*\*(Overall Summary|总体摘要)[:：]\*\*\s*", "", s)
            mode = None
        elif s.startswith("**关键点"):
            mode = "key_points"
        elif s.startswith("**Key Topics") or s.startswith("**关键主题"):
            mode = "topics"
        elif s.startswith("**Conclusion") or s.startswith("**结论"):
            conclusion = re.sub(r"\*\*(Conclusion|结论)[:：]\*\*\s*", "", s)
            mode = None
        elif mode == "key_points" and s.startswith("-"):
            key_points.append(re.sub(r"^-\s*", "", s))
        elif mode == "topics" and re.match(r"^\d+\.", s):
            topics.append(re.sub(r"^\d+\.\s*", "", s))

    return {"summary": summary, "key_points": key_points, "topics": topics, "conclusion": conclusion}


def _strip_bold_markers(text):
    """Remove ** markdown from text so it displays cleanly."""
    return re.sub(r'\*\*', '', text)


def _render_topic_list(items, is_chinese):
    """Render a list of topic items (name:desc or plain) as HTML."""
    sep = "：" if is_chinese else ":"
    html = '<ul class="topic-list">'
    for t in items:
        parts = t.split(sep, 1)
        if len(parts) == 2:
            name = _strip_bold_markers(parts[0].strip())
            html += f'<li><strong>{name}</strong>{sep}{bold(parts[1])}</li>'
        else:
            html += f"<li>{bold(t)}</li>"
    html += "</ul>"
    return html


def render_section_1(content, video_url, is_chinese=False):
    parsed = _parse_section_1(content)
    html = ""

    if parsed["summary"]:
        html += f'<p class="summary">{bold(parsed["summary"])}</p>'

    # Chinese: key_points first, then topics. English: topics only.
    if parsed["key_points"]:
        html += _render_topic_list(parsed["key_points"], is_chinese)
    if parsed["topics"]:
        html += _render_topic_list(parsed["topics"], is_chinese)

    if parsed["conclusion"]:
        label = "结论" if is_chinese else "Conclusion"
        html += f'<div class="conclusion"><strong>{label}:</strong> {bold(parsed["conclusion"])}</div>'

    return html


def render_section_2(content, video_url, is_chinese=False):
    content = make_timestamp_link(content, video_url)
    blocks = []
    current_title, current_body, current_quote = "", "", ""

    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r'^\d+\.\s+\*\*', s) or (re.match(r'^\d+\.', s) and not s.startswith("   ")):
            if current_title:
                blocks.append((current_title, current_body, current_quote))
            text = re.sub(r'^\d+\.\s*', '', s)
            if ":" in text:
                parts = text.split(":", 1)
                current_title = re.sub(r'\*\*', '', parts[0]).strip()
                current_body = bold(parts[1].strip())
            else:
                current_title = re.sub(r'\*\*', '', text).strip()
                current_body = ""
            current_quote = ""
        elif s.lower().startswith("quote:") or s.startswith("引用："):
            current_quote = re.sub(r'^(quote:|引用：)\s*', '', s, flags=re.IGNORECASE)
        else:
            current_body += " " + bold(s)

    if current_title:
        blocks.append((current_title, current_body, current_quote))

    html = ""
    for title, body, quote in blocks:
        html += f'<div class="theme-row">'
        html += f'<div class="theme-title">{title}</div>'
        if body.strip():
            html += f'<div class="theme-body">{body.strip()}</div>'
        if quote:
            html += f'<div class="quote-block">{quote}</div>'
        html += '</div>'
    return html


def render_section_3(content, video_url, is_chinese=False):
    content = make_timestamp_link(content, video_url)
    actions = []
    current_title, current_why, current_how = "", "", ""

    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r'^\d+\.', s):
            if current_title:
                actions.append((current_title, current_why, current_how))
            current_title = re.sub(r'^\d+\.\s*', '', s)
            current_why, current_how = "", ""
        elif "why it matters" in s.lower() or "重要性" in s:
            current_why = re.sub(r'^[-*\s]*(?:why it matters|重要性)[^:]*[：:]\*{0,2}\s*', '', s, flags=re.IGNORECASE)
        elif "how to apply" in s.lower() or "如何应用" in s:
            current_how = re.sub(r'^[-*\s]*(?:how to apply|如何应用)[^:]*[：:]\*{0,2}\s*', '', s, flags=re.IGNORECASE)

    if current_title:
        actions.append((current_title, current_why, current_how))

    html = ""
    for title, why, how in actions:
        html += '<div class="action-row">'
        html += f'<div class="action-title">{bold(title)}</div>'
        html += '<div class="action-body">'
        why_label = "重要性" if is_chinese else "Why it matters"
        how_label = "如何应用" if is_chinese else "How to apply"
        if why:
            html += f'<span class="action-label">{why_label}:</span> {bold(why)}<br>'
        if how:
            html += f'<span class="action-label">{how_label}:</span> {bold(how)}'
        html += '</div></div>'
    return html


def render_section_4(content, video_url, is_chinese=False):
    content = make_timestamp_link(content, video_url)
    html = ""
    current_body, current_quote = "", ""

    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r'^\d+\.', s):
            if current_body or current_quote:
                html += f'<div class="obs-row"><div class="theme-body">{bold(current_body)}</div>'
                if current_quote:
                    html += f'<div class="quote-block">{current_quote}</div>'
                html += '</div>'
            current_body = re.sub(r'^\d+\.\s*', '', s)
            current_quote = ""
        elif s.lower().startswith("quote:") or s.startswith("引用："):
            current_quote = re.sub(r'^(quote:|引用：)\s*', '', s, flags=re.IGNORECASE)
        else:
            current_body += " " + s

    if current_body or current_quote:
        html += f'<div class="obs-row"><div class="theme-body">{bold(current_body)}</div>'
        if current_quote:
            html += f'<div class="quote-block">{current_quote}</div>'
        html += '</div>'
    return html


def render_section_5(content, video_url, is_chinese=False):
    html = ""
    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue
        s = re.sub(r'^-\s*', '', s)
        html += f'<p class="plain-item">• {bold(s)}</p>'
    return html


def render_section_6(content, video_url, is_chinese=False):
    items = []
    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue
        m = re.match(r'^\d+\.\s*(.+)', s)
        if m:
            text = m.group(1)
            if " — " in text:
                parts = text.split(" — ", 1)
                items.append((parts[0].strip(), parts[1].strip()))
            else:
                items.append((text.strip(), ""))

    html = '<table class="entity-grid" cellpadding="0" cellspacing="0">'
    for i, (name, ctx) in enumerate(items):
        if i % 2 == 0:
            html += '<tr>'
        clean_name = re.sub(r'\*\*', '', name)
        pad = "padding:0 4px 5px 0;" if i % 2 == 0 else "padding:0 0 5px 4px;"
        html += f'<td style="width:50%;vertical-align:top;{pad}"><div class="entity-pill"><div class="entity-name">{clean_name}</div>'
        if ctx:
            html += f'<div class="entity-ctx">{bold(ctx)}</div>'
        html += '</div></td>'
        if i % 2 == 1:
            html += '</tr>'
    if len(items) % 2 == 1:
        html += '<td style="width:50%;"></td></tr>'
    html += '</table>'
    return html


def render_section_7(content, video_url, is_chinese=False):
    html = ""
    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue
        s = re.sub(r'^\d+\.\s*', '', s)
        html += f'<div class="tweet-box">{bold(s)}</div>'
    return html


def _blog_title_html(text):
    """Render Essay angles: title (bold, same as other parts) on first line, description on second. No colon."""
    text = _strip_bold_markers(text)
    if ": " in text:
        title_part, desc_part = text.split(": ", 1)
        return f'<div class="theme-title">{title_part.strip()}</div><div class="theme-body" style="font-weight:normal">{desc_part.strip()}</div>'
    return f'<div class="theme-title">{text}</div>'


def render_section_8(content, video_url, is_chinese=False):
    html = ""
    current_title, current_arg, current_quote = "", "", ""

    for line in content.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r'^\d+\.', s):
            if current_title:
                html += f'<div class="blog-row"><div class="blog-title">{_blog_title_html(current_title)}</div>'
                if current_arg:
                    html += f'<div class="blog-arg">{current_arg}</div>'
                if current_quote:
                    html += f'<div class="blog-quote">"{current_quote}"</div>'
                html += '</div>'
            current_title = re.sub(r'^\d+\.\s*(Title:\s*|标题：\s*)', '', s).strip('"').strip('\u300c\u300d\u201c\u201d')
            current_arg, current_quote = "", ""
        elif s.lower().startswith("core argument:") or s.startswith("核心论点："):
            current_arg = bold(re.sub(r'^(core argument:|核心论点：)\s*', '', s, flags=re.IGNORECASE))
        elif s.lower().startswith("anchor quote:") or s.startswith("锚点引用："):
            raw = re.sub(r'^(anchor quote:|锚点引用：)\s*["\'\u201c\u300c]?', '', s, flags=re.IGNORECASE).rstrip('"\'\u201d\u300d')
            current_quote = make_timestamp_link(bold(raw), video_url)  # Timestamps in quote clickable like Part 2

    if current_title:
        html += f'<div class="blog-row"><div class="blog-title">{_blog_title_html(current_title)}</div>'
        if current_arg:
            html += f'<div class="blog-arg">{current_arg}</div>'
        if current_quote:
            html += f'<div class="blog-quote">"{current_quote}"</div>'
        html += '</div>'
    return html


SECTION_RENDERERS = {
    1: render_section_1,
    2: render_section_2,
    3: render_section_3,
    4: render_section_4,
    5: render_section_5,
    6: render_section_6,
    7: render_section_7,
    8: render_section_8,
}


def card_anchor(video):
    """Generate a stable anchor ID from video id."""
    return f"vid-{video['video_id']}"


def render_card(item):
    video = item["video"]
    digest = item["digest"]
    video_url = video["url"]
    anchor = card_anchor(video)
    hosts, guests = parse_header(digest)
    sections = split_sections(digest)
    is_chinese = any(line.startswith("**主播") for line in digest.split("\n")[:6])

    host_label = "主播" if is_chinese else "Host"
    guest_label = "嘉宾" if is_chinese else "Guest"
    byline = ""
    if hosts:
        byline += f"{host_label}: <strong>{hosts}</strong>"
    if guests and guests != "N/A":
        byline += f" &nbsp;·&nbsp; {guest_label}: <strong>{guests}</strong>"
    byline += f' <a class="watch-link" href="{video_url}">▶ Watch original →</a>'

    html = f"""
    <div class="card" id="{anchor}">
      <div class="card-top">
        <div class="card-channel">{video['channel']}</div>
        <div class="card-title">{video['title']}</div>
        <div class="card-byline">{byline}</div>
      </div>
      <div class="card-body">
    """

    # Part 3 (actionable) last; display labels ③–⑧ follow display order
    render_order = [1, 2, 4, 5, 6, 7, 8, 3]
    for num in render_order:
        if num not in sections:
            continue
        css_class, label = SECTION_CONFIG[num]
        content = sections[num]
        renderer = SECTION_RENDERERS.get(num)
        rendered = renderer(content, video_url, is_chinese) if renderer else f"<p>{content}</p>"
        if rendered.strip():
            html += f'<div class="section"><div class="section-label {css_class}">{label}</div>{rendered}</div>'

    html += "</div></div>"
    return html


def build_toc(digests):
    rows = ""
    for i, item in enumerate(digests, 1):
        video = item["video"]
        anchor = card_anchor(video)
        rows += f"""
        <tr class="toc-row">
          <td style="padding:5px 8px 5px 0;width:22px;font-size:11px;color:#777;vertical-align:top;">{i}.</td>
          <td style="padding:5px 8px 5px 0;width:140px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#555;vertical-align:top;">{video['channel']}</td>
          <td style="padding:5px 0;vertical-align:top;"><a class="toc-link" href="#{anchor}">{video['title']}</a></td>
        </tr>"""
    return f"""
    <div class="toc">
      <div class="toc-title">In This Issue</div>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">{rows}</table>
    </div>"""


def render_brief_card(item):
    """Compact card for short videos: Quick Take + Key Points only."""
    video = item["video"]
    digest = item["digest"]
    video_url = video["url"]
    anchor = card_anchor(video)

    lines = digest.strip().split("\n")
    html_parts = []
    bullets = []

    def flush_bullets():
        if bullets:
            items_html = "".join(
                f'<li style="font-size:13px;line-height:1.6;color:#333;margin-bottom:3px;">{bold(b)}</li>'
                for b in bullets
            )
            html_parts.append(f'<ul style="margin:4px 0 6px;padding-left:18px;">{items_html}</ul>')
        bullets.clear()

    in_bullets = False
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("- "):
            bullets.append(s[2:])
            in_bullets = True
        else:
            if in_bullets:
                flush_bullets()
                in_bullets = False
            html_parts.append(
                f'<p style="margin:0 0 8px;font-size:13px;line-height:1.6;color:#1a1a1a;">{bold(s)}</p>'
            )
    if in_bullets:
        flush_bullets()

    content_html = "\n".join(html_parts)
    return f"""
    <div class="card" id="{anchor}" style="border-left:3px solid #6366f1;">
      <div class="card-top" style="padding:14px 26px 10px;">
        <div class="card-channel">{video['channel']} <span style="font-size:10px;font-weight:600;color:#6366f1;text-transform:uppercase;letter-spacing:0.8px;margin-left:6px;">· Quick Take</span></div>
        <div class="card-title">{video['title']}</div>
        <div class="card-byline"><a class="watch-link" href="{video_url}">▶ Watch original →</a></div>
      </div>
      <div class="card-body" style="padding:12px 26px 18px;">
        {content_html}
      </div>
    </div>"""


def render_short_videos_section(short_videos):
    if not short_videos:
        return ""
    rows = ""
    for v in short_videos:
        rows += f'<tr><td style="padding:4px 10px 4px 0;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#555;white-space:nowrap;vertical-align:top;">{v["channel"]}</td><td style="padding:4px 0;font-size:13px;vertical-align:top;"><a href="{v["url"]}" style="color:#1d4ed8;text-decoration:none;">{v["title"]}</a></td></tr>'
    return f"""
    <div class="card" style="margin-top:8px;">
      <div class="card-top" style="padding:14px 26px 10px;">
        <div class="card-channel">Also Updated Today</div>
        <div style="font-size:12px;color:#666;margin-top:2px;">Under 20 min — no digest generated</div>
      </div>
      <div class="card-body" style="padding:12px 26px 16px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">{rows}</table>
      </div>
    </div>"""


def build_email_html(digests, short_videos=None):
    today = date.today().strftime("%B %d, %Y")
    count = len(digests)

    toc_html = build_toc(digests)
    cards_html = "\n".join(render_card(item) for item in digests)
    short_html = render_short_videos_section(short_videos or [])

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>{CSS}</style></head>
<body>
<div class="email">
  <div class="header">
    <div>
      <div class="header-title">📺 Daily Digest</div>
      <div class="header-sub">Your AI-powered briefing</div>
    </div>
    <div>
      <div class="header-date">{today}</div>
      <div class="header-count">{count} new video{"s" if count != 1 else ""}</div>
    </div>
  </div>
  {toc_html}
  {cards_html}
  {short_html}
</div>
</body>
</html>"""


def send_digest(digests, short_videos=None):
    today = date.today().strftime("%B %d, %Y")
    count = len(digests)
    subject = f"📺 Daily Digest — {today} ({count} new video{'s' if count != 1 else ''})"
    html_body = build_email_html(digests, short_videos or [])
    _send_html_email(subject, html_body)
