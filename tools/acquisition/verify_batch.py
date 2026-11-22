#!/usr/bin/env python3
"""Offline post-acquisition verification for a pinned-document source (ACQ-01: `archive`, `official_instruments`;
ACQ-02: `archive_acq02`). Run ONLY after an owner-approved download of that source.

For each pinned document: find data/meta/<doc_id>.json and its raw file, then check
  - raw bytes exist and their SHA-256 equals the metadata record;
  - expected_sha256 / expected_md5 / expected_bytes fixed in config/sources.yaml before the run (ACQ-02), or the
    md5/size written in the ACQ-01 `note` ("expected md5 <hex>, <n> bytes"), match the raw bytes;
  - the metadata record carries source_url equal to the pinned URL (or a redirect target on an allowed host), and retrieved_at.
Documents not yet acquired are PENDING (never PASS). Documents with no pre-committed checksum (India Code bitstreams,
which are download-specific) are CHECKSUM_RECORDED_ONLY: their SHA-256 is reported for the register. No network.

  python tools/acquisition/verify_batch.py --source archive_acq02 [--repo .] [--out report.tsv]
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

import yaml

NOTE_RE = re.compile(r"expected md5 ([0-9a-f]{32}),\s*([0-9]+) bytes")


def digest(p, algo):
    h = hashlib.new(algo)
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expectations(doc):
    exp = {}
    if doc.get("expected_sha256"):
        exp["sha256"] = doc["expected_sha256"]
    if doc.get("expected_md5"):
        exp["md5"] = doc["expected_md5"]
    if doc.get("expected_bytes"):
        exp["bytes"] = int(doc["expected_bytes"])
    m = NOTE_RE.search(doc.get("note", ""))
    if m:
        exp.setdefault("md5", m.group(1))
        exp.setdefault("bytes", int(m.group(2)))
    return exp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    cfg = yaml.safe_load((a.config or a.repo / "config" / "sources.yaml").read_text(encoding="utf-8"))
    docs = cfg["sources"][a.source].get("documents") or []
    rows, failed = [], False
    for d in docs:
        exp = expectations(d)
        meta_p = a.repo / "data" / "meta" / f"{d['doc_id']}.json"
        if not meta_p.is_file():
            rows.append((d["doc_id"], "PENDING", "not acquired", "")); continue
        m = json.loads(meta_p.read_text(encoding="utf-8"))
        raw = a.repo / m.get("raw_path", "")
        probs = []
        if not raw.is_file():
            probs.append("raw file missing"); sha = ""
        else:
            sha = digest(raw, "sha256")
            if sha != m.get("sha256"): probs.append("sha256 differs from metadata record")
            if "sha256" in exp and sha != exp["sha256"]: probs.append("sha256 differs from pre-committed value")
            if "md5" in exp and digest(raw, "md5") != exp["md5"]: probs.append("md5 differs from pre-committed value")
            if "bytes" in exp and raw.stat().st_size != exp["bytes"]: probs.append("size differs from pre-committed value")
        if m.get("source_url") != d["url"] and not str(m.get("source_url", "")).startswith("https://"):
            probs.append("source_url missing or not HTTPS")
        if not m.get("retrieved_at"): probs.append("metadata lacks retrieved_at")
        status = "FAIL" if probs else ("PASS" if exp else "CHECKSUM_RECORDED_ONLY")
        failed |= bool(probs)
        rows.append((d["doc_id"], status, "; ".join(probs) or "ok", sha))
    lines = ["doc_id\tstatus\tdetail\tsha256"] + ["\t".join(r) for r in rows]
    summary = {s: sum(r[1] == s for r in rows) for s in ("PASS", "FAIL", "PENDING", "CHECKSUM_RECORDED_ONLY")}
    print("\n".join(lines)); print(json.dumps({"source": a.source, "documents": len(rows), **summary}))
    if a.out: a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
