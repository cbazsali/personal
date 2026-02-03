#!/usr/bin/env python3
from pathlib import Path
import re

DIARY_DIR = Path.home() / "wiki" / "diary"
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

def main():
    files = sorted(DIARY_DIR.glob("*.md"))
    if not files:
        print(f"No .md files found in {DIARY_DIR}")
        return

    hits = []
    for f in files:
        try:
            first = f.open("r", encoding="utf-8").readline().strip()
        except Exception as e:
            print(f"Could not read {f}: {e}")
            continue

        if "#blog" not in first:
            continue

        m = DATE_RE.search(first)
        if not m:
            print(f"Skipping (no YYYY-MM-DD found on line 1): {f.name} :: {first}")
            continue

        hits.append((m.group(1), f.name, first))

    hits.sort(reverse=True, key=lambda x: x[0])

    print("Blog candidates (newest first):")
    if not hits:
        print("  (none found)")
        return

    for date_s, fname, first in hits:
        print(f"  {date_s}  {fname}  ::  {first}")

if __name__ == "__main__":
    main()

