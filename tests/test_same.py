"""Проверки на спојувањето на ист производ меѓу синџири, без мрежа."""
from catalog.same import alike, compare, features, pairs_for, same_qty


def hit(chain, name, qty, price=50):
    words, numbers = features(name)
    return {"chain": chain, "name": name, "price": price, "qty": qty, "words": words, "numbers": numbers, "promo": False}


def test_features_drop_the_size_and_keep_numbers():
    words, numbers = features("МЛЕКО БИТОЛСКО 1л 2.8%")
    assert words == {"МЛЕКО", "БИТОЛСКО"} and numbers == {"2.8"}
    words, numbers = features("BARILLA ШПАГЕТИ 500Г")
    assert "БАРИЛА" in words and not numbers


def test_alike_and_compare():
    assert alike("БИТОЛСКО", "БИТОЛСКИ") and alike("РИВ", "РИВЕ")
    assert not alike("ГАУДА", "ЕДАМЕР")
    assert compare(frozenset({"РИО", "КУБАНИТА"}), frozenset({"КУБАНИТА", "РИО", "ГОЛД"})) == (2, 0, 1)


def test_same_qty():
    assert same_qty(1.0, 1.0) and same_qty(0.5, 0.505) and not same_qty(0.5, 1.0)
    assert same_qty("на мерење", "на мерење") and not same_qty("на мерење", 1.0) and not same_qty(None, 1.0)


def test_pairs_need_same_brand_variant_and_size():
    per = {"zito": [hit("zito", "МЛЕКО БИТОЛСКО 1л 2.8%", 1.0), hit("zito", "МЛЕКО БИТОЛСКО 1л 3.2%", 1.0),
                    hit("zito", "МЛЕКО ЗБРЕГОВ 2л 2.8% СО ЧЕП", 2.0), hit("zito", "МЛЕКО АЛПСКО 1л 3.5%", 1.0)],
           "ramstore": [hit("ramstore", "БИТОЛСКО МЛЕКО 2.8% ММ 1Л", 1.0), hit("ramstore", "БИТОЛСКО МЛЕКО 3.2% ММ 1Л", 1.0),
                        hit("ramstore", "ЗБРЕГОВ МЛЕКО 2.8% ММ 1Л", 1.0), hit("ramstore", "МЕГЛЕ МЛЕКО 3.5% MM 1Л", 1.0)],
           "stokomak": [], "kam": []}
    found = {(a["name"], b["name"]): s for a, b, s in pairs_for("mleko-trajno", per)}
    assert found == {("МЛЕКО БИТОЛСКО 1л 2.8%", "БИТОЛСКО МЛЕКО 2.8% ММ 1Л"): 1.0,
                     ("МЛЕКО БИТОЛСКО 1л 3.2%", "БИТОЛСКО МЛЕКО 3.2% ММ 1Л"): 1.0}
