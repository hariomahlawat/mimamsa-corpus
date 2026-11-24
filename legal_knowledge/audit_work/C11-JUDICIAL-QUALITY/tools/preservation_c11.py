#!/usr/bin/env python3
"""C11 Priority Zero: verify the registered source copies that exist only in the temporary C5 working store.

Reads the Cycle 10 MISSING_SOURCE_EVIDENCE.csv (kind REGISTERED_COPY_BYTES_NOT_IN_CANONICAL_STORE) and the pinned C5
copy and master registers; locates each copy under the working store (env MIMAMSA_WORKING_STORE, the directory that
holds downloads/); re-hashes it; checks whether identical bytes exist as a git blob anywhere in the repository object
store (any branch, any commit) or in the Hugging Face listing; records access markings. It never copies, uploads,
modifies or deletes a source file.

  MIMAMSA_WORKING_STORE=<dir> python -I -B preservation_c11.py --repo <full clone> [--check]
"""
import argparse, csv, hashlib, io, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "preservation"
C10 = PKG.parent / "C10-RECONCILIATION"
REGISTER_COMMIT = "21e73b8348767d5f1524167fcec538e1aad6e732"
REG = "legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/"
KIND = "REGISTERED_COPY_BYTES_NOT_IN_CANONICAL_STORE"


def git(repo, *a, inp=None):
    return subprocess.run(["git", "-C", repo, *a], input=inp, capture_output=True, check=True).stdout


def rcsv(b):
    return list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))


def csv_text(fields, rows):
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue()


def blob_oid(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def build(repo, store):
    miss = [r for r in rcsv((C10 / "outputs" / "MISSING_SOURCE_EVIDENCE.csv").read_bytes()) if r["kind"] == KIND]
    copies = {r["copy_id"]: r for r in rcsv(git(repo, "show", f"{REGISTER_COMMIT}:{REG}source_copy_register.csv"))}
    master = {r["source_id"]: r for r in rcsv(git(repo, "show", f"{REGISTER_COMMIT}:{REG}source_master_register.csv"))}
    inv = {r["sha256"]: r for r in rcsv((C10 / "outputs" / "UNIFIED_CORPUS_INVENTORY.csv").read_bytes())}
    rows, oids = [], {}
    for m in sorted(miss, key=lambda r: r["item"]):
        cp = copies.get(m["item"], {})
        sid = cp.get("source_id") or m["source_ids"]
        ms = master.get(sid, {})
        paths = [p.strip() for p in (cp.get("held_paths") or "").split(";") if p.strip()]
        found, status, size, rehash, used = [], "MISSING", "", "", ""
        for p in paths:
            fp = Path(store) / p if store else None
            if fp and fp.is_file() and not fp.is_symlink():
                data = fp.read_bytes()
                h = hashlib.sha256(data).hexdigest()
                found.append(p)
                if not used:
                    used, size, rehash = p, len(data), h
                    status = "PRESENT_HASH_MATCH" if h == m["sha256"] else "PRESENT_HASH_MISMATCH"
                    oids[m["sha256"]] = blob_oid(data)
        marking = ms.get("access_marking") or ""
        rows.append(dict(copy_id=m["item"], source_id=sid, sha256=m["sha256"], registered_bytes=cp.get("bytes", ""),
                         title=m["title"], working_store_paths=";".join(paths), present_paths=";".join(found),
                         rehash_sha256=rehash, bytes=size, status=status,
                         size_matches_register="YES" if size != "" and str(size) == str(cp.get("bytes", "")) else ("NO" if size != "" else ""),
                         access_marking=marking or "NONE_RECORDED",
                         access_class="SEGREGATE_RESTRICTED_MARKING" if "official use" in marking.lower() else "PUBLIC_DOCUMENT_NO_MARKING_RECORDED",
                         source_url=ms.get("source_url", ""), provenance=(ms.get("provenance") or "")[:300],
                         acquisition_provenance=(cp.get("acquisition_provenance") or "")[:300],
                         kb_exact_anchor_rows=inv.get(m["sha256"], {}).get("kb_exact_anchor_rows", ""),
                         git_blob_oid=oids.get(m["sha256"], ""), git_object_present="", hf_listing_present="", printed_marking_scan="NOT_SCANNED"))
    # duplicate in another persistent store: the git object store (any ref) and the HF listing captured by C10
    if oids:
        res = git(repo, "cat-file", "--batch-check", inp=("\n".join(oids.values()) + "\n").encode()).decode().splitlines()
        present = {l.split()[0] for l in res if not l.endswith("missing")}
    else:
        present = set()
    for r in rows:
        r["git_object_present"] = ("YES" if r["git_blob_oid"] in present else "NO") if r["git_blob_oid"] else "NOT_CHECKED_FILE_MISSING"
        r["hf_listing_present"] = "YES" if inv.get(r["sha256"], {}).get("presence", "") in ("HF_AND_GITHUB_RAW_DATA", "HF_ONLY") else "NO"
    # printed-marking scan (every page, text layer): a hit is recorded with context and classified by a fixed rule
    scan = []
    import re
    try:
        import pymupdf
        pymupdf.TOOLS.mupdf_display_errors(False)
    except ImportError:
        pymupdf = None
    pat = re.compile(r"for\s+official\s+use|restricted|confidential|not\s+to\s+be\s+(?:published|communicated)", re.I)
    for r in rows:
        if r["status"] != "PRESENT_HASH_MATCH" or pymupdf is None:
            continue
        d = pymupdf.open(str(Path(store) / r["present_paths"].split(";")[0]))
        for i in range(d.page_count):
            t = " ".join(d[i].get_text().split())
            for mm in pat.finditer(t):
                ctx = t[max(0, mm.start() - 60):mm.end() + 40]
                marking_like = bool(re.search(r"for official use|not to be (published|communicated)", mm.group(0), re.I))
                scan.append(dict(copy_id=r["copy_id"], page=i + 1, term=mm.group(0), context=ctx,
                                 classification="POSSIBLE_DOCUMENT_MARKING_REVIEW" if marking_like else "ORDINARY_WORD_USE_OR_FORM_TEXT"))
        r["printed_marking_scan"] = ("POSSIBLE_MARKING" if any(x["copy_id"] == r["copy_id"] and x["classification"].startswith("POSSIBLE") for x in scan)
                                     else "NO_MARKING_FOUND_TEXT_LAYER")
    fields = list(rows[0].keys())
    acct = {}
    for r in rows:
        acct[r["status"]] = acct.get(r["status"], 0) + 1
    sums = "".join(f"{r['sha256']}  {r['present_paths'].split(';')[0]}\n" for r in rows if r["status"] == "PRESENT_HASH_MATCH")
    summary = dict(copies=len(rows), status=acct,
                   restricted=[r["copy_id"] for r in rows if r["access_class"].startswith("SEGREGATE")],
                   exact_anchor_copies=[r["copy_id"] for r in rows if r["kb_exact_anchor_rows"] not in ("", "0")],
                   in_git_objects=sum(1 for r in rows if r["git_object_present"] == "YES"),
                   in_hf_listing=sum(1 for r in rows if r["hf_listing_present"] == "YES"),
                   possible_markings=sorted({x["copy_id"] for x in scan if x["classification"].startswith("POSSIBLE")}),
                   total_bytes=sum(int(r["bytes"]) for r in rows if r["bytes"] != ""),
                   register_commit=REGISTER_COMMIT)
    return {"PRESERVATION_INVENTORY.csv": csv_text(fields, rows),
            "SOURCE_MANIFEST.sha256": sums,
            "MARKING_SCAN.csv": csv_text(["copy_id", "page", "term", "context", "classification"], scan),
            "PRESERVATION_SUMMARY.json": json.dumps(summary, indent=1, sort_keys=True) + "\n"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    out = build(a.repo, os.environ.get("MIMAMSA_WORKING_STORE", ""))
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        if bad:
            print("CHECK FAILED:", ", ".join(bad)); return 1
        print(f"preservation outputs reproduce ({len(out)} files)"); return 0
    OUT.mkdir(exist_ok=True)
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(out["PRESERVATION_SUMMARY.json"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
