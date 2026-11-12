"""Јадења изразени во потреби: колку чини едно јадење денес.

    python -m planner.recipes           # сите јадења, од најевтиното по порција

Секое јадење е за четири порции. Состојките се потреби од каталогот, со количина во единицата на
потребата (кг, л, парче). Сол, бибер и вода не се бројат. Количините се прва проценка и чекаат
проверка; цената ја пресметува кодот, по цена по единица, од денешните ценовници.
"""
from __future__ import annotations

import sys

from catalog.match import CHAINS, LABEL
from catalog.needs import NEEDS
from catalog.same import collect

from .basket import offer

PORTIONS = 4
RECIPES: dict[str, list[tuple[str, float]]] = {
    "Тавче гравче": [("grav", 0.5), ("kromid", 0.3), ("crven-piper", 0.01), ("maslo-soncogledovo", 0.08)],
    "Грав со колбас": [("grav", 0.5), ("kromid", 0.2), ("kolbasi", 0.3), ("crven-piper", 0.01), ("maslo-soncogledovo", 0.05)],
    "Леќа чорба": [("lekja", 0.4), ("kromid", 0.15), ("morkov", 0.15), ("maslo-soncogledovo", 0.05)],
    "Пилешко со ориз": [("pileski-kopani", 1.0), ("oriz", 0.3), ("kromid", 0.15), ("morkov", 0.15), ("maslo-soncogledovo", 0.05)],
    "Пилешка супа со фиде": [("pile-celo", 0.8), ("morkov", 0.2), ("kompir", 0.3), ("fide-jufki", 0.1), ("kromid", 0.1)],
    "Грашок со пилешко": [("grasok", 0.8), ("pileski-kopani", 0.8), ("kromid", 0.15), ("morkov", 0.15), ("maslo-soncogledovo", 0.05)],
    "Пилешки стек со пире": [("pileski-gradi", 0.6), ("kompir", 1.0), ("mleko-trajno", 0.2), ("margarin", 0.05)],
    "Мусака": [("kompir", 1.2), ("meleno-meso", 0.5), ("kromid", 0.2), ("jajca", 3), ("mleko-trajno", 0.3), ("maslo-soncogledovo", 0.08)],
    "Полнети пиперки": [("piperki", 1.0), ("meleno-meso", 0.5), ("oriz", 0.15), ("kromid", 0.15), ("domatno-pire", 0.2), ("maslo-soncogledovo", 0.05)],
    "Сарма": [("zelka", 1.5), ("meleno-meso", 0.5), ("oriz", 0.15), ("kromid", 0.15), ("slanina-puseno", 0.1), ("maslo-soncogledovo", 0.05)],
    "Ќофтиња со компири": [("meleno-meso", 0.6), ("kromid", 0.15), ("jajca", 1), ("leb-bel", 0.1), ("kompir", 1.0), ("maslo-soncogledovo", 0.1)],
    "Шпагети со мелено месо": [("spageti", 0.5), ("meleno-meso", 0.4), ("domatno-pire", 0.5), ("kromid", 0.15), ("kaskaval", 0.1)],
    "Макарони со сирење": [("makaroni", 0.5), ("sirenje-belo", 0.3), ("jajca", 2), ("maslo-soncogledovo", 0.03)],
    "Пита со сирење": [("kori", 0.5), ("sirenje-belo", 0.4), ("jajca", 3), ("jogurt", 0.3), ("maslo-soncogledovo", 0.1)],
    "Компир манџа со свинско": [("kompir", 1.2), ("svinsko-meso", 0.5), ("kromid", 0.2), ("morkov", 0.1), ("crven-piper", 0.01), ("maslo-soncogledovo", 0.05)],
    "Турли тава": [("svinsko-meso", 0.5), ("kompir", 0.5), ("modar-patlidzan", 0.4), ("piperki", 0.3), ("domati", 0.4), ("kromid", 0.2), ("maslo-soncogledovo", 0.05)],
    "Ориз со зеленчук": [("oriz", 0.3), ("zamrznat-zelencuk", 0.6), ("kromid", 0.15), ("domatno-pire", 0.2), ("maslo-soncogledovo", 0.05)],
    "Јајца со домати и сирење": [("jajca", 8), ("domati", 0.6), ("piperki", 0.3), ("sirenje-belo", 0.2), ("maslo-soncogledovo", 0.03)],
    "Тиквици со јајца": [("tikvici", 1.0), ("jajca", 4), ("sirenje-belo", 0.2), ("maslo-soncogledovo", 0.05)],
    "Риба со компири": [("riba-zamrznata", 0.8), ("kompir", 1.0), ("limoni", 0.1), ("brasno-belo", 0.05), ("maslo-soncogledovo", 0.08)],
    "Палачинки со џем": [("brasno-belo", 0.3), ("jajca", 3), ("mleko-trajno", 0.6), ("dzem", 0.2), ("maslo-soncogledovo", 0.05)],
    "Домашна пица": [("brasno-belo", 0.5), ("kvasec-svez", 0.02), ("kecap", 0.15), ("kaskaval", 0.3), ("sunka", 0.15), ("pecurki", 0.2)],
    "Виршли со јајца и компири": [("virsli", 0.4), ("jajca", 4), ("kompir", 0.8), ("maslo-soncogledovo", 0.05)],
    "Шопска салата": [("domati", 0.6), ("krastavici", 0.4), ("piperki", 0.2), ("kromid", 0.1), ("sirenje-belo", 0.2), ("maslo-soncogledovo", 0.03)],
}

# Главната состојка на јадењето: менито не става исто повеќе од двапати неделно. „прилог" не е главно јадење.
KIND = {"Тавче гравче": "грав", "Грав со колбас": "грав", "Леќа чорба": "леќа", "Пилешко со ориз": "пилешко",
        "Пилешка супа со фиде": "пилешко", "Грашок со пилешко": "пилешко", "Пилешки стек со пире": "пилешко",
        "Мусака": "мелено месо", "Полнети пиперки": "мелено месо", "Сарма": "мелено месо", "Ќофтиња со компири": "мелено месо",
        "Шпагети со мелено месо": "мелено месо", "Макарони со сирење": "тесто", "Пита со сирење": "тесто",
        "Домашна пица": "тесто", "Палачинки со џем": "тесто", "Компир манџа со свинско": "свинско", "Турли тава": "свинско",
        "Ориз со зеленчук": "зеленчук", "Јајца со домати и сирење": "јајца", "Тиквици со јајца": "јајца",
        "Виршли со јајца и компири": "јајца", "Риба со компири": "риба", "Шопска салата": "прилог"}


def cost() -> list[dict]:
    """Цена на секое јадење кај секој синџир (ако ги има сите состојки) и од најевтиниот за секоја состојка."""
    data = collect()
    units = {n.id: n.unit for n in NEEDS}
    out = []
    for dish, parts in RECIPES.items():
        per_chain = {c: 0.0 for c in CHAINS}
        mixed, complete = 0.0, True
        for need_id, qty in parts:
            prices = {c: offer(data[need_id][c], units[need_id], qty) for c in CHAINS}
            have = [p["by_unit"] for p in prices.values() if p]
            if not have:
                complete = False
                continue
            mixed += min(have)
            for c in CHAINS:
                per_chain[c] = None if per_chain[c] is None or not prices[c] else per_chain[c] + prices[c]["by_unit"]
        out.append({"dish": dish, "mixed": round(mixed) if complete else None,
                    **{c: None if per_chain[c] is None else round(per_chain[c]) for c in CHAINS}})
    return sorted(out, key=lambda r: (r["mixed"] is None, r["mixed"] or 0))


def main(argv: list[str]) -> int:
    print(f"{'јадење за ' + str(PORTIONS) + ' порции':28} {'најевт.':>8} {'порција':>8} | " + " ".join(f"{LABEL[c]:>9}" for c in CHAINS))
    for r in cost():
        cells = " ".join(f"{r[c]:>9}" if r[c] is not None else f"{'-':>9}" for c in CHAINS)
        mixed = "-" if r["mixed"] is None else r["mixed"]
        portion = "-" if r["mixed"] is None else round(r["mixed"] / PORTIONS)
        print(f"{r['dish']:28} {mixed:>8} {portion:>8} | {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
