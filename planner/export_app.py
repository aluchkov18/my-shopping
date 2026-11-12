"""Податоци за прототипот: јадењата и цените на нивните состојки, како еден JSON.

    python -m planner.export_app <излез.json> [датум]
"""
from __future__ import annotations

import json
import sys

from catalog.match import CHAINS, LABEL
from catalog.needs import NEEDS
from catalog.same import collect

from .menu import PERISHABLE
from .recipes import DISHES, POSNO


def build(day: str) -> dict:
    data = collect()
    used = {need for _, parts in DISHES.values() for need, _ in parts}
    needs = {}
    for n in NEEDS:
        if n.id not in used:
            continue
        offers = {}
        for c in CHAINS:
            rows = []
            for h in data[n.id][c]:
                if not h["unit_price"] or h.get("outlier") or (h["trust"] < 2 and h["qty"] != "на мерење"):
                    continue
                by_weight = h["qty"] == "на мерење" or h["qty"] is None
                size = None if by_weight else round(h["price"] / h["unit_price"], 3)
                rows.append([h["name"][:44], h["price"], h["unit_price"], size])
            offers[c] = sorted(rows, key=lambda r: r[2])
        needs[n.id] = {"name": n.name, "unit": n.unit, "keeps": n.group not in PERISHABLE, "offers": offers}
    dishes = {name: {"kind": kind, "posno": name in POSNO, "parts": parts} for name, (kind, parts) in DISHES.items()}
    return {"day": day, "city": "Велес", "chains": [[c, LABEL[c]] for c in CHAINS], "needs": needs, "dishes": dishes}


if __name__ == "__main__":
    out = build(sys.argv[2] if len(sys.argv) > 2 else "")
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print(len(out["needs"]), "потреби,", len(out["dishes"]), "јадења,", sum(len(v) for n in out["needs"].values() for v in n["offers"].values()), "производи")
