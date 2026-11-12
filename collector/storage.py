"""Запис на диск: тековни цени по продавница (текстуален CSV) и дневен список на промени.

Тековната датотека се презапишува секој ден; историјата ја чува git, а промените
дополнително се испишуваат во data/changes/<датум>.csv за лесно читање.
"""
from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from datetime import date, timedelta

from .common import FIELDS

CHANGE_FIELDS = [
    "chain", "store_id", "kind", "name", "description",
    "old_price", "new_price", "old_regular", "new_regular",
    "old_discount", "new_discount", "old_promo", "new_promo", "variants",
]


SAVED = FIELDS + ["seen"]        # колони во датотека со паметење: и денот кога редот е последен пат прочитан
_DAY = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


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


def promo_end(period: str) -> date | None:
    """Последниот датум во „11.11.2026 до 24.11.2026"."""
    found = _DAY.findall(period or "")
    try:
        return date(int(found[-1][2]), int(found[-1][1]), int(found[-1][0])) if found else None
    except ValueError:
        return None


def carry(previous: list[dict] | None, rows: list[dict], today: date, days: int) -> list[dict]:
    """Денешните редови плус оние што денес ги нема, а биле прочитани во последните `days` дена.

    Кај Жито едно читање пропушта околу четвртина од редовите: страниците немаат постојан редослед,
    па дел од редовите се повторуваат, а дел се прескокнуваат (проба во data/probe/zito.json).
    Затоа ред што денес го нема не се брише веднаш. Пренесен ред со истечена акција се враќа на редовна цена.
    """
    stamp, out, taken = today.isoformat(), [], set()
    for r in rows:                                   # исти редови повторени во едно читање се запишуваат еднаш
        full = tuple(r[f] for f in FIELDS)
        if full not in taken:
            taken.add(full)
            out.append({**r, "seen": stamp})
    have = {(r["name"], r["description"]) for r in rows}
    yesterday = (today - timedelta(days=1)).isoformat()
    for r in previous or []:
        if (r["name"], r["description"]) in have:
            continue
        seen = r.get("seen") or yesterday            # датотека од пред паметењето: прочитана е вчера
        if (today - date.fromisoformat(seen)).days > days:
            continue
        old = {f: r.get(f, "") for f in FIELDS}
        ended = promo_end(old["promo_period"])
        if old["discount_price"] and ended and ended < today:
            if not old["regular_price"]:
                continue
            old.update(price=old["regular_price"], discount_price="", discount_pct="", promo_type="", promo_period="")
        full = tuple(old[f] for f in FIELDS)
        if full not in taken:
            taken.add(full)
            out.append({**old, "seen": seen})
    out.sort(key=lambda r: (r["name"], r["description"], float(r["price"] or 0), r["promo_type"]))
    return out


def diff(old: list[dict], new: list[dict]) -> list[dict]:
    """Што е ново, што исчезнало и каде се сменила цена или акција."""
    def group(rows):
        by_key = defaultdict(list)
        for r in rows:
            by_key[(r["name"], r["description"])].append(
                (r["price"], r["regular_price"], r["discount_price"], r["promo_type"]))
        # Различни варијанти, без повторувања: Жито го повторува истиот ред, секој ден различен број пати.
        return {k: sorted(set(v), key=lambda s: (float(s[0] or 0), s)) for k, v in by_key.items()}

    before, after = group(old), group(new)
    changes = []
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key), after.get(key)
        if a == b:
            continue
        kind = "new" if a is None else "removed" if b is None else "changed"
        only_old, only_new = [v for v in a or [] if v not in (b or [])], [v for v in b or [] if v not in (a or [])]
        x = (only_old or a or [("", "", "", "")])[0]          # варијантата што се смени, не само најевтината
        y = (only_new or b or [("", "", "", "")])[0]
        changes.append({
            "kind": kind, "name": key[0], "description": key[1],
            "old_price": x[0], "new_price": y[0], "old_regular": x[1], "new_regular": y[1],
            "old_discount": x[2], "new_discount": y[2], "old_promo": x[3], "new_promo": y[3],
            "variants": max(len(a or []), len(b or [])),
        })
    return changes
