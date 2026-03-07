#!/usr/bin/env python3
from pathlib import Path
import html
import re
import shutil
import subprocess
from datetime import datetime
from urllib.parse import quote

DIARY_DIR = Path.home() / "wiki" / "diary"
SITE_DIR = Path.home() / "sites" / "personal"
BLOG_INDEX = SITE_DIR / "blog.html"
BLOG_DIR = SITE_DIR / "blog"

START_MARK = "<!-- Blog entries start here -->"
END_MARK = "<!-- Blog entries end here -->"
MAIN_OPEN_RE = re.compile(r"(<main[^>]*>)", re.IGNORECASE)
MAIN_CLOSE_RE = re.compile(r"(</main>)", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
TITLE_RE = re.compile(r"^\s*##\s+(.+?)\s*$")
HREF_SRC_RE = re.compile(r'(?P<attr>\b(?:href|src)=")(?P<url>[^"]+)(")')

# Fill these in once you have created/configured Giscus.
# Leave them blank for now if you want to generate the new structure first.
GISCUS_REPO = "cbazsali/personal"
GISCUS_REPO_ID = "R_kgDORFs_hQ"
GISCUS_CATEGORY = "Announcements"
GISCUS_CATEGORY_ID = "DIC_kwDORFs_hc4C35RQ"
GISCUS_MAPPING = "pathname"
GISCUS_THEME = "preferred_color_scheme"
GISCUS_REACTIONS_ENABLED = "1"
GISCUS_EMIT_METADATA = "0"
GISCUS_INPUT_POSITION = "bottom"
GISCUS_LANG = "en"
GISCUS_LOADING = "lazy"


def has_pandoc() -> bool:
    try:
        subprocess.run(["pandoc", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def escape_html(s: str) -> str:
    return html.escape(s, quote=True)


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

    paras = [p.strip() for p in md.split("\n\n") if p.strip()]
    out = []
    for para in paras:
        out.append("<p>" + escape_html(para).replace("\n", "<br>\n") + "</p>")
    return "\n".join(out)


def strip_html_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def extract_title_and_body(lines_after_header):
    title = None
    remaining = []
    for line in lines_after_header:
        if title is None:
            m = TITLE_RE.match(line)
            if m:
                title = m.group(1).strip()
                continue
        remaining.append(line)
    return title, remaining


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[’']", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "post"


def post_filename(date_s: str, title: str | None) -> str:
    if title:
        return f"{date_s}-{slugify(title)}.html"
    return f"{date_s}.html"


def post_url(date_s: str, title: str | None) -> str:
    return f"blog/{quote(post_filename(date_s, title))}"


def first_nonempty_paragraph_text(body_html: str) -> str:
    paragraphs = re.findall(r"<p>(.*?)</p>", body_html, flags=re.IGNORECASE | re.DOTALL)
    for p in paragraphs:
        text = re.sub(r"\s+", " ", strip_html_tags(p)).strip()
        if text:
            return text
    text = re.sub(r"\s+", " ", strip_html_tags(body_html)).strip()
    return text


def parse_blog_posts(use_pandoc: bool):
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
        datetime.strptime(date_s, "%Y-%m-%d")

        title, body_lines = extract_title_and_body(lines[1:])
        body_md = "\n".join(body_lines).lstrip("\n")
        body_html = markdown_to_html(body_md, use_pandoc)
        excerpt = first_nonempty_paragraph_text(body_html)
        url = post_url(date_s, title)
        posts.append(
            {
                "date": date_s,
                "title": title,
                "display_title": f"{date_s} {title}" if title else date_s,
                "body_md": body_md,
                "body_html": body_html,
                "excerpt": excerpt,
                "filename": post_filename(date_s, title),
                "url": url,
            }
        )

    posts.sort(reverse=True, key=lambda x: x["date"])
    return posts


def replace_between_markers(full_text: str, new_middle: str) -> str:
    if START_MARK not in full_text or END_MARK not in full_text:
        raise RuntimeError("Could not find start/end markers in blog.html")

    before, rest = full_text.split(START_MARK, 1)
    _middle, after = rest.split(END_MARK, 1)
    new_section = (
        START_MARK
        + "\n\n"
        + (new_middle.strip() + "\n\n" if new_middle.strip() else "")
        + END_MARK
    )
    return before + new_section + after


def update_index_html(posts) -> None:
    original = BLOG_INDEX.read_text(encoding="utf-8")
    if posts:
        chunks = []
        for post in posts:
            title_html = (
                f'<h2 class="blog-title"><a href="{escape_html(post["url"])}">{escape_html(post["display_title"])}</a></h2>'
            )
            excerpt_html = ""
            if post["excerpt"]:
                excerpt_html = f'\n<p>{escape_html(post["excerpt"])} <a href="{escape_html(post["url"])}">Read post →</a></p>'
            chunks.append(
                f'''<article class="blog-entry">
{title_html}{excerpt_html}
</article>'''
            )
        index_entries_html = "\n\n".join(chunks)
    else:
        index_entries_html = '<p>No blog posts yet.</p>'

    updated = replace_between_markers(original, index_entries_html)
    BLOG_INDEX.write_text(updated, encoding="utf-8")


def adjust_relative_urls(fragment: str, levels_up: int) -> str:
    prefix = "../" * levels_up

    def repl(m: re.Match[str]) -> str:
        url = m.group("url")
        if (
            url.startswith(("http://", "https://", "mailto:", "tel:", "#", "/", "data:"))
            or url.startswith("../")
        ):
            return m.group(0)
        return f'{m.group("attr")}{prefix}{url}"'

    return HREF_SRC_RE.sub(repl, fragment)


def extract_shell(template_html: str):
    m_open = MAIN_OPEN_RE.search(template_html)
    m_close = MAIN_CLOSE_RE.search(template_html)
    if not m_open or not m_close or m_close.start() <= m_open.end():
        raise RuntimeError("Could not locate <main>...</main> in blog.html template")

    shell_before_main = template_html[: m_open.end()]
    shell_after_main = template_html[m_close.start() :]
    return shell_before_main, shell_after_main


def title_tag(display_title: str) -> str:
    return f"{display_title} – Colin Bazsali"


def set_page_title(html_text: str, new_title: str) -> str:
    return re.sub(r"<title>.*?</title>", f"<title>{escape_html(new_title)}</title>", html_text, count=1, flags=re.IGNORECASE | re.DOTALL)


def giscus_block() -> str:
    if not all([GISCUS_REPO, GISCUS_REPO_ID, GISCUS_CATEGORY, GISCUS_CATEGORY_ID]):
        return (
            '<section class="comments">\n'
            '  <h2>Comments</h2>\n'
            '  <p>Comments will appear here after Giscus is configured in <code>blog_build.py</code>.</p>\n'
            '</section>'
        )

    return f'''<section class="comments">
  <h2>Comments</h2>
  <script src="https://giscus.app/client.js"
          data-repo="{escape_html(GISCUS_REPO)}"
          data-repo-id="{escape_html(GISCUS_REPO_ID)}"
          data-category="{escape_html(GISCUS_CATEGORY)}"
          data-category-id="{escape_html(GISCUS_CATEGORY_ID)}"
          data-mapping="{escape_html(GISCUS_MAPPING)}"
          data-reactions-enabled="{escape_html(GISCUS_REACTIONS_ENABLED)}"
          data-emit-metadata="{escape_html(GISCUS_EMIT_METADATA)}"
          data-input-position="{escape_html(GISCUS_INPUT_POSITION)}"
          data-theme="{escape_html(GISCUS_THEME)}"
          data-lang="{escape_html(GISCUS_LANG)}"
          crossorigin="anonymous"
          async>
  </script>
</section>'''


def build_post_page(post, shell_before_main: str, shell_after_main: str) -> str:
    before = set_page_title(shell_before_main, title_tag(post["display_title"]))
    before = adjust_relative_urls(before, levels_up=1)
    after = adjust_relative_urls(shell_after_main, levels_up=1)

    content = f'''\n\t\t\t<h1>Blog</h1>
\t\t\t<article class="blog-entry">
\t\t\t\t<h2>{escape_html(post["display_title"])}</h2>
\t\t\t\t<div class="blog-body">
{post["body_html"]}
\t\t\t\t</div>
\t\t\t</article>
\t\t\t<p><a href="../blog.html">← Back to blog</a></p>
\t\t\t{giscus_block()}\n\t\t'''
    return before + content + after


def write_post_pages(posts) -> None:
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    for old_html in BLOG_DIR.glob("*.html"):
        old_html.unlink()

    template_html = BLOG_INDEX.read_text(encoding="utf-8")
    shell_before_main, shell_after_main = extract_shell(template_html)

    for post in posts:
        post_path = BLOG_DIR / post["filename"]
        post_html = build_post_page(post, shell_before_main, shell_after_main)
        post_path.write_text(post_html, encoding="utf-8")


def main():
    if not BLOG_INDEX.exists():
        raise SystemExit(f"Missing: {BLOG_INDEX}")

    use_pandoc = has_pandoc()
    posts = parse_blog_posts(use_pandoc)
    update_index_html(posts)
    write_post_pages(posts)

    print(f"Wrote blog index: {BLOG_INDEX}")
    print(f"Wrote {len(posts)} post page(s) into {BLOG_DIR}")
    print("Renderer:", "pandoc" if use_pandoc else "minimal fallback (no pandoc found)")


if __name__ == "__main__":
    main()
