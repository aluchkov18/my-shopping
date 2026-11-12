"""Јадења изразени во потреби: колку чини едно јадење денес.

    python -m planner.recipes           # сите јадења, од најевтиното по порција
    python -m planner.recipes 15        # само првите 15

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
# Јадење: (вид, состојки). Видот е главната состојка; менито не става ист вид повеќе од двапати неделно.
# „прилог" не е главно јадење. Состојка е (потреба, количина во единицата на потребата) за четири порции.
M = "maslo-soncogledovo"
DISHES: dict[str, tuple[str, list[tuple[str, float]]]] = {
    # --- грав, леќа, наут
    "Тавче гравче": ("грав", [("grav", 0.5), ("kromid", 0.3), ("crven-piper", 0.01), (M, 0.08)]),
    "Грав чорба": ("грав", [("grav", 0.4), ("kromid", 0.2), ("morkov", 0.15), ("crven-piper", 0.01), (M, 0.05)]),
    "Грав со колбас": ("грав", [("grav", 0.5), ("kromid", 0.2), ("kolbasi", 0.3), ("crven-piper", 0.01), (M, 0.05)]),
    "Грав со суви ребра": ("грав", [("grav", 0.5), ("slanina-puseno", 0.3), ("kromid", 0.2), ("crven-piper", 0.01), (M, 0.03)]),
    "Леќа чорба": ("леќа и наут", [("lekja", 0.4), ("kromid", 0.15), ("morkov", 0.15), (M, 0.05)]),
    "Наут со зеленчук": ("леќа и наут", [("naut", 0.4), ("kromid", 0.15), ("morkov", 0.15), ("domatno-pire", 0.2), (M, 0.05)]),
    # --- пилешко
    "Ориз со пилешки копан": ("пилешко", [("pileski-kopani", 1.0), ("oriz", 0.3), ("kromid", 0.15), ("morkov", 0.15), (M, 0.05)]),
    "Пилешка супа со фиде": ("пилешко", [("pile-celo", 0.8), ("morkov", 0.2), ("kompir", 0.3), ("fide-jufki", 0.1), ("kromid", 0.1)]),
    "Манџа грашок со пилешко": ("пилешко", [("grasok", 0.8), ("pileski-kopani", 0.8), ("kromid", 0.15), ("morkov", 0.15), (M, 0.05)]),
    "Пилешки стек со пире": ("пилешко", [("pileski-gradi", 0.6), ("kompir", 1.0), ("mleko-trajno", 0.2), ("margarin", 0.05)]),
    "Похован пилешки стек со пире": ("пилешко", [("pileski-gradi", 0.6), ("jajca", 2), ("prezla", 0.1), ("brasno-belo", 0.05), (M, 0.15),
                                                  ("kompir", 1.0), ("mleko-trajno", 0.2), ("margarin", 0.05)]),
    "Пилешко со компири во рерна": ("пилешко", [("pileski-kopani", 1.2), ("kompir", 1.5), ("kromid", 0.2), (M, 0.06), ("zacin-univerzalen", 0.01)]),
    "Пилешки крилца со компири": ("пилешко", [("pileski-krilca", 1.0), ("kompir", 1.2), (M, 0.05)]),
    "Компир манџа со пилешко": ("пилешко", [("kompir", 1.2), ("pileski-kopani", 0.8), ("kromid", 0.2), ("morkov", 0.1), ("crven-piper", 0.01), (M, 0.05)]),
    "Пилешки паприкаш": ("пилешко", [("pileski-kopani", 0.8), ("piperki", 0.4), ("kromid", 0.2), ("domatno-pire", 0.2), ("crven-piper", 0.01), (M, 0.05)]),
    "Пилешко филе во павлака со печурки": ("пилешко", [("pileski-gradi", 0.6), ("pavlaka-gotvenje", 0.2), ("pecurki", 0.3), ("oriz", 0.3), (M, 0.03)]),
    "Ѓувеч со пилешко": ("пилешко", [("pileski-kopani", 0.8), ("kompir", 0.5), ("modar-patlidzan", 0.3), ("piperki", 0.3), ("domati", 0.4),
                                      ("morkov", 0.1), ("oriz", 0.1), ("kromid", 0.2), (M, 0.05)]),
    # --- мелено месо
    "Мусака": ("мелено месо", [("kompir", 1.2), ("meleno-meso", 0.5), ("kromid", 0.2), ("jajca", 3), ("mleko-trajno", 0.3), (M, 0.08)]),
    "Полнети пиперки": ("мелено месо", [("piperki", 1.0), ("meleno-meso", 0.5), ("oriz", 0.15), ("kromid", 0.15), ("domatno-pire", 0.2), (M, 0.05)]),
    "Полнети тиквици": ("мелено месо", [("tikvici", 1.2), ("meleno-meso", 0.4), ("oriz", 0.1), ("kromid", 0.15), ("domatno-pire", 0.2), (M, 0.05)]),
    "Сарма": ("мелено месо", [("zelka", 1.5), ("meleno-meso", 0.5), ("oriz", 0.15), ("kromid", 0.15), ("slanina-puseno", 0.1), (M, 0.05)]),
    "Пире со ќофтиња": ("мелено месо", [("meleno-meso", 0.6), ("kromid", 0.15), ("jajca", 1), ("leb-bel", 0.1), (M, 0.1),
                                         ("kompir", 1.2), ("mleko-trajno", 0.2), ("margarin", 0.05)]),
    "Шпагети со мелено месо": ("мелено месо", [("spageti", 0.5), ("meleno-meso", 0.4), ("domatno-pire", 0.5), ("kromid", 0.15), ("kaskaval", 0.1)]),
    "Макарони со мелено месо": ("мелено месо", [("makaroni", 0.5), ("meleno-meso", 0.4), ("kromid", 0.15), ("domatno-pire", 0.3), (M, 0.03)]),
    "Плескавици со помфрит": ("мелено месо", [("meleno-meso", 0.7), ("kromid", 0.1), ("pomfrit", 0.8), (M, 0.1), ("leb-bel", 0.3)]),
    "Ќебапи со кромид и леб": ("мелено месо", [("meleno-meso", 0.7), ("kromid", 0.3), ("leb-bel", 0.5)]),
    # --- свинско и јунешко
    "Компир манџа со свинско": ("свинско", [("kompir", 1.2), ("svinsko-meso", 0.5), ("kromid", 0.2), ("morkov", 0.1), ("crven-piper", 0.01), (M, 0.05)]),
    "Турли тава": ("свинско", [("svinsko-meso", 0.5), ("kompir", 0.5), ("modar-patlidzan", 0.4), ("piperki", 0.3), ("domati", 0.4), ("kromid", 0.2), (M, 0.05)]),
    "Зелка со месо": ("свинско", [("zelka", 1.5), ("svinsko-meso", 0.5), ("kromid", 0.15), ("crven-piper", 0.01), (M, 0.05)]),
    "Боранија со месо": ("свинско", [("zamrznat-zelencuk", 0.8), ("svinsko-meso", 0.4), ("kromid", 0.15), ("domatno-pire", 0.2), (M, 0.05)]),
    "Селско месо": ("свинско", [("svinsko-meso", 0.6), ("pecurki", 0.3), ("kromid", 0.3), ("piperki", 0.2), ("domatno-pire", 0.2), (M, 0.05)]),
    "Свинска вешалица со пржени компири": ("свинско", [("svinsko-meso", 0.7), ("kompir", 1.2), (M, 0.15)]),
    "Пастрмајлија": ("свинско", [("brasno-belo", 0.6), ("kvasec-svez", 0.02), ("svinsko-meso", 0.5), ("jajca", 4), (M, 0.05)]),
    "Јунешка чорба": ("јунешко", [("junesko-meso", 0.4), ("morkov", 0.2), ("kompir", 0.3), ("kromid", 0.1), ("fide-jufki", 0.05), ("jajca", 1), ("limoni", 0.05)]),
    "Гулаш со макарони": ("јунешко", [("junesko-meso", 0.6), ("kromid", 0.4), ("crven-piper", 0.02), ("domatno-pire", 0.2), (M, 0.05), ("makaroni", 0.4)]),
    "Јунешко со компири": ("јунешко", [("junesko-meso", 0.5), ("kompir", 1.0), ("kromid", 0.2), ("morkov", 0.1), ("crven-piper", 0.01), (M, 0.05)]),
    # --- риба
    "Риба со компири": ("риба", [("riba-zamrznata", 0.8), ("kompir", 1.0), ("limoni", 0.1), ("brasno-belo", 0.05), (M, 0.08)]),
    "Пржена риба со ориз": ("риба", [("riba-zamrznata", 0.8), ("brasno-belo", 0.05), (M, 0.15), ("oriz", 0.3), ("limoni", 0.1)]),
    "Макарони со туна": ("риба", [("makaroni", 0.5), ("tuna", 0.3), ("domatno-pire", 0.3), ("kromid", 0.1), (M, 0.03)]),
    # --- јајца, виршли и колбаси
    "Јајца со домати и сирење": ("јајца", [("jajca", 8), ("domati", 0.6), ("piperki", 0.3), ("sirenje-belo", 0.2), (M, 0.03)]),
    "Тиквици со јајца": ("јајца", [("tikvici", 1.0), ("jajca", 4), ("sirenje-belo", 0.2), (M, 0.05)]),
    "Пржени пиперки со сирење и јајца": ("јајца", [("piperki", 1.0), ("sirenje-belo", 0.3), ("jajca", 4), (M, 0.08)]),
    "Кајгана со сирење": ("јајца", [("jajca", 8), ("sirenje-belo", 0.2), (M, 0.03), ("leb-bel", 0.5)]),
    "Пржени јајца со компири": ("јајца", [("jajca", 8), ("kompir", 1.2), (M, 0.15)]),
    "Омлет со шунка и кашкавал": ("јајца", [("jajca", 8), ("sunka", 0.15), ("kaskaval", 0.15), (M, 0.03), ("leb-bel", 0.4)]),
    "Виршли со јајца и компири": ("виршли и колбаси", [("virsli", 0.4), ("jajca", 4), ("kompir", 0.8), (M, 0.05)]),
    "Виршли со помфрит": ("виршли и колбаси", [("virsli", 0.5), ("pomfrit", 0.8), (M, 0.1), ("kecap", 0.05)]),
    "Колбас со пржени компири и јајца": ("виршли и колбаси", [("kolbasi", 0.4), ("kompir", 1.0), ("jajca", 4), (M, 0.1)]),
    "Панирано со пире": ("панирано", [("panirano-zamrznato", 0.6), ("kompir", 1.0), ("mleko-trajno", 0.2), ("margarin", 0.05), (M, 0.1)]),
    # --- теста
    "Макарони со сирење": ("тесто", [("makaroni", 0.5), ("sirenje-belo", 0.3), ("jajca", 2), (M, 0.03)]),
    "Макарони со кашкавал во рерна": ("тесто", [("makaroni", 0.5), ("kaskaval", 0.25), ("jajca", 3), ("mleko-trajno", 0.4), ("margarin", 0.04)]),
    "Шпагети со доматен сос": ("тесто", [("spageti", 0.5), ("domatno-pire", 0.5), ("kromid", 0.1), ("luk", 0.02), (M, 0.04)]),
    "Шпагети со сланина и павлака": ("тесто", [("spageti", 0.5), ("slanina-puseno", 0.2), ("pavlaka-gotvenje", 0.2), ("jajca", 2), ("kaskaval", 0.1)]),
    "Пита со сирење": ("тесто", [("kori", 0.5), ("sirenje-belo", 0.4), ("jajca", 3), ("jogurt", 0.3), (M, 0.1)]),
    "Пита со праз": ("тесто", [("kori", 0.5), ("praz", 1), ("sirenje-belo", 0.2), ("jajca", 2), (M, 0.12)]),
    "Пита со мелено месо": ("тесто", [("kori", 0.5), ("meleno-meso", 0.4), ("kromid", 0.3), (M, 0.12)]),
    "Мекици со сирење": ("тесто", [("brasno-belo", 0.5), ("kvasec-svez", 0.02), ("jogurt", 0.2), (M, 0.3), ("sirenje-belo", 0.3)]),
    "Качамак со сирење": ("тесто", [("brasno-pcenkarno", 0.4), ("sirenje-belo", 0.3), ("margarin", 0.05), ("kiselo-mleko", 0.5)]),
    "Попара": ("тесто", [("leb-bel", 0.5), ("sirenje-belo", 0.3), ("margarin", 0.05), ("mleko-trajno", 0.3)]),
    "Домашна пица": ("тесто", [("brasno-belo", 0.5), ("kvasec-svez", 0.02), ("kecap", 0.15), ("kaskaval", 0.3), ("sunka", 0.15), ("pecurki", 0.2)]),
    "Тост сендвичи со шунка и кашкавал": ("тесто", [("tost-leb", 0.5), ("sunka", 0.2), ("kaskaval-slajs", 0.2), ("kecap", 0.05)]),
    "Палачинки со џем": ("тесто", [("brasno-belo", 0.3), ("jajca", 3), ("mleko-trajno", 0.6), ("dzem", 0.2), (M, 0.05)]),
    # --- зеленчук
    "Ориз со зеленчук": ("зеленчук", [("oriz", 0.3), ("zamrznat-zelencuk", 0.6), ("kromid", 0.15), ("domatno-pire", 0.2), (M, 0.05)]),
    "Ориз со печурки": ("зеленчук", [("oriz", 0.35), ("pecurki", 0.4), ("kromid", 0.15), (M, 0.05), ("zacin-univerzalen", 0.01)]),
    "Зелка со ориз": ("зеленчук", [("zelka", 1.2), ("oriz", 0.2), ("kromid", 0.15), ("morkov", 0.1), ("crven-piper", 0.01), (M, 0.06)]),
    "Праз со ориз": ("зеленчук", [("praz", 1), ("oriz", 0.3), ("morkov", 0.1), (M, 0.06)]),
    "Посна компир манџа": ("зеленчук", [("kompir", 1.2), ("kromid", 0.2), ("morkov", 0.15), ("domatno-pire", 0.1), ("crven-piper", 0.01), (M, 0.06)]),
    "Посни полнети пиперки": ("зеленчук", [("piperki", 1.0), ("oriz", 0.3), ("kromid", 0.2), ("morkov", 0.15), ("domatno-pire", 0.2), (M, 0.08)]),
    "Имам бајлди": ("зеленчук", [("modar-patlidzan", 1.0), ("kromid", 0.4), ("domati", 0.5), ("luk", 0.03), (M, 0.1)]),
    "Чорба од зеленчук": ("зеленчук", [("kompir", 0.4), ("morkov", 0.2), ("kromid", 0.1), ("zamrznat-zelencuk", 0.3), ("fide-jufki", 0.05), (M, 0.03)]),
    "Пржени тиквици со јогурт": ("зеленчук", [("tikvici", 1.2), ("brasno-belo", 0.1), (M, 0.15), ("jogurt", 0.5), ("luk", 0.02)]),
    "Похован карфиол со јогурт": ("зеленчук", [("karfiol-brokula", 1.0), ("jajca", 2), ("brasno-belo", 0.1), (M, 0.15), ("jogurt", 0.4)]),
    # --- прилог
    "Шопска салата": ("прилог", [("domati", 0.6), ("krastavici", 0.4), ("piperki", 0.2), ("kromid", 0.1), ("sirenje-belo", 0.2), (M, 0.03)]),
}
RECIPES = {dish: parts for dish, (_, parts) in DISHES.items()}
KIND = {dish: kind for dish, (kind, _) in DISHES.items()}
# Посно: без месо, јајца и млечно.
POSNO = {"Тавче гравче", "Грав чорба", "Леќа чорба", "Наут со зеленчук", "Шпагети со доматен сос", "Ориз со зеленчук", "Ориз со печурки",
         "Зелка со ориз", "Праз со ориз", "Посна компир манџа", "Посни полнети пиперки", "Имам бајлди", "Чорба од зеленчук"}


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
    rows = cost()
    for r in rows[:int(argv[0])] if argv else rows:
        cells = " ".join(f"{r[c]:>9}" if r[c] is not None else f"{'-':>9}" for c in CHAINS)
        mixed = "-" if r["mixed"] is None else r["mixed"]
        portion = "-" if r["mixed"] is None else round(r["mixed"] / PORTIONS)
        print(f"{r['dish']:28} {mixed:>8} {portion:>8} | {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
