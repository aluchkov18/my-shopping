"""Дневно читање: за секој синџир ги наоѓа продавниците во избраниот град, ги чита
ценовниците и ги запишува во data/. Пад на една продавница не ги запира другите.

    python -m collector.run            # сè од stores.json
    python -m collector.run kam zito   # само наведените синџири
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import kam, proverkanaceni, ramstore, storage
from .common import FIELDS
from .net import Blocked, Polite

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
_DATE = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})")


def discover(net: Polite, spec: dict, city: str) -> list[dict]:
    """Продавниците на еден синџир во градот: [{id, name, target}]."""
    want = city.casefold()
    kind = spec["kind"]
    if kind == "proverkanaceni":
        found = [{"id": i, "name": n, "target": i} for i, n in proverkanaceni.list_stores(net, spec["base"])
                 if want in n.casefold() or i in spec.get("ids", [])]
    elif kind == "kam":
        found = [{"id": s["id"], "name": s["name"], "target": s["url"]} for s in kam.list_stores(net)
                 if s["city"].casefold() == want and s["url"]]
    elif kind == "ramstore":
        found = [{"id": slug, "name": slug, "target": url} for slug, url in ramstore.list_stores(net)
                 if spec["match"] in slug]
    else:
        raise ValueError(f"непознат вид извор: {kind}")
    limit = spec.get("max_stores")
    return found[:limit] if limit else found


def read(net: Polite, spec: dict, store: dict) -> dict:
    kind = spec["kind"]
    if kind == "proverkanaceni":
        return proverkanaceni.read_store(net, spec["base"], store["target"])
    if kind == "kam":
        return kam.read_store(net, store["target"])
    return ramstore.read_store(net, store["target"])


def pricelist_day(text: str | None) -> date | None:
    m = _DATE.search(text or "")
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    except ValueError:
        return None


def spread(per_store: dict[str, list[dict]]) -> dict | None:
    """Колку производи имаат иста цена во сите продавници на синџирот каде што ги има."""
    if len(per_store) < 2:
        return None
    prices = defaultdict(dict)
    for store_id, rows in per_store.items():
        for r in rows:
            prices[(r["name"], r["description"])].setdefault(store_id, r["price"])
    shared = [p for p in prices.values() if len(p) >= 2]
    same = sum(1 for p in shared if len(set(p.values())) == 1)
    return {"stores": len(per_store), "products_in_2plus_stores": len(shared), "same_price_everywhere": same}


def main(argv: list[str]) -> int:
    with open(os.path.join(ROOT, "stores.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    today = datetime.now(ZoneInfo("Europe/Skopje")).date()
    only = set(argv)
    net = Polite(delay=cfg.get("delay_seconds", 1.2))
    results, changes, spreads = [], [], {}

    for chain, spec in cfg["chains"].items():
        if only and chain not in only:
            continue
        try:
            stores = discover(net, spec, cfg["city"])
        except Exception as exc:  # цел синџир недостапен
            results.append({"chain": chain, "store_id": "", "store": "", "status": "blocked" if isinstance(exc, Blocked) else "failed",
                            "rows": 0, "error": f"{type(exc).__name__}: {exc}"[:300]})
            traceback.print_exc()
            continue
        if not stores:
            results.append({"chain": chain, "store_id": "", "store": "", "status": "no_stores", "rows": 0,
                            "error": f"нема продавница во {cfg['city']}"})
            continue

        per_store = {}
        for store in stores:
            started = time.monotonic()
            entry = {"chain": chain, "store_id": store["id"], "store": store["name"], "rows": 0}
            try:
                out = read(net, spec, store)
            except Exception as exc:
                entry.update(status="blocked" if isinstance(exc, Blocked) else "failed",
                             error=f"{type(exc).__name__}: {exc}"[:300])
                traceback.print_exc()
            else:
                rows = storage.to_text_rows(out["rows"])
                day = pricelist_day(out["updated"])
                entry.update(
                    status="ok" if rows else "empty", rows=len(rows), duplicates=storage.count_duplicates(rows),
                    discounts=sum(1 for r in rows if r["discount_price"]),
                    expected=out["expected"], updated=out["updated"],
                    stale=bool(day and day < today),
                )
                if out["expected"] is not None and out["expected"] != len(rows):
                    entry["warning"] = f"страницата вели {out['expected']} артикли, прочитани {len(rows)}"
                if rows:
                    path = os.path.join(DATA, "current", chain, f"{store['id']}.csv")
                    previous = storage.read_csv(path)
                    keep = spec.get("carry_days", 0)          # колку дена се памети ред што денес не е прочитан
                    saved = storage.carry(previous, rows, today, keep) if keep else rows
                    if keep:
                        entry["carried"] = sum(1 for r in saved if r["seen"] != today.isoformat())
                    if previous is not None:
                        for c in storage.diff(previous, saved):
                            changes.append({"chain": chain, "store_id": store["id"], **c})
                    entry["first_read"] = previous is None
                    storage.write_csv(path, saved, storage.SAVED if keep else FIELDS)
                    per_store[store["id"]] = saved
            entry["seconds"] = round(time.monotonic() - started, 1)
            results.append(entry)
            print(f"{chain:9} {store['name'][:28]:28} {entry['status']:8} {entry['rows']:6} реда  {entry['seconds']:6}s"
                  f"  {entry.get('warning') or entry.get('error') or ''}", flush=True)
        s = spread(per_store)
        if s:
            spreads[chain] = s

    stamp = today.isoformat()
    if changes:
        storage.write_csv(os.path.join(DATA, "changes", f"{stamp}.csv"), changes, storage.CHANGE_FIELDS)
    summary = {"date": stamp, "city": cfg["city"], "requests": net.count, "changes": len(changes),
               "price_spread_within_chain": spreads, "stores": results}
    os.makedirs(os.path.join(DATA, "runs"), exist_ok=True)
    with open(os.path.join(DATA, "runs", f"{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)

    ok = [r for r in results if r["status"] == "ok"]
    lines = [f"## Цени {stamp} — {cfg['city']}", "",
             f"Прочитани продавници: {len(ok)} од {len(results)} · редови: {sum(r['rows'] for r in ok)} · "
             f"промени: {len(changes)} · барања: {net.count}", "",
             "| Синџир | Продавница | Состојба | Редови | Попусти | Ажурирано | Забелешка |", "|---|---|---|---|---|---|---|"]
    for r in results:
        note = r.get("warning") or r.get("error") or ("стар ценовник" if r.get("stale") else "")
        lines.append(f"| {r['chain']} | {r['store']} | {r['status']} | {r['rows']} | {r.get('discounts', '')} | {r.get('updated') or ''} | {note} |")
    for chain, s in spreads.items():
        lines.append(f"\n{chain}: {s['same_price_everywhere']} од {s['products_in_2plus_stores']} производи имаат иста цена во сите {s['stores']} продавници.")
    report = "\n".join(lines)
    print("\n" + report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
