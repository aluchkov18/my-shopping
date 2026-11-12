"""Податоци за прототипот како еден JSON: сите потреби со цените, јадењата и акциите.

    python -m planner.export_app <излез.json> [датум]

Понуда: [име, цена, цена по единица, големина на пакување или null за на мерење, 0 без акција / 1 акција / 2 акција со картичка];
         на акција следуваат уште редовна цена (или null) и рок „од/до" како ГГГГ-ММ-ДД/ГГГГ-ММ-ДД.
Акција: [синџир, име, цена, редовна, попуст %, важи до, со картичка, потреба, најевтино во градот,
         синџир со истиот производ или -1, цената таму, важи од].
Ист производ: [име, потреба, цена кај секој синџир или null, акции како [синџир, „од/до"]].
Промена: [потреба, стара најниска цена по единица, нова, синџир] меѓу последните две дневни слики.
"""
from __future__ import annotations

import json
import sys

from catalog.history import latest
from catalog.match import CHAINS, LABEL
from catalog.needs import NEEDS
from catalog.promos import build as promos
from catalog.promos import span
from catalog.same import collect, run

from .menu import PERISHABLE
from .recipes import DISHES, POSNO

NAME = 48      # знаци од името што ги гледа корисникот


def offers(hits: list[dict], deals: dict) -> list[list]:
    rows = []
    for h in hits:
        if not h["unit_price"] or h.get("outlier") or (h["trust"] < 2 and h["qty"] != "на мерење"):
            continue
        by_weight = h["qty"] == "на мерење" or h["qty"] is None
        size = None if by_weight else round(h["price"] / h["unit_price"], 3)
        row = [h["name"][:NAME], h["price"], h["unit_price"], size, int(bool(h["promo"]))]
        deal = deals.get((h["chain"], h["name"], h["description"]))
        if deal:                          # редовната цена кажува колку штеди акцијата и колку чини производот без картичка
            row[4] = 2 if deal[1] else 1
        if row[4]:
            row += [deal[0] if deal else None, "/".join(span(h.get("period", "")))]
        rows.append(row)
    return sorted(rows, key=lambda r: r[2])


def build(day: str) -> dict:
    data, found = collect(), promos()
    deals = {(p["chain"], p["name"], p["description"]): (p["regular"], p["card"]) for p in found}
    needs = {n.id: {"name": n.name, "unit": n.unit, "group": n.group, "keeps": n.group not in PERISHABLE,
                    "offers": {c: offers(data[n.id][c], deals) for c in CHAINS}} for n in NEEDS}
    dishes = {name: {"kind": kind, "posno": name in POSNO, "parts": parts} for name, (kind, parts) in DISHES.items()}
    deals = [[CHAINS.index(p["chain"]), p["name"][:NAME], p["price"], p["regular"], p["pct"], p["until"], int(p["card"]), p["need"],
              int(p["cheapest"]), CHAINS.index(p["elsewhere"][0]) if p["elsewhere"] else -1, p["elsewhere"][1] if p["elsewhere"] else 0, p["since"]]
             for p in found]
    same = []
    for group in run()[0]:
        price = {h["chain"]: h["price"] for h in group}
        if max(price.values()) > min(price.values()):
            name = next(h["name"] for c in CHAINS for h in group if h["chain"] == c)
            same.append([name[:NAME], group[0]["need"]] + [price.get(c) for c in CHAINS]
                        + [[[CHAINS.index(h["chain"]), "/".join(span(h.get("period", "")))] for h in group if h["promo"]]])
    since, moved = latest()
    return {"since": ".".join(reversed(since.split("-"))) if since else "",
            "changes": [[c["need"], c["old"], c["new"], CHAINS.index(c["chain"])] for c in moved if c["need"] in needs and c["sure"]],
            "same": sorted(same, key=lambda r: -(max(v for v in r[2:6] if v) - min(v for v in r[2:6] if v))),
            "day": day, "city": "Велес", "chains": [[c, LABEL[c]] for c in CHAINS], "groups": list(dict.fromkeys(n.group for n in NEEDS)),
            "needs": needs, "dishes": dishes, "promos": deals}


if __name__ == "__main__":
    out = build(sys.argv[2] if len(sys.argv) > 2 else "")
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print(len(out["needs"]), "потреби,", len(out["dishes"]), "јадења,", len(out["promos"]), "акции,",
          sum(len(v) for n in out["needs"].values() for v in n["offers"].values()), "производи")
