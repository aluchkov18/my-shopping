"""КАМ: список продавници како JSON, ценовник како текстуален PDF по продавница."""
from __future__ import annotations

import io
import re

import pdfplumber

from .common import clean, make_row, parse_number, split_discount

BASE = "https://kam.mk/"
PAGE_URL = BASE + "ceni-vo-marketi.nspx"
SHOPS_URL = BASE + "ShopsWeb/LoadShopList"

_UPDATED = re.compile(r"ажурирање на цените:\s*([0-9.]+\s+[0-9:]+\s*(?:AM|PM)?)")


def parse_shops(payload) -> list[dict]:
    """Од одговорот на LoadShopList: ид, име, град и адреса на PDF-от."""
    items = payload if isinstance(payload, list) else (payload.get("Data") or payload.get("data") or [])
    shops = []
    for item in items:
        files = item.get("ShopFiles") or []
        path = clean(files[0].get("RelativePath")) if files else ""
        shops.append({
            "id": str(item.get("Id")), "name": clean(item.get("Name")),
            "city": clean(item.get("City")), "url": BASE + path.lstrip("/") if path else None,
        })
    return shops


def parse_pdf(data: bytes) -> tuple[list[dict], str | None]:
    rows: list[dict] = []
    updated = None
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for number, page in enumerate(pdf.pages):
            if number == 0:
                m = _UPDATED.search(page.extract_text() or "")
                updated = clean(m.group(1)) if m else None
            for table in page.extract_tables():
                for cells in table:
                    if not cells or len(cells) < 6:
                        continue
                    cells = list(cells) + [None] * (9 - len(cells))
                    price = parse_number(cells[1])
                    name = clean(cells[0])
                    if price is None or not name:
                        continue  # заглавие или празен ред
                    row = make_row(
                        name=name, price=price, unit_price=cells[2], description=cells[3],
                        available=cells[4], regular_price=parse_number(cells[5]),
                        promo_type=cells[7], promo_period=cells[8],
                    )
                    row["discount_price"], row["discount_pct"] = split_discount(cells[6])
                    rows.append(row)
    return rows, updated


def list_stores(net) -> list[dict]:
    resp = net.post(SHOPS_URL, json={}, headers={"Referer": PAGE_URL})
    return parse_shops(resp.json())


def read_store(net, url: str) -> dict:
    resp = net.get(url)
    if not resp.content.startswith(b"%PDF"):
        raise ValueError(f"{url}: одговорот не е PDF")
    rows, updated = parse_pdf(resp.content)
    return {"rows": rows, "expected": None, "updated": updated}
