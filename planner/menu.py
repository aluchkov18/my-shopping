"""Неделно мени според буџет: мени, листа за пазарење и каде е најевтино.

    python -m planner.menu 1200 4        # буџет во денари за седум главни јадења, број на членови

Избира седум различни главни јадења што се вклопуваат во буџетот, со најмногу две од ист вид
(пилешко, мелено месо, грав...). Меѓу менијата што се вклопуваат го зема најразновидното, па
најбогатото. Потоа ги собира состојките во една листа и ја пресметува кај секој синџир.
Сè е пресметка од ценовниците; ниту една цена не е проценета.
"""
from __future__ import annotations

import sys
from collections import Counter
from itertools import combinations

from catalog.match import CHAINS, LABEL
from catalog.needs import NEEDS

from .basket import price
from .recipes import KIND, PORTIONS, RECIPES, cost

DAYS = ["понеделник", "вторник", "среда", "четврток", "петок", "сабота", "недела"]


def choose(budget: float, people: int, days: int = 7) -> dict:
    scale = people / PORTIONS
    priced = {r["dish"]: r["mixed"] * scale for r in cost() if r["mixed"] is not None and KIND[r["dish"]] != "прилог"}
    best, cheapest = None, None
    for menu in combinations(sorted(priced), days):
        kinds = Counter(KIND[d] for d in menu)
        if max(kinds.values()) > 2:
            continue
        total = sum(priced[d] for d in menu)
        if cheapest is None or total < cheapest[0]:
            cheapest = (total, menu)
        if total <= budget and (best is None or (len(kinds), total) > best[0]):
            best = ((len(kinds), total), menu)
    fits = best is not None
    menu = best[1] if fits else cheapest[1]
    return {"fits": fits, "menu": order(list(menu)), "dish_cost": {d: round(priced[d]) for d in menu},
            "cheapest_possible": round(cheapest[0]), "scale": scale}


def order(menu: list[str]) -> list[str]:
    """Распоред по денови: исти видови да не се еден по друг."""
    out = []
    while menu:
        pick = next((d for d in menu if not out or KIND[d] != KIND[out[-1]]), menu[0])
        out.append(pick)
        menu.remove(pick)
    return out


def shopping(menu: list[str], scale: float) -> list[tuple[str, float]]:
    total: Counter = Counter()
    for dish in menu:
        for need_id, qty in RECIPES[dish]:
            total[need_id] += qty * scale
    return [(need_id, round(qty, 2)) for need_id, qty in total.items()]


def plan(budget: float, people: int) -> dict:
    chosen = choose(budget, people)
    basket = shopping(chosen["menu"], chosen["scale"])
    return {**chosen, "basket": basket, "priced": price(basket)}


def main(argv: list[str]) -> int:
    budget, people = float(argv[0]), int(argv[1])
    result = plan(budget, people)
    lines, single = result["priced"]["lines"], result["priced"]["single"]
    if not result["fits"]:
        print(f"Буџетот од {budget:g} ден. не стига. Најевтиното мени со вакви правила чини {result['cheapest_possible']} ден.\n")
    print(f"Мени за {people}, седум главни јадења:")
    for day, dish in zip(DAYS, result["menu"]):
        print(f"  {day:11} {dish:28} {result['dish_cost'][dish]:>5} ден.  ({KIND[dish]})")
    print(f"  вкупно за потрошеното: {sum(result['dish_cost'].values())} ден.\n")
    names = {n.id: n.name for n in NEEDS}
    print("Листа за пазарење:")
    for l in sorted(lines, key=lambda l: l["name"]):
        where = min((c for c in CHAINS if l["offers"][c]), key=lambda c: l["offers"][c]["by_unit"])
        print(f"  {l['name'][:30]:30} {l['wanted']:>5g} {l['unit']:5} најевтино: {LABEL[where]}")
    print()
    for c in CHAINS:
        missing = single[c]["missing"]
        full = sum(l["offers"][c]["cost"] for l in lines if l["offers"][c])
        print(f"  {LABEL[c]:9} на каса {round(full):>5} ден." + (f"  нема: {', '.join(missing)}" if missing else "  има сè"))
    for s in result["priced"]["split"][:2]:
        a, b = s["chains"]
        print(f"  {LABEL[a]} + {LABEL[b]}: {s['total']} ден. за потрошеното ({s['items'][a]} ставки + {s['items'][b]})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
