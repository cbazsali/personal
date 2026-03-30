#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import quote
from typing import Optional

DIARY_DIR = Path.home() / "wiki" / "diary"
OUT_FEED = Path.home() / "sites" / "personal" / "feed.xml"

SITE_TITLE = "Colin Bazsali"
FEED_TITLE = "Colin Bazsali – Blog"
SITE_URL = "https://colinbazsali.com/"
BLOG_INDEX_URL = "https://colinbazsali.com/blog.html"
FEED_URL = "https://colinbazsali.com/feed.xml"
DESCRIPTION = "Updates from Colin Bazsali."

MAX_ITEMS = 50
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
LEGACY_TITLE_RE = re.compile(r"^\s*##\s+(.+?)\s*$")
SECTION_RE = re.compile(r"^\s*##\s+(.+?)\s*$")
BLOG_SECTION_RE = re.compile(r"^\s*##\s+.*\B#blog\b.*$", re.IGNORECASE)
BLOG_TITLE_RE = re.compile(r"^\s*###\s+(.+?)\s*$")


def markdown_to_html(md: str) -> str:
    p = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "html"],
        input=(md.rstrip() + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return p.stdout.decode("utf-8").rstrip()


def xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[’']", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "post"


def post_filename(date_s: str, title: Optional[str]) -> str:
    if title:
        return f"{date_s}-{slugify(title)}.html"
    return f"{date_s}.html"


def post_link(date_s: str, title: Optional[str]) -> str:
    return f"https://colinbazsali.com/blog/{quote(post_filename(date_s, title))}"


def split_blog_title_and_body(lines):
    title = None
    body_start = 0
    for i, line in enumerate(lines):
        if title is None:
            m = BLOG_TITLE_RE.match(line)
            if m:
                title = m.group(1).strip()
                body_start = i + 1
                break
        if line.strip():
            body_start = i
            break
    else:
        body_start = len(lines)

    body_lines = lines[body_start:]
    return title, body_lines


def extract_legacy_post(lines_after_header):
    title = None
    body_lines = []
    title_found = False

    for line in lines_after_header:
        if not title_found:
            m = LEGACY_TITLE_RE.match(line)
            if m:
                title = m.group(1).strip()
                title_found = True
                continue
        body_lines.append(line)

    return title, body_lines


def extract_blog_section(lines_after_header):
    in_blog = False
    section_lines = []

    for line in lines_after_header:
        if BLOG_SECTION_RE.match(line):
            if in_blog:
                break
            in_blog = True
            continue

        if in_blog and SECTION_RE.match(line):
            break

        if in_blog:
            section_lines.append(line)

    if not in_blog:
        return None

    title, body_lines = split_blog_title_and_body(section_lines)
    return title, body_lines


def parse_one_file(f: Path):
    lines = f.read_text(encoding="utf-8").splitlines()
    if not lines:
        return None

    first = lines[0].strip()
    if "#blog" not in first:
        return None

    m = DATE_RE.search(first)
    if not m:
        return None

    date_s = m.group(1)
    dt = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    mixed_result = extract_blog_section(lines[1:])
    if mixed_result is not None:
        title, body_lines = mixed_result
    else:
        title, body_lines = extract_legacy_post(lines[1:])

    body_md = "\n".join(body_lines).lstrip("\n").rstrip() + "\n"
    body_md = body_md.strip()
    if not body_md:
        return None

    body_html = markdown_to_html(body_md)
    item_title = title or date_s
    link = post_link(date_s, title)
    guid = link
    pubdate = format_datetime(dt)

    return (dt, item_title, link, guid, pubdate, body_html)


def main():
    items = []
    for f in sorted(DIARY_DIR.glob("*.md")):
        parsed = parse_one_file(f)
        if parsed is not None:
            items.append(parsed)

    items.sort(reverse=True, key=lambda x: x[0])
    items = items[:MAX_ITEMS]

    last_build = format_datetime(datetime.now(timezone.utc))

    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append('<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">')
    parts.append("<channel>")
    parts.append(f"<title>{xml_escape(FEED_TITLE)}</title>")
    parts.append(f"<link>{xml_escape(BLOG_INDEX_URL)}</link>")
    parts.append(f"<description>{xml_escape(DESCRIPTION)}</description>")
    parts.append(f"<lastBuildDate>{last_build}</lastBuildDate>")
    parts.append(
        f"<atom:link href=\"{xml_escape(FEED_URL)}\" rel=\"self\" type=\"application/rss+xml\" xmlns:atom=\"http://www.w3.org/2005/Atom\"/>"
    )

    for dt, title, link, guid, pubdate, body_html in items:
        parts.append("<item>")
        parts.append(f"<title>{xml_escape(title)}</title>")
        parts.append(f"<link>{xml_escape(link)}</link>")
        parts.append(f"<guid isPermaLink=\"true\">{xml_escape(guid)}</guid>")
        parts.append(f"<pubDate>{pubdate}</pubDate>")
        parts.append(f"<description>{xml_escape(title)}</description>")
        parts.append("<content:encoded><![CDATA[")
        parts.append(body_html)
        parts.append("]]></content:encoded>")
        parts.append("</item>")

    parts.append("</channel>")
    parts.append("</rss>")

    OUT_FEED.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote RSS feed: {OUT_FEED} ({len(items)} item(s))")


if __name__ == "__main__":
    main()
