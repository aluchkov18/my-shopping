"""Проверка дека страницата за GitHub Pages се гради како цел документ, без мрежа."""
import importlib.util
import os


def test_site_is_a_whole_page_with_app_files(tmp_path):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("build_page", os.path.join(here, "prototype", "build.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    page = open(module.site(str(tmp_path), "11.11.2026"), encoding="utf-8").read()
    assert page.startswith("<!doctype html>") and page.rstrip().endswith("</html>")
    head = page.split("</head>")[0]
    assert "<title>My Shopping</title>" in head and 'rel="manifest"' in head and 'content="noindex"' in head and "<main>" not in head
    assert "/*DATA*/" not in page and '"promos":[' in page
    assert {"index.html", "manifest.webmanifest", "sw.js", "icon-192.png", "icon-512.png", "fonts.css", "fonts"} <= set(os.listdir(tmp_path))
    assert 'href="fonts.css"' in head and "fonts.googleapis.com" not in page          # фонтовите се во папката: ист изглед и без мрежа
    for name in ("manrope-cyrillic.woff2", "nunito-sans-cyrillic.woff2"):
        assert name in os.listdir(tmp_path / "fonts") and name in open(tmp_path / "fonts.css", encoding="utf-8").read()
