#!/usr/bin/env python3
"""C13 A7: compare every pinned document in the open crawler PRs (#8 ACQ-01, #9 DESW, #17 ACQ-02, #23 ACQ-03)
against the current corpus byte index (pr_review/CORPUS_BYTE_INDEX.csv.gz). Offline; reads the PR heads with git.

For each pinned document: source key, PR, doc_id, URL, pinned sha256/md5/bytes (from expected_* fields, the ACQ-01
`note` form "expected md5 <hex>, <n> bytes", India Code listing_* and expected_served_sha256), and whether the corpus
already holds a byte-identical copy (sha256 or md5 equality; a size-only equality is reported separately and is NOT
treated as identity).

Usage:  python -I pr_pin_check.py [--repo <worktree>]          # write pr_review/PR_PIN_CHECK_C13.csv
        python -I pr_pin_check.py --check                       # rebuild and compare with the committed file
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent
INDEX = OUT_DIR / "pr_review" / "CORPUS_BYTE_INDEX.csv.gz"
OUT = OUT_DIR / "pr_review" / "PR_PIN_CHECK_C13.csv"
SUMMARY = OUT_DIR / "pr_review" / "PR_PIN_CHECK_SUMMARY.txt"
DEFAULT_REPO = HERE.parents[3]

# PR head commits inspected (refs/pull/N/head on 2026-11-25).
PR_HEADS = {"7": "feec0103", "8": "1b948727", "9": "97933ccf", "17": "b8ee3176", "23": "60715342"}
# Which PR introduced which source key (verified with git diff between the stacked heads).
SOURCE_PR = {"archive": "8", "official_instruments": "8", "desw": "9", "archive_acq02": "17",
             "archive_acq03": "23", "official_instruments_acq03": "23"}
NOTE_RE = re.compile(r"expected md5 ([0-9a-f]{32}),\s*([0-9]+) bytes")
# Same instrument already held as a different carrier copy (C5 source_copy_register titles; preserved at HF 5524c3d9).
# Manual identity mapping, not byte identity.
SAME_INSTRUMENT_HELD = {
    "act-air-force-army-laws-amendment-1975": "C5-SRC-P0-AA-AMD-ACT13-1975 (India Code 1975-13.pdf, 69,521 bytes, sha256 8358d2b3...)",
    "act-army-amendment-1992": "C5-SRC-P0-AA-AMD-ACT37-1992 (India Code 1992-37.pdf / A1992-37.pdf; 3 copies)",
    "act-commanders-in-chief-change-designation-1955": "C5-SRC-P0-AA-AMD-ACT19-1955 (India Code A1955-19.pdf, 173,255 bytes; the PR pins the archive.org Gazette Extraordinary scan, a different carrier)",
}
C7 = Path("/home/user/c7")
PREFIX_RE = re.compile(r"SHA-256 ([0-9a-f]{8,63})\b")
LISTING_RE = re.compile(r"([0-9][0-9,]*) bytes md5 ([0-9a-f]{32})")


def load_cfg(repo: Path, rev: str) -> dict:
    txt = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:config/sources.yaml"], check=True,
                         capture_output=True, text=True).stdout
    return yaml.safe_load(txt)


def build(repo: Path) -> tuple[str, str]:
    idx = list(csv.DictReader(io.StringIO(gzip.decompress(INDEX.read_bytes()).decode())))
    by_sha, by_md5, by_size = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in idx:
        if r["sha256"]:
            by_sha[r["sha256"]].append(r["path"])
        if r["md5"]:
            by_md5[r["md5"]].append(r["path"])
        if r["bytes"]:
            by_size[int(r["bytes"])].append(r["path"])
    rm = subprocess.run(["git", "-C", str(C7), "show", "ad77758d:data/raw_manifest.csv"], check=True,
                        capture_output=True, text=True).stdout
    by_url = defaultdict(list)
    for r in csv.DictReader(io.StringIO(rm)):
        for u in [r["source_url"]] + [a for a in re.split(r"[;| ]+", r.get("source_aliases") or "") if a]:
            by_url[u].append(r["raw_path"])
    live = {}
    nodes = OUT_DIR / "allowlist" / "ARCHIVE_ITEM_NODES.csv"
    if nodes.exists():
        for r in csv.DictReader(open(nodes)):
            live[f"https://archive.org/download/{r['identifier']}/{r['file']}"] = r
    cfgs = {"23": load_cfg(repo, PR_HEADS["23"]), "9": load_cfg(repo, PR_HEADS["9"])}
    rows = []
    for key, pr in SOURCE_PR.items():
        cfg = cfgs["9"] if key == "desw" else cfgs["23"]
        src = cfg["sources"].get(key) or {}
        for d in src.get("documents", []) or []:
            note = str(d.get("note") or "")
            sha = str(d.get("expected_sha256") or "").lower()
            md5 = str(d.get("expected_md5") or "").lower()
            size = d.get("expected_bytes") or ""
            m = NOTE_RE.search(note)
            if m:
                md5 = md5 or m.group(1)
                size = size or int(m.group(2))
            listing_md5 = str(d.get("listing_md5") or "").lower()
            listing_bytes = d.get("listing_bytes") or ""
            lm = LISTING_RE.search(note)
            if lm and not listing_md5 and key.startswith("official_instruments"):
                listing_bytes, listing_md5 = int(lm.group(1).replace(",", "")), lm.group(2)
            served = str(d.get("expected_served_sha256") or "").lower()
            hits = []
            if sha and sha in by_sha:
                hits += [f"sha256:{p}" for p in by_sha[sha]]
            for h in (served,):
                if h and h in by_sha:
                    hits += [f"served_sha256:{p}" for p in by_sha[h]]
            for h, lab in ((md5, "md5"), (listing_md5, "listing_md5")):
                if h and h in by_md5:
                    hits += [f"{lab}:{p}" for p in by_md5[h]]
            pm = PREFIX_RE.search(note)
            if not hits and pm:
                hits += [f"sha256_prefix_in_note({pm.group(1)}):{p}" for h, ps in by_sha.items()
                         if h.startswith(pm.group(1)) for p in ps]
            url_hits = by_url.get(d.get("url", ""), [])
            size_only = []
            if not hits:
                for s in (size, listing_bytes):
                    if s and int(s) in by_size:
                        size_only += by_size[int(s)]
            pinned = bool(sha or md5 or served)
            if not hits and url_hits:
                status = "ALREADY_IN_CORPUS_SAME_SOURCE_URL (crawler copy; served bytes differ from listing pins by design)"
                hits = [f"source_url:{p}" for p in url_hits]
            elif not hits and d.get("doc_id") in SAME_INSTRUMENT_HELD:
                status = "SAME_INSTRUMENT_HELD_DIFFERENT_CARRIER (manual identity; not byte identity)"
                hits = [SAME_INSTRUMENT_HELD[d["doc_id"]]]
            elif hits and all(h.startswith("sha256_prefix") for h in hits):
                status = "ALREADY_IN_CORPUS_SHA256_PREFIX_ONLY"
            elif hits:
                status = "ALREADY_IN_CORPUS_BYTE_IDENTICAL"
            elif not pinned and not listing_md5:
                status = "NO_INTEGRITY_PIN_NOT_IN_CORPUS_BY_HASH"
            elif size_only:
                status = "NOT_IN_CORPUS_BY_HASH_SIZE_COINCIDENCE_ONLY"
            else:
                status = "NOT_IN_CORPUS"
            rows.append({"pr": pr, "source": key, "doc_id": d.get("doc_id", ""), "url": d.get("url", ""),
                         "title": d.get("title", ""), "pinned_sha256": sha, "pinned_md5": md5,
                         "pinned_bytes": size, "listing_md5": listing_md5, "listing_bytes": listing_bytes,
                         "expected_served_sha256": served, "corpus_status": status,
                         "corpus_matches": " | ".join(sorted(set(hits))),
                         "size_only_matches": " | ".join(sorted(set(size_only)))[:400],
                         "archive_metadata_2026_11_25": (lambda L: "" if not L else (
                             "PIN_MATCHES_LIVE_METADATA" if L["file_md5"] == md5 and str(L["file_size"]) == str(size)
                             else f"PIN_DIFFERS_FROM_LIVE_METADATA (md5 {L['file_md5']}, size {L['file_size']})"))(live.get(d.get("url", "")))})
    s = io.StringIO()
    w = csv.DictWriter(s, list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    c = Counter((r["pr"], r["source"], r["corpus_status"]) for r in rows)
    lines = [f"pinned documents: {len(rows)}"] + [f"PR #{k[0]} {k[1]}: {k[2]} = {v}" for k, v in sorted(c.items())]
    tot = Counter(r["corpus_status"] for r in rows)
    tot.update(f"archive.org live metadata: {r['archive_metadata_2026_11_25']}" for r in rows if r["archive_metadata_2026_11_25"])
    lines += [f"TOTAL {k} = {v}" for k, v in sorted(tot.items())]
    return s.getvalue(), "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    csv_text, summ = build(a.repo)
    if a.check:
        ok = OUT.read_text() == csv_text and SUMMARY.read_text() == summ
        print("CHECK", "OK" if ok else "FAIL", OUT.name)
        return 0 if ok else 1
    OUT.write_text(csv_text)
    SUMMARY.write_text(summ)
    print(summ)
    return 0


if __name__ == "__main__":
    sys.exit(main())
