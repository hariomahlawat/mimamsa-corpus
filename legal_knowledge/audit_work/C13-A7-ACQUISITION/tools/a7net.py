"""C13 A7 shared network policy (used by allowlist_probe.py and acquire_c13.py).

Policy (derived from crawler/http.py and C12 acquisition/tools/acquire.py, made stricter where the C13 brief says so):
  * a host must be in the caller's permitted set; NEVER_CONTACT (aftjabalpur.in and every subdomain) and the
    config's blocked_hosts (and their subdomains) are refused before any socket is opened;
  * HTTPS only (an http:// URL or redirect hop is refused);
  * redirects are followed manually and each hop is re-checked against the permitted set; a login/CAPTCHA-looking
    hop stops the request;
  * robots.txt is read once per origin before anything else there: 200 -> obeyed (Crawl-delay honoured);
    4xx -> no robots file (RFC 9309), allowed; 5xx or unreachable -> disallowed (fail closed);
  * at least 2.0 s between requests to the same host; one request at a time;
  * TLS verification is always on. For egazette.gov.in only, the two public Let's Encrypt intermediates the server
    omits (pinned by SHA-256 in allowlist/egazette_intermediates.pem) are added as lookup certificates, and
    VERIFY_X509_PARTIAL_CHAIN is cleared, so the chain must still end at ISRG Root X1 in the proxy CA bundle;
  * User-Agent from config defaults; the HTTP From header is sent ONLY if MIMAMSA_CONTACT_EMAIL is set;
  * every request (robots.txt included) is appended to the caller's request log.
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import urljoin, urlsplit

import httpx

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"
EGAZETTE_INTERMEDIATES = OUT_DIR / "allowlist" / "egazette_intermediates.pem"
# SHA-256 of the DER form of each pinned intermediate (verified 2026-11-25; see allowlist/EGAZETTE_TLS_C13.md).
EGAZETTE_PINS = {
    "13949634d99cd6fd6aa80bc034fefacceb1969feef986586713ecdbb05758d3f",  # C=US, O=Let's Encrypt, CN=YR1
    "072639d0b140d5bffae16ad9c3f6cc6086040621f51ee61a6d46a8915c07cf76",  # C=US, O=ISRG, CN=Root YR (cross-signed by ISRG Root X1)
}
MIN_DELAY = 2.0
TIMEOUT = 90.0
MAX_TRIES = 5
BACKOFF = 4.0
MAX_BYTES = 200_000_000
ROBOTS_AGENT = "Mimamsa-Corpus"
UA = "Mimamsa-Corpus/0.1 (research collection of public military-law texts)"
LOGIN_RE = re.compile(r"login|signin|sign-in|captcha|auth", re.I)
NEVER_CONTACT = ("aftjabalpur.in",)
LOG_COLS = ["time_utc", "tool", "target_id", "purpose", "method", "url", "host", "status", "bytes", "elapsed_ms",
            "content_type", "etag", "last_modified", "error"]


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().rstrip(".")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def under(host: str, domains) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def egazette_context() -> ssl.SSLContext:
    import base64
    pem = EGAZETTE_INTERMEDIATES.read_text()
    found = set()
    for block in re.findall(r"-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----", pem, re.S):
        found.add(hashlib.sha256(base64.b64decode("".join(block.split()))).hexdigest())
    if found != EGAZETTE_PINS:
        raise RuntimeError(f"egazette intermediates file does not match the pinned SHA-256 set: {sorted(found)}")
    ctx = ssl.create_default_context(cafile=CA_BUNDLE)
    ctx.load_verify_locations(str(EGAZETTE_INTERMEDIATES))
    ctx.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN   # chain must end at a self-signed root in the bundle
    return ctx


class Net:
    def __init__(self, tool: str, permitted: set[str], forbidden: set[str], log_path: Path):
        self.tool = tool
        self.permitted = {h.lower() for h in permitted}
        self.forbidden = {h.lower() for h in forbidden} | set(NEVER_CONTACT)
        frm = os.environ.get("MIMAMSA_CONTACT_EMAIL", "").strip()
        headers = {"User-Agent": UA, **({"From": frm} if frm else {})}
        self.clients = {
            "default": httpx.Client(follow_redirects=False, timeout=TIMEOUT, headers=headers, verify=CA_BUNDLE),
        }
        if EGAZETTE_INTERMEDIATES.exists():
            self.clients["egazette"] = httpx.Client(follow_redirects=False, timeout=TIMEOUT, headers=headers,
                                                    verify=egazette_context())
        self.last: dict[str, float] = {}
        self.delay: dict[str, float] = {}
        self.robots: dict[str, tuple[object, str]] = {}
        new = not log_path.exists()
        self.logf = open(log_path, "a", newline="")
        self.log = csv.writer(self.logf)
        if new:
            self.log.writerow(LOG_COLS)

    def close(self):
        for c in self.clients.values():
            c.close()
        self.logf.close()

    def check_host(self, url: str) -> str | None:
        p = urlsplit(url)
        h = host_of(url)
        if under(h, self.forbidden):
            return "FORBIDDEN_HOST"
        if p.scheme != "https":
            return "NOT_HTTPS"
        if h not in self.permitted:
            return "HOST_NOT_PERMITTED"
        return None

    def _send(self, url: str, target: str, purpose: str, method: str = "GET"):
        bad = self.check_host(url)
        if bad:
            raise RuntimeError(f"internal: refusing {url}: {bad}")
        host = host_of(url)
        last = self.last.get(host)
        if last is not None:
            wait = self.delay.get(host, MIN_DELAY) - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        client = self.clients["egazette"] if host == "egazette.gov.in" and "egazette" in self.clients else self.clients["default"]
        t0 = time.monotonic()
        ts = now()
        try:
            with client.stream(method, url) as resp:
                chunks, n = [], 0
                for c in resp.iter_bytes():
                    n += len(c)
                    if n > MAX_BYTES:
                        raise ValueError("larger than 200 MB cap")
                    chunks.append(c)
                body = b"".join(chunks)
                status, headers = resp.status_code, dict(resp.headers)
        except (httpx.HTTPError, ValueError, ssl.SSLError) as e:
            self.last[host] = time.monotonic()
            err = f"{type(e).__name__}: {e}"[:300]
            self.log.writerow([ts, self.tool, target, purpose, method, url, host, "", "",
                               int((time.monotonic() - t0) * 1000), "", "", "", err])
            self.logf.flush()
            return None, None, err
        self.last[host] = time.monotonic()
        self.log.writerow([ts, self.tool, target, purpose, method, url, host, status, len(body),
                           int((time.monotonic() - t0) * 1000), headers.get("content-type", ""),
                           headers.get("etag", ""), headers.get("last-modified", ""), ""])
        self.logf.flush()
        return (status, headers), body, None

    def send_retry(self, url: str, target: str, purpose: str):
        meta = body = err = None
        for attempt in range(1, MAX_TRIES + 1):
            meta, body, err = self._send(url, target, purpose if attempt == 1 else f"{purpose} (retry {attempt})")
            retry = (err is not None and "CERTIFICATE_VERIFY_FAILED" not in err) or (meta is not None and (meta[0] == 429 or meta[0] >= 500))
            if err and ("403" in err or "407" in err):
                retry = False
            if not retry or attempt == MAX_TRIES:
                return meta, body, err
            time.sleep(BACKOFF * 2 ** (attempt - 1))
        return meta, body, err

    def robots_ok(self, url: str, target: str) -> tuple[bool, str]:
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self.robots:
            self.robots[origin] = self._load_robots(origin, target)
        rule, desc = self.robots[origin]
        if isinstance(rule, bool):
            return rule, desc
        ok = rule.can_fetch(ROBOTS_AGENT, url)
        return ok, desc + ("; path allowed" if ok else "; path DISALLOWED")

    def robots_text(self, url: str) -> str:
        p = urlsplit(url)
        return getattr(self, "_robots_raw", {}).get(f"{p.scheme}://{p.netloc}", "")

    def _load_robots(self, origin: str, target: str):
        url = origin + "/robots.txt"
        meta, body, err = self._send(url, target, "robots.txt")
        hops = 0
        while meta and meta[0] in (301, 302, 303, 307, 308) and meta[1].get("location") and hops < 3:
            nxt = urljoin(url, meta[1]["location"])
            if self.check_host(nxt):
                return False, f"robots.txt redirects to a non-permitted target ({nxt}): disallow"
            url, hops = nxt, hops + 1
            meta, body, err = self._send(url, target, "robots.txt (redirect)")
        if err:
            return False, f"robots.txt unreachable ({err[:140]}): disallow (fail closed)"
        st = meta[0]
        if st == 200:
            txt = body.decode("utf-8", "replace")
            self._robots_raw = getattr(self, "_robots_raw", {})
            self._robots_raw[origin] = txt
            if "<html" in txt[:500].lower():
                return True, "robots.txt 200 but an HTML page (no robots rules served): treated as no robots file"
            rp = robotparser.RobotFileParser()
            rp.parse(txt.splitlines())
            d = rp.crawl_delay(ROBOTS_AGENT)
            if d:
                self.delay[host_of(origin)] = max(MIN_DELAY, float(d))
            return rp, "robots.txt 200 parsed" + (f" (crawl-delay {d})" if d else "")
        if 400 <= st < 500:
            return True, f"robots.txt HTTP {st}: no robots file (RFC 9309), allowed"
        return False, f"robots.txt HTTP {st}: disallow (fail closed)"

    def get(self, url: str, target: str, purpose: str = "document") -> dict:
        hops = 0
        chain = []
        while True:
            bad = self.check_host(url)
            if bad:
                return {"status": ("REDIRECT_" + bad) if hops else bad, "url": url, "chain": chain}
            ok, rdesc = self.robots_ok(url, target)
            if not ok:
                return {"status": "ROBOTS_DISALLOWED", "url": url, "robots": rdesc, "chain": chain}
            meta, body, err = self.send_retry(url, target, purpose if not hops else f"{purpose} (redirect {hops})")
            if err:
                return {"status": "TLS_VERIFY_FAILED" if "CERTIFICATE_VERIFY_FAILED" in err else "NETWORK_ERROR",
                        "url": url, "error": err, "robots": rdesc, "chain": chain}
            st, headers = meta
            chain.append(f"{st} {url}")
            if st in (301, 302, 303, 307, 308) and headers.get("location"):
                nxt = urljoin(url, headers["location"])
                if LOGIN_RE.search(urlsplit(nxt).path + "?" + urlsplit(nxt).query):
                    return {"status": "BLOCKED_LOGIN_OR_CAPTCHA_REDIRECT", "url": nxt, "robots": rdesc, "chain": chain}
                hops += 1
                if hops > 5:
                    return {"status": "TOO_MANY_REDIRECTS", "url": nxt, "robots": rdesc, "chain": chain}
                url = nxt
                continue
            return {"status": f"HTTP_{st}", "http_status": st, "url": url, "body": body, "robots": rdesc,
                    "headers": {k: headers.get(k, "") for k in ("content-type", "content-length", "etag",
                                                                "last-modified", "content-disposition", "date")},
                    "chain": chain}
