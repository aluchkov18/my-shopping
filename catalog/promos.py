"""Акции од сите синџири, со проверка дали акцијата навистина е добра.

    python -m catalog.promos            # преглед + catalog/promos.csv

За секој производ на акција: редовна и акциска цена, попуст, до кога важи и дали бара картичка.
Две проверки што синџирот не ги кажува:
  - дали акциската цена по единица е најниска во градот за таа потреба (најевтино млеко, не само поевтино)
  - колку чини истиот производ кај другите синџири, ако го имаат
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys
from collections import Counter

from .match import CHAINS, LABEL, ROOT
from .needs import NEEDS
from .same import collect, run

CARD = re.compile(r"клуб|лојалност", re.I)
_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


def raw() -> dict[str, dict[tuple, dict]]:
    out = {}
    for chain in CHAINS:
        best: dict[tuple, dict] = {}
        for path in glob.glob(os.path.join(ROOT, "data", "current", chain, "*.csv")):
            with open(path, encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    key = (r["name"], r["description"])
                    if float(r["price"] or 0) > 0 and (key not in best or float(r["price"]) < float(best[key]["price"])):
                        best[key] = r
        out[chain] = best
    return out


def build() -> list[dict]:
    return judge(raw(), collect(), run()[0])


def judge(rows_by_chain: dict, data: dict, groups: list) -> list[dict]:
    """Акциите од ценовниците (rows_by_chain), споредени со каталогот (data) и со истите производи кај другите (groups)."""
    names = {n.id: n for n in NEEDS}
    index, floor = {}, {}
    for need_id, per in data.items():
        for chain, hits in per.items():
            for h in hits:
                index[(chain, h["name"], h["description"])] = (need_id, h)
            ok = [h["unit_price"] for h in hits if h["unit_price"] and h["trust"] >= 2 and not h.get("outlier")]
            floor[(need_id, chain)] = min(ok) if ok else None
    twins = {}
    for group in groups:
        for h in group:
            twins[(h["chain"], h["name"], h["description"])] = [(o["chain"], o["price"]) for o in group if o is not h]

    out = []
    for chain, rows in rows_by_chain.items():
        for (name, description), r in rows.items():
            price, regular = float(r["price"]), float(r["regular_price"] or 0)
            if not (regular > price > 0):
                continue
            pct = round(100 * (1 - price / regular))
            if not 5 <= pct <= 80:
                continue
            dates = _DATE.findall(r["promo_period"])
            until = "-".join(reversed(dates[-1])) if dates else ""
            need_id, hit = index.get((chain, name, description), (None, None))
            item = {"chain": chain, "name": name, "description": description, "price": price, "regular": regular, "pct": pct, "until": until,
                    "card": bool(CARD.search(r["promo_type"])), "need": need_id or "", "group": names[need_id].group if need_id else "Друго",
                    "unit_price": None, "cheapest": False, "elsewhere": None}
            if hit and hit["unit_price"] and hit["trust"] >= 2 and not hit.get("outlier"):
                item["unit_price"] = hit["unit_price"]
                others = [floor[(need_id, c)] for c in CHAINS if c != chain and floor.get((need_id, c))]
                own = [h["unit_price"] for h in data[need_id][chain] if h is not hit and h["unit_price"] and h["trust"] >= 2 and not h.get("outlier")]
                item["cheapest"] = bool(others) and hit["unit_price"] <= min(others) and (not own or hit["unit_price"] <= min(own))
            if (chain, name, description) in twins:
                item["elsewhere"] = min(twins[(chain, name, description)], key=lambda t: t[1])      # (синџир, цена) на истиот производ
            out.append(item)
    return sorted(out, key=lambda p: (-p["cheapest"], -p["pct"], p["name"]))


def main(argv: list[str]) -> int:
    items = build()
    print(f"акции: {len(items)} | по синџир: {dict(Counter(LABEL[p['chain']] for p in items))}")
    print(f"со картичка: {sum(p['card'] for p in items)} | во потреба: {sum(bool(p['need']) for p in items)} | "
          f"најевтини во градот за потребата: {sum(p['cheapest'] for p in items)}")
    known = [p for p in items if p["elsewhere"]]
    worse = [p for p in known if p["elsewhere"][1] < p["price"]]
    print(f"ист производ кај друг синџир: {len(known)} | од нив другаде поевтино и покрај акцијата: {len(worse)}")
    for p in items[:12]:
        print(f"  {LABEL[p['chain']][:1]} -{p['pct']:>2}%  {p['regular']:>5g} -> {p['price']:>5g}  {p['name'][:46]}")
    with open(os.path.join(ROOT, "catalog", "promos.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["chain", "name", "regular", "price", "pct", "until", "card", "need", "unit_price", "cheapest_for_need",
                    "same_product_chain", "same_product_price"])
        for p in items:
            w.writerow([p["chain"], p["name"], f"{p['regular']:g}", f"{p['price']:g}", p["pct"], p["until"], int(p["card"]), p["need"],
                        "" if p["unit_price"] is None else f"{p['unit_price']:g}", int(p["cheapest"]),
                        p["elsewhere"][0] if p["elsewhere"] else "", f"{p['elsewhere'][1]:g}" if p["elsewhere"] else ""])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
