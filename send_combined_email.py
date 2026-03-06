from datetime import date
from dotenv import load_dotenv
import pathlib

import re
from send_email import CSS, render_card, card_anchor, render_short_videos_section, _send_html_email, bold

_MONTH_CN = ["1月", "2月", "3月", "4月", "5月", "6月",
             "7月", "8月", "9月", "10月", "11月", "12月"]


def _date_cn():
    today = date.today()
    return f"{_MONTH_CN[today.month - 1]}{today.day}日"


def _adapt_for_render(item):
    """Bridge podcast episode dict to the format render_card expects."""
    ep = item["episode"]
    return {"video": {**ep, "video_id": ep["anchor_id"]}, "digest": item["digest"]}

load_dotenv()


def build_combined_toc(youtube_digests, podcast_digests):
    rows = ""
    num = 1

    if youtube_digests:
        rows += '<tr><td colspan="3" style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#888;padding:6px 0 4px;">📺 YouTube</td></tr>'
        for item in youtube_digests:
            video = item["video"]
            anchor = card_anchor(video)
            rows += f"""
        <tr class="toc-row">
          <td style="padding:5px 8px 5px 0;width:22px;font-size:11px;color:#777;vertical-align:top;">{num}.</td>
          <td style="padding:5px 8px 5px 0;width:140px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#555;vertical-align:top;">{video['channel']}</td>
          <td style="padding:5px 0;vertical-align:top;"><a class="toc-link" href="#{anchor}">{video['title']}</a></td>
        </tr>"""
            num += 1

    if podcast_digests:
        margin = "padding-top:10px;" if youtube_digests else ""
        rows += f'<tr><td colspan="3" style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#888;padding:6px 0 4px;{margin}">🎙️ 播客</td></tr>'
        for item in podcast_digests:
            adapted = _adapt_for_render(item)
            video = adapted["video"]
            anchor = card_anchor(video)
            rows += f"""
        <tr class="toc-row">
          <td style="padding:5px 8px 5px 0;width:22px;font-size:11px;color:#777;vertical-align:top;">{num}.</td>
          <td style="padding:5px 8px 5px 0;width:140px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#555;vertical-align:top;">{video['channel']}</td>
          <td style="padding:5px 0;vertical-align:top;"><a class="toc-link" href="#{anchor}">{video['title']}</a></td>
        </tr>"""
            num += 1

    return f"""
    <div class="toc">
      <div class="toc-title">In This Issue</div>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">{rows}</table>
    </div>"""


def build_combined_email_html(youtube_digests, podcast_digests, yt_short_videos=None):
    today_en = date.today().strftime("%B %d, %Y")
    date_cn = _date_cn()
    yt_count = len(youtube_digests)
    pod_count = len(podcast_digests)

    toc_html = build_combined_toc(youtube_digests, podcast_digests)

    youtube_html = ""
    if youtube_digests:
        youtube_html = "\n".join(render_card(item) for item in youtube_digests)

    podcast_html = ""
    if podcast_digests:
        adapted = [_adapt_for_render(item) for item in podcast_digests]
        podcast_html = "\n".join(render_card(item) for item in adapted)

    short_html = render_short_videos_section(yt_short_videos or [])

    divider = ""
    if youtube_digests and podcast_digests:
        divider = '<hr style="border:none;border-top:2px solid #ddd;margin:24px 0;">'

    count_line = []
    if yt_count:
        count_line.append(f"{yt_count} video{'s' if yt_count != 1 else ''}")
    if pod_count:
        count_line.append(f"{pod_count} 期播客")
    count_str = " · ".join(count_line)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="light">
  <meta name="supported-color-schemes" content="light">
  <style>{CSS}</style>
</head>
<body>
<div class="email">
  <div class="header">
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <td style="vertical-align:middle;">
          <div class="header-title">📺🎙️ Daily Digest</div>
          <div class="header-sub">YouTube + 播客 · AI 智能摘要</div>
        </td>
        <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
          <div class="header-date">{today_en} · {date_cn}</div>
          <div class="header-count">{count_str}</div>
        </td>
      </tr>
    </table>
  </div>
  {toc_html}
  {youtube_html}
  {divider}
  {podcast_html}
  {short_html}
</div>
</body>
</html>"""


def send_combined_digest(youtube_digests, podcast_digests, yt_short_videos=None):
    today = date.today().strftime("%B %d, %Y")
    yt_count = len(youtube_digests)
    pod_count = len(podcast_digests)

    parts = []
    if yt_count:
        parts.append(f"{yt_count} video{'s' if yt_count != 1 else ''}")
    if pod_count:
        parts.append(f"{pod_count} 期播客")
    subject = f"📺🎙️ Daily Digest — {today} ({', '.join(parts)})"
    html_body = build_combined_email_html(youtube_digests, podcast_digests, yt_short_videos or [])

    # Save HTML copy to archive before sending
    today_iso = date.today().isoformat()
    archive_dir = pathlib.Path("archive") / today_iso
    archive_dir.mkdir(parents=True, exist_ok=True)
    html_path = archive_dir / "digest.html"
    html_path.write_text(html_body, encoding="utf-8")
    print(f"[INFO] HTML archive saved to {html_path}")

    _send_html_email(subject, html_body)


def _linkify_citations(text: str, url_map: dict) -> str:
    """Replace [N] or [N, M, ...] with clickable superscript links."""
    def replace(m):
        nums = [int(x.strip()) for x in m.group(1).split(',')]
        parts = []
        for n in nums:
            url = url_map.get(n, "")
            if url:
                parts.append(f'<a href="{url}" style="color:#1d4ed8;font-size:10px;font-weight:700;vertical-align:super;text-decoration:none;">[{n}]</a>')
            else:
                parts.append(f'[{n}]')
        return ''.join(parts)
    return re.sub(r'\[([\d,\s]+)\]', replace, text)


def _render_weekly_synthesis(synthesis_md: str, url_map: dict) -> str:
    """Convert weekly synthesis markdown to HTML."""
    html = ""
    in_themes = False
    in_insights = False
    in_theme_block = False  # tracks whether a theme-row div is open
    in_insight_block = False  # tracks whether an insight-row div is open

    for line in synthesis_md.split("\n"):
        s = line.strip()
        if not s:
            continue

        is_indented = line.startswith((' ', '\t'))

        if s.startswith("## Converging Signals"):
            html += '<div class="section"><div class="section-label label-2" style="margin-bottom:12px;">Converging Signals</div>'
            in_themes = True
            in_insights = False
            continue

        if s.startswith("## Standout Takes"):
            if in_theme_block:
                html += '</div>'
                in_theme_block = False
            if in_themes:
                html += '</div>'
            html += '<div class="section" style="margin-top:16px;"><div class="section-label label-3" style="margin-bottom:12px;">Standout Takes</div>'
            in_insights = True
            in_themes = False
            continue

        if re.match(r'[-*]\s+\*\*', s) and in_themes and not is_indented:
            if in_theme_block:
                html += '</div>'
            match = re.match(r'[-*]\s+\*\*(.+?)\*\*[：:]\s*(.+)', s)
            if match:
                theme_name = match.group(1)
                theme_desc = _linkify_citations(match.group(2), url_map)
                html += f'<div class="theme-row"><div class="theme-title">{theme_name}</div><div class="theme-body" style="margin-bottom:5px;">{bold(theme_desc)}</div>'
            else:
                content = _linkify_citations(re.sub(r'^[-*]\s+', '', s), url_map)
                html += f'<div class="theme-row"><div class="theme-body" style="margin-bottom:5px;">{bold(content)}</div>'
            in_theme_block = True

        elif re.match(r'[-*]\s+', s) and in_themes and is_indented:
            content = _linkify_citations(re.sub(r'^[-*]\s+', '', s), url_map)
            html += f'<div style="font-size:12px;color:#444;padding:3px 0 3px 12px;line-height:1.5;border-left:2px solid #e5e7eb;margin:2px 0 2px 4px;">→ {content}</div>'

        elif re.match(r'[-*]\s+', s) and in_insights and not is_indented:
            if in_insight_block:
                html += '</div>'
            content = _linkify_citations(re.sub(r'^[-*]\s+', '', s), url_map)
            html += f'<div class="theme-row"><div class="theme-body">• {bold(content)}</div>'
            in_insight_block = True

        elif re.match(r'[-*]\s+\[', s) and in_insights and is_indented:
            content = _linkify_citations(re.sub(r'^[-*]\s+', '', s), url_map)
            html += f'<div style="font-size:12px;color:#444;padding:3px 0 3px 12px;line-height:1.5;border-left:2px solid #e5e7eb;margin:2px 0 2px 4px;">→ {content}</div>'

    if in_theme_block:
        html += '</div>'
    if in_insight_block:
        html += '</div>'
    if in_themes or in_insights:
        html += '</div>'

    return html


def _render_weekly_digest_list(items: list[tuple[str, str, str, str]]) -> str:
    """Render the 'This week's digests' list grouped by date.

    Args:
        items: List of (title, url, channel, date_str) tuples
    """
    if not items:
        return ""

    from datetime import date as date_type

    # Group by date, preserving global sequential numbering
    groups: dict[str, list] = {}
    for i, (title, url, channel, d) in enumerate(items, 1):
        groups.setdefault(d, []).append((i, title, url, channel))

    rows = ""
    for date_str, group_items in groups.items():
        d = date_type.fromisoformat(date_str)
        day_label = d.strftime("%a, %b %-d")
        rows += f'''<tr>
          <td colspan="2" style="padding:10px 0 3px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#999;">{day_label}</td>
        </tr>'''
        for i, title, url, channel in group_items:
            rows += f'''<tr class="toc-row">
              <td style="padding:4px 8px 4px 0;width:22px;font-size:11px;color:#777;vertical-align:top;">{i}.</td>
              <td style="padding:4px 0;vertical-align:top;"><a href="{url}" style="color:#1d4ed8;text-decoration:none;">{title}</a><span style="color:#666;font-size:12px;"> — {channel}</span></td>
            </tr>'''

    return f'''
    <div class="section" style="margin-top:20px;">
      <div class="section-label label-6" style="margin-bottom:12px;">This Week's Digests</div>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">{rows}</table>
    </div>'''


def build_weekly_email_html(synthesis_md: str, items: list[tuple[str, str, str, str]], date_range: str) -> str:
    """Build HTML for weekly digest email.

    Args:
        synthesis_md: Markdown content with themes and insights
        items: List of (title, url, channel, date_str) tuples
        date_range: Display string like "Mar 1–7, 2026"
    """
    url_map = {i: url for i, (_, url, _, _) in enumerate(items, 1)}
    synthesis_html = _render_weekly_synthesis(synthesis_md, url_map)
    digest_list_html = _render_weekly_digest_list(items)
    item_count = len(items)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="light">
  <meta name="supported-color-schemes" content="light">
  <style>{CSS}</style>
</head>
<body>
<div class="email">
  <div class="header">
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <td style="vertical-align:middle;">
          <div class="header-title">📊 Weekly Digest</div>
          <div class="header-sub">Your week in themes · AI synthesis</div>
        </td>
        <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
          <div class="header-date">{date_range}</div>
          <div class="header-count">{item_count} item{"s" if item_count != 1 else ""}</div>
        </td>
      </tr>
    </table>
  </div>
  <div class="card">
    <div class="card-body" style="padding:20px 26px;">
      {synthesis_html}
      {digest_list_html}
    </div>
  </div>
</div>
</body>
</html>"""


def send_weekly_digest(synthesis_md: str, items: list[tuple[str, str, str, str]], date_range: str):
    """Send weekly digest email.

    Args:
        synthesis_md: Markdown content with themes and insights
        items: List of (title, url, channel, date_str) tuples
        date_range: Display string like "Mar 1–7, 2026"
    """
    item_count = len(items)
    subject = f"📊 Weekly Digest — {date_range} ({item_count} item{'s' if item_count != 1 else ''})"
    html_body = build_weekly_email_html(synthesis_md, items, date_range)

    today_iso = date.today().isoformat()
    archive_dir = pathlib.Path("archive") / today_iso
    archive_dir.mkdir(parents=True, exist_ok=True)
    html_path = archive_dir / "weekly_digest.html"
    html_path.write_text(html_body, encoding="utf-8")
    print(f"[INFO] Weekly HTML archive saved to {html_path}")

    _send_html_email(subject, html_body)
