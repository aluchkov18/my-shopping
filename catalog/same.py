"""Ист производ кај повеќе синџири: ист бренд, иста варијанта, иста количина.

    python -m catalog.same            # извештај + catalog/same.csv
    python -m catalog.same 40         # и 40 случајни парови за проверка со око

Ниту еден ценовник нема баркод, па производот се препознава по називот. Се споредуваат само
производи од иста потреба и со иста количина. Од називот се тргаат количината и зборовите што
го кажуваат видот (МЛЕКО, ПАШТЕТА); остануваат брендот и варијантата.

  сигурно   - останатите зборови и броевите (масленост, тип на брашно) се исти кај двата
  веројатно - едниот назив има до два збора повеќе (едниот синџир ја испуштил варијантата)

Секој од двата мора да му е единствен најдобар кандидат на другиот. Цената не учествува во
одлуката: таа е она што сакаме да го споредиме.

Веројатните парови чекаат преглед. Пресудите се чуваат во catalog/review.csv (да или не) и важат
и за следните денови, сè додека називите се исти: потврден пар станува сигурен, одбиен се трга.
"""
from __future__ import annotations

import csv
import os
import random
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations

from .match import CHAINS, LABEL, ROOT, Matcher, amount, load_products, mark_outliers, unit_price
from .needs import NEEDS

LATIN = {"SH": "Ш", "CH": "Ч", "ZH": "Ж", "A": "А", "B": "Б", "C": "К", "D": "Д", "E": "Е", "F": "Ф", "G": "Г", "H": "Х",
         "I": "И", "J": "Ј", "K": "К", "L": "Л", "M": "М", "N": "Н", "O": "О", "P": "П", "Q": "К", "R": "Р", "S": "С",
         "T": "Т", "U": "У", "V": "В", "W": "В", "X": "КС", "Y": "И", "Z": "З"}
_LATIN = re.compile("|".join(sorted(LATIN, key=len, reverse=True)))
_SIZE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:КГР|КГ|KG|ГР|GR|МЛ|ML|ЛИТ|ЛТ|Л|L|Г|G|М|M)(?![А-ЯЃЌЈЉЊЏЅA-Z])"
                   r"|\d+\s*[XХ*]\s*\d+(?:[.,]\d+)?|\d+\s*/\s*\d+|\d+\s*(?:ПАР|КОМ|ПАРЧ|РОЛН|ТАБЛ|КАПС)\w*")
_NUMBER = re.compile(r"(?<![\d.,])\d{1,3}(?:[.,]\d+)?(?![\d.,])")
_WORD = re.compile(r"\d[А-ЯЃЌЈЉЊЏЅ]{2,}|[А-ЯЃЌЈЉЊЏЅ]{3,}")          # и „5КА"
STOP = {"ЗА", "СО", "ОД", "ВО", "НА", "БЕЗ", "ИЛИ", "ММ", "МАСТ", "МАСЛЕНОСТ", "МАСТИ", "КЕСА", "ПАКУВАЊЕ", "ПАКУВАН",
        "ПЕТ", "ЛИМЕНКА", "КУТИЈА", "ТЕГЛА", "ШИШЕ", "ФОЛИЈА", "НОВО", "АКЦИЈА", "ВАКУМ", "ВАКУУМ", "РЕФУС", "СВЕЖ",
        "СВЕЖА", "СВЕЖО", "КЛАСА", "ПАР", "ПАРЧЕ", "ГРАМ", "КГР", "ЛИТ", "ДОЈПАК", "ЧЕП", "КАПАЧЕ", "ТЕТРАПАК",
        # видот на производот, кога правилото на потребата не го фаќа како посебен збор
        "СОК", "ЗАБИ", "ПИЈАЛОК", "ПИЈАЛ", "НАПИТОК", "КОСА", "ВОДА", "ЧОКОЛ", "ЧОКОЛАДО", "ЧОКОЛАДА", "ЕНЕРГЕТСКИ",
        "ЕНЕРГЕТ", "МЕСО", "САЛАМА", "БОНБОНИ", "КАФЕ", "СРЕДСТВО", "СРЕД", "ДЕТЕР", "ДЕТЕРГЕНТ", "ТУШИРАЊЕ", "САДОВИ",
        "ПЕРЕЊЕ", "ПЕРЕЊА", "ПАК", "ПАРЧИЊА", "ПАРЧ", "СМРЗ", "ШАМПОН", "ПАСТА", "САПУН", "ЧАЈ", "ЛЕБ", "СУПА"}


def normalise(text: str) -> str:
    text = _LATIN.sub(lambda m: LATIN[m.group(0)], text.upper())
    return re.sub(r"(.)\1", r"\1", text)                       # БАРИЛЛА и БАРИЛА се исто


def alike(a: str, b: str) -> bool:
    """Ист збор напишан малку поинаку: БИТОЛСКО и БИТОЛСКИ, РИВ и РИВЕ, ЧОКОЛ и ЧОКОЛАДО."""
    if a == b:
        return True
    short, long = sorted((a, b), key=len)
    if len(short) >= 3 and long.startswith(short) and len(long) - len(short) <= 2:
        return True
    return len(short) >= 5 and len(long) - len(short) <= 1 and short[:-1] == long[:len(short) - 1]


def compare(a: frozenset, b: frozenset) -> tuple[int, int, int]:
    """Колку зборови се заеднички, колку има само првиот, колку само вториот."""
    left = list(b)
    shared = 0
    for word in a:
        for other in left:
            if alike(word, other):
                left.remove(other)
                shared += 1
                break
    return shared, len(a) - shared, len(left)


def features(name: str) -> tuple[frozenset, frozenset]:
    """Зборови и броеви од називот, без количината."""
    text = normalise(name)
    bare = _SIZE.sub(" ", text)
    numbers = frozenset(n.replace(",", ".").rstrip("0").rstrip(".") if "." in n or "," in n else n
                        for n in _NUMBER.findall(bare))
    words = frozenset(w for w in _WORD.findall(bare) if w not in STOP)
    return words, numbers


def collect() -> dict[str, dict[str, list[dict]]]:
    """Производите по потреба и синџир, со количина и цена по единица."""
    products = load_products()
    taken, out = {}, {}
    for need in NEEDS:
        matcher, per = Matcher(need), {}
        for chain in CHAINS:
            hits = []
            for p in products[chain]:
                key = (chain, p["name"], p["description"])
                if key in taken or not matcher.match(chain, p):
                    continue
                taken[key] = need.id
                value, trust = unit_price(p, need, chain)
                qty = amount(p["name"], need.unit)
                if qty is None and value and trust == 3 and abs(value - p["price"]) < 0.01 * p["price"]:
                    qty = "на мерење"
                elif qty is None and value and trust == 1:
                    qty = round(p["price"] / value, 3)         # количината ја кажува објавената единечна цена
                words, numbers = features(p["name"])
                hits.append({**p, "chain": chain, "need": need.id, "unit_price": value, "trust": trust,
                             "qty": qty, "words": words, "numbers": numbers})
            per[chain] = hits
        mark_outliers([h for hits in per.values() for h in hits])
        out[need.id] = per
    return out


def verdicts() -> dict[frozenset, bool]:
    path = os.path.join(ROOT, "catalog", "review.csv")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {frozenset({(r["chain_a"], r["name_a"]), (r["chain_b"], r["name_b"])}): r["same"] == "да"
                for r in csv.DictReader(fh)}


def same_qty(a, b) -> bool:
    if a is None or b is None:
        return False
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    return abs(a - b) <= 0.03 * max(a, b)


def pairs_for(need_id: str, per: dict[str, list[dict]]) -> list[tuple[dict, dict, float]]:
    everything = [h for hits in per.values() for h in hits]
    if len(everything) < 2:
        return []
    # Зборовите што го кажуваат видот: оние што ги бара правилото на потребата, и нивните скратеници.
    rule = re.compile(next(n.kw for n in NEEDS if n.id == need_id) or "$^")
    kind = {w for h in everything for w in h["words"] if rule.search(w)}
    kind |= {w for h in everything for w in h["words"] if any(k.startswith(w) for k in kind)}
    # Од нив, „главни" се оние што ги има во четвртина од производите (ПАШТЕТА, ШАМПОН). Останатите
    # (ФАНТА, ПАСТРМКА, ГАУДА) го разликуваат производот и мора да се совпаднат како бренд.
    count = Counter(w for h in everything for w in h["words"] & kind)
    head = {w for w, n in count.items() if n >= 0.25 * len(everything)}
    head |= {w for w in kind if any(k.startswith(w) or w.startswith(k) for k in head)}
    for h in everything:
        h["brand"] = h["words"] - head
        h["kind"] = h["words"] & kind
    # Барем еден заеднички збор мора да е редок во потребата: бренд, не опис како „ПИЛЕШКИ".
    frequency = Counter(w for h in everything for w in h["brand"])
    rare = {w for w, n in frequency.items() if n <= max(4, 0.12 * len(everything))}

    def score(a: dict, b: dict) -> float:
        if not same_qty(a["qty"], b["qty"]) or not a["brand"] or not b["brand"]:
            return 0.0
        shared, only_a, only_b = compare(a["brand"], b["brand"])
        if not shared or (only_a and only_b):
            return 0.0
        related = lambda w, others: any(w.startswith(o) or o.startswith(w) for o in others)
        if any(not related(w, b["kind"]) for w in a["kind"]) and any(not related(w, a["kind"]) for w in b["kind"]):
            return 0.0                                         # ПАСТРМКА наспроти ОСЛИЌ, ГАУДА наспроти ЕДАМЕР
        named = any(alike(w, v) for w in a["brand"] & rare for v in b["brand"])
        if not named and not (a["numbers"] and a["numbers"] == b["numbers"]):
            return 0.0                                         # ниту редок збор, ниту ист број (2.8%, Т-400)
        if a["numbers"] != b["numbers"] and a["numbers"] and b["numbers"]:
            return 0.0
        extra = only_a + only_b + (a["numbers"] != b["numbers"])
        return 1.0 if extra == 0 else 0.8 - 0.1 * extra if extra <= 2 else 0.0

    result = []
    for x, y in combinations(CHAINS, 2):
        table = {(i, j): s for i, a in enumerate(per[x]) for j, b in enumerate(per[y]) if (s := score(a, b)) > 0}
        best_x, best_y = defaultdict(list), defaultdict(list)
        for (i, j), s in table.items():
            best_x[i].append((s, j))
            best_y[j].append((s, i))
        for (i, j), s in table.items():
            first_x, first_y = sorted(best_x[i], reverse=True), sorted(best_y[j], reverse=True)
            alone_x = first_x[0][1] == j and (len(first_x) == 1 or first_x[1][0] < s)
            alone_y = first_y[0][1] == i and (len(first_y) == 1 or first_y[1][0] < s)
            if alone_x and alone_y:
                result.append((per[x][i], per[y][j], s))
    reviewed = verdicts()
    decided = []
    for a, b, s in result:
        verdict = reviewed.get(frozenset({(a["chain"], a["name"]), (b["chain"], b["name"])}))
        if verdict is None:
            decided.append((a, b, s))
        elif verdict:
            decided.append((a, b, 1.0))
    return decided


def clusters(pairs: list[tuple[dict, dict, float]]) -> list[list[dict]]:
    """Паровите се врзуваат во групи; група со два производи од ист синџир се отфрла како несигурна."""
    parent: dict[int, int] = {}
    items: dict[int, dict] = {}

    def find(k: int) -> int:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for a, b, _ in pairs:
        for h in (a, b):
            parent.setdefault(id(h), id(h))
            items[id(h)] = h
        parent[find(id(a))] = find(id(b))
    groups = defaultdict(list)
    for k, h in items.items():
        groups[find(k)].append(h)
    return [g for g in groups.values() if len({h["chain"] for h in g}) == len(g)]


def run() -> tuple[list[list[dict]], list[tuple[dict, dict, float]]]:
    """Групи од сигурни парови, и сите парови (сигурните имаат оцена 1.0)."""
    all_pairs, all_clusters = [], []
    for need_id, per in collect().items():
        found = pairs_for(need_id, per)
        all_pairs.extend(found)
        all_clusters.extend(clusters([x for x in found if x[2] == 1.0]))
    return all_clusters, all_pairs


def main(argv: list[str]) -> int:
    groups, pairs = run()
    sure = [x for x in pairs if x[2] == 1.0]
    maybe = [x for x in pairs if x[2] < 1.0]
    by_size = Counter(len(g) for g in groups)
    print(f"сигурни парови: {len(sure)} | веројатни (за преглед): {len(maybe)} | групи: {len(groups)} "
          f"| по број синџири: {dict(sorted(by_size.items()))}")
    for label, chosen in (("сигурни", sure), ("веројатни", maybe)):
        same = sum(1 for a, b, _ in chosen if a["price"] == b["price"])
        near = sum(1 for a, b, _ in chosen if max(a["price"], b["price"]) <= 1.1 * min(a["price"], b["price"]))
        print(f"  {label}: иста цена {100 * same // max(1, len(chosen))}%, до 10% разлика {100 * near // max(1, len(chosen))}%")
    numbers = [a for a in argv if a.isdigit()]
    if numbers:
        random.seed(7)
        wanted = maybe if "веројатни" in argv else sure
        for a, b, s in random.sample(wanted, min(int(numbers[0]), len(wanted))):
            print(f"  {s:.1f} {a['need'][:14]:14} {LABEL[a['chain']][:1]} {a['price']:>5.0f} {a['name'][:44]:44} | "
                  f"{LABEL[b['chain']][:1]} {b['price']:>5.0f} {b['name'][:44]}")
    folder = os.path.join(ROOT, "catalog")
    with open(os.path.join(folder, "same.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["group", "need", "chain", "name", "price", "unit_price", "promo"])
        ordered = sorted(groups, key=lambda g: (g[0]["need"], min(h["name"] for h in g)))
        for number, g in enumerate(ordered, 1):
            for h in sorted(g, key=lambda h: CHAINS.index(h["chain"])):
                w.writerow([number, h["need"], h["chain"], h["name"], f"{h['price']:g}",
                            "" if h["unit_price"] is None else f"{h['unit_price']:g}", int(h["promo"])])
    with open(os.path.join(folder, "same_review.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["need", "chain_a", "name_a", "price_a", "chain_b", "name_b", "price_b"])
        for a, b, _ in sorted(maybe, key=lambda x: (x[0]["need"], x[0]["name"])):
            w.writerow([a["need"], a["chain"], a["name"], f"{a['price']:g}", b["chain"], b["name"], f"{b['price']:g}"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
