"""Платформата proverkanaceni.mk: Жито маркети, Стокомак (и други на истата услуга).

Една страница дава најмногу 100 реда: ?org=<продавница>&page=<n>&perPage=100&search=
Ред без попуст има 6 ќелии, ред со попуст 9.
"""
from __future__ import annotations

import re

import lxml.html

from .common import cell_text, clean, make_row, parse_number, split_discount

PER_PAGE = 100
MAX_PAGES = 150

_TOTAL = re.compile(r"од\s+(\d+)\s+артикли")
_UPDATED = re.compile(r"ажурирање на цените:\s*([0-9./]+\s+[0-9:]+)")


def parse_stores(html: str) -> list[tuple[str, str]]:
    doc = lxml.html.fromstring(html)
    stores = []
    for opt in doc.xpath('//select[@name="org"]/option'):
        value = (opt.get("value") or "").strip()
        if value:
            stores.append((value, clean(opt.text_content())))
    return stores


def parse_page(html: str) -> tuple[list[dict], int | None, str | None]:
    """Враќа (редови, вкупно артикли според страницата, текст за последно ажурирање)."""
    doc = lxml.html.fromstring(html)
    rows = []
    for tr in doc.xpath("//table//tbody/tr"):
        cells = [cell_text(td) for td in tr.xpath("./td")]
        if len(cells) < 6 or not cells[0]:
            continue  # „Нема податоци за прикажување" е една ќелија
        row = make_row(
            name=cells[0], price=parse_number(cells[1]), unit_price=cells[2],
            description=cells[3], available=cells[4], regular_price=parse_number(cells[5]),
        )
        if len(cells) >= 9:
            row["discount_price"], row["discount_pct"] = split_discount(cells[6])
            row["promo_type"], row["promo_period"] = cells[7], cells[8]
        rows.append(row)
    text = doc.text_content()
    total = _TOTAL.search(text)
    updated = _UPDATED.search(text)
    return rows, int(total.group(1)) if total else None, clean(updated.group(1)) if updated else None


def list_stores(net, base: str) -> list[tuple[str, str]]:
    resp = net.get(base)
    resp.encoding = "utf-8"
    return parse_stores(resp.text)


def read_store(net, base: str, org: str) -> dict:
    rows: list[dict] = []
    total = updated = None
    for page in range(1, MAX_PAGES + 1):
        resp = net.get(base, params={"org": org, "page": page, "perPage": PER_PAGE, "search": ""})
        resp.encoding = "utf-8"
        page_rows, page_total, page_updated = parse_page(resp.text)
        total = page_total if page_total is not None else total
        updated = page_updated or updated
        rows.extend(page_rows)
        if len(page_rows) < PER_PAGE or (total is not None and len(rows) >= total):
            break
    return {"rows": rows, "expected": total, "updated": updated}
