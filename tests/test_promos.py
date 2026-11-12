"""Проверки на акциите, без мрежа."""
from catalog.promos import judge


def hit(chain, name, price, unit_price, promo=False):
    return {"chain": chain, "name": name, "description": "", "price": price, "unit_price": unit_price, "trust": 3, "promo": promo}


def row(price, regular, kind="промотивна цена", period="11.11.2026 до 24.11.2026"):
    return {"price": str(price), "regular_price": str(regular), "promo_type": kind, "promo_period": period}


def test_promo_is_checked_against_the_city_and_the_same_product():
    a, b = hit("zito", "МЛЕКО А 1л", 40, 40, True), hit("zito", "МЛЕКО Б 1л", 50, 50)
    c, d = hit("stokomak", "МЛЕКО А 1Л", 38, 38), hit("kam", "МЛЕКО В 1л", 45, 45, True)
    data = {"mleko-trajno": {"zito": [a, b], "stokomak": [c], "kam": [d], "ramstore": []}}
    rows = {"zito": {("МЛЕКО А 1л", ""): row(40, 55, "клуб цена"), ("ЧОКОЛАДО", ""): row(90, 100), ("СИТНО", ""): row(99, 100)},
            "kam": {("МЛЕКО В 1л", ""): row(45, 60, period="")}}
    out = {p["name"]: p for p in judge(rows, data, [[a, c]])}
    assert set(out) == {"МЛЕКО А 1л", "ЧОКОЛАДО", "МЛЕКО В 1л"}              # попуст под 5% не е акција
    milk = out["МЛЕКО А 1л"]
    assert milk["pct"] == 27 and milk["card"] and milk["since"] == "2026-11-11" and milk["until"] == "2026-11-24" and milk["need"] == "mleko-trajno"
    assert not milk["cheapest"] and milk["elsewhere"] == ("stokomak", 38)      # истото млеко е поевтино кај Стокомак и без акција
    assert out["ЧОКОЛАДО"]["need"] == "" and out["ЧОКОЛАДО"]["group"] == "Друго" and not out["ЧОКОЛАДО"]["card"]
    assert not out["МЛЕКО В 1л"]["cheapest"] and out["МЛЕКО В 1л"]["until"] == ""


def test_cheapest_means_lowest_unit_price_in_the_city():
    a = hit("ramstore", "ОРИЗ 1кг", 60, 60, True)
    data = {"oriz": {"zito": [hit("zito", "ОРИЗ Ж 1кг", 75, 75)], "stokomak": [], "kam": [hit("kam", "ОРИЗ К 1кг", 70, 70)], "ramstore": [a]}}
    out = judge({"ramstore": {("ОРИЗ 1кг", ""): row(60, 80, "ЛОЈАЛНОСТ")}}, data, [])
    assert out[0]["cheapest"] and out[0]["card"] and out[0]["elsewhere"] is None


def test_history_reports_only_real_moves_of_the_city_minimum():
    from catalog.history import changes
    row = lambda unit, name="X", promo=False: {"unit_price": unit, "price": unit, "promo": promo, "name": name}
    old = {"mleko-trajno": {"zito": row(48), "kam": row(52)}, "oriz": {"zito": row(70)}, "seker": {"zito": row(60)}, "sol": {"zito": row(20)}}
    new = {"mleko-trajno": {"zito": row(48), "kam": row(44, "МЛЕКО К", True)}, "oriz": {"zito": row(70.5)}, "seker": {"zito": row(66)}, "jajca": {"zito": row(9)}}
    out = changes(old, new)
    assert [c["need"] for c in out] == ["mleko-trajno", "seker"]                 # оризот е заокружување, јајцата немаат вчера
    assert out[0]["chain"] == "kam" and out[0]["pct"] == -8 and out[0]["promo"] and out[1]["pct"] == 10
    assert out[0]["sure"] and out[1]["sure"]                                     # шеќерот е истиот производ, поскап
    gone = changes({"seker": {"zito": row(60, "ШЕЌЕР А")}}, {"seker": {"zito": row(66, "ШЕЌЕР Б")}})
    assert gone[0]["pct"] == 10 and not gone[0]["sure"]                          # вчерашниот производ го нема: можеби е само пропуштен
