"""Податоци за прототипот како еден JSON: сите потреби со цените, јадењата и акциите.

    python -m planner.export_app <излез.json> [датум]

Понуда: [име, цена, цена по единица, големина на пакување или null за на мерење, 1 ако е на акција].
Акција: [синџир, име, цена, редовна, попуст %, важи до, со картичка, потреба, најевтино во градот,
         синџир со истиот производ или -1, цената таму].
"""
from __future__ import annotations

import json
import sys

from catalog.match import CHAINS, LABEL
from catalog.needs import NEEDS
from catalog.promos import build as promos
from catalog.same import collect

from .menu import PERISHABLE
from .recipes import DISHES, POSNO

NAME = 48      # знаци од името што ги гледа корисникот


def offers(hits: list[dict]) -> list[list]:
    rows = []
    for h in hits:
        if not h["unit_price"] or h.get("outlier") or (h["trust"] < 2 and h["qty"] != "на мерење"):
            continue
        by_weight = h["qty"] == "на мерење" or h["qty"] is None
        size = None if by_weight else round(h["price"] / h["unit_price"], 3)
        rows.append([h["name"][:NAME], h["price"], h["unit_price"], size, int(bool(h["promo"]))])
    return sorted(rows, key=lambda r: r[2])


def build(day: str) -> dict:
    data = collect()
    needs = {n.id: {"name": n.name, "unit": n.unit, "group": n.group, "keeps": n.group not in PERISHABLE,
                    "offers": {c: offers(data[n.id][c]) for c in CHAINS}} for n in NEEDS}
    dishes = {name: {"kind": kind, "posno": name in POSNO, "parts": parts} for name, (kind, parts) in DISHES.items()}
    deals = [[CHAINS.index(p["chain"]), p["name"][:NAME], p["price"], p["regular"], p["pct"], p["until"], int(p["card"]), p["need"],
              int(p["cheapest"]), CHAINS.index(p["elsewhere"][0]) if p["elsewhere"] else -1, p["elsewhere"][1] if p["elsewhere"] else 0]
             for p in promos()]
    return {"day": day, "city": "Велес", "chains": [[c, LABEL[c]] for c in CHAINS], "groups": list(dict.fromkeys(n.group for n in NEEDS)),
            "needs": needs, "dishes": dishes, "promos": deals}


if __name__ == "__main__":
    out = build(sys.argv[2] if len(sys.argv) > 2 else "")
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print(len(out["needs"]), "потреби,", len(out["dishes"]), "јадења,", len(out["promos"]), "акции,",
          sum(len(v) for n in out["needs"].values() for v in n["offers"].values()), "производи")
