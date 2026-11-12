"""Неделно мени според буџет: мени, листа за пазарење и каде е најевтино.

    python -m planner.menu 1200 4                          # буџет (ден.) за седум главни јадења, број на членови
    python -m planner.menu 1200 4 --posno                  # среда и петок посно
    python -m planner.menu 1200 4 --omileni planner/omileni.txt

Избира седум различни главни јадења што се вклопуваат во буџетот, со најмногу две од ист вид
(пилешко, мелено месо, грав...). Меѓу менијата што се вклопуваат: прво она со повеќе омилени
јадења (до три неделно), па поразновидното, па побогатото. Потоа ги собира состојките во една
листа и ја пресметува кај секој синџир. Сè е пресметка од ценовниците; ниту една цена не е проценета.
"""
from __future__ import annotations

import random
import sys
from collections import Counter

from catalog.match import CHAINS, LABEL
from catalog.needs import NEEDS

from .basket import price
from .recipes import KIND, PORTIONS, POSNO, RECIPES, cost

DAYS = ["понеделник", "вторник", "среда", "четврток", "петок", "сабота", "недела"]
FASTING_DAYS = (2, 4)                    # среда и петок
MAX_FAVOURITES = 3


def choose(budget: float, people: int, favourites: frozenset = frozenset(), fasting: bool = False, days: int = 7) -> dict:
    scale = people / PORTIONS
    priced = {r["dish"]: r["mixed"] * scale for r in cost() if r["mixed"] is not None and KIND[r["dish"]] != "прилог"}
    dishes = sorted(priced)
    lean = len(FASTING_DAYS) if fasting else 0

    def valid(menu) -> bool:
        return max(Counter(KIND[d] for d in menu).values()) <= 2 and sum(d in POSNO for d in menu) >= lean

    def score(menu) -> tuple:
        total = sum(priced[d] for d in menu)
        if total > budget:
            return (0, 0, 0, -total)                          # надвор од буџетот: колку поевтино, толку подобро
        return (1, min(MAX_FAVOURITES, sum(d in favourites for d in menu)), len({KIND[d] for d in menu}), total)

    # Најевтиното можно: посните прво (ако треба), па по ред на цена додека видот дозволува.
    cheapest, kinds = [], Counter()
    by_price = sorted(dishes, key=priced.get)
    for d in [x for x in by_price if x in POSNO][:lean] + by_price:
        if len(cheapest) < days and d not in cheapest and kinds[KIND[d]] < 2:
            cheapest.append(d)
            kinds[KIND[d]] += 1

    # Пребарување: од повеќе почетни менија, заменувај по едно јадење додека има подобрување.
    rng, best = random.Random(0), list(cheapest)
    for start in range(40):
        menu = list(cheapest) if start == 0 else rng.sample(dishes, days)
        if not valid(menu):
            continue
        improved = True
        while improved:
            improved = False
            for i in range(days):
                for d in dishes:
                    if d in menu:
                        continue
                    trial = menu[:i] + [d] + menu[i + 1:]
                    if valid(trial) and score(trial) > score(menu):
                        menu, improved = trial, True
        if score(menu) > score(best):
            best = menu
    fits = score(best)[0] == 1
    return {"fits": fits, "menu": order(best, fasting), "dish_cost": {d: round(priced[d]) for d in best},
            "cheapest_possible": round(sum(priced[d] for d in cheapest)), "scale": scale}


def order(menu: list[str], fasting: bool = False) -> list[str]:
    """Распоред по денови: посно во среда и петок ако се бара, исти видови да не се еден по друг."""
    menu, out = list(menu), [None] * len(menu)
    if fasting:
        for day in FASTING_DAYS:
            lean = next((d for d in menu if d in POSNO), None)
            if lean and day < len(out):
                out[day] = lean
                menu.remove(lean)
    for day in range(len(out)):
        if out[day] is None:
            before = out[day - 1] if day else None
            after = out[day + 1] if day + 1 < len(out) else None
            near = {KIND[d] for d in (before, after) if d}
            pick = next((d for d in menu if KIND[d] not in near), menu[0])
            out[day] = pick
            menu.remove(pick)
    return out


def shopping(menu: list[str], scale: float) -> list[tuple[str, float]]:
    total: Counter = Counter()
    for dish in menu:
        for need_id, qty in RECIPES[dish]:
            total[need_id] += qty * scale
    return [(need_id, round(qty, 2)) for need_id, qty in total.items()]


def plan(budget: float, people: int, favourites: frozenset = frozenset(), fasting: bool = False) -> dict:
    chosen = choose(budget, people, favourites, fasting)
    basket = shopping(chosen["menu"], chosen["scale"])
    return {**chosen, "basket": basket, "priced": price(basket)}


def main(argv: list[str]) -> int:
    budget, people = float(argv[0]), int(argv[1])
    favourites = frozenset()
    if "--omileni" in argv:
        with open(argv[argv.index("--omileni") + 1], encoding="utf-8") as fh:
            favourites = frozenset(line.strip() for line in fh if line.strip() and not line.startswith("#"))
        unknown = favourites - set(RECIPES)
        if unknown:
            print("Не ги знам овие јадења:", ", ".join(sorted(unknown)))
    result = plan(budget, people, favourites, "--posno" in argv)
    lines, single = result["priced"]["lines"], result["priced"]["single"]
    if not result["fits"]:
        print(f"Буџетот од {budget:g} ден. не стига. Најевтиното мени со вакви правила чини {result['cheapest_possible']} ден.\n")
    print(f"Мени за {people}, седум главни јадења:")
    for day, dish in zip(DAYS, result["menu"]):
        marks = ("  омилено" if dish in favourites else "") + ("  посно" if dish in POSNO else "")
        print(f"  {day:11} {dish[:34]:34} {result['dish_cost'][dish]:>5} ден.{marks}")
    print(f"  вкупно за потрошеното: {sum(result['dish_cost'].values())} ден.\n")
    if "--lista" in argv:
        print("Листа за пазарење:")
        for l in sorted(lines, key=lambda l: l["name"]):
            where = min((c for c in CHAINS if l["offers"][c]), key=lambda c: l["offers"][c]["by_unit"])
            print(f"  {l['name'][:30]:30} {l['wanted']:>5g} {l['unit']:5} најевтино: {LABEL[where]}")
        print()
    else:
        print(f"Листа за пазарење: {len(lines)} ставки (--lista за да се испише)")
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
