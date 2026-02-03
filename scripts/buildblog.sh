#!/usr/bin/env bash
set -euo pipefail

~/sites/personal/scripts/blog_build.py
~/sites/personal/scripts/rss_build.py
echo "OK: blog + RSS rebuilt"

