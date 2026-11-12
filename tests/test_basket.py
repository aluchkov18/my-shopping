"""Проверки на кошничката, без мрежа."""
from planner.basket import offer, single


def hit(name, price, unit_price, qty, trust=3):
    return {"name": name, "price": price, "unit_price": unit_price, "qty": qty, "trust": trust}


def test_whole_packs_and_cheapest_unit():
    hits = [hit("МЛЕКО 1л", 50, 50, 1.0), hit("МЛЕКО 2л", 90, 45, 2.0)]
    best = offer(hits, "л", 3)
    assert best["cost"] == 150 and best["packs"] == 3 and best["name"] == "МЛЕКО 1л"     # 2 x 2л би биле 180
    assert best["by_unit"] == 135                                                        # 3 л по 45
    assert offer(hits, "л", 4)["cost"] == 180


def test_by_weight_is_bought_exactly():
    best = offer([hit("КАШКАВАЛ РЕФУС", 435, 435, "на мерење")], "кг", 0.3)
    assert best["cost"] == 130.5 and best["packs"] is None


def test_unconfirmed_prices_are_left_out():
    assert offer([hit("ПРАШОК 3кг", 300, 100, None, trust=1), hit("ПРАШОК 2кг", 0, None, 2.0, trust=0)], "кг", 1) is None


def test_single_compares_only_common_lines():
    lines = [{"name": "Млеко", "offers": {c: {"cost": 60, "by_unit": 50} for c in ("zito", "stokomak", "kam", "ramstore")}},
             {"name": "Месо", "offers": {"zito": {"cost": 300, "by_unit": 300}, "stokomak": None, "kam": None, "ramstore": None}}]
    result = single(lines)
    assert result["common"] == 1 and result["zito"]["by_unit"] == 50 and result["stokomak"]["missing"] == ["Месо"]


def test_recipes_use_known_needs():
    from catalog.needs import NEEDS
    from planner.recipes import RECIPES
    known = {n.id for n in NEEDS}
    assert all(need in known and qty > 0 for parts in RECIPES.values() for need, qty in parts)
    assert len(RECIPES) >= 20


def test_menu_order_and_shopping_list():
    from planner.menu import order, shopping
    from planner.recipes import KIND
    menu = order(["Мусака", "Сарма", "Леќа чорба", "Тавче гравче"])
    assert sorted(menu) == sorted(["Мусака", "Сарма", "Леќа чорба", "Тавче гравче"])
    assert all(KIND[a] != KIND[b] for a, b in zip(menu, menu[1:]))
    basket = dict(shopping(["Тавче гравче", "Леќа чорба"], 1.5))
    assert basket["grav"] == 0.75 and basket["kromid"] == 0.68 and basket["lekja"] == 0.6
    assert set(KIND) >= {"Мусака", "Шопска салата"}
