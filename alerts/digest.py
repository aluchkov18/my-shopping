"""Утринска порака за телефон: што се смени кај она што се следи и кои акции истекуваат.

    python -m alerts.digest          # ја печати пораката за последните две дневни слики

Пораката се составува од две дневни слики (catalog/history) и од акциите. Ако нема што да се каже,
порака нема: телефонот не ѕвони без причина.
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

from catalog.history import changes, days, load
from catalog.match import LABEL, ROOT
from catalog.needs import NEEDS

LIMIT = 6       # најмногу редови во еден дел, за пораката да се прочита на еден поглед
BIG = -10       # поевтинување во проценти што вреди да се спомене и ако потребата не се следи


def watched() -> list[str]:
    with open(os.path.join(ROOT, "alerts", "sledam.txt"), encoding="utf-8") as fh:
        return [line.split("#")[0].strip() for line in fh if line.split("#")[0].strip()]


def money(value: float) -> str:
    return f"{value:.0f}" if value >= 100 or abs(value - round(value)) < 0.05 else f"{value:.1f}".replace(".", ",")


def compose(moved: list[dict], promos: list[dict], watch: list[str], day: str) -> tuple[str, str] | None:
    """(наслов, текст) или None. moved се промените од catalog.history.changes, promos од catalog.promos.build."""
    needs, chosen = {n.id: n for n in NEEDS}, set(watch)

    def row(c: dict) -> str:
        need = needs[c["need"]]
        return (f"• {need.name}: {money(c['old'])} → {money(c['new'])} ден. за 1 {need.unit}, {LABEL[c['chain']]}"
                + (" (акција)" if c["promo"] else ""))

    known = [c for c in moved if c["need"] in needs and c.get("sure", True)]
    down = [c for c in known if c["need"] in chosen and c["pct"] < 0]
    up = sorted((c for c in known if c["need"] in chosen and c["pct"] > 0), key=lambda c: -c["pct"])
    city = [c for c in known if c["need"] not in chosen and c["pct"] <= BIG][:3]
    tomorrow = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    ending = [p for p in promos if p["need"] in chosen and p["cheapest"] and p["until"] in (day, tomorrow)][:3]

    parts = []
    if down:
        parts.append("Поевтино:\n" + "\n".join(row(c) for c in down[:LIMIT]))
    if up:
        parts.append("Поскапо:\n" + "\n".join(row(c) for c in up[:LIMIT]))
    if city:
        parts.append("Уште во градот:\n" + "\n".join(row(c) for c in city))
    if ending:
        parts.append("Акцијата истекува:\n" + "\n".join(
            f"• {p['name'].capitalize()}: {money(p['price'])} ден., {LABEL[p['chain']]} ({'денес' if p['until'] == day else 'утре'})"
            for p in ending))
    if not parts:
        return None
    counts = ", ".join(text for text in (f"поевтино {len(down)}" if down else "", f"поскапо {len(up)}" if up else "") if text)
    return f"Велес {day[8:]}.{day[5:7]}.: {counts or 'вести од маркетите'}", "\n".join(parts)


def today() -> tuple[str, str] | None:
    known = days()
    if len(known) < 2:
        return None
    from catalog.promos import build
    return compose(changes(load(known[-2]), load(known[-1])), build(), watched(), known[-1])


if __name__ == "__main__":
    message = today()
    print("\n".join(message) if message else "нема вести")
    sys.exit(0)
