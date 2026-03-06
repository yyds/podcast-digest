#!/usr/bin/env python3
"""Weekly digest: synthesize common themes from the past week's content."""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

from synthesize import extract_part1, parse_digest_metadata, synthesize_weekly
from send_combined_email import send_weekly_digest


def get_date_range(days_back: int = 7) -> tuple[date, date]:
    """Return (start_date, end_date) for the past N days."""
    end = date.today()
    start = end - timedelta(days=days_back)
    return start, end


def scan_archive(start_date: date, end_date: date) -> list[dict]:
    """Scan archive directories for digest files in the date range.
    
    Returns list of dicts with: title, channel, url, part1
    """
    archive_root = Path("archive")
    if not archive_root.exists():
        print("[WARN] Archive directory not found")
        return []

    items = []
    current = start_date

    while current <= end_date:
        date_dir = archive_root / current.isoformat()
        if date_dir.exists():
            for md_file in date_dir.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    metadata = parse_digest_metadata(content)
                    part1 = extract_part1(content)

                    if metadata["title"] and part1:
                        items.append({
                            "title": metadata["title"],
                            "channel": metadata["channel"],
                            "url": metadata["url"],
                            "part1": part1,
                            "date": current.isoformat(),
                        })
                except Exception as e:
                    print(f"[WARN] Failed to parse {md_file}: {e}")
                    continue

        current += timedelta(days=1)

    return items


def format_date_range(start: date, end: date) -> str:
    """Format date range for display: 'Mar 1–7, 2026'."""
    if start.month == end.month:
        return f"{start.strftime('%b')} {start.day}–{end.day}, {end.year}"
    return f"{start.strftime('%b %d')}–{end.strftime('%b %d')}, {end.year}"


def main():
    print("[INFO] Starting weekly digest...")

    start_date, end_date = get_date_range(7)
    print(f"[INFO] Scanning archive for {start_date} to {end_date}")

    items = scan_archive(start_date, end_date)
    print(f"[INFO] Found {len(items)} digest files")

    if len(items) < 2:
        print("[INFO] Not enough content for weekly synthesis (need at least 2). Skipping.")
        return

    synthesis_input = [(item["title"], item["part1"]) for item in items]
    print(f"[INFO] Generating synthesis with Gemini...")
    synthesis_md = synthesize_weekly(synthesis_input)

    if not synthesis_md:
        print("[ERROR] Failed to generate synthesis")
        return

    print("[INFO] Synthesis complete. Sending email...")

    digest_items = [(item["title"], item["url"], item["channel"], item["date"]) for item in items]
    date_range_str = format_date_range(start_date, end_date)

    send_weekly_digest(synthesis_md, digest_items, date_range_str)
    print("[INFO] Weekly digest complete!")


if __name__ == "__main__":
    main()
