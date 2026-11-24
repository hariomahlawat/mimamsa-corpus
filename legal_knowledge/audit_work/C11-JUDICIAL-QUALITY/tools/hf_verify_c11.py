#!/usr/bin/env python3
"""C11 cross-repository integrity statuses for every distinct copy (Hugging Face vs GitHub raw-data vs working store).
Status vocabulary (assignment Part III): BYTE_VERIFIED, DECLARED_HASH_ONLY, PATH_SIZE_MATCH_ONLY, NOT_CHECKED, MISMATCH, UNAVAILABLE.
HF-hosted bytes were not readable, so no HF copy can be BYTE_VERIFIED here; GitHub raw-data copies were re-hashed by C10.
  python -I -B hf_verify_c11.py [--check]"""
import argparse, csv, io, json, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "hf_verification"
INV = PKG.parent / "C10-RECONCILIATION" / "outputs" / "UNIFIED_CORPUS_INVENTORY.csv"
LOCAL_IDENTICAL = PKG.parent / "C10-HF-JUDGMENTS" / "outputs" / "HF_JUDGMENT_COPY_REGISTER.csv"
MAP = {  # C10 evidence -> (HF status, declarer)
    "HF_PATH_SIZE_MATCH_DECLARED": ("DECLARED_HASH_ONLY", "HF data/SHA256SUMS (path and size equal to GitHub raw-data; SHA256SUMS sample-matched to GitHub's)"),
    "HF_SIDECAR_DECLARED": ("DECLARED_HASH_ONLY", "HF legal_knowledge sidecar JSON"),
    "HF_UPLOAD_RUN_REMOTE_VERIFIED": ("DECLARED_HASH_ONLY", "GitHub Actions upload-run log reporting remote verification (not re-performed here)"),
    "GITHUB_MML_MANIFEST_DECLARED": ("PATH_SIZE_MATCH_ONLY", "GitHub MML manifest declares the hash; HF shows path and size only"),
}


def build():
    inv = list(csv.DictReader(open(INV, encoding="utf-8")))
    local = {r["sha256"]: r for r in csv.DictReader(open(LOCAL_IDENTICAL, encoding="utf-8"))}
    rows = []
    for r in inv:
        pres = r["presence"]
        if pres in ("HF_AND_GITHUB_RAW_DATA", "HF_ONLY"):
            st, by = MAP.get(r["hf_byte_verification"], ("NOT_CHECKED", "no HF evidence recorded"))
        else:
            st, by = "UNAVAILABLE", "not present in the HF listing (working-store-only copy)"
        gh = ("BYTE_VERIFIED" if r["gh_byte_verification"].startswith("REHASHED") and "MISMATCH" not in r["gh_byte_verification"] else
              "MISMATCH" if "MISMATCH" in r["gh_byte_verification"] else "UNAVAILABLE" if not r["gh_raw_data_paths"] else "NOT_CHECKED")
        lc = local.get(r["sha256"], {})
        localv = ("BYTE_VERIFIED_LOCAL_IDENTICAL_COPY" if lc.get("source_document_verification", "").startswith("WORKING_STORE_REHASHED") else
                  "BYTE_VERIFIED_WORKING_STORE" if pres.startswith("C5_WORKING_STORE") else "")
        rows.append(dict(sha256=r["sha256"], bytes=r["bytes"], category=r["category"], title=r["title"][:160], presence=pres,
                         hf_status=st, hf_hash_declared_by=by, github_raw_data_status=gh, local_copy_status=localv,
                         hf_paths=r["hf_paths"], hf_revision="UNPINNED (latest logged e1a7fa47)"))
    acct = Counter((x["presence"], x["hf_status"]) for x in rows)
    summ = dict(distinct_copies=len(rows), hf_status=dict(sorted(Counter(x["hf_status"] for x in rows).items())),
                github_status=dict(sorted(Counter(x["github_raw_data_status"] for x in rows).items())),
                by_presence={f"{a}|{b}": n for (a, b), n in sorted(acct.items())},
                hf_only=[dict(sha256=x["sha256"][:12], title=x["title"][:80], hf_status=x["hf_status"], local=x["local_copy_status"]) for x in rows if x["presence"] == "HF_ONLY"],
                capture=json.loads((OUT / "hf_capture_c11.json").read_text(encoding="utf-8"))["sha256sums_sample"]["conclusion"])
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(rows[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    return {"HF_INTEGRITY_STATUS.csv": s.getvalue(), "HF_INTEGRITY_SUMMARY.json": json.dumps(summ, indent=1, sort_keys=True) + "\n"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    out = build()
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED: " + ", ".join(bad) if bad else f"hf integrity statuses reproduce ({len(out)} files)"); return 1 if bad else 0
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(out["HF_INTEGRITY_SUMMARY.json"]); return 0


if __name__ == "__main__":
    sys.exit(main())
