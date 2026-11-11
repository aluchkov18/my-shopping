"""Рамстор: една страница по продавница, со целиот асортиман во една табела."""
from __future__ import annotations

import re

import lxml.html

from .common import cell_text, clean, make_row, parse_number, split_discount

STORES_URL = "https://ramstore.com.mk/marketi/"

_STORE_LINK = re.compile(r"location\.href='(https://ramstore\.com\.mk/marketi/([^/']+)/?)'")
_UPDATED = re.compile(r"ажурирање на цените:\s*([0-9.]+\s+[0-9:]+\s*(?:AM|PM)?)")

# Заглавие во табелата -> наша колона. Се чита по име, не по редослед.
HEADERS = {
    "НАЗИВ НА ПРОИЗВОД": "name", "ПРОДАЖНА ЦЕНА": "price", "ЕДИНЕЧНА ЦЕНА": "unit_price",
    "ОПИС НА ПРОИЗВОД": "description", "ДОСТАПНОСТ НА ПРОИЗВОД": "available",
    "РЕДОВНА ЦЕНА": "regular_price", "ЦЕНА СО ПОПУСТ": "discount", "ТИП НА АКЦИЈА": "promo_type",
    "ВРЕМЕТРАЕЊЕ НА АКЦИЈА": "promo_period",
}


def parse_stores(html: str) -> list[tuple[str, str]]:
    """(slug, адреса) за секоја продавница, без повторувања."""
    seen: dict[str, str] = {}
    for url, slug in _STORE_LINK.findall(html):
        seen.setdefault(slug, url if url.endswith("/") else url + "/")
    return list(seen.items())


def parse_store(html: str) -> tuple[list[dict], str | None]:
    doc = lxml.html.fromstring(html)
    tables = doc.xpath('//table[@id="productsTable"]') or doc.xpath("//table[.//th]")
    if not tables:
        raise ValueError("Рамстор: не ја најдов табелата со цени")
    table = tables[0]
    index = {}
    for i, th in enumerate(table.xpath(".//thead//th")):
        field = HEADERS.get(clean(th.text_content()).upper())
        if field:
            index[field] = i
    if "name" not in index or "price" not in index:
        raise ValueError("Рамстор: заглавието на табелата е сменето")
    rows = []
    for tr in table.xpath(".//tbody/tr"):
        cells = [cell_text(td) for td in tr.xpath("./td")]
        get = lambda f: cells[index[f]] if f in index and index[f] < len(cells) else ""
        price = parse_number(get("price"))
        if not get("name") or price is None:
            continue
        row = make_row(
            name=get("name"), price=price, unit_price=get("unit_price"), description=get("description"),
            available=get("available"), regular_price=parse_number(get("regular_price")),
            promo_type=get("promo_type"), promo_period=get("promo_period"),
        )
        row["discount_price"], row["discount_pct"] = split_discount(get("discount"))
        rows.append(row)
    m = _UPDATED.search(doc.text_content())
    return rows, clean(m.group(1)) if m else None


def list_stores(net) -> list[tuple[str, str]]:
    resp = net.get(STORES_URL)
    resp.encoding = "utf-8"
    return parse_stores(resp.text)


def read_store(net, url: str) -> dict:
    resp = net.get(url)
    resp.encoding = "utf-8"
    rows, updated = parse_store(resp.text)
    return {"rows": rows, "expected": None, "updated": updated}
