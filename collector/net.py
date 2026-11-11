"""Учтив HTTP клиент: се претставува, почитува robots.txt, чека меѓу барања, повторува при пад."""
from __future__ import annotations

import time
import urllib.robotparser
from urllib.parse import urlsplit

import requests

USER_AGENT = "MyShopping-collector/0.1 (daily reader of public price lists)"


class Blocked(Exception):
    """Изворот не дозволува читање (robots.txt или 403)."""


class Polite:
    def __init__(self, delay: float = 1.2, timeout: int = 120, retries: int = 3):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "mk,en;q=0.5"})
        self.delay, self.timeout, self.retries = delay, timeout, retries
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.count = 0

    # -- robots.txt -----------------------------------------------------
    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        root = f"{parts.scheme}://{parts.netloc}"
        if root not in self._robots:
            parser = None
            try:
                self._wait(parts.netloc)
                resp = self.session.get(f"{root}/robots.txt", timeout=30)
                if resp.status_code == 200:
                    parser = urllib.robotparser.RobotFileParser()
                    parser.parse(resp.text.splitlines())
            except requests.RequestException:
                parser = None  # нема одговор за robots.txt -> нема правила
            self._robots[root] = parser
        parser = self._robots[root]
        return True if parser is None else parser.can_fetch(USER_AGENT, url)

    def _wait(self, host: str) -> None:
        gap = time.monotonic() - self._last.get(host, 0.0)
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last[host] = time.monotonic()

    # -- барања -----------------------------------------------------------
    def request(self, method: str, url: str, **kw) -> requests.Response:
        if not self._allowed(url):
            raise Blocked(f"robots.txt не дозволува: {url}")
        host = urlsplit(url).netloc
        error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            self._wait(host)
            self.count += 1
            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kw)
            except requests.RequestException as exc:
                error = exc
            else:
                if resp.status_code in (401, 403):
                    raise Blocked(f"{resp.status_code} за {url}")
                if resp.status_code < 400:
                    return resp
                error = requests.HTTPError(f"{resp.status_code} за {url}")
                if resp.status_code not in (429, 500, 502, 503, 504):
                    break  # 404 и слични не се поправаат со повторување
            time.sleep(5 * attempt)
        raise error  # type: ignore[misc]

    def get(self, url: str, **kw) -> requests.Response:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw) -> requests.Response:
        return self.request("POST", url, **kw)
