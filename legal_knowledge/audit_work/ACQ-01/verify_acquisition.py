#!/usr/bin/env python3
"""Offline post-acquisition check for ACQ-01 (run only after an owner-approved download).

For every batch item that names an expected_md5/expected_size, find the metadata record data/meta/<doc_id>.json
and its raw file, then check: raw bytes exist and are unmodified (sha256 equals the metadata record, md5/size equal
the archive.org values fixed before the run), and the record carries source_url, retrieved_at, issue_date and
source. Items not yet acquired are reported as PENDING, never as passed. Makes no network requests.

  python legal_knowledge/audit_work/ACQ-01/verify_acquisition.py [--repo ROOT]
"""
import argparse, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(p: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=HERE.parents[2])
    a = ap.parse_args()
    plan = json.loads((HERE / "batches.json").read_text(encoding="utf-8"))
    report, failed = [], False
    for b in plan["batches"]:
        for it in b["items"]:
            if not it.get("expected_md5"):
                report.append((b["batch"], it["doc_id"], "SKIP", "no pre-committed checksum (non-archive route)"))
                continue
            meta_p = a.repo / "data" / "meta" / f"{it['doc_id']}.json"
            if not meta_p.is_file():
                report.append((b["batch"], it["doc_id"], "PENDING", "not acquired"))
                continue
            m = json.loads(meta_p.read_text(encoding="utf-8"))
            raw = a.repo / m.get("raw_path", "")
            problems = []
            if not raw.is_file():
                problems.append("raw file missing")
            else:
                if digest(raw, "sha256") != m.get("sha256"):
                    problems.append("sha256 differs from metadata record")
                if digest(raw, "md5") != it["expected_md5"]:
                    problems.append("md5 differs from archive.org value fixed before the run")
                if raw.stat().st_size != it["expected_size"]:
                    problems.append("size differs from archive.org value")
            for k in ("source_url", "retrieved_at", "issue_date", "source"):
                if not m.get(k):
                    problems.append(f"metadata lacks {k}")
            if m.get("source_url") and it["archive_identifier"] not in m["source_url"]:
                problems.append("source_url does not name the planned archive.org item")
            failed |= bool(problems)
            report.append((b["batch"], it["doc_id"], "FAIL" if problems else "PASS", "; ".join(problems) or "ok"))
    for r in report:
        print("\t".join(r))
    print(f"PASS={sum(r[2]=='PASS' for r in report)} FAIL={sum(r[2]=='FAIL' for r in report)} "
          f"PENDING={sum(r[2]=='PENDING' for r in report)} SKIP={sum(r[2]=='SKIP' for r in report)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
