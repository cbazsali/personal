#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
from datetime import datetime

DIARY_DIR = Path.home() / "wiki" / "diary"
BLOG_HTML = Path.home() / "sites" / "personal" / "blog.html"

START_MARK = "<!-- Blog entries start here -->"
END_MARK   = "<!-- Blog entries end here -->"

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
TITLE_RE = re.compile(r"^\s*##\s+(.+?)\s*$")

def has_pandoc() -> bool:
    try:
        subprocess.run(["pandoc", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def escape_html(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))

def markdown_to_html(md: str, use_pandoc: bool) -> str:
    md = md.rstrip() + "\n"
    if use_pandoc:
        p = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html"],
            input=md.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return p.stdout.decode("utf-8").rstrip()

    # Minimal fallback: paragraph breaks on blank lines; preserve line breaks inside paragraphs.
    paras = [p.strip() for p in md.split("\n\n") if p.strip()]
    out = []
    for para in paras:
        out.append("<p>" + escape_html(para).replace("\n", "<br>\n") + "</p>")
    return "\n".join(out)

def extract_title_and_body(lines_after_header):
    """
    Look for the first '## ' header in the body and treat it as the post title.
    Remove that title line from the body so it doesn't render twice.
    Returns (title_or_none, remaining_lines).
    """
    title = None
    remaining = []
    for line in lines_after_header:
        if title is None:
            m = TITLE_RE.match(line)
            if m:
                title = m.group(1)
                continue
        remaining.append(line)
    return title, remaining

def parse_blog_posts():
    posts = []
    for f in sorted(DIARY_DIR.glob("*.md")):
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        if not lines:
            continue

        first = lines[0].strip()
        if "#blog" not in first:
            continue

        m = DATE_RE.search(first)
        if not m:
            continue

        date_s = m.group(1)
        datetime.strptime(date_s, "%Y-%m-%d")  # validate

        title, body_lines = extract_title_and_body(lines[1:])
        body_md = "\n".join(body_lines).lstrip("\n")
        posts.append((date_s, title, body_md))

    posts.sort(reverse=True, key=lambda x: x[0])  # newest first
    return posts

def build_entries_html(posts, use_pandoc: bool) -> str:
    chunks = []
    for date_s, title, body_md in posts:
        body_html = markdown_to_html(body_md, use_pandoc)
        title_html = f'\n  <h2 class="blog-title">{escape_html(title)}</h2>' if title else ''
        chunks.append(
            f'''<article class="blog-entry" id="{date_s}">
<h1 class="blog-date">{date_s}</h1>{title_html}
<div class="blog-body">
{body_html}
</div>
</article>'''
        )
    return "\n\n".join(chunks)

def replace_between_markers(full_text: str, new_middle: str) -> str:
    if START_MARK not in full_text or END_MARK not in full_text:
        raise RuntimeError("Could not find start/end markers in blog.html")

    before, rest = full_text.split(START_MARK, 1)
    middle, after = rest.split(END_MARK, 1)

    # Replace only the middle section; keep markers intact
    new_section = (
        START_MARK
        + "\n\n"
        + (new_middle.strip() + "\n\n" if new_middle.strip() else "")
        + END_MARK
    )

    return before + new_section + after

def main():
    if not BLOG_HTML.exists():
        raise SystemExit(f"Missing: {BLOG_HTML}")

    use_pandoc = has_pandoc()
    posts = parse_blog_posts()
    entries_html = build_entries_html(posts, use_pandoc)

    original = BLOG_HTML.read_text(encoding="utf-8")
    updated = replace_between_markers(original, entries_html)
    BLOG_HTML.write_text(updated, encoding="utf-8")

    print(f"Wrote {len(posts)} entr{'y' if len(posts)==1 else 'ies'} into {BLOG_HTML}")
    print("Renderer:", "pandoc" if use_pandoc else "minimal fallback (no pandoc found)")

if __name__ == "__main__":
    main()

