"""Проверки на утринската порака, без мрежа."""
from alerts import send
from alerts.digest import compose, watched
from catalog.needs import NEEDS


def move(need, old, new, chain="kam", promo=False):
    return {"need": need, "old": old, "new": new, "chain": chain, "promo": promo, "name": "X", "pct": round(100 * (new / old - 1))}


def test_watch_list_uses_known_needs():
    known = {n.id for n in NEEDS}
    assert len(watched()) >= 20 and all(need in known for need in watched())


def test_message_says_what_moved_for_the_watched_needs():
    moved = [{**move("mleko-trajno", 47, 43, promo=True), "name": "МЛЕКО К"}, move("pivo", 100, 80, "zito"), move("seker", 60, 66, "zito"), move("kola", 50, 48)]
    promos = [{"need": "oriz", "cheapest": True, "since": "2026-10-22", "until": "2026-11-13", "name": "ОРИЗ 1кг", "price": 60, "chain": "ramstore"},
              {"need": "mleko-trajno", "cheapest": True, "since": "2026-11-09", "until": "2026-11-23", "name": "МЛЕКО К", "price": 43, "chain": "kam"},
              {"need": "oriz", "cheapest": False, "until": "2026-11-13", "name": "ОРИЗ ДРУГ", "price": 90, "chain": "zito"},
              {"need": "pivo", "cheapest": True, "until": "2026-11-12", "name": "ПИВО", "price": 40, "chain": "zito"}]
    title, body = compose(moved, promos, ["mleko-trajno", "seker", "oriz"], "2026-11-12")
    assert title == "Велес 12.11.: поевтино 1, поскапо 1"
    assert "• Трајно млеко: 47 → 43 ден. за 1 л, КАМ (акција од 09.11. до 23.11.)" in body and "• Шеќер: 60 → 66 ден. за 1 кг, Жито" in body
    assert "Уште во градот:\n• Пиво" in body and "Кола" not in body            # колата не се следи и падот е мал
    assert "• Ориз 1кг: 60 ден., Рамстор (од 22.10. до 13.11., истекува утре)" in body and "ДРУГ" not in body and "Пиво: 40" not in body


def test_no_news_means_no_message():
    assert compose([move("kola", 50, 48)], [], ["mleko-trajno"], "2026-11-12") is None


def test_without_a_channel_nothing_is_sent(tmp_path, monkeypatch):
    monkeypatch.setattr(send, "LOG", str(tmp_path / "dnevnik.csv"))
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    monkeypatch.setattr(send, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("не смее да прати")))
    assert send.main(["proba"]) == 0
    assert (tmp_path / "dnevnik.csv").read_text(encoding="utf-8").strip().endswith("proba,нема канал")
    monkeypatch.setenv("NTFY_TOPIC", "kanal")
    monkeypatch.setattr(send, "post", lambda topic, title, body, click="": 200)
    send.main(["proba"])
    assert (tmp_path / "dnevnik.csv").read_text(encoding="utf-8").strip().endswith("proba,пратена")
