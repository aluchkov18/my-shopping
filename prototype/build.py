"""Го составува прототипот: шаблонот app.html со вметнати податоци од ценовниците.

    python prototype/build.py <излез.html> [датум]     # дел од страница, за објавување како артефакт
    python prototype/build.py --site <папка> [датум]   # цела страница за GitHub Pages: index.html, икони, работа без мрежа

Без датум се зема денот на последното читање од data/runs.
"""
import glob
import json
import os
import re
import shutil
import sys

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
sys.path.insert(0, root)
from planner.export_app import build  # noqa: E402

HEAD = """<!doctype html>
<html lang="mk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="theme-color" content="#FEFCF8">
<meta name="color-scheme" content="light">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="icon-192.png">
<style>html { -webkit-text-size-adjust: 100%; } body { margin: 0; }</style>
"""
FONTS = re.compile(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]*">')
TAIL = """<script>if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});</script>
</body>
</html>
"""


def last_day() -> str:
    runs = sorted(glob.glob(os.path.join(root, "data", "runs", "*.json")))
    return ".".join(reversed(os.path.basename(runs[-1])[:-5].split("-"))) if runs else ""


def fragment(day: str) -> str:
    with open(os.path.join(here, "app.html"), encoding="utf-8") as fh:
        page = fh.read()
    data = json.dumps(build(day), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    assert page.count("/*DATA*/") == 1
    return page.replace("/*DATA*/", data)


def site(folder: str, day: str) -> str:
    os.makedirs(folder, exist_ok=True)
    head, body = fragment(day).split("</style>", 1)          # наслов, фонтови и стилови одат во главата
    head, swapped = FONTS.subn('<link rel="stylesheet" href="fonts.css">', head)      # фонтовите се во папката, па страницата изгледа исто и без мрежа
    assert swapped == 1
    path = os.path.join(folder, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HEAD + head + "</style>\n</head>\n<body>" + body + TAIL)
    shutil.copytree(os.path.join(here, "site"), folder, dirs_exist_ok=True)
    return path


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--site"]:
        out = site(args[1], args[2] if len(args) > 2 else last_day())
    else:
        out = args[0]
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(fragment(args[1] if len(args) > 1 else last_day()))
    print(out, os.path.getsize(out), "бајти")
