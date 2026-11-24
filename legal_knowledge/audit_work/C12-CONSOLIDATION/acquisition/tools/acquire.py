#!/usr/bin/env python3
"""C12 Workstream H: execute the targeted acquisition plan (acquisition/TARGETS.csv).

Policy (mirrors crawler/http.py on legal-knowledge/v2.5-staging, made stricter where the brief says so):
  * only hosts in an `allowed_hosts` entry of sources.yaml.snapshot; aftjabalpur.in and blocked_hosts never;
  * redirects followed only to allow-listed hosts; login/CAPTCHA-looking redirects stop the target;
  * robots.txt read once per origin before anything else on that origin: 200 -> obeyed (Crawl-delay
    honoured), 4xx -> no robots (allowed), 5xx or unreachable -> disallowed, except indiacode's
    documented exceptions (not used by any target here);
  * at least 2.0 s between requests to the same host (the buckets' 0.3 s allowance is NOT used);
  * the config's User-Agent and From header; no cookies kept, no login, no CAPTCHA handling;
  * every request (robots included) appended to acquisition/REQUEST_LOG.csv;
  * downloads stored outside the git worktree at
      scratchpad/c12_acquired/<sha256[:2]>/<sha256>/<original-filename>, never overwritten.

Usage:  python -I acquire.py --dry-run      # counts per host, no network
        python -I acquire.py                # live run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import urljoin, urlsplit

import httpx
import yaml

HERE = Path(__file__).resolve().parent
ACQ = HERE.parent
STORE = Path("/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12_acquired")
WORKTREE = Path("/home/user/mimamsa-corpus")
REQUEST_LOG = ACQ / "REQUEST_LOG.csv"
RESULTS = ACQ / "fetch_results.json"

MIN_DELAY = 2.0
TIMEOUT = 60.0
MAX_TRIES = 5
BACKOFF = 4.0
MAX_BYTES = 200_000_000
ROBOTS_AGENT = "Mimamsa-Corpus"
LOGIN_RE = re.compile(r"login|signin|sign-in|captcha|auth", re.I)
NEVER_CONTACT = {"aftjabalpur.in", "www.aftjabalpur.in"}

CFG = yaml.safe_load((ACQ / "sources.yaml.snapshot").read_text())
ALLOWED = set()
for _s in CFG["sources"].values():
    ALLOWED.update(h.lower() for h in _s.get("allowed_hosts", []))
FORBIDDEN = {h.lower() for h in CFG.get("blocked_hosts", [])} | NEVER_CONTACT
ALLOWED -= FORBIDDEN
UA = CFG["defaults"]["user_agent"]
# Contact address for the HTTP From header: read ONLY from the environment (set by the owner), never
# from the config file. The C12 live run of 2026-11-24 10:13-10:15Z sent the config's contact_email in
# From; after a session privacy policy objected, the header was made opt-in (see README).
import os
FROM = os.environ.get("MIMAMSA_CONTACT_EMAIL", "").strip()

assert not str(STORE).startswith(str(WORKTREE)), "store must be outside the git worktree"


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Client:
    def __init__(self):
        self.http = httpx.Client(follow_redirects=False, timeout=TIMEOUT,
                                 headers={"User-Agent": UA, **({"From": FROM} if FROM else {})})
        self.last: dict[str, float] = {}
        self.delay: dict[str, float] = {}
        self.robots: dict[str, tuple[object, str]] = {}
        new = not REQUEST_LOG.exists()
        self.logf = open(REQUEST_LOG, "a", newline="")
        self.log = csv.writer(self.logf)
        if new:
            self.log.writerow(["time_utc", "target_id", "purpose", "method", "url", "host", "status", "bytes",
                               "elapsed_ms", "error"])

    def _send(self, url: str, target: str, purpose: str):
        host = host_of(url)
        if host not in ALLOWED or host in FORBIDDEN:
            raise RuntimeError(f"internal: refusing non-allow-listed host {host}")
        last = self.last.get(host)
        if last is not None:
            wait = self.delay.get(host, MIN_DELAY) - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        t0 = time.monotonic()
        ts = now()
        try:
            with self.http.stream("GET", url) as resp:
                chunks, n = [], 0
                for c in resp.iter_bytes():
                    n += len(c)
                    if n > MAX_BYTES:
                        raise ValueError("larger than max_file_mb")
                    chunks.append(c)
                body = b"".join(chunks)
                status, headers = resp.status_code, dict(resp.headers)
        except (httpx.HTTPError, ValueError) as e:
            self.last[host] = time.monotonic()
            self.log.writerow([ts, target, purpose, "GET", url, host, "", "", int((time.monotonic() - t0) * 1000),
                               f"{type(e).__name__}: {e}"[:300]])
            self.logf.flush()
            return None, None, f"{type(e).__name__}: {e}"[:300]
        self.last[host] = time.monotonic()
        self.log.writerow([ts, target, purpose, "GET", url, host, status, len(body),
                           int((time.monotonic() - t0) * 1000), ""])
        self.logf.flush()
        return (status, headers), body, None

    def send_retry(self, url: str, target: str, purpose: str):
        for attempt in range(1, MAX_TRIES + 1):
            meta, body, err = self._send(url, target, purpose if attempt == 1 else f"{purpose} (retry {attempt})")
            retry = err is not None or meta[0] == 429 or meta[0] >= 500
            # A proxy policy refusal is not retried (README: do not retry 403/407 policy denials).
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

    def _load_robots(self, origin: str, target: str):
        url = origin + "/robots.txt"
        meta, body, err = self._send(url, target, "robots.txt")
        hops = 0
        while meta and meta[0] in (301, 302, 303, 307, 308) and meta[1].get("location") and hops < 3:
            nxt = urljoin(url, meta[1]["location"])
            if host_of(nxt) not in ALLOWED:
                return False, f"robots.txt redirects off the allow-list ({host_of(nxt)}): disallow"
            url, hops = nxt, hops + 1
            meta, body, err = self._send(url, target, "robots.txt (redirect)")
        if err:
            return False, f"robots.txt unreachable ({err[:120]}): disallow (fail closed)"
        st = meta[0]
        if st == 200:
            rp = robotparser.RobotFileParser()
            rp.parse(body.decode("utf-8", "replace").splitlines())
            d = rp.crawl_delay(ROBOTS_AGENT)
            if d:
                self.delay[host_of(origin)] = max(MIN_DELAY, float(d))
            return rp, f"robots.txt 200 parsed" + (f" (crawl-delay {d})" if d else "")
        if 400 <= st < 500:
            return True, f"robots.txt HTTP {st}: no robots file, allowed"
        return False, f"robots.txt HTTP {st}: disallow (fail closed)"

    def get(self, url: str, target: str):
        """GET with allow-list-only redirects. Returns dict with final url, status, body, error, robots."""
        hops = 0
        while True:
            h = host_of(url)
            if h in FORBIDDEN:
                return {"status": "FORBIDDEN_HOST", "url": url}
            if h not in ALLOWED:
                return {"status": "REDIRECT_TO_NON_ALLOW_LISTED_HOST" if hops else "BLOCKED_HOST_NOT_ALLOW_LISTED", "url": url}
            ok, rdesc = self.robots_ok(url, target)
            if not ok:
                return {"status": "ROBOTS_DISALLOWED", "url": url, "robots": rdesc}
            meta, body, err = self.send_retry(url, target, "document" if not hops else f"document (redirect {hops})")
            if err:
                return {"status": "NETWORK_ERROR", "url": url, "error": err, "robots": rdesc}
            st, headers = meta
            if st in (301, 302, 303, 307, 308) and headers.get("location"):
                nxt = urljoin(url, headers["location"])
                if LOGIN_RE.search(urlsplit(nxt).path):
                    return {"status": "BLOCKED_LOGIN_OR_CAPTCHA_REDIRECT", "url": nxt, "robots": rdesc}
                hops += 1
                if hops > 5:
                    return {"status": "TOO_MANY_REDIRECTS", "url": nxt, "robots": rdesc}
                if host_of(nxt) not in ALLOWED:
                    return {"status": "REDIRECT_TO_NON_ALLOW_LISTED_HOST", "url": nxt, "robots": rdesc,
                            "redirect_from": url}
                url = nxt
                continue
            return {"status": f"HTTP_{st}", "http_status": st, "url": url, "body": body, "robots": rdesc,
                    "content_type": headers.get("content-type", "")}


def analyse_pdf(path: Path) -> dict:
    data = path.read_bytes()
    out = {"bytes": len(data), "md5": hashlib.md5(data).hexdigest(), "is_pdf": data[:5] == b"%PDF-",
           "eof_at_end": b"%%EOF" in data[-2048:], "eof_count": data.count(b"%%EOF")}
    try:
        import pymupdf
        doc = pymupdf.open(str(path))
        out["pages"] = doc.page_count
        chars = [len(doc[i].get_text("text").strip()) for i in range(doc.page_count)]
        out["pages_with_text"] = sum(1 for c in chars if c >= 50)
        out["pages_without_text"] = [i + 1 for i, c in enumerate(chars) if c < 50]
        out["opens"] = True
        out["repaired"] = bool(getattr(doc, "is_repaired", False))
        doc.close()
    except Exception as e:  # noqa: BLE001
        out.update({"opens": False, "pages": None, "pages_with_text": None, "open_error": str(e)[:200]})
    if not out["is_pdf"]:
        out["completeness"] = "NOT_A_PDF"
    elif not out["opens"]:
        out["completeness"] = "INCOMPLETE_DOES_NOT_OPEN"
    elif not out["eof_at_end"]:
        out["completeness"] = "INCOMPLETE_NO_TRAILING_EOF"
    elif out["pages_without_text"]:
        out["completeness"] = (f"STRUCTURALLY_COMPLETE; {out['pages_with_text']}/{out['pages']} pages have a text layer "
                               f"(pages without text: {','.join(map(str, out['pages_without_text'][:20]))}; likely scanned, OCR needed)")
    else:
        out["completeness"] = f"COMPLETE (%%EOF at end; opens; text on all {out['pages']} pages)"
    out.pop("pages_without_text", None)
    return out


def store(body: bytes, filename: str) -> tuple[str, Path, bool]:
    sha = hashlib.sha256(body).hexdigest()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename) or "download.pdf"
    d = STORE / sha[:2] / sha
    d.mkdir(parents=True, exist_ok=True)
    p = d / safe
    existed = p.exists()
    if not existed:
        tmp = d / (safe + ".part")
        tmp.write_bytes(body)
        tmp.rename(p)
    return sha, p, existed


def relation(t: dict, sha: str, a: dict) -> str:
    wt = t["workstream_target"]
    if wt == "1":
        if sha == t["existing_sha256"]:
            return "IDENTICAL_TO_STORED_TRUNCATED_COPY: remote copy is also truncated"
        if a["completeness"].startswith(("COMPLETE", "STRUCTURALLY_COMPLETE")):
            return f"DIFFERENT_FROM_STORED_COPY ({t['existing_sha256'][:16]}): SEPARATE_REPLACEMENT_COPY_CANDIDATE (stored copy not overwritten)"
        return f"DIFFERENT_FROM_STORED_COPY ({t['existing_sha256'][:16]}) BUT ALSO INCOMPLETE: not a replacement"
    if wt == "5":
        return ("VERIFIED: sha256 EQUALS crawler-logged value" if sha == t["expected_sha256"]
                else f"MISMATCH: sha256 differs from crawler-logged {t['expected_sha256'][:16]}")
    if wt == "4":
        if t["expected_md5"] and a["md5"] == t["expected_md5"]:
            return "MATCHES archive.org md5 pin (byte-identical to the pinned facsimile)"
        if t["expected_md5"]:
            return f"DIFFERS from archive.org md5 pin {t['expected_md5'][:12]} (needs identity check; not a verification failure if the copy is the government original)"
        return "NO_PIN"
    return ""


def run(dry: bool) -> int:
    targets = list(csv.DictReader(open(ACQ / "TARGETS.csv")))
    fetch = [t for t in targets if t["action"] == "FETCH"]
    hosts = Counter(host_of(t["url"]) for t in fetch)
    print(f"{len(targets)} targets; {len(fetch)} to fetch; per host: {dict(hosts)}")
    for h in hosts:
        assert h in ALLOWED and h not in FORBIDDEN, h
    if dry:
        fb = Counter(host_of(t["fallback_url"]) for t in fetch if t["fallback_url"].startswith("http"))
        print(f"fallbacks if the primary fails: {dict(fb)}")
        return 0
    cl = Client()
    results = {}
    if RESULTS.exists():
        results = json.loads(RESULTS.read_text())
    for t in fetch:
        tid = t["target_id"]
        if tid in results and results[tid].get("sha256"):
            continue                                    # resumable: already fetched
        attempts = []
        urls = [t["url"]] + ([t["fallback_url"]] if t["fallback_url"].startswith("http") else [])
        res = None
        for u in urls:
            r = cl.get(u, tid)
            body = r.pop("body", None)
            attempts.append({k: v for k, v in r.items()})
            if r.get("http_status") == 200 and body:
                if body[:5] != b"%PDF-":
                    attempts[-1]["status"] = "HTTP_200_NOT_PDF"
                    attempts[-1]["note"] = body[:120].decode("latin-1")
                    continue
                sha, path, existed = store(body, t["original_filename"] or u.rsplit("/", 1)[-1])
                a = analyse_pdf(path)
                res = {"status": "DOWNLOADED", "url": r["url"], "sha256": sha, "path": str(path),
                       "already_in_store": existed, "robots": r.get("robots"), **a,
                       "relation": relation(t, sha, a), "retrieved_at": now()}
                break
        if res is None:
            last = attempts[-1]
            res = {"status": last["status"], "url": last.get("url"), "robots": last.get("robots", ""),
                   "error": last.get("error", "")}
        res["attempts"] = attempts
        results[tid] = res
        RESULTS.write_text(json.dumps(results, indent=1))
        print(tid, res["status"], res.get("sha256", "")[:12], res.get("completeness", res.get("error", ""))[:80], flush=True)
    cl.logf.close()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    sys.exit(run(ap.parse_args().dry_run))
