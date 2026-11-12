"""Го составува прототипот: шаблонот app.html со вметнати податоци од ценовниците.

    python prototype/build.py <излез.html> [датум]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from planner.export_app import build  # noqa: E402

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "app.html"), encoding="utf-8") as fh:
    page = fh.read()
data = json.dumps(build(sys.argv[2] if len(sys.argv) > 2 else ""), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
assert page.count("/*DATA*/") == 1
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    fh.write(page.replace("/*DATA*/", data))
print(os.path.getsize(sys.argv[1]), "бајти")
