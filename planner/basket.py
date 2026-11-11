"""Кошничка: колку чини иста листа на потреби кај секој синџир, и како да се подели на два маркета.

    python -m planner.basket                     # примерна неделна кошничка
    python -m planner.basket moja.csv            # сопствена: редови „потреба,количина"

Две пресметки за секоја потреба и синџир:
  по единица  - бараната количина по најниската цена по единица. Не зависи од големината на
                пакувањето, па е фер споредба меѓу синџири.
  на каса     - најевтиниот начин да се купи количината со цели пакувања од еден производ. Тоа е
                она што навистина се плаќа, но синџир што има само големо пакување излегува поскап.
Стоката на мерење се купува точно колку што треба. Цените ги пресметува кодот, од ценовниците.
"""
from __future__ import annotations

import csv
import math
import sys
from itertools import combinations

from catalog.match import CHAINS, LABEL
from catalog.needs import NEEDS
from catalog.same import collect

# Примерна недела за четиричлено семејство. Количините се во единицата на потребата.
SAMPLE = [("mleko-trajno", 6), ("jogurt", 3), ("kiselo-mleko", 1.2), ("jajca", 20), ("sirenje-belo", 0.5), ("kaskaval", 0.3),
          ("leb-bel", 3.3), ("pile-celo", 1.5), ("meleno-meso", 1), ("virsli", 0.5), ("kompir", 3), ("kromid", 1),
          ("domati", 1.5), ("krastavici", 1), ("piperki", 1), ("zelka", 1.5), ("jabolka", 2), ("banani", 1.5),
          ("maslo-soncogledovo", 1), ("seker", 1), ("brasno-belo", 2), ("oriz", 1), ("makaroni", 1), ("grav", 0.5),
          ("kafe-meleno", 0.2), ("sok-ovosen", 2), ("voda-negazirana", 9), ("toaletna-hartija", 10), ("prasok-perenje", 1),
          ("sredstvo-sadovi", 0.5)]


def offer(hits: list[dict], unit: str, wanted: float) -> dict | None:
    """Најевтиниот производ за бараната количина во еден синџир."""
    best, lowest = None, None
    for h in hits:
        if not h["unit_price"] or h["trust"] < 2 and h["qty"] != "на мерење" or h.get("outlier"):
            continue
        if h["qty"] == "на мерење" or h["qty"] is None:
            packs, cost, got = None, h["unit_price"] * wanted, wanted
        else:
            size = h["price"] / h["unit_price"]                 # колку единици има во едно пакување
            packs = max(1, math.ceil(wanted / size - 1e-9))
            cost, got = packs * h["price"], packs * size
        if best is None or cost < best["cost"]:
            best = {"name": h["name"], "cost": round(cost, 1), "packs": packs, "got": round(got, 2)}
        if lowest is None or h["unit_price"] < lowest:
            lowest = h["unit_price"]
    if best:
        best["by_unit"] = round(lowest * wanted, 1)
    return best


def price(basket: list[tuple[str, float]]) -> dict:
    data = collect()
    units = {n.id: (n.name, n.unit) for n in NEEDS}
    lines = []
    for need_id, wanted in basket:
        name, unit = units[need_id]
        offers = {c: offer(data[need_id][c], unit, wanted) for c in CHAINS}
        lines.append({"need": need_id, "name": name, "unit": unit, "wanted": wanted, "offers": offers})
    return {"lines": lines, "single": single(lines), "split": split(lines)}


def single(lines: list[dict]) -> dict:
    """Сè од еден синџир. Споредбата важи само за ставките што ги имаат сите синџири."""
    common = [l for l in lines if all(l["offers"][c] for c in CHAINS)]
    out = {"common": len(common)}
    for c in CHAINS:
        out[c] = {"by_unit": round(sum(l["offers"][c]["by_unit"] for l in common)),
                  "at_till": round(sum(l["offers"][c]["cost"] for l in common)),
                  "missing": [l["name"] for l in lines if not l["offers"][c]]}
    out["best_mix"] = round(sum(min(l["offers"][c]["by_unit"] for c in CHAINS) for l in common))
    return out


def split(lines: list[dict]) -> list[dict]:
    """Секој пар синџири: секоја ставка од поевтиниот од двата. Само парови што ја покриваат целата листа."""
    out = []
    for a, b in combinations(CHAINS, 2):
        total, count, covered = 0.0, {a: 0, b: 0}, True
        for l in lines:
            options = [(l["offers"][c]["by_unit"], c) for c in (a, b) if l["offers"][c]]
            if not options:
                covered = False
                break
            cost, chain = min(options)
            total += cost
            count[chain] += 1
        if covered:
            out.append({"chains": (a, b), "total": round(total), "items": count})
    return sorted(out, key=lambda x: x["total"])


def main(argv: list[str]) -> int:
    basket = SAMPLE
    if argv:
        with open(argv[0], encoding="utf-8", newline="") as fh:
            basket = [(r[0], float(r[1])) for r in csv.reader(fh) if r and not r[0].startswith("#")]
    result = price(basket)
    for l in result["lines"]:
        cells = " | ".join(f"{LABEL[c][:1]} {l['offers'][c]['by_unit']:>6.0f}" if l["offers"][c] else f"{LABEL[c][:1]}      -" for c in CHAINS)
        print(f"{l['name'][:26]:26} {l['wanted']:>5g} {l['unit']:5} {cells}")
        if "-v" in argv:
            for c in CHAINS:
                o = l["offers"][c]
                if o:
                    print(f"{'':10}{LABEL[c][:1]} {o['cost']:>6.0f}  {'' if o['packs'] is None else str(o['packs']) + ' x '}{o['name'][:60]}")
    print()
    print(f"Ставки што ги имаат сите четири: {result['single']['common']} од {len(result['lines'])}")
    for c in CHAINS:
        s = result["single"][c]
        print(f"{LABEL[c]:9} по единица {s['by_unit']:>6} ден. | на каса {s['at_till']:>6} ден."
              + (f"  (нема: {', '.join(s['missing'])})" if s["missing"] else ""))
    print(f"Секоја ставка од најевтиниот синџир: {result['single']['best_mix']} ден. (по единица)")
    for s in result["split"][:3]:
        a, b = s["chains"]
        print(f"{LABEL[a]} + {LABEL[b]}: {s['total']} ден.  ({s['items'][a]} ставки од {LABEL[a]}, {s['items'][b]} од {LABEL[b]})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
