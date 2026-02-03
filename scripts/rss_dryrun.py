#!/usr/bin/env python3
from pathlib import Path
import re
from datetime import datetime
import subprocess

DIARY_DIR = Path.home() / "wiki" / "diary"
BLOG_URL  = "https://colinbazsali.com/blog.html"

DATE_RE  = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
TITLE_RE = re.compile(r"^\s*##\s+(.+?)\s*$")

def extract_title_and_body(lines):
    title = None
    body = []
    for line in lines:
        if title is None:
            m = TITLE_RE.match(line)
            if m:
                title = m.group(1)
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

def main():
    hits = []

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
        datetime.strptime(date_s, "%Y-%m-%d")

        title, body_lines = extract_title_and_body(lines[1:])
        title = title or date_s

        body_md = "\n".join(body_lines).lstrip("\n")
        body_html = markdown_to_html(body_md)

        link = f"{BLOG_URL}#{date_s}"
        hits.append((date_s, title, link, body_html))

    hits.sort(reverse=True, key=lambda x: x[0])

    if not hits:
        print("No RSS entries found.")
        return

    for date_s, title, link, html in hits:
        print("=" * 72)
        print(f"DATE : {date_s}")
        print(f"TITLE: {title}")
        print(f"LINK : {link}")
        print("-" * 72)
        print(html.strip())
        print()

if __name__ == "__main__":
    main()

