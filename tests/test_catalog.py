"""Проверки на каталогот без мрежа: читање количина, објавена единечна цена и доверба."""
from catalog.match import Matcher, amount, published, unit_price
from catalog.needs import NEEDS

BY_ID = {n.id: n for n in NEEDS}


def product(name, price, unit="", description=""):
    return {"name": name, "description": description, "price": price, "unit": unit}


def test_amount_reads_sizes_and_multipacks():
    assert amount("МЛЕКО БИТОЛСКО 1л 2.8%", "л") == 1
    assert amount("ШЕЌЕР ЖИТО 900гр ПАКУВАН", "кг") == 0.9
    assert amount("ОРИЗ БАСМАТИ 4*125гр", "кг") == 0.5
    assert amount("ВАНИЛИН ШЕЌЕР ПОДРАВКА 8гр 6ПАК.", "кг") == 0.048
    assert amount("АЛУМИНИУМСКА ФОЛИЈА 5КА 30м", "м") == 30
    assert amount("ЈАЈЦА ГОЛДЕН М 30/1", "парче") == 30
    assert amount("ЕКОНОМИЧНО ПАКУВАЊЕ ЈАЈЦА Л 1/10", "парче") == 10
    assert amount("СВЕЖ КОМПИР А", "кг") is None


def test_published_normalises_each_chain_format():
    assert published("100gr = 326.00 ден.") == ("кг", 3260.0)
    assert published("1КГР = 369.00 ден.") == ("кг", 369.0)
    assert published("100 МЛ: =10.1ДЕН") == ("л", 101.0)
    assert published("1 гр = 156.00 ден.") == ("кг", 156.0)        # КАМ мисли на килограм
    assert published("1par = 7.50 ден.") == ("парче", 7.5)
    assert published("") is None


def test_trust_levels():
    oil = BY_ID["maslo-soncogledovo"]
    assert unit_price(product("БРИЛИЈАНТ СОНЧОГЛЕДОВО МАСЛО 1Л", 101, "100 МЛ: =10.1ДЕН"), oil) == (101.0, 3)
    assert unit_price(product("ЈОГУРТ ДУКАТ 1кг 2.8%мм", 85, "100gr = 25.76 ден."), BY_ID["jogurt"]) == (None, 0)
    assert unit_price(product("ПРАШОК АРИЕЛ 1.3кг", 549), BY_ID["prasok-perenje"])[1] == 2
    cheese = BY_ID["kaskaval"]
    assert unit_price(product("КАШКАВАЛ КРАВЈИ БОН АПЕТИТ РЕФУС", 435, "100gr = 43.50 ден."), cheese) == (435.0, 3)
    assert unit_price(product("БРАШНО ТИП 500 1 КГ КАМКО", 25), BY_ID["brasno-belo"], "kam") == (25.0, 3)


def test_ingredient_is_not_the_product():
    cheese = Matcher(BY_ID["kaskaval"])
    assert cheese.match("kam", product("КАШКАВАЛ МЕШАН БЕЛА ФАРМ 1КГ", 519))
    assert not cheese.match("kam", product("ПИРОШКИ КАШКАВАЛ ГУСТО 400ГР", 92))
    assert not cheese.match("stokomak", product("ВИРШЛА ПИЛЕШКА СО КАШКАВАЛ 200гр", 43))
    assert not Matcher(BY_ID["puter"]).match("kam", product("САПУН ДОВЕ 90ГР ПУТЕР", 53))
    oil = Matcher(BY_ID["maslo-soncogledovo"])
    assert oil.match("ramstore", product("БРИЛИЈАНТ СОНЧОГЛЕДОВО МАСЛО 1Л", 101, description="СОНЧОГЛЕДОВО МАСЛО"))
    assert not oil.match("ramstore", product("ТУНА ВО СОНЧОГЛЕДОВО МАСЛО 170Г", 65))


def test_need_ids_are_unique():
    ids = [n.id for n in NEEDS]
    assert len(ids) == len(set(ids))
    assert all(n.unit in ("кг", "л", "м", "парче") for n in NEEDS)
