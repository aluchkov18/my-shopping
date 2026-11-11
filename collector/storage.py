"""Запис на диск: тековни цени по продавница (текстуален CSV) и дневен список на промени.

Тековната датотека се презапишува секој ден; историјата ја чува git, а промените
дополнително се испишуваат во data/changes/<датум>.csv за лесно читање.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

from .common import FIELDS

CHANGE_FIELDS = [
    "chain", "store_id", "kind", "name", "description",
    "old_price", "new_price", "old_regular", "new_regular",
    "old_discount", "new_discount", "old_promo", "new_promo", "variants",
]


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def to_text_rows(rows: list[dict]) -> list[dict]:
    """Сè во текст и во постојан редослед, за git да гледа само вистински промени."""
    out = [{f: fmt(r.get(f)) for f in FIELDS} for r in rows]
    out.sort(key=lambda r: (r["name"], r["description"], float(r["price"] or 0), r["promo_type"]))
    return out


def count_duplicates(text_rows: list[dict]) -> int:
    seen, dups = set(), 0
    for r in text_rows:
        key = tuple(r[f] for f in FIELDS)
        dups += key in seen
        seen.add(key)
    return dups


def read_csv(path: str) -> list[dict] | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: str, rows: list[dict], fields: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def diff(old: list[dict], new: list[dict]) -> list[dict]:
    """Што е ново, што исчезнало и каде се сменила цена или акција."""
    def group(rows):
        by_key = defaultdict(list)
        for r in rows:
            by_key[(r["name"], r["description"])].append(
                (r["price"], r["regular_price"], r["discount_price"], r["promo_type"]))
        return {k: sorted(v, key=lambda s: (float(s[0] or 0), s)) for k, v in by_key.items()}

    before, after = group(old), group(new)
    changes = []
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key), after.get(key)
        if a == b:
            continue
        kind = "new" if a is None else "removed" if b is None else "changed"
        x, y = (a or [("", "", "", "")])[0], (b or [("", "", "", "")])[0]
        changes.append({
            "kind": kind, "name": key[0], "description": key[1],
            "old_price": x[0], "new_price": y[0], "old_regular": x[1], "new_regular": y[1],
            "old_discount": x[2], "new_discount": y[2], "old_promo": x[3], "new_promo": y[3],
            "variants": max(len(a or []), len(b or [])),
        })
    return changes
