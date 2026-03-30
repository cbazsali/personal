#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import quote
from typing import Optional

DIARY_DIR = Path.home() / "wiki" / "diary"
OUT_FEED  = Path.home() / "sites" / "personal" / "feed.xml"

SITE_TITLE = "Colin Bazsali"
FEED_TITLE = "Colin Bazsali – Blog"
SITE_URL   = "https://colinbazsali.com/"
BLOG_INDEX_URL = "https://colinbazsali.com/blog.html"
FEED_URL   = "https://colinbazsali.com/feed.xml"
DESCRIPTION = "Updates from Colin Bazsali."

MAX_ITEMS = 50
DATE_RE  = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
TITLE_RE = re.compile(r"^\s*##\s+(.+?)\s*$")


def extract_title_and_body(lines):
    title = None
    body = []
    for line in lines:
        if title is None:
            m = TITLE_RE.match(line)
            if m:
                title = m.group(1).strip()
                continue
        body.append(line)
    return title, body


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
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


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


def main():
    items = []
    for f in sorted(DIARY_DIR.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        if not lines:
            continue

        first = lines[0].strip()
        if "#blog" not in first:
            continue

        m = DATE_RE.search(first)
        if not m:
            continue

        date_s = m.group(1)
        dt = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        title, body_lines = extract_title_and_body(lines[1:])
        item_title = title or date_s
        body_md = "\n".join(body_lines).lstrip("\n")
        body_html = markdown_to_html(body_md)

        link = post_link(date_s, title)
        guid = link
        pubdate = format_datetime(dt)

        items.append((dt, item_title, link, guid, pubdate, body_html))

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
    parts.append(f"<atom:link href=\"{xml_escape(FEED_URL)}\" rel=\"self\" type=\"application/rss+xml\" xmlns:atom=\"http://www.w3.org/2005/Atom\"/>")

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
