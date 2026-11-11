"""Прва рака каталог: кои производи од ценовниците спаѓаат во која потреба.

    python -m catalog.match             # извештај + catalog/needs.csv + catalog/matches.csv
    python -m catalog.match kompir med  # детали за наведените потреби
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys
from collections import defaultdict

from .needs import NEEDS, Need

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAINS = ["zito", "stokomak", "kam", "ramstore"]
LABEL = {"zito": "Жито", "stokomak": "Стокомак", "kam": "КАМ", "ramstore": "Рамстор"}

# Знак во описот дека редот е свежо овошје или зеленчук (за синџирите без категории како кај Жито).
FRESH = re.compile(r"СОРТ[АA]|КАЛИБР|ОВОШЈЕ|ЗЕЛЕНЧУК|ПОТЕКЛО|СВЕЖ")

# Свежата стока не е замрзната, сушена или во тегла.
FRESH_NO = re.compile(r"ЗАМР|СМРЗ|СУШЕН|КОНЗЕРВ|ТЕГЛА|\bМИКС\b|САЛАТА ОД")
# Кога свежата стока не се продава на мерење, цената не е за килограм.
BY_PIECE = re.compile(r"ПАРЧЕ|ГЛАВИЦ|СНОПЧЕ|ВРЗОП|ВРСКА|САКСИЈ|ПАКУВАН|МРЕЖ|КЕСА|ТАЦНА")

# Комплети од повеќе различни производи не се споредуваат.
BUNDLE = re.compile(r"^СЕТ\b|\bСЕТ\b|ГРАТИС")

# „ПИТА СО СИРЕЊЕ" не е сирење: зборот не смее да доаѓа веднаш по ваков предлог.
GUARD = re.compile(r"(?:^|[\s/,(])(?:СО|БЕЗ|ОД|ЗА|И|ВКУС(?: НА)?|АРОМА(?: НА)?)\s+$")

_NUM = r"(\d+(?:\.\d+)?)"
_UNIT = r"(КГР|КГ|KG|ГР|GR|МЛ|ML|ЛИТ|ЛТ|Л(?![А-ЯЃЌЈЉЊЏЅA-Z])|L(?![A-ZА-Я])|Г(?![А-ЯЃЌЈЉЊЏЅA-Z])|G(?![A-ZА-Я]))"
_METRE = re.compile(rf"{_NUM}\s*[МM](?![А-ЯЃЌЈЉЊЏЅA-Z])")
_FACTOR = {"КГР": 1, "КГ": 1, "KG": 1, "ЛИТ": 1, "ЛТ": 1, "Л": 1, "L": 1, "ГР": .001, "GR": .001, "Г": .001, "G": .001, "МЛ": .001, "ML": .001}
_MULTI = re.compile(rf"(\d+)\s*П?\s*[XХ*]\s*{_NUM}\s*{_UNIT}")
_MULTI_AFTER = re.compile(rf"{_NUM}\s*{_UNIT}\.?\s*[XХ*]?\s*(\d+)\s*(?:ПАК|/1\b)")   # „8гр 6ПАК", „330мл 6/1"
_SINGLE = re.compile(rf"{_NUM}\s*{_UNIT}")
_COUNT = [re.compile(r"(\d+)\s*/\s*1\b"), re.compile(r"\b1\s*/\s*(\d+)\b"),
          re.compile(r"(?<![-\d])(\d+)\s*(?:ПАРЧ|ПАР\b|ПАР\.|КОМ|БР\b|РОЛН|ТАБЛ|КАПС|ФИЛТ)"),
          re.compile(r"\b[XХ]\s*(\d+)\b")]


def amount(name: str, unit: str) -> float | None:
    """Количина во единицата на потребата: килограми/литри, или број парчиња."""
    t = re.sub(r"(?<=\d),(?=\d)", ".", name.upper())
    if unit == "м":
        m = _METRE.search(t)
        return float(m.group(1)) if m else None
    if unit == "парче":
        for rx in _COUNT:
            m = rx.search(t)
            if m and 0 < int(m.group(1)) <= 200:
                return float(m.group(1))
        return 1.0
    m = _MULTI.search(t)
    if m:
        return int(m.group(1)) * float(m.group(2)) * _FACTOR[m.group(3)]
    m = _MULTI_AFTER.search(t)
    if m and 1 < int(m.group(3)) <= 48:
        return int(m.group(3)) * float(m.group(1)) * _FACTOR[m.group(2)]
    m = _SINGLE.search(t)
    if m:
        return float(m.group(1)) * _FACTOR[m.group(2)]
    return None


_PUB = re.compile(r"^\s*(\d+)?\s*([^\d=:]*?)\s*:?\s*=\s*([\d.,]+)")
_PUB_MASS, _PUB_VOL = {"GR", "ГР", "КГР", "КГ", "KG"}, {"ML", "МЛ", "Л", "L"}
_PUB_PIECE = {"PAR", "ПАР", "P", "PAR.", "ПАРЧЕ"}


def published(text: str) -> tuple[str, float] | None:
    """Единечната цена што ја објавува синџирот, сведена на ден. за 1 кг, 1 л или 1 парче.

    Секој синџир ја пишува поинаку: „100gr = 326.00 ден.", „1КГР = 369.00 ден.", „100 ГР: =4.67ДЕН".
    КАМ пишува и „1 гр = 470.00" и „1 мл = 1127.14", а мисли на килограм и литар.
    """
    m = _PUB.match(text or "")
    if not m:
        return None
    base, label = int(m.group(1) or 1), m.group(2).strip().upper()
    try:
        value = float(m.group(3).replace(",", ".").rstrip("."))
    except ValueError:
        return None
    if value <= 0:
        return None
    if label in _PUB_PIECE:
        return ("парче", value) if base == 1 else None
    if label in {"М", "M"}:
        return ("м", value) if base == 1 else None
    if label not in _PUB_MASS and label not in _PUB_VOL:
        return None
    kind = "кг" if label in _PUB_MASS else "л"
    if label in {"GR", "ГР", "ML", "МЛ"}:
        if base == 1:
            return kind, value
        return (kind, value * 1000 / base) if base >= 50 else None
    return (kind, value / base) if base == 1 else None


def unit_price(p: dict, need: Need, chain: str = "") -> tuple[float | None, int]:
    """Цена по единица на потребата и доверба.

    Два независни извори: количината прочитана од називот и единечната цена што ја објавува синџирот.
      3 = се согласуваат (до 7%), или стоката е на мерење и објавената цена е самата цена
      2 = само од називот (синџирот не објавил единечна цена)
      1 = само објавената (во називот нема количина)
      0 = изворите не се согласуваат; тогаш нема цена, редот оди на проверка
    """
    qty = amount(p["name"], need.unit)
    pub = published(p["unit"])
    measure = need.unit in ("кг", "л", "м")
    if need.fresh and need.unit == "парче":
        return p["price"], 2                                       # снопче, главица: едно парче е едно пакување
    if pub is None:
        same = False
    elif need.unit == "м" or pub[0] == "м":
        same = need.unit == pub[0]
    else:
        same = (pub[0] in ("кг", "л")) if measure else pub[0] == "парче"
    if measure:
        mine = p["price"] / qty if qty else None
    else:
        mine = p["price"] / qty if qty and qty > 1 else None      # qty == 1 значи „не најдов број"
    if same and mine:
        if 0.93 <= mine / pub[1] <= 1.07:
            return round(pub[1], 2), 3
        return None, 0
    if same:
        by_weight = measure and qty is None and abs(pub[1] / p["price"] - 1) < 0.01
        return round(pub[1], 2), 3 if by_weight else 1
    if mine:
        # КАМ не објавува единечна цена кога пакувањето е точно 1 кг или 1 л: таа е самата цена.
        whole = chain == "kam" and measure and not p["unit"] and abs(qty - 1) < 1e-9
        return round(mine, 2), 3 if whole else 2
    if need.fresh and measure and not BY_PIECE.search(p["name"].upper()):
        return p["price"], 2                                       # се продава на мерење: цената е за 1 кг
    if not measure:
        return p["price"], 2
    return None, 2


def load_products() -> dict[str, list[dict]]:
    """Различни производи по синџир, со најниската денешна цена меѓу продавниците."""
    out = {}
    for chain in CHAINS:
        best: dict[tuple, dict] = {}
        for path in glob.glob(os.path.join(ROOT, "data", "current", chain, "*.csv")):
            with open(path, encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    key = (r["name"], r["description"])
                    price = float(r["price"] or 0)
                    if price > 0 and (key not in best or price < best[key]["price"]):
                        best[key] = {"name": r["name"], "description": r["description"], "price": price,
                                     "regular": r["regular_price"], "promo": bool(r["discount_price"]),
                                     "unit": r["unit_price"]}
        out[chain] = list(best.values())
    return out


# Што не е храна, а го содржи зборот (сапун со путер, салама за куче).
NONFOOD = re.compile(r"САПУН|ШАМПОН|\bДЕО\b|ДЕЗОДОРАНС|ЛОСИОН|РЕГЕНЕРАТ|БАЛЗАМ|\bКРЕМА? ЗА (РАЦЕ|ЛИЦЕ|ТЕЛО|СОНЧ)|ЗА ЗАБИ|ТУШ|КУПКА|СВЕЌ"
                     r"|ИГРАЧК|ОСВЕЖУВАЧ|ОМЕКНУВАЧ|ДЕТЕРГЕНТ|КУЧ|МАЧ|МИЛЕНИЦ|ПАРФЕМ|\bМАСКА\b|БОЈА ЗА|ЗА КОСА|ЗА УСНИ|МИЦЕЛАР|ТОНИК|ЗА ЛИЦЕ")
# Готови и тестени производи што само го содржат состојокот (пирошки со кашкавал).
PASTRY = re.compile(r"ПИРОШК|БУРЕК|\bПИЦА|\bПИТА\b|КРОАСАН|КИФЛ|ПОГАЧ|СЕНДВИЧ|КРЕКЕР|ГРИСИН|ПЕРЕЦ|ЗЕМИЧК|ЊОКИ|ТОРТЕЛИН|РАВИОЛ"
                    r"|ПАЛАЧИНК|МЕДАЉОН|НАГЕТ|КРОКЕТ|ЛАЗАЊ|МАНТИ|РОЛНИЦ|ШТРУДЛ")
FOOD = {"Млечни и јајца", "Месо и риба", "Леб и теста", "Брашно, жита и тестенини", "Масло, шеќер и зачини",
        "Конзерви и намази", "Зеленчук и овошје", "Пијалоци", "Слатко и грицки"}
NO_PASTRY = {"Млечни и јајца", "Месо и риба", "Брашно, жита и тестенини", "Масло, шеќер и зачини", "Конзерви и намази"}


class Matcher:
    def __init__(self, need: Need):
        self.need = need
        self.kw = re.compile(need.kw) if need.kw else None
        self.no = re.compile(need.no) if need.no else None
        self.zk = re.compile(need.zk) if need.zk else None
        self.zd = set(need.zd)
        self.must = re.compile(need.must) if need.must else None
        self.own_pastry = bool(PASTRY.search(need.kw))      # потреба што самата е пециво или панирано

    def match(self, chain: str, p: dict) -> bool:
        name, desc = p["name"].upper(), p["description"].upper()
        if self.must and not self.must.search(name):
            return False
        if chain == "zito" and self.zd and p["description"]:      # Жито има и редови без категорија
            if p["description"] not in self.zd or BUNDLE.search(name):
                return False
            if self.zk and not self.zk.search(name):
                return False
            return not (self.no and self.no.search(name))
        text = f"{name} // {desc}"
        if BUNDLE.search(name):
            return False
        if not (self.kw and any(not GUARD.search(text[:m.start()]) for m in self.kw.finditer(text))):
            return False
        if self.no and self.no.search(text):
            return False
        if self.need.group in FOOD and NONFOOD.search(text):
            return False
        if self.need.group in NO_PASTRY and not self.own_pastry and PASTRY.search(name):
            return False
        if self.need.fresh and (FRESH_NO.search(text) or (chain != "zito" and not FRESH.search(desc))):
            return False
        return True


def cheapest(hits: list[dict], need: Need) -> dict | None:
    """Најевтиното по единица меѓу редовите со доверба 2 или 3 што не отскокнуваат од останатите."""
    priced = [h for h in hits if h["unit_price"] and h["trust"] >= 2 and not h.get("outlier")]
    return min(priced, key=lambda h: h["unit_price"]) if priced else None


def mark_outliers(hits: list[dict]) -> None:
    """Цена од еден извор не може да биде двојно пониска од најниската потврдена за истата потреба:
    тоа речиси секогаш е грешка во изворот (цена за едно кесиче, а назив за цела кутија)."""
    confirmed = [h["unit_price"] for h in hits if h["unit_price"] and h["trust"] == 3]
    if not confirmed:
        return
    floor = min(confirmed)
    for h in hits:
        if h["unit_price"] and h["trust"] == 2 and h["unit_price"] < 0.5 * floor:
            h["outlier"] = True


def run() -> tuple[list[dict], list[dict]]:
    products = load_products()
    matchers = [Matcher(n) for n in NEEDS]
    matches, summary = [], []
    taken: dict[tuple, str] = {}
    for m in matchers:
        n = m.need
        row = {"id": n.id, "group": n.group, "name": n.name, "unit": n.unit}
        per_chain = {}
        for chain in CHAINS:
            hits = []
            for p in products[chain]:
                key = (chain, p["name"], p["description"])
                if key in taken or not m.match(chain, p):
                    continue
                taken[key] = n.id
                value, trust = unit_price(p, n, chain)
                hits.append({**p, "chain": chain, "need": n.id, "unit_price": value, "trust": trust})
            matches.extend(hits)
            per_chain[chain] = hits
        mark_outliers([h for hits in per_chain.values() for h in hits])
        for chain, hits in per_chain.items():
            best = cheapest(hits, n)
            row[chain] = len(hits)
            row[f"{chain}_min"] = best["unit_price"] if best else None
            row[f"{chain}_ex"] = best["name"] if best else ""
        summary.append(row)
    return summary, matches


def main(argv: list[str]) -> int:
    summary, matches = run()
    argv = [a for a in argv if not a.startswith("-")]
    if argv:
        for need_id in argv:
            print(f"\n=== {need_id}")
            for chain in CHAINS:
                hits = sorted((m for m in matches if m["need"] == need_id and m["chain"] == chain),
                              key=lambda h: (h["unit_price"] is None, h["unit_price"] or 0))
                print(f"-- {LABEL[chain]} ({len(hits)})")
                for h in hits[:14]:
                    print(f"   {h['unit_price']!s:>8} {h['trust']}{'!' if h.get('outlier') else ' '}{h['price']:>6.0f}  {h['name']}  //  {h['description'][:34]}  [{h['unit']}]")
        return 0

    print(f"{'потреба':22} {'Ж':>4} {'С':>4} {'К':>4} {'Р':>4} | најевтино по единица: Жито / Стокомак / КАМ / Рамстор")
    for r in summary:
        mins = " / ".join(f"{r[c + '_min']:.4g}" if r[c + "_min"] else "-" for c in CHAINS)
        print(f"{r['id']:22} {r['zito']:4} {r['stokomak']:4} {r['kam']:4} {r['ramstore']:4} | {mins}")
        if "-v" in sys.argv:
            for c in CHAINS:
                if r[c + "_ex"]:
                    print(f"{'':26}{LABEL[c][:1]} {r[c + '_min']:>8.4g}  {r[c + '_ex']}")
    total = {c: sum(r[c] for r in summary) for c in CHAINS}
    print("вкупно споени:", total, "| потреби:", len(summary),
          "| без ниту еден производ:", [r["id"] for r in summary if not any(r[c] for c in CHAINS)])

    out = os.path.join(ROOT, "catalog")
    with open(os.path.join(out, "needs.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["id", "group", "name", "unit"] + CHAINS + [f"{c}_min" for c in CHAINS] + [f"{c}_example" for c in CHAINS])
        for r in summary:
            w.writerow([r["id"], r["group"], r["name"], r["unit"]] + [r[c] for c in CHAINS]
                       + ["" if r[f"{c}_min"] is None else f"{r[f'{c}_min']:g}" for c in CHAINS]
                       + [r[f"{c}_ex"] for c in CHAINS])
    with open(os.path.join(out, "matches.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["need", "chain", "name", "description", "price", "unit_price", "trust", "promo"])
        for m in sorted(matches, key=lambda m: (m["need"], m["chain"], m["name"])):
            w.writerow([m["need"], m["chain"], m["name"], m["description"], f"{m['price']:g}",
                        "" if m["unit_price"] is None else f"{m['unit_price']:g}",
                        -1 if m.get("outlier") else m["trust"], int(m["promo"])])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
