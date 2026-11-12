"""Дневна слика на каталогот: најниската цена по единица за секоја потреба кај секој синџир.

    python -m catalog.history 2026-11-12      # ја запишува catalog/history/2026-11-12.csv
    python -m catalog.history                 # што се смени меѓу последните две слики

Од две слики се гледа што поевтини и што поскапе во градот. Тоа се и податоците за известувањата.
"""
from __future__ import annotations

import csv
import glob
import os
import sys

from .match import CHAINS, ROOT, cheapest
from .needs import NEEDS
from .same import collect

FOLDER = os.path.join(ROOT, "catalog", "history")
STEP = 0.02      # помала промена од 2% на цената по единица не се брои: тоа е заокружување, не поевтинување


def snapshot() -> list[list]:
    data = collect()
    rows = []
    for need in NEEDS:
        for chain in CHAINS:
            best = cheapest(data[need.id][chain], need)
            if best:
                rows.append([need.id, chain, f"{best['unit_price']:g}", f"{best['price']:g}", int(bool(best["promo"])), best["name"]])
    return rows


def write(day: str) -> str:
    os.makedirs(FOLDER, exist_ok=True)
    path = os.path.join(FOLDER, day + ".csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["need", "chain", "unit_price", "price", "promo", "name"])
        w.writerows(snapshot())
    return path


def days() -> list[str]:
    return sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(FOLDER, "*.csv")))


def load(day: str) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    with open(os.path.join(FOLDER, day + ".csv"), encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["need"], {})[r["chain"]] = {"unit_price": float(r["unit_price"]), "price": float(r["price"]),
                                                         "promo": r["promo"] == "1", "name": r["name"]}
    return out


def lowest(per_chain: dict[str, dict]) -> tuple[str, dict] | None:
    return min(per_chain.items(), key=lambda kv: kv[1]["unit_price"]) if per_chain else None


def changes(old: dict, new: dict) -> list[dict]:
    """Потреби каде најниската цена во градот се смени за повеќе од STEP. Најголемите поевтинувања први.

    sure: поевтинувањето се гледа во денешниот ценовник, па е сигурно. Поскапување е сигурно само кога
    истиот производ кај истиот синџир денес чини повеќе; ако вчерашниот најевтин производ го нема во
    денешното читање, можеби само е пропуштен (Жито не ги дава сите редови при секое читање)."""
    out = []
    for need in new:
        before, after = lowest(old.get(need, {})), lowest(new[need])
        if not before or not after:
            continue
        a, b = before[1]["unit_price"], after[1]["unit_price"]
        if abs(b - a) > STEP * a:
            same = new[need].get(before[0], {}).get("name") == before[1]["name"]
            out.append({"need": need, "old": a, "new": b, "chain": after[0], "name": after[1]["name"], "promo": after[1]["promo"],
                        "pct": round(100 * (b / a - 1)), "sure": b < a or same})
    return sorted(out, key=lambda c: (c["pct"], c["need"]))


def latest() -> tuple[str, list[dict]]:
    """(датум на претходната слика, промени до последната); празно ако има само една слика."""
    known = days()
    return (known[-2], changes(load(known[-2]), load(known[-1]))) if len(known) >= 2 else ("", [])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(write(sys.argv[1]))
    else:
        since, moved = latest()
        names = {n.id: n.name for n in NEEDS}
        print(f"слики: {len(days())} | промени од {since or '-'}: {len(moved)}")
        for c in moved[:30]:
            print(f"  {c['pct']:>+4}%  {c['old']:>7g} -> {c['new']:>7g}  {names.get(c['need'], c['need'])} ({c['chain']})")
