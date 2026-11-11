"""Трите табели за листот за читање, како CSV.

    python -m catalog.export <папка>

  potrebi.csv   - потреба, единица, најниска цена по единица кај секој синџир
  proizvodi.csv - производот што стои зад секоја од тие цени
  isti.csv      - ист производ кај повеќе синџири, со цената кај секој
"""
from __future__ import annotations

import csv
import os
import sys

from .match import CHAINS, LABEL, cheapest
from .needs import NEEDS, NOTES
from .same import clusters, collect, pairs_for


def rounded(value: float) -> float:
    return round(value, 2) if value < 10 else round(value, 1) if value < 100 else round(value)


def text(value) -> str:
    """Празно за ништо; апостроф пред текст што табелата би го прочитала како формула."""
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    value = str(value)
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def tables() -> tuple[list[list], list[list], list[list]]:
    collected = collect()
    by_id = {n.id: n for n in NEEDS}
    needs, products, same = [], [], []
    for need_id, per in collected.items():
        need = by_id[need_id]
        best = {c: cheapest(per[c], need) for c in CHAINS}
        value = {c: rounded(best[c]["unit_price"]) if best[c] else None for c in CHAINS}
        present = [v for v in value.values() if v is not None]
        low = min(present) if present else None
        where = ", ".join(LABEL[c] for c in CHAINS if value[c] is not None and value[c] == low)
        needs.append([need.name, need.unit] + [value[c] for c in CHAINS] + [low, where, need.group]
                     + [len(per[c]) for c in CHAINS] + [NOTES.get(need_id, "")])
        for c in CHAINS:
            if best[c]:
                products.append([need.name, LABEL[c], best[c]["name"], best[c]["price"], value[c], need.unit])
        sure = [x for x in pairs_for(need_id, per) if x[2] == 1.0]
        for group in sorted(clusters(sure), key=lambda g: min(h["name"] for h in g)):
            price = {h["chain"]: h["price"] for h in group}
            name = next(h["name"] for c in CHAINS for h in group if h["chain"] == c)
            low, high = min(price.values()), max(price.values())
            promo = ", ".join(LABEL[h["chain"]] for c in CHAINS for h in group if h["chain"] == c and h["promo"])
            same.append([name] + [price.get(c) for c in CHAINS] + [low, round((high / low - 1) * 100), need.name, promo])
    return needs, products, same


def main(argv: list[str]) -> int:
    folder = argv[0] if argv else "."
    os.makedirs(folder, exist_ok=True)
    needs, products, same = tables()
    chains = [LABEL[c] for c in CHAINS]
    files = {
        "potrebi.csv": (["Потреба", "Ед."] + chains + ["Најниска", "Каде", "Група"]
                        + [f"Производи {c}" for c in chains] + ["Забелешка"], needs),
        "proizvodi.csv": (["Потреба", "Синџир", "Најевтин производ", "Цена", "По единица", "Ед."], products),
        "isti.csv": (["Производ"] + chains + ["Најниска", "Разлика %", "Потреба", "Акција кај"], same),
    }
    for name, (header, rows) in files.items():
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows([[text(float(c) if isinstance(c, (int, float)) and not isinstance(c, bool) else c)
                               for c in row] for row in rows])
        print(f"{name}: {len(rows)} реда")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
