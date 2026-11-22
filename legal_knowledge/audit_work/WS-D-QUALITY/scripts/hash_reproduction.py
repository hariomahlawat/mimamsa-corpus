#!/usr/bin/env python3
"""WS-D deliverable 1: reproduce frozen hashes (stdlib only, read-only).

Checks, without modifying anything:
  * the 658 KB and 53 case files against the published frozen SHA-256 values;
  * every per-record hash in the PILOT-01 and R23-VERIFY-01 frozen manifests
    (KB_RECORD/CASE_ROW = SHA-256 of the exact JSONL line bytes; MML_PROVISION =
    SHA-256 of canonical JSON {id, provision, mml_files});
  * the MML manifest SHA-256 recorded in the pilot manifest;
  * the eight MML originals against the manifest, when local bytes are supplied
    with --mml-dir (never fetched); and the transport ZIP against the receipt
    value when --mml-zip is supplied.

A matching hash proves byte integrity of the examined copy only, never legal
authenticity, edition, completeness of amendments or current law.

Usage: python3 hash_reproduction.py [--mml-dir DIR] [--mml-zip FILE] [--out FILE]
Exit 1 on any mismatch among checks that were run.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AW = ROOT / "legal_knowledge" / "audit_work"
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
CASES = ROOT / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
MML_MANIFEST = ROOT / "legal_knowledge/manual_sources/MML_Originals_Manifest.csv"
FROZEN = {"records_658.jsonl": "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1",
          "cases_53.jsonl": "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a"}
# From legal_knowledge/manual_sources/UPLOAD_RECEIPT_2026-11-22.md
RECEIPT_ZIP_SHA = "9d82b9c5cb9ac56f41fd6ca74ed0a4704a5897fd26a239fdbafe0377e511f31c"
BATCHES = ("PILOT-01", "R23-VERIFY-01")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def line_index(path: Path):
    """{id: (line_no, sha256(line bytes))} using the build_baseline convention:
    split on b'\\n', skip blank lines, number non-blank lines from 1."""
    out = {}
    lines = [l for l in path.read_bytes().split(b"\n") if l.strip()]
    for n, l in enumerate(lines, 1):
        out[json.loads(l)["id"]] = (n, sha(l))
    return out, len(lines)


def mml_provision_hash(rec: dict) -> str:
    obj = {"id": rec["record_id"], "provision": rec["provision"], "mml_files": rec["mml_files"]}
    # Convention recovered by WS-D (not documented in the manifest): json.dumps
    # with sort_keys=True and DEFAULT separators (", ", ": "); ASCII escaping
    # does not matter for these values. Compact separators do NOT reproduce it.
    return sha(json.dumps(obj, sort_keys=True).encode("utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mml-dir", type=Path)
    ap.add_argument("--mml-zip", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    res = {"artifact": "WS-D hash reproduction", "tool": "legal_knowledge/audit_work/WS-D-QUALITY/scripts/hash_reproduction.py",
           "caveat": "Byte integrity only; not legal authenticity, edition, amendment completeness or current law.",
           "files": [], "manifests": [], "mml_originals": None, "mml_transport_zip": None, "summary": {}}
    fails = []
    kb_idx, kb_n = line_index(KB)
    case_idx, case_n = line_index(CASES)
    for p, n in ((KB, kb_n), (CASES, case_n)):
        got = sha(p.read_bytes())
        ok = got == FROZEN[p.name]
        res["files"].append({"path": str(p.relative_to(ROOT)), "records": n, "expected_sha256": FROZEN[p.name],
                             "actual_sha256": got, "match": ok})
        ok or fails.append(f"{p.name} sha mismatch")
    mml_rows = list(csv.DictReader(io.StringIO(MML_MANIFEST.read_text(encoding="utf-8"))))
    mml_sha = sha(MML_MANIFEST.read_bytes())
    for b in BATCHES:
        man = json.loads((AW / b / "pilot-manifest.json").read_text(encoding="utf-8"))
        snap = man.get("input_snapshot", {})
        entry = {"batch": b, "kb_file_sha256_match": snap.get("kb_file_sha256") == FROZEN["records_658.jsonl"],
                 "cases_file_sha256_match": snap.get("cases_file_sha256") == FROZEN["cases_53.jsonl"],
                 "mml_manifest_sha256": None, "records": [], "by_kind": {}}
        if "mml_manifest_sha256" in man:
            entry["mml_manifest_sha256"] = {"expected": man["mml_manifest_sha256"], "actual": mml_sha,
                                            "match": man["mml_manifest_sha256"] == mml_sha}
            entry["mml_manifest_sha256"]["match"] or fails.append(f"{b} mml manifest sha mismatch")
        entry["kb_file_sha256_match"] or fails.append(f"{b} kb snapshot")
        entry["cases_file_sha256_match"] or fails.append(f"{b} cases snapshot")
        mml_by_name = {r["filename"]: r["sha256"] for r in mml_rows}
        for r in man["records"]:
            rid, kind, exp = r["record_id"], r["kind"], r.get("original_sha256")
            if kind == "KB_RECORD":
                line, got = kb_idx.get(rid, (None, None))
                basis = "sha256(JSONL line bytes)"
                line_ok = r.get("source_line") in (None, line)
            elif kind == "CASE_ROW":
                line, got = case_idx.get(rid, (None, None))
                basis = "sha256(JSONL line bytes)"
                line_ok = r.get("source_line") in (None, line)
            elif kind == "MML_PROVISION":
                line, got, basis = None, mml_provision_hash(r), "sha256(json.dumps({id,provision,mml_files}, sort_keys=True), default separators)"
                line_ok = all(mml_by_name.get(k) == v for k, v in r["mml_files"].items())
            else:
                line, got, basis, line_ok = None, None, "unknown kind", False
            ok = got == exp and line_ok
            entry["records"].append({"record_id": rid, "kind": kind, "basis": basis, "expected": exp, "actual": got,
                                     "source_line_or_file_refs_consistent": line_ok, "match": ok})
            k = entry["by_kind"].setdefault(kind, {"total": 0, "match": 0})
            k["total"] += 1; k["match"] += ok
            ok or fails.append(f"{b} {rid} mismatch")
        res["manifests"].append(entry)
    if a.mml_dir:
        rows = []
        for r in mml_rows:
            p = a.mml_dir / r["filename"]
            if not p.is_file():
                rows.append({"filename": r["filename"], "present": False, "match": None}); continue
            b_ = p.read_bytes(); got = sha(b_)
            ok = got == r["sha256"] and len(b_) == int(r["bytes"])
            rows.append({"filename": r["filename"], "present": True, "bytes": len(b_), "expected_bytes": int(r["bytes"]),
                         "expected_sha256": r["sha256"], "actual_sha256": got, "match": ok})
            ok or fails.append(f"MML {r['filename']} mismatch")
        res["mml_originals"] = {"dir": "<scratchpad>/" + a.mml_dir.name if "scratchpad" in str(a.mml_dir) else str(a.mml_dir),
                                "checked": sum(x["present"] for x in rows), "matched": sum(bool(x["match"]) for x in rows),
                                "expected": len(mml_rows), "rows": rows}
    else:
        res["mml_originals"] = {"status": "NOT_CHECKED", "reason": "no --mml-dir supplied; bytes are private and not in git"}
    if a.mml_zip:
        zb = a.mml_zip.read_bytes(); got = sha(zb)
        members = {}
        with zipfile.ZipFile(io.BytesIO(zb)) as z:
            for i in z.infolist():
                if not i.is_dir():
                    members[i.filename] = sha(z.read(i))
        want = {r["filename"]: r["sha256"] for r in mml_rows}
        member_match = {n: any(m.endswith("/" + n) or m == n for m, h in members.items() if h == s) for n, s in want.items()}
        res["mml_transport_zip"] = {"expected_sha256_per_receipt": RECEIPT_ZIP_SHA, "actual_sha256": got,
                                    "match": got == RECEIPT_ZIP_SHA, "member_count": len(members),
                                    "originals_found_in_zip_with_manifest_hash": sum(member_match.values()),
                                    "per_original": member_match}
        (got == RECEIPT_ZIP_SHA) or fails.append("zip sha mismatch")
        all(member_match.values()) or fails.append("zip member mismatch")
    else:
        res["mml_transport_zip"] = {"status": "NOT_CHECKED"}
    res["summary"] = {"failures": fails, "all_run_checks_match": not fails}
    text = json.dumps(res, indent=2, ensure_ascii=False) + "\n"
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
