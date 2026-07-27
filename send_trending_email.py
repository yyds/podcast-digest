import os
import pathlib
import html
from datetime import date
from urllib.parse import urlparse
from dotenv import load_dotenv
from send_email import CSS, _send_html_email

load_dotenv()

_MONTH_CN = ["1月", "2月", "3月", "4月", "5月", "6月",
             "7月", "8月", "9月", "10月", "11月", "12月"]

_h = html.escape


def _date_cn():
    today = date.today()
    return f"{_MONTH_CN[today.month - 1]}{today.day}日"


def _render_github_section(repos):
    if not repos:
        return ""

    items_html = ""
    for repo in repos:
        star_text = f"+{repo['today_stars']:,} ⭐" if repo.get("today_stars") else ""
        en_title = repo.get("en_title", "")
        cn_title = repo.get("cn_title", "")
        en_what = repo.get("en_what", "")
        cn_what = repo.get("cn_what", "")
        features = repo.get("features", "")
        en_value = repo.get("en_value", "")
        cn_value = repo.get("cn_value", "")
        topics = repo.get("topics", [])

        rank = repo['rank']
        repo_url = repo['url']
        repo_name = repo['repo']
        about_text = repo.get("description", "")

        topics_html = ""
        if topics:
            topic_tags = " ".join(
                f'<span style="font-size:10px;color:#666;background:#f0f0ec;padding:1px 6px;border-radius:3px;margin-right:4px;">#{_h(t)}</span>'
                for t in topics[:5]
            )
            topics_html = f'<div style="padding:4px 0 0 18px;">{topic_tags}</div>'

        feature_lines = ""
        if features:
            feature_list = [f.strip() for f in features.replace("；", ";").split(";") if f.strip()]
            if feature_list:
                feature_lines = "".join(
                    f'<div style="padding:1px 0 1px 18px;font-size:12px;color:#333;line-height:1.5;"><span style="color:#666;">▸</span> {_h(f)}</div>'
                    for f in feature_list
                )

        title_line = f"{rank}. <a href=\"{_h(repo_url)}\" style=\"color:#0969da;text-decoration:none;\">{_h(repo_name)}</a>"
        if en_title:
            title_line += f' <span style="font-weight:400;color:#555;">— {_h(en_title)}</span>'
        if cn_title:
            title_line += f' <span style="font-size:11px;font-weight:400;color:#888;">· {_h(cn_title)}</span>'

        about_html = ""
        if about_text:
            about_html = f'<div style="font-size:11.5px;color:#888;line-height:1.5;padding:4px 0 0 18px;font-style:italic;">About: {_h(about_text)}</div>'

        items_html += f"""
    <div style="padding:14px 0;border-bottom:1px solid #e8e8e4;">
      <div style="font-size:13px;font-weight:700;color:#111;margin-bottom:4px;line-height:1.4;">
        {title_line}
        <span style="font-size:11px;color:#666;font-weight:500;margin-left:8px;">{_h(star_text)}</span>
      </div>
      <div style="font-size:12px;color:#444;line-height:1.6;padding:2px 0 2px 18px;">
        {_h(en_what)}
      </div>
      <div style="font-size:11.5px;color:#666;line-height:1.5;padding:0 0 4px 18px;">
        {_h(cn_what)}
      </div>
      {feature_lines}
      {about_html}
      <div style="font-size:12px;color:#333;line-height:1.6;padding:4px 0 0 18px;">
        {_h(en_value)}
      </div>
      <div style="font-size:11.5px;color:#666;line-height:1.5;padding:2px 0 0 18px;">
        {_h(cn_value)}
      </div>
      {topics_html}
    </div>"""

    return f"""
  <div class="card">
    <div class="card-top">
      <div class="card-channel">📈 GitHub Trending · TypeScript</div>
      <div class="card-title">{len(repos)} trending TypeScript repos · {len(repos)} 个热门 TS 项目</div>
    </div>
    <div class="card-body">
      {items_html}
    </div>
  </div>"""


def _render_hn_section(stories):
    if not stories:
        return ""

    items_html = ""
    for story in stories:
        score_text = f"{story['score']} pts" if story.get("score") else ""
        comments_text = f"{story['comments']} comments" if story.get("comments") else ""
        cn_title = story.get("cn_title", "")
        en_summary = story.get("en_summary", "")
        cn_summary = story.get("cn_summary", "")

        story_rank = story['rank']
        story_title = story['title']
        story_url = story['url']
        story_hn_url = story['hn_url']

        domain = ""
        if story_url and "news.ycombinator.com" not in story_url:
            try:
                domain = urlparse(story_url).netloc.replace("www.", "")
            except Exception:
                pass

        domain_html = f'<span style="margin:0 6px;">·</span><span style="color:#999;">{_h(domain)}</span>' if domain else ''

        items_html += f"""
    <div style="padding:12px 0;border-bottom:1px solid #e8e8e4;">
      <div style="font-size:13px;font-weight:700;color:#111;margin-bottom:3px;">
        {story_rank}. <a href="{_h(story_url)}" style="color:#0969da;text-decoration:none;">{_h(story_title)}</a>
      </div>
      <div style="font-size:11px;color:#666;padding:1px 0 4px 18px;">
        {_h(cn_title)}
        <span style="margin:0 6px;">·</span>
        {_h(score_text)}
        <span style="margin:0 6px;">·</span>
        <a href="{_h(story_hn_url)}" style="color:#666;text-decoration:none;">{_h(comments_text)}</a>
        {domain_html}
      </div>
      <div style="font-size:12px;color:#333;line-height:1.6;padding:2px 0 0 18px;">
        {_h(en_summary)}
      </div>
      <div style="font-size:11.5px;color:#666;line-height:1.5;padding:2px 0 0 18px;">
        {_h(cn_summary)}
      </div>
    </div>"""

    return f"""
  <div class="card">
    <div class="card-top">
      <div class="card-channel">🔥 Hacker News</div>
      <div class="card-title">Top {len(stories)} stories · {len(stories)} 条热门</div>
    </div>
    <div class="card-body">
      {items_html}
    </div>
  </div>"""


def build_trending_email_html(github_repos, hn_stories):
    today_en = date.today().strftime("%B %d, %Y")
    date_cn = _date_cn()
    gh_count = len(github_repos)
    hn_count = len(hn_stories)

    count_parts = []
    if gh_count:
        count_parts.append(f"{gh_count} GitHub repos")
    if hn_count:
        count_parts.append(f"{hn_count} HN stories")
    count_str = " · ".join(count_parts)

    github_html = _render_github_section(github_repos)
    hn_html = _render_hn_section(hn_stories)

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
          <div class="header-title">📈🔥 GitHub &amp; HN Trending</div>
          <div class="header-sub">每日技术热点 · AI 中文解读</div>
        </td>
        <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
          <div class="header-date">{today_en} · {date_cn}</div>
          <div class="header-count">{_h(count_str)}</div>
        </td>
      </tr>
    </table>
  </div>
  {github_html}
  {hn_html}
</div>
</body>
</html>"""


def send_trending_digest(github_repos, hn_stories):
    today = date.today().strftime("%B %d, %Y")
    gh_count = len(github_repos)
    hn_count = len(hn_stories)

    parts = []
    if gh_count:
        parts.append(f"{gh_count} GitHub")
    if hn_count:
        parts.append(f"{hn_count} HN")
    subject = f"📈🔥 GitHub & HN Trending — {today} ({', '.join(parts)})"
    html_body = build_trending_email_html(github_repos, hn_stories)

    today_iso = date.today().isoformat()
    archive_dir = pathlib.Path("archive") / today_iso
    archive_dir.mkdir(parents=True, exist_ok=True)
    html_path = archive_dir / "trending_digest.html"
    html_path.write_text(html_body, encoding="utf-8")
    print(f"[INFO] Trending HTML archive saved to {html_path}")

    _send_html_email(subject, html_body)
