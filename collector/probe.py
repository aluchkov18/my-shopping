"""Проба: зошто едно читање на продавница на Жито пропушта дел од редовите.

    python -m collector.probe [продавница]      # резултатот оди во data/probe/zito.json

Прашања: дали редоследот на страниците е постојан, дали страницата нуди подредување или поголема
страница, и дали редовите носат некаква ознака. Околу 40 барања, со истата пауза како читањето.
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.parse import parse_qsl, urlsplit

import lxml.html

from .net import Polite
from .proverkanaceni import parse_page

BASE = "https://zito.proverkanaceni.mk/"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "probe", "zito.json")


def keys(rows: list[dict]) -> list[str]:
    return [f"{r['name']} | {r['description']} | {r['price']}" for r in rows]


def fetch(net: Polite, **params) -> tuple[str, list[str], int | None]:
    resp = net.get(BASE, params={"search": "", **params})
    resp.encoding = "utf-8"
    rows, total, _ = parse_page(resp.text)
    return resp.text, keys(rows), total


def inspect(html: str) -> dict:
    doc = lxml.html.fromstring(html)
    params, examples = set(), []
    for a in doc.xpath("//a[@href]"):
        href = a.get("href")
        found = [k for k, _ in parse_qsl(urlsplit(href).query)]
        if found and href not in examples and len(examples) < 12:
            examples.append(href[:200])
        params.update(found)
    selects = {s.get("name") or s.get("id") or "?": [(o.get("value"), (o.text_content() or "").strip()[:30]) for o in s.xpath("./option")][:12]
               for s in doc.xpath("//select")}
    heads = [{"text": (th.text_content() or "").strip()[:30], "attrs": dict(th.attrib), "inner": lxml.html.tostring(th, encoding="unicode")[:200]}
             for th in doc.xpath("//table//th")]
    first = doc.xpath("//table//tbody/tr")
    return {
        "link_params": sorted(params), "link_examples": examples, "selects": selects,
        "inputs": [dict(i.attrib) for i in doc.xpath("//input")][:12],
        "forms": [dict(f.attrib) for f in doc.xpath("//form")],
        "table_heads": heads,
        "first_row_html": lxml.html.tostring(first[0], encoding="unicode")[:900] if first else "",
        "scripts": [s.get("src") for s in doc.xpath("//script[@src]")][:10],
        "framework_hints": sorted(set(re.findall(r"wire:[a-z.]+|x-data|livewire|hx-get|data-sort[a-z-]*|sortable", html)))[:20],
    }


def main(argv: list[str]) -> int:
    org = argv[0] if argv else "9"
    net = Polite()
    out: dict = {"store": org}

    html, first, total = fetch(net, org=org, page=1, perPage=100)
    out["total"] = total
    out["page"] = inspect(html)
    again = [fetch(net, org=org, page=1, perPage=100)[1] for _ in range(2)]
    out["page1_three_reads"] = {"rows": [len(first)] + [len(a) for a in again], "same_order": [a == first for a in again],
                                "same_set": [set(a) == set(first) for a in again], "first_names": [first[:4]] + [a[:4] for a in again]}

    passes = []
    for _ in range(2):
        seen: list[str] = []
        for page in range(1, 7):
            seen += fetch(net, org=org, page=page, perPage=100)[1]
        passes.append(seen)
    out["six_pages_twice"] = {"rows": [len(p) for p in passes], "distinct": [len(set(p)) for p in passes],
                              "common_between_passes": len(set(passes[0]) & set(passes[1]))}

    tries = {}
    for label, params in {
        "perPage=200": {"perPage": 200}, "perPage=500": {"perPage": 500}, "perPage=10000": {"perPage": 10000},
        "sort=name": {"perPage": 100, "sort": "name"}, "sortBy=name": {"perPage": 100, "sortBy": "name"},
        "orderBy=name": {"perPage": 100, "orderBy": "name"}, "order=name": {"perPage": 100, "order": "name"},
        "sort=name&direction=asc": {"perPage": 100, "sort": "name", "direction": "asc"},
        "sort_by=name&sort_dir=asc": {"perPage": 100, "sort_by": "name", "sort_dir": "asc"},
    }.items():
        _, got, _ = fetch(net, org=org, page=1, **params)
        names = [k.split(" | ")[0] for k in got]
        tries[label] = {"rows": len(got), "sorted_by_name": names == sorted(names), "same_as_plain": got == first, "first": names[:3]}
    out["tries"] = tries
    names = [k.split(" | ")[0] for k in first]
    out["plain_sorted_by_name"] = names == sorted(names)
    out["requests"] = net.count

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "page"}, ensure_ascii=False)[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
