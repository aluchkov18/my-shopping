"""Заеднички делови: чистење текст, читање броеви, облик на еден ред од ценовник."""
from __future__ import annotations

import re

# Колони во секоја зачувана датотека, по овој редослед.
FIELDS = [
    "name", "description", "price", "regular_price", "discount_price",
    "discount_pct", "promo_type", "promo_period", "unit_price", "available",
]

_NUM = re.compile(r"\d[\d.,\s]*")
_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


def clean(text: str | None) -> str:
    """Сите празнини (и нови редови) во едно празно место."""
    return re.sub(r"\s+", " ", text or "").strip()


def cell_text(element) -> str:
    """Текстот на една ќелија; <br> и вгнездени тагови стануваат празно место."""
    return clean(" ".join(element.itertext()))


def parse_number(text: str | None) -> float | None:
    """Прв број во текстот: '85 ден.' -> 85.0, '145.00' -> 145.0, '1.099,00' -> 1099.0."""
    m = _NUM.search(text or "")
    if not m:
        return None
    s = re.sub(r"\s", "", m.group(0)).rstrip(".,")
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        s = s.replace(thou, "").replace(dec, ".")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = f"{head.replace(',', '')}.{tail}" if len(tail) in (1, 2) else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "." in s:
        head, _, tail = s.partition(".")
        if len(tail) == 3:  # 1.099 = илјада деведесет и девет
            s = head + tail
    try:
        return float(s)
    except ValueError:
        return None


def parse_pct(text: str | None) -> float | None:
    m = _PCT.search(text or "")
    return float(m.group(1).replace(",", ".")) if m else None


def make_row(**kw) -> dict:
    """Ред со сите колони; што недостига останува празно."""
    row = {f: kw.get(f) for f in FIELDS}
    for f in ("name", "description", "promo_type", "promo_period", "unit_price", "available"):
        row[f] = clean(row[f])
    return row


def split_discount(cell: str | None) -> tuple[float | None, float | None]:
    """'110ден. Попуст: 15%' или '185.00 -11.48%' -> (цена со попуст, процент)."""
    cell = clean(cell)
    if not cell:
        return None, None
    return parse_number(cell), parse_pct(cell)
