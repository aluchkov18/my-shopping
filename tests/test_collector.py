"""Проверки без мрежа: читање броеви, трите формати на ценовник, споредба на два дена."""
from datetime import date

from collector import kam, proverkanaceni, ramstore, storage
from collector.common import parse_number, parse_pct, split_discount
from collector.run import pricelist_day, spread


def test_numbers():
    assert parse_number("85 ден.") == 85
    assert parse_number("145.00") == 145
    assert parse_number("110ден.") == 110
    assert parse_number("1.099,00 ден.") == 1099
    assert parse_number("1,099.50") == 1099.5
    assert parse_number("1.099") == 1099
    assert parse_number("8.5") == 8.5
    assert parse_number("12,5") == 12.5
    assert parse_number("1 249 ден.") == 1249
    assert parse_number("") is None and parse_number("нема") is None
    assert parse_pct("Попуст: 15%") == 15 and parse_pct("-11,48 %") == 11.48
    assert split_discount("110ден. Попуст: 15%") == (110, 15)
    assert split_discount("185.00 -11.48%") == (185, 11.48)
    assert split_discount("  ") == (None, None)


PLATFORM = """
<html><body>
<form><select name="org"><option value="">Одберете маркет</option>
<option value="2">2 Трговски - Велес</option><option value="8">8 Бутел1 - Скопје</option></select></form>
<p>Датум и време на последно ажурирање на цените: 11/11/2026 20:36</p>
<table><thead><tr><th>Назив</th></tr></thead><tbody>
<tr><td>МЛЕКО ПРОБА 1л 2.8%</td><td> 69 ден. </td><td>100ml = 6.90 ден.</td><td>Млеко ухт</td><td>Да</td><td>69 ден.</td></tr>
<tr><td>МЛЕКО ПРОБА 1л 1.5%</td><td>49 ден.</td><td>100ml = 4.90 ден.</td><td>Млеко ухт</td><td>Да</td><td>79 ден.</td>
    <td>49 ден.<br>Попуст:38%</td><td>промотивна цена</td><td>11.11.2026 до<br>24.11.2026</td></tr>
<tr><td colspan="9">Нема податоци за прикажување</td></tr>
</tbody></table>
<div>Прикажи 1 - 2 од 2 артикли</div>
</body></html>
"""


def test_platform_page():
    assert proverkanaceni.parse_stores(PLATFORM) == [("2", "2 Трговски - Велес"), ("8", "8 Бутел1 - Скопје")]
    rows, total, updated = proverkanaceni.parse_page(PLATFORM)
    assert total == 2 and updated == "11/11/2026 20:36"
    assert [r["name"] for r in rows] == ["МЛЕКО ПРОБА 1л 2.8%", "МЛЕКО ПРОБА 1л 1.5%"]
    plain, promo = rows
    assert plain["price"] == 69 and plain["regular_price"] == 69 and plain["discount_price"] is None
    assert promo["price"] == 49 and promo["regular_price"] == 79
    assert promo["discount_price"] == 49 and promo["discount_pct"] == 38
    assert promo["promo_type"] == "промотивна цена" and promo["promo_period"] == "11.11.2026 до 24.11.2026"


RAMSTORE = """
<html><body>
<button onclick="location.href='https://ramstore.com.mk/marketi/ramstor-veles/';">Види цени</button>
<button onclick="location.href='https://ramstore.com.mk/marketi/ramstore-vardar/';">Види цени</button>
<button onclick="location.href='https://ramstore.com.mk/marketi/ramstor-veles/';">Види цени</button>
<h3>Датум и време на последно ажурирање на цените: 11.11.2026 4:00AM</h3>
<table id="productsTable"><thead><tr>
<th>НАЗИВ НА ПРОИЗВОД</th><th>ПРОДАЖНА ЦЕНА</th><th>ЕДИНЕЧНА ЦЕНА</th><th>ОПИС НА ПРОИЗВОД</th>
<th>ДОСТАПНОСТ НА ПРОИЗВОД</th><th>РЕДОВНА ЦЕНА</th><th>ЦЕНА СО ПОПУСТ</th><th>ПОЕНИ</th>
<th>ТИП НА АКЦИЈА</th><th>ВРЕМЕТРАЕЊЕ НА АКЦИЈА</th></tr></thead><tbody>
<tr><td>ОРИЗ ПРОБА 900 ГР </td><td>145.00</td><td><span>100 ГР: =16.11ДЕН</span></td><td>ОРИЗ </td><td>ДА</td>
    <td> </td><td> </td><td></td><td></td><td> </td></tr>
<tr><td>ЧОКОЛАДО ПРОБА 150ГР </td><td>185.00</td><td><span>100 ГР: =123.33ДЕН</span></td><td>ЧОКОЛАДО </td><td>ДА</td>
    <td> 209.00 </td><td> 185.00<br>-11.48% </td><td>40</td><td>ЛОЈАЛНОСТ</td><td> 01.11.2026 - 21.11.2026 </td></tr>
</tbody></table></body></html>
"""


def test_ramstore():
    assert ramstore.parse_stores(RAMSTORE) == [
        ("ramstor-veles", "https://ramstore.com.mk/marketi/ramstor-veles/"),
        ("ramstore-vardar", "https://ramstore.com.mk/marketi/ramstore-vardar/"),
    ]
    rows, updated = ramstore.parse_store(RAMSTORE)
    assert updated == "11.11.2026 4:00AM" and len(rows) == 2
    assert rows[0]["name"] == "ОРИЗ ПРОБА 900 ГР" and rows[0]["price"] == 145 and rows[0]["regular_price"] is None
    assert rows[1]["discount_price"] == 185 and rows[1]["discount_pct"] == 11.48
    assert rows[1]["regular_price"] == 209 and rows[1]["promo_type"] == "ЛОЈАЛНОСТ"


def test_kam_shops():
    payload = [
        {"Id": 40, "Name": "Велес", "City": "Велес", "ShopFiles": [{"RelativePath": "2026/11/11/40.pdf"}]},
        {"Id": 95, "Name": "Аеродром - 4", "City": "Скопје", "ShopFiles": []},
    ]
    shops = kam.parse_shops(payload)
    assert shops[0] == {"id": "40", "name": "Велес", "city": "Велес", "url": "https://kam.mk/2026/11/11/40.pdf"}
    assert shops[1]["url"] is None


def test_storage_roundtrip_and_diff(tmp_path):
    day1 = [
        {"name": "Б", "description": "x", "price": 50.0, "regular_price": 50.0},
        {"name": "А", "description": "x", "price": 101.0, "regular_price": 101.0},
        {"name": "В", "description": "x", "price": 30.0, "regular_price": 30.0},
    ]
    rows1 = storage.to_text_rows(day1)
    assert [r["name"] for r in rows1] == ["А", "Б", "В"] and rows1[0]["price"] == "101"
    path = str(tmp_path / "current" / "zito" / "2.csv")
    storage.write_csv(path, rows1, list(rows1[0]))
    assert storage.read_csv(path) == rows1
    assert storage.diff(rows1, rows1) == []

    day2 = [
        {"name": "А", "description": "x", "price": 89.0, "regular_price": 101.0, "discount_price": 89.0, "promo_type": "акција"},
        {"name": "Б", "description": "x", "price": 50.0, "regular_price": 50.0},
        {"name": "Г", "description": "x", "price": 12.5, "regular_price": 12.5},
    ]
    changes = {c["name"]: c for c in storage.diff(rows1, storage.to_text_rows(day2))}
    assert set(changes) == {"А", "В", "Г"}
    assert changes["А"]["kind"] == "changed" and changes["А"]["old_price"] == "101" and changes["А"]["new_price"] == "89"
    assert changes["В"]["kind"] == "removed" and changes["Г"]["kind"] == "new" and changes["Г"]["new_price"] == "12.5"
    assert storage.count_duplicates(rows1 + rows1[:1]) == 1


def test_dates_and_spread():
    assert pricelist_day("11/11/2026 20:36") == date(2026, 11, 11)
    assert pricelist_day("02.10.2026 5:49:36AM") == date(2026, 10, 2)
    assert pricelist_day(None) is None and pricelist_day("нема датум") is None
    a = [{"name": "А", "description": "", "price": "10"}, {"name": "Б", "description": "", "price": "20"}]
    b = [{"name": "А", "description": "", "price": "10"}, {"name": "Б", "description": "", "price": "22"}]
    assert spread({"1": a}) is None
    assert spread({"1": a, "2": b}) == {"stores": 2, "products_in_2plus_stores": 2, "same_price_everywhere": 1}


def test_diff_ignores_repeated_rows_and_shows_the_variant_that_moved():
    row = lambda price, promo="": {"name": "МЛЕКО 1л", "description": "Млеко", "price": price, "regular_price": "60", "discount_price": "", "promo_type": promo}
    assert storage.diff([row("60"), row("60")], [row("60")]) == []                       # истиот ред повторен: не е промена
    moved = storage.diff([row("50"), row("60")], [row("50"), row("55", "промотивна цена")])
    assert len(moved) == 1 and moved[0]["kind"] == "changed"
    assert (moved[0]["old_price"], moved[0]["new_price"], moved[0]["new_promo"]) == ("60", "55", "промотивна цена")
