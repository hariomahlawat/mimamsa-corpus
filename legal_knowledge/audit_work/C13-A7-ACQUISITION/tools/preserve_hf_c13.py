#!/usr/bin/env python3
"""C13 A7: preserve the acquired public source files on the HF dataset (additive, parent_commit pinned), then
re-download at the new revision and verify SHA-256. Nothing is ingested into data/ (A1 relevance and duplicate gate
first).

Layout (C12 preservation convention): legal_knowledge/preservation/c13_a7_acquired/<sha[:2]>/<sha>/<original filename>
plus <file>.meta.json, and legal_knowledge/preservation/c13_a7_acquired/PACKAGE_SHA256SUMS.

Eligibility: DOWNLOADED rows whose bytes re-hash correctly, whose sha256 is not the FOUO copy and not already in the
corpus, and whose access check is PUBLIC (MARKING_REVIEW_C13.csv clears term hits that are body-text references).

Usage:  python -I preserve_hf_c13.py --stage     # build the local package (no network)
        python -I preserve_hf_c13.py --upload    # one additive commit pinned to the current HF head, then verify
        python -I preserve_hf_c13.py --verify REV
        python -I preserve_hf_c13.py --check     # local package vs HF_VERIFY_C13.csv and PACKAGE_SHA256SUMS
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "scripts"))
MANIFEST = BASE / "acquisition" / "ACQUISITION_MANIFEST_C13.csv"
MARKING = BASE / "acquisition" / "MARKING_REVIEW_C13.csv"
PKG = Path("/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13_a7_hf_package")
PREFIX = "legal_knowledge/preservation/c13_a7_acquired"
REPO_ID = "hariomahlawat/mimamsa-corpus"
EXPECTED_PARENT = "844383f55d3b8e61068c3c786a69e8160061cc32"   # HF head at upload time (3864faf3 + sibling C13 metadata overlay 844383f5)
COMMITS = BASE / "acquisition" / "HF_COMMITS_C13.csv"
VERIFY = BASE / "acquisition" / "HF_VERIFY_C13.csv"
FOUO = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def eligible() -> list[dict]:
    cleared = {r["target_id"]: r for r in csv.DictReader(open(MARKING))} if MARKING.exists() else {}
    out = []
    for r in csv.DictReader(open(MANIFEST)):
        if r["status"] != "DOWNLOADED":
            continue
        assert r["sha256"] != FOUO
        if r["corpus_duplicate"]:
            continue
        if r["access_eligibility"].startswith("HOLD") and cleared.get(r["target_id"], {}).get("decision") != "PUBLIC_TERM_IS_BODY_TEXT_REFERENCE":
            continue
        assert sha(Path(r["stored_path"])) == r["sha256"], r["target_id"]
        out.append(r)
    return out


def stage() -> int:
    rows = eligible()
    if PKG.exists():
        shutil.rmtree(PKG)
    sums = []
    for r in rows:
        src = Path(r["stored_path"])
        rel = f"{r['sha256'][:2]}/{r['sha256']}/{src.name}"
        dst = PKG / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        ingest = "NOT_INGESTED_PENDING_A1_RELEVANCE_AND_DUPLICATE_GATE"
        meta = {
            "target_id": r["target_id"], "group": r["group"], "title_or_description": r["description"],
            "source_url": r["final_url"], "requested_url": r["requested_url"], "host": r["host"],
            "host_allow_listed_at_staging_a4c0c382": r["allow_listed"], "robots": r["robots"],
            "http_status_chain": r["http_status_chain"], "content_type": r["content_type"], "etag": r["etag"],
            "last_modified": r["last_modified"], "retrieved_at": r["retrieved_at"], "sha256": r["sha256"],
            "md5": r["md5"], "bytes": r["bytes"], "original_filename": r["original_filename"],
            "integrity": r["integrity"], "pdf_completeness": r["completeness"],
            "access_marking_scan_first_6_pages": r["access_marking_scan_first_6_pages"],
            "access_eligibility": r["access_eligibility"] if not r["access_eligibility"].startswith("HOLD")
            else "PUBLIC_COURT_RECORD (marking-term hits are body-text references; see MARKING_REVIEW_C13.csv)",
            "relevance_keywords_first_6_pages": r["relevance_keywords_first_6_pages"],
            "ingestion_state": ingest, "selection_reason": r["selection_reason"], "provenance": r["provenance"],
            "evidence_status": "AUTOMATED_CANDIDATE_NOT_VERIFIED (byte and pin checks only; not legal authentication)",
            "recorded_by": "C13 A7 legal_knowledge/audit_work/C13-A7-ACQUISITION"}
        mp = dst.with_name(dst.name + ".meta.json")
        mp.write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n")
        sums += [f"{r['sha256']}  ./{rel}", f"{sha(mp)}  ./{rel}.meta.json"]
    (PKG / "PACKAGE_SHA256SUMS").write_text("\n".join(sums) + "\n")
    shutil.copyfile(PKG / "PACKAGE_SHA256SUMS", BASE / "acquisition" / "HF_PACKAGE_SHA256SUMS")
    print(f"staged {len(rows)} files ({len(sums)} entries) in {PKG}")
    return 0


def local_files() -> list[tuple[Path, str]]:
    return [(p, f"{PREFIX}/{p.relative_to(PKG).as_posix()}") for p in sorted(PKG.rglob("*")) if p.is_file()]


def upload() -> int:
    from huggingface_hub import CommitOperationAdd, HfApi
    from hf_protect import assert_additive
    api = HfApi()
    head = api.dataset_info(REPO_ID).sha
    if head != EXPECTED_PARENT:
        print(f"HF head moved: {head} != {EXPECTED_PARENT}; stop and re-check (nothing uploaded)")
        return 2
    files = local_files()
    existing = set(api.list_repo_files(REPO_ID, repo_type="dataset", revision=head))
    clash = [rp for _, rp in files if rp in existing]
    if clash:
        print("paths already present on HF (additive-only: refusing):", clash[:5])
        return 3
    assert_additive(api, REPO_ID, files, revision=head)
    ops = [CommitOperationAdd(path_in_repo=rp, path_or_fileobj=str(p)) for p, rp in files]
    info = api.create_commit(REPO_ID, repo_type="dataset", operations=ops, parent_commit=head,
                             commit_message=f"C13 A7: preserve {sum(1 for _, rp in files if rp.endswith('.pdf'))} acquired public source PDFs (Gazette instruments, first-tier judgments); additive, not ingested")
    rev = info.oid
    new = not COMMITS.exists()
    with open(COMMITS, "a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(["hf_commit", "parent_commit", "prefix", "files", "pdfs", "message"])
        w.writerow([rev, head, PREFIX, len(files), sum(1 for _, rp in files if rp.endswith(".pdf")), info.commit_message if hasattr(info, "commit_message") else ""])
    print("committed", rev)
    return verify(rev)


def verify(rev: str) -> int:
    from huggingface_hub import hf_hub_download
    out = PKG.parent / f"c13_a7_hf_verify_{rev[:8]}"
    rows, bad = [], 0
    for p, rp in local_files():
        got = Path(hf_hub_download(REPO_ID, rp, repo_type="dataset", revision=rev, local_dir=str(out)))
        ok = sha(got) == sha(p)
        bad += not ok
        rows.append({"path_in_repo": rp, "revision": rev, "local_sha256": sha(p), "redownloaded_sha256": sha(got),
                     "status": "VERIFIED_REDOWNLOAD_SHA256_EQUAL" if ok else "MISMATCH"})
    with open(VERIFY, "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"verified {len(rows)} files at {rev}: {bad} mismatches")
    return 1 if bad else 0


def check() -> int:
    v = {r["path_in_repo"]: r for r in csv.DictReader(open(VERIFY))}
    sums = {}
    for line in (BASE / "acquisition" / "HF_PACKAGE_SHA256SUMS").read_text().splitlines():
        h, rel = line.split("  ", 1)
        sums[f"{PREFIX}/{rel[2:]}"] = h
    ok = set(v) == set(sums) | {f"{PREFIX}/PACKAGE_SHA256SUMS"} and all(
        r["status"] == "VERIFIED_REDOWNLOAD_SHA256_EQUAL" and (rp not in sums or sums[rp] == r["redownloaded_sha256"])
        for rp, r in v.items())
    print("CHECK", "OK" if ok else "FAIL", f"{len(v)} verified paths")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--stage", action="store_true")
    g.add_argument("--upload", action="store_true")
    g.add_argument("--verify")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.exit(stage() if a.stage else upload() if a.upload else verify(a.verify) if a.verify else check())
