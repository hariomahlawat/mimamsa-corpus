#!/usr/bin/env python3
"""C13 A7 Part 2: validate proposed allow-list additions (no document downloads from non-allow-listed hosts).

Per candidate host: TLS chain validity (proxy CA bundle, strict), robots.txt, and whether the landing page or the
judgment/document entry point shows a CAPTCHA or login. archive.org: the item metadata API (archive.org is already
allow-listed) gives each pinned item's storage nodes (d1/d2) and item directory, from which the item-path-restricted
proposal is built; for each distinct node, a robots.txt request checks TLS and robots (no item file is requested).

Writes allowlist/PROBE_RESULTS.csv, allowlist/ARCHIVE_ITEM_NODES.csv and appends to allowlist/PROBE_REQUEST_LOG.csv.

Usage:  python -I allowlist_probe.py --dry-run     # list what would be requested
        python -I allowlist_probe.py               # live probe
        python -I allowlist_probe.py --check       # verify the committed outputs against PROBE_SHA256SUMS
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a7net  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "allowlist"
REPO = HERE.parents[3]
LOG = OUT / "PROBE_REQUEST_LOG.csv"
SUMS = OUT / "PROBE_SHA256SUMS"
OUTPUTS = ["PROBE_RESULTS.csv", "ARCHIVE_ITEM_NODES.csv"]

CAPTCHA_RE = re.compile(r"captcha|recaptcha|hcaptcha|siwp_captcha|captcha_image|g-recaptcha", re.I)
LOGIN_RE = re.compile(r"type=[\"']password[\"']|\blog ?in\b|sign ?in", re.I)

# Candidate pages: (host, url, purpose). Only robots.txt and these entry pages are requested.
CANDIDATES = [
    ("sci.gov.in", "https://sci.gov.in/", "landing"),
    ("www.sci.gov.in", "https://www.sci.gov.in/", "landing"),
    ("www.sci.gov.in", "https://www.sci.gov.in/judgements-judgement-date/", "judgment search entry"),
    ("api.sci.gov.in", "https://api.sci.gov.in/", "landing"),
    ("desw.gov.in", "https://desw.gov.in/", "landing"),
    ("egazette.gov.in", "https://egazette.gov.in/", "landing (allow-listed; TLS fix check)"),
]


def archive_items() -> list[tuple[str, str]]:
    """(identifier, file) for every archive.org pin in the open PRs plus the C12 archive.org fallbacks."""
    items = []
    with open(HERE.parent / "pr_review" / "PR_PIN_CHECK_C13.csv") as f:
        for r in csv.DictReader(f):
            m = re.match(r"https://archive\.org/download/([^/]+)/(.+)$", r["url"])
            if m and r["corpus_status"] != "ALREADY_IN_CORPUS_BYTE_IDENTICAL":
                items.append((m.group(1), m.group(2)))
    c12 = HERE.parents[1] / "C12-CONSOLIDATION" / "acquisition" / "TARGETS.csv"
    for r in csv.DictReader(open(c12)):
        m = re.match(r"https://archive\.org/download/([^/]+)/(.+)$", r["fallback_url"])
        if m:
            items.append((m.group(1), m.group(2)))
    seen, out = set(), []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def tls_chain(host: str) -> str:
    """Chain as served, verified strictly against the proxy CA bundle (openssl through the proxy)."""
    try:
        p = subprocess.run(["openssl", "s_client", "-proxy", "127.0.0.1:33405", "-connect", f"{host}:443",
                            "-servername", host, "-CAfile", a7net.CA_BUNDLE, "-no-CApath",
                            "-verify_hostname", host],
                           input=b"", capture_output=True, timeout=45)
        txt = p.stdout.decode("latin-1") + p.stderr.decode("latin-1")
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    m = re.search(r"Verify return code: (\d+) \(([^)]*)\)", txt)
    issuers = re.findall(r"^\s*\d+ s:(.*)\n\s*i:(.*)$", txt, re.M)
    chain = " ; ".join(f"[{s.strip()} <- {i.strip()}]" for s, i in issuers)
    return (f"verify={m.group(1)} ({m.group(2)})" if m else "NO_HANDSHAKE") + (f"; served {len(issuers)} cert(s): {chain}" if issuers else "")


def page_flags(body: bytes) -> str:
    t = body[:400000].decode("utf-8", "replace")
    flags = []
    if CAPTCHA_RE.search(t):
        flags.append("CAPTCHA_MARKER")
    if re.search(r"type=[\"']password[\"']", t, re.I):
        flags.append("PASSWORD_FIELD")
    return ",".join(flags) or "none"


def tls_only() -> int:
    """Redo only the TLS column (handshakes, no HTTP request). The first live run (2026-11-25) passed
    -verify_return_error, with which s_client reported 'Verify return code: 0' after an aborted handshake for
    egazette.gov.in; that flag is no longer used."""
    p = OUT / "PROBE_RESULTS.csv"
    rows = list(csv.DictReader(open(p)))
    cache = {}
    for r in rows:
        if r["host"] not in cache:
            cache[r["host"]] = tls_chain(r["host"])
        r["tls_openssl_strict"] = cache[r["host"]]
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    SUMS.write_text("".join(f"{hashlib.sha256((OUT / n).read_bytes()).hexdigest()}  {n}\n" for n in OUTPUTS))
    print(f"TLS re-checked for {len(cache)} hosts")
    return 0


def run(dry: bool) -> int:
    items = archive_items()
    hosts = sorted({c[0] for c in CANDIDATES})
    print(f"candidate hosts: {hosts}; archive.org items: {len(items)} (metadata API only)")
    if dry:
        for c in CANDIDATES:
            print("would GET robots.txt + ", c[1])
        for ident, _ in items:
            print("would GET https://archive.org/metadata/" + ident)
        return 0
    permitted = set(hosts) | {"archive.org"}
    net = a7net.Net("allowlist_probe", permitted, set(), LOG)
    results = []
    tls_done = {}
    for host, url, purpose in CANDIDATES:
        if host not in tls_done:
            tls_done[host] = tls_chain(host)
        r = net.get(url, "PROBE-" + host, purpose)
        body = r.pop("body", b"") or b""
        results.append({"host": host, "url": url, "purpose": purpose, "tls_openssl_strict": tls_done[host],
                        "robots": r.get("robots", ""), "robots_txt_head": net.robots_text(url)[:300].replace("\n", " | "),
                        "status": r["status"], "final_url": r.get("url", ""), "redirect_chain": " > ".join(r.get("chain", [])),
                        "error": r.get("error", ""), "bytes": len(body), "page_flags": page_flags(body) if body else "",
                        "content_type": (r.get("headers") or {}).get("content-type", "")})
    nodes = []
    node_hosts = {}
    for ident, fname in items:
        r = net.get(f"https://archive.org/metadata/{ident}", "PROBE-archive-metadata", "item metadata API")
        body = r.pop("body", b"") or b""
        row = {"identifier": ident, "file": fname, "metadata_status": r["status"], "server": "", "d1": "", "d2": "",
               "dir": "", "file_md5": "", "file_size": "", "is_dark": "", "source_field": ""}
        if r.get("http_status") == 200:
            try:
                md = json.loads(body)
            except ValueError:
                md = {}
            row.update({"server": md.get("server", ""), "d1": md.get("d1", ""), "d2": md.get("d2", ""),
                        "dir": md.get("dir", ""), "is_dark": md.get("is_dark", "")})
            meta = md.get("metadata") or {}
            row["source_field"] = str(meta.get("source", "") or meta.get("identifier-access", ""))[:200]
            for f in md.get("files", []):
                if f.get("name") == fname:
                    row["file_md5"], row["file_size"] = f.get("md5", ""), f.get("size", "")
            for h in (row["d1"], row["d2"]):
                if h:
                    node_hosts.setdefault(h, []).append(ident)
        nodes.append(row)
    # Storage nodes: TLS + robots.txt only (each node host is a candidate, so it is probed, never fetched from).
    net.permitted |= set(node_hosts)
    for h in sorted(node_hosts):
        tls = tls_chain(h)
        ok, rdesc = net.robots_ok(f"https://{h}/", "PROBE-archive-node")
        results.append({"host": h, "url": f"https://{h}/robots.txt", "purpose": f"archive.org storage node for {len(node_hosts[h])} item(s)",
                        "tls_openssl_strict": tls, "robots": rdesc, "robots_txt_head": net.robots_text(f"https://{h}/")[:300].replace("\n", " | "),
                        "status": "ROBOTS_ONLY", "final_url": "", "redirect_chain": "", "error": "", "bytes": "",
                        "page_flags": "", "content_type": ""})
    net.close()
    for name, rows in (("PROBE_RESULTS.csv", results), ("ARCHIVE_ITEM_NODES.csv", nodes)):
        with open(OUT / name, "w", newline="") as f:
            w = csv.DictWriter(f, list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    SUMS.write_text("".join(f"{hashlib.sha256((OUT / n).read_bytes()).hexdigest()}  {n}\n" for n in OUTPUTS))
    print(f"wrote {len(results)} probe rows, {len(nodes)} archive item rows")
    return 0


def check() -> int:
    ok = True
    for line in SUMS.read_text().splitlines():
        h, n = line.split("  ", 1)
        good = hashlib.sha256((OUT / n).read_bytes()).hexdigest() == h
        ok &= good
        print("CHECK", "OK" if good else "FAIL", n)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--tls-only", action="store_true")
    a = ap.parse_args()
    sys.exit(check() if a.check else tls_only() if a.tls_only else run(a.dry_run))
