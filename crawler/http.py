"""The only place the crawler talks HTTP.

PoliteClient enforces, for every request: the allow-list (also on every redirect hop),
robots.txt, a per-host minimum delay, a size cap, the audit trail, and "stop and report"
on login walls / access denials. It never retries by itself: failures go back to the
crawl-state queue, which schedules the retry with backoff.

Replay mode serves responses from a folder of saved pages (index.json maps URL -> file),
so source modules can be built and tested without touching the live site.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib import robotparser
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

from .audit import AuditLog
from .config import Config, url_host

ROBOTS_AGENT = "Mimamsa-Corpus"
ROBOTS_LENIENT_TIMEOUT = 20.0   # seconds to wait for robots.txt on a source with the unreachable exception
log = logging.getLogger("mimamsa.http")
LOGIN_PATH_RE = re.compile(r"(log-?in|sign-?in|captcha|/auth\b|/sso\b)", re.I)
REDIRECTS = (301, 302, 303, 307, 308)
MAX_REDIRECTS = 5


class CrawlError(Exception):
    retryable = False
    status_code: int | None = None


class NotAllowed(CrawlError):
    """URL is off the allow-list (or on the block list)."""


class RobotsDisallowed(CrawlError):
    """robots.txt forbids this URL (or robots.txt could not be read)."""


class Blocked(CrawlError):
    """Login wall, CAPTCHA or access denial. Stop the source and report to a human."""


class UserAgentNotSet(CrawlError):
    """Live requests are refused while the contact email is the placeholder."""


class FetchError(CrawlError):
    def __init__(self, msg: str, *, retryable: bool, status_code: int | None = None):
        super().__init__(msg)
        self.retryable = retryable
        self.status_code = status_code


@dataclass
class FetchResult:
    url: str                 # final URL after redirects
    status: int
    headers: dict[str, str]  # lower-cased keys
    content: bytes

    @property
    def content_type(self) -> str | None:
        ct = self.headers.get("content-type")
        return ct.split(";")[0].strip().lower() if ct else None

    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


def replay_transport(directory: Path | str) -> httpx.MockTransport:
    """Serve saved pages. index.json: {url: "file"} or {url: {"file", "status", "content_type"}}.
    URLs not in the index answer 404."""
    directory = Path(directory)
    index = json.loads((directory / "index.json").read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        entry = index.get(str(request.url))
        if entry is None:
            return httpx.Response(404, text="not in replay set")
        if isinstance(entry, str):
            entry = {"file": entry}
        body = (directory / entry["file"]).read_bytes() if entry.get("file") else b""
        headers = dict(entry.get("headers", {}))
        ctype = entry.get("content_type") or _guess_type(entry.get("file", ""))
        if ctype:
            headers["content-type"] = ctype
        return httpx.Response(entry.get("status", 200), content=body, headers=headers)

    return httpx.MockTransport(handler)


def is_pdf_url(url: str) -> bool:
    """True if the path, or any query value (…?file=x.pdf), names a PDF."""
    parts = urlsplit(url)
    if parts.path.lower().endswith(".pdf"):
        return True
    return any(v.lower().endswith(".pdf") for vals in parse_qs(parts.query).values() for v in vals)


def _guess_type(name: str) -> str | None:
    return {".html": "text/html; charset=utf-8", ".pdf": "application/pdf",
            ".txt": "text/plain"}.get(Path(name).suffix.lower())


class PoliteClient:
    def __init__(self, cfg: Config, audit: AuditLog, source: str, *,
                 transport: httpx.BaseTransport | None = None, replay: bool = False,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic,
                 record_dir: Path | None = None):
        if not replay and cfg.user_agent_is_placeholder():
            raise UserAgentNotSet("set a real contact email in defaults.contact_email before any live request")
        self.cfg, self.audit, self.source, self.replay = cfg, audit, source, replay
        self.sleep = (lambda s: None) if replay and sleep is time.sleep else sleep
        self.clock = clock
        self.min_delay = float(cfg.setting(source, "min_delay_seconds"))
        self.max_bytes = int(float(cfg.setting(source, "max_file_mb")) * 1_000_000)
        self.record_dir = record_dir
        self.client = httpx.Client(transport=transport, follow_redirects=False,
                                   timeout=float(cfg.setting(source, "timeout_seconds")),
                                   headers={"User-Agent": cfg.defaults["user_agent"],
                                            "From": cfg.defaults["contact_email"]})
        self._last: dict[str, float] = {}
        self._delay: dict[str, float] = {}
        self._robots: dict[str, robotparser.RobotFileParser | bool] = {}
        self.robots_exception_used = False
        self.requests_made = 0
        self.waited_seconds = 0.0   # politeness delay a live run spends (in replay: would spend)

    def close(self) -> None:
        self.client.close()

    # ------------------------------------------------------------------ public
    def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResult:
        hops = 0
        while True:
            ok, why = self.cfg.is_url_allowed(self.source, url)
            if not ok:
                raise NotAllowed(f"{url}: {why}")
            if not self._robots_ok(url):
                raise RobotsDisallowed(f"{url}: disallowed by robots.txt")
            r = self._send(url, headers)
            if r.status in REDIRECTS and r.headers.get("location"):
                nxt = urljoin(url, r.headers["location"])
                if LOGIN_PATH_RE.search(urlsplit(nxt).path):
                    raise Blocked(f"{url} redirects to {nxt}: looks like a login or CAPTCHA wall")
                hops += 1
                if hops > MAX_REDIRECTS:
                    raise FetchError(f"{url}: too many redirects", retryable=False)
                url = nxt
                continue
            if r.status in (401, 403, 407):
                raise Blocked(f"{url}: HTTP {r.status} (access denied)")
            if r.status == 429 or r.status >= 500:
                raise FetchError(f"{url}: HTTP {r.status}", retryable=True, status_code=r.status)
            return r

    def get_many(self, urls: list[str], workers: int) -> list:
        """Fetch several URLs at once. ONLY for sources flagged `open_data_bucket` (bulk-access object
        storage); government hosts always go one request at a time through get().
        Returns, in order, a FetchResult or the exception get() would have raised."""
        if not self.cfg.source(self.source).get("open_data_bucket"):
            raise CrawlError(f"{self.source} is not an open-data bucket: parallel requests are not allowed")
        from concurrent.futures import ThreadPoolExecutor

        def one(url: str):
            ok, why = self.cfg.is_url_allowed(self.source, url)
            if not ok:
                return NotAllowed(f"{url}: {why}"), None
            t0 = time.monotonic()
            try:
                with self.client.stream("GET", url) as resp:
                    chunks, n = [], 0
                    for chunk in resp.iter_bytes():
                        n += len(chunk)
                        if n > self.max_bytes:
                            return FetchError(f"{url}: larger than max_file_mb", retryable=False), t0
                        chunks.append(chunk)
                    r = FetchResult(url, resp.status_code, dict(resp.headers), b"".join(chunks))
            except httpx.TransportError as e:
                return FetchError(f"{url}: {type(e).__name__}: {e}", retryable=True), t0
            if r.status in (401, 403, 407):
                return Blocked(f"{url}: HTTP {r.status} (access denied)"), t0
            if r.status == 429 or r.status >= 500 or r.status in REDIRECTS:
                return FetchError(f"{url}: HTTP {r.status}", retryable=r.status not in REDIRECTS, status_code=r.status), t0
            return r, t0

        if urls and not self._robots_ok(urls[0]):         # one robots.txt check for the bucket, as get() does
            return [RobotsDisallowed(f"{u}: disallowed by robots.txt") for u in urls]
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            done = list(pool.map(one, urls))
        out = []
        for url, (res, t0) in zip(urls, done):            # audit trail is written here, on the calling thread
            if t0 is not None:
                self.requests_made += 1
                ok = isinstance(res, FetchResult)
                self.audit.request(method="GET", url=url, status_code=res.status if ok else getattr(res, "status_code", None),
                                   nbytes=len(res.content) if ok else None,
                                   elapsed_ms=int((time.monotonic() - t0) * 1000), error=None if ok else str(res),
                                   source=self.source)
            out.append(res)
        return out

    # ---------------------------------------------------------------- internals
    def _robots_ok(self, url: str) -> bool:
        if not self.cfg.setting(self.source, "obey_robots_txt"):
            return True
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        rule = self._robots[origin]
        return rule if isinstance(rule, bool) else rule.can_fetch(ROBOTS_AGENT, url)

    def _load_robots(self, origin: str) -> robotparser.RobotFileParser | bool:
        url = origin + "/robots.txt"
        # Per-source exception (sources.<name>.robots_unreachable: allow): if robots.txt cannot be
        # fetched at all (timeout / connection error), proceed as if the site had none. A robots.txt
        # that IS served is always obeyed, and a 5xx answer still means "disallow".
        lenient = self.cfg.source(self.source).get("robots_unreachable") == "allow"
        try:
            r = self._send(url, timeout=ROBOTS_LENIENT_TIMEOUT if lenient else None)
        except FetchError as e:
            if lenient and e.status_code is None:
                log.warning("robots.txt unreachable at %s (%s); proceeding under the %s robots_unreachable "
                            "exception", url, e, self.source)
                self.robots_exception_used = True
                return True
            return False
        try:
            for _ in range(3):
                if r.status not in REDIRECTS or not r.headers.get("location"):
                    break
                url = urljoin(url, r.headers["location"])
                if not self.cfg.is_url_allowed(self.source, url)[0]:
                    return False
                r = self._send(url)
        except FetchError:
            return False                      # unreachable: assume everything is disallowed
        if r.status == 200:
            rp = robotparser.RobotFileParser()
            rp.parse(r.text().splitlines())
            delay = rp.crawl_delay(ROBOTS_AGENT)
            if delay:
                host = url_host(origin)
                self._delay[host] = max(self.min_delay, float(delay))
            return rp
        if 400 <= r.status < 500:
            return True                       # no robots.txt: nothing is disallowed
        if r.status >= 500 and self.cfg.source(self.source).get("robots_5xx") == "allow":
            log.warning("robots.txt at %s answers HTTP %s; proceeding under the %s robots_5xx exception",
                        url, r.status, self.source)
            self.robots_exception_used = True
            return True
        return False                          # 5xx / odd answers: be conservative

    def _send(self, url: str, headers: dict[str, str] | None = None, *,
              timeout: float | None = None) -> FetchResult:
        host = url_host(url)
        last = self._last.get(host)
        if last is not None:
            wait = self._delay.get(host, self.min_delay) - (self.clock() - last)
            if wait > 0:
                self.waited_seconds += wait
                self.sleep(wait)
        t0 = self.clock()
        self.requests_made += 1
        try:
            extra = {"timeout": timeout} if timeout else {}
            with self.client.stream("GET", url, headers=headers or {}, **extra) as resp:
                chunks, n = [], 0
                for chunk in resp.iter_bytes():
                    n += len(chunk)
                    if n > self.max_bytes:
                        raise FetchError(f"{url}: larger than max_file_mb", retryable=False)
                    chunks.append(chunk)
                result = FetchResult(url, resp.status_code, dict(resp.headers), b"".join(chunks))
        except httpx.TransportError as e:
            self._last[host] = self.clock()
            err = f"{type(e).__name__}: {e}"
            self._audit(url, None, None, t0, err)
            raise FetchError(f"{url}: {err}", retryable=True) from e
        except FetchError as e:
            self._last[host] = self.clock()
            self._audit(url, None, None, t0, str(e))
            raise
        self._last[host] = self.clock()
        self._audit(url, result.status, len(result.content), t0, None)
        if self.record_dir and result.status == 200:
            self._record(result)
        return result

    def _audit(self, url, status, nbytes, t0, error) -> None:
        self.audit.request(method="GET", url=url, status_code=status, nbytes=nbytes,
                           elapsed_ms=int((self.clock() - t0) * 1000), error=error, source=self.source)

    def _record(self, r: FetchResult) -> None:
        """Save a live response so it can be replayed later (listing pages for fixtures)."""
        self.record_dir.mkdir(parents=True, exist_ok=True)
        ext = {"text/html": ".html", "application/pdf": ".pdf", "text/plain": ".txt"}.get(r.content_type or "", ".bin")
        name = hashlib.sha256(r.url.encode()).hexdigest()[:16] + ext
        (self.record_dir / name).write_bytes(r.content)
        idx_path = self.record_dir / "index.json"
        idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
        idx[r.url] = {"file": name, "content_type": r.headers.get("content-type")}
        idx_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")
