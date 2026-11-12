"""Ја праќа утринската порака на телефон преку ntfy.

    python -m alerts.send            # порака за последните две дневни слики; ништо ако нема вести
    python -m alerts.send proba      # пробна порака

Каналот е во околината (NTFY_TOPIC), не во репото: кој го знае името на каналот, може да чита и да праќа на него.
Што се случило се запишува во alerts/dnevnik.csv, без името на каналот.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

from catalog.match import ROOT

from .digest import today

LOG = os.path.join(ROOT, "alerts", "dnevnik.csv")
SERVER = "https://ntfy.sh/"
PAGE = "https://aluchkov18.github.io/my-shopping/"       # допир на пораката ја отвора страницата
TRIAL = ("My Shopping: проба", "Известувањата работат. По утринското читање на цените тука стигнува што поевтинило и што поскапело.")


def post(topic: str, title: str, body: str, click: str = "") -> int:
    payload = {"topic": topic, "title": title, "message": body[:1800], "tags": ["shopping_cart"]}
    if click:
        payload["click"] = click
    request = urllib.request.Request(SERVER, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status


def record(kind: str, result: str) -> None:
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/Skopje"))
    except Exception:
        now = datetime.now(timezone.utc)
    fresh = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if fresh:
            w.writerow(["time", "kind", "result"])
        w.writerow([now.strftime("%Y-%m-%d %H:%M"), kind, result])
    print(kind + ":", result)


def main(argv: list[str]) -> int:
    kind = "proba" if argv[:1] == ["proba"] else "dnevna"
    message = TRIAL if kind == "proba" else today()
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not message:
        record(kind, "нема вести")
    elif not topic:
        print("\n".join(message))
        record(kind, "нема канал")
    else:
        try:
            status = post(topic, message[0], message[1], os.environ.get("NTFY_CLICK", "").strip() or PAGE)
            record(kind, "пратена" if status == 200 else f"одговор {status}")
        except Exception as error:                      # пораката не смее да го сруши дневното читање
            record(kind, "грешка: " + type(error).__name__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
