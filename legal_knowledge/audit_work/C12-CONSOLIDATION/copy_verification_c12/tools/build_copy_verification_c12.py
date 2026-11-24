#!/usr/bin/env python3
"""C12 per-copy source verification manifest, preservation overlay and preservation-risk closure.

Owner directive, Cycle 12 closeout (2026-11-24). Database research only: nothing in a frozen or original register,
the knowledge base, the crawler data or Hugging Face is changed. Every output here is a derivative.

Byte-verification evidence: ../hf_verification_c12/HASH_LEDGER.csv.gz (every HF file at revision 5524c3d9 downloaded
and hashed; `computed_sha256` is the sha256 of the downloaded bytes). A copy is called BYTE_VERIFIED only when that
computed sha256 equals the expected sha256 of the copy. Declared hashes, LFS pointers and size matches are not used
as byte verification.

  python -I -B tools/build_copy_verification_c12.py               # build all outputs (offline, deterministic)
  python -I -B tools/build_copy_verification_c12.py --check       # rebuild in memory and byte-compare
  python -I -B tools/build_copy_verification_c12.py rehash-local  # re-hash local working copies (4 retrieved + 25
                                                                  # acquired) into LOCAL_REHASH_C12.csv (evidence)
  python -I -B tools/build_copy_verification_c12.py rehash-hf-ingested  # network: re-download the 18 ingested raw
                                                                  # copies at HF 15bd03cc, hash them (evidence)

Refresh C12-v2 (after judicial_recovery_c12, git fe9f4332): 18 of the 25 acquisitions ingested at HF 15bd03cc,
7 excluded as not relevant; HF af7f9d06 added derived text/meta for the 4 SC originals (not source copies).
"""
import csv, gzip, hashlib, io, json, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent          # copy_verification_c12/
PKG = OUT.parent                                       # C12-CONSOLIDATION/
AW = PKG.parent                                        # audit_work/
REV = "5524c3d99b6a069249012fecea75093b875a22c7"
REPO = "hariomahlawat/mimamsa-corpus"
VERSION = "C12-v2"
LEDGER_REL = "legal_knowledge/audit_work/C12-CONSOLIDATION/hf_verification_c12/HASH_LEDGER.csv.gz"
PRES_PREFIX = "legal_knowledge/preservation/c5_working_store/"

IN = {
    "c10_inventory": AW / "C10-RECONCILIATION/outputs/UNIFIED_CORPUS_INVENTORY.csv",
    "c10_manifest": AW / "C10-RECONCILIATION/outputs/RECONCILIATION_MANIFEST.json",
    "c10_equivalence": AW / "C10-RECONCILIATION/outputs/COPY_EQUIVALENCE_REGISTER.csv",
    "c10_missing": AW / "C10-RECONCILIATION/outputs/MISSING_SOURCE_EVIDENCE.csv",
    "c10_citation_coverage": AW / "C10-RECONCILIATION/workstreams/quality/outputs/citation_coverage_c10.csv",
    "c10_quality_inventory_snapshot": AW / "C10-RECONCILIATION/workstreams/quality/inputs/c10_outputs_snapshot/UNIFIED_CORPUS_INVENTORY.csv",
    "c5_copy_register": AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv",
    "c5_master_register": AW / "SOURCE-LIBRARY-C5/registers/source_master_register.csv",
    "ledger_v0000_copy_register": AW / "AUTH-LEDGER/effective/v0000/source_copy_register.csv",
    "c11_preservation_inventory": AW / "C11-JUDICIAL-QUALITY/preservation/PRESERVATION_INVENTORY.csv",
    "c11_source_manifest": AW / "C11-JUDICIAL-QUALITY/preservation/SOURCE_MANIFEST.sha256",
    "c11_identity_register": AW / "C11-JUDICIAL-QUALITY/identity/outputs/JUDGMENT_IDENTITY_REGISTER.csv",
    "c11_incomplete_plan": AW / "C11-JUDICIAL-QUALITY/identity/outputs/INCOMPLETE_23_RECOVERY_PLAN.csv",
    "hf_ledger": PKG / "hf_verification_c12/HASH_LEDGER.csv.gz",
    "hf_summary": PKG / "hf_verification_c12/SUMMARY.json",
    "hf_paths": PKG / "hf_verification_c12/HF_VS_GIT_PATHS.csv",
    "hf_incomplete": PKG / "hf_verification_c12/INCOMPLETE_FILES_HF.csv",
    "hf_retrieved": PKG / "hf_verification_c12/HF_RETRIEVED_CANDIDATES.csv",
    "hf_discrepancies": PKG / "hf_verification_c12/DISCREPANCIES.csv",
    "hf_sha256sums": PKG / "hf_verification_c12/SHA256SUMS",
    "hf_manifest_csv": PKG / "hf_verification_c12/capture_refs/data__manifest.csv.gz",
    "hf_raw_manifest": PKG / "hf_verification_c12/capture_refs/data__raw_manifest.csv.gz",
    "hf_package_sums": PKG / "hf_verification_c12/capture_refs/legal_knowledge__preservation__c5_working_store__PACKAGE_SHA256SUMS.gz",
    "c12_package_sums": PKG / "preservation/PACKAGE_SHA256SUMS_C12.txt",
    "c12_acquisition": PKG / "acquisition/ACQUISITION_MANIFEST.csv",
    "c12_priority_verification": PKG / "statutory_citations/outputs/PRIORITY_VERIFICATION.csv",
    "c12_improvement_matrix": PKG / "statutory_citations/outputs/IMPROVEMENT_MATRIX.csv",
    "local_rehash": OUT / "LOCAL_REHASH_C12.csv",
    "jr_ingestion_log": PKG / "judicial_recovery_c12/INGESTION_LOG.csv",
    "jr_hf_commits": PKG / "judicial_recovery_c12/HF_COMMITS.csv",
    "jr_verification": PKG / "judicial_recovery_c12/VERIFICATION.csv",
    "jr_staged_manifest": PKG / "judicial_recovery_c12/STAGED_MANIFEST.csv",
    "hf_ingested_redownload": OUT / "HF_INGESTED_REDOWNLOAD_C12.csv",
}
REV_B = "15bd03ccce7241b1294176fa7c19ab1c5dc109cb"   # 18 judgments ingested (raw, text, meta)
REV_A = "af7f9d069e71314879c1756f914943d9d2ab777a"   # derived text/meta for the 4 SC originals


def rel(p):
    return str(Path(p).resolve().relative_to(AW.parent.parent))


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rcsv(p):
    if str(p).endswith(".gz"):
        return list(csv.DictReader(io.TextIOWrapper(gzip.open(p), encoding="utf-8", newline="")))
    return list(csv.DictReader(open(p, encoding="utf-8", newline="")))


def wcsv(rows, cols):
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=cols, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return s.getvalue()


def split(v, sep=";"):
    return [t.strip() for t in (v or "").split(sep) if t.strip()]


# --------------------------------------------------------------------------------------------------------------------
def rehash_local():
    rows = []
    for r in rcsv(IN["hf_retrieved"]):
        p = Path(r["saved_to"])
        rows.append(dict(group="HF_RETRIEVED_4", key=r["hf_sha256"], path=str(p), exists="YES" if p.is_file() else "NO",
                         size=str(p.stat().st_size) if p.is_file() else "", sha256=sha_file(p) if p.is_file() else ""))
    for r in rcsv(IN["c12_acquisition"]):
        if r["workstream_target"] != "5":
            continue
        p = Path(r["stored_path"])
        rows.append(dict(group="C12_ACQUISITION_25", key=r["target_id"], path=str(p), exists="YES" if p.is_file() else "NO",
                         size=str(p.stat().st_size) if p.is_file() else "", sha256=sha_file(p) if p.is_file() else ""))
    rows.sort(key=lambda r: (r["group"], r["key"]))
    IN["local_rehash"].write_text(wcsv(rows, ["group", "key", "path", "exists", "size", "sha256"]), encoding="utf-8")
    print(f"LOCAL_REHASH_C12.csv: {len(rows)} rows; present {sum(r['exists'] == 'YES' for r in rows)}")
    return 0


def rehash_hf_ingested():
    import tempfile
    from huggingface_hub import hf_hub_download
    rows = []
    with tempfile.TemporaryDirectory(prefix="cv12_hfdl_") as td:
        for r in rcsv(IN["jr_verification"]):
            if r["hf_commit"] != REV_B or not r["hf_path"].startswith("data/raw/"):
                continue
            f = hf_hub_download(REPO, r["hf_path"], repo_type="dataset", revision=REV_B, local_dir=td)
            rows.append(dict(hf_path=r["hf_path"], revision=REV_B, size=str(os.path.getsize(f)), computed_sha256=sha_file(f)))
    rows.sort(key=lambda r: r["hf_path"])
    IN["hf_ingested_redownload"].write_text(wcsv(rows, ["hf_path", "revision", "size", "computed_sha256"]), encoding="utf-8")
    print(f"HF_INGESTED_REDOWNLOAD_C12.csv: {len(rows)} files downloaded at {REV_B[:8]} and hashed")
    return 0


# --------------------------------------------------------------------------------------------------------------------
def build():
    inp_sha = {k: sha_file(v) for k, v in sorted(IN.items())}
    hf_sums = dict(reversed(l.split("  ", 1)) for l in IN["hf_sha256sums"].read_text().splitlines() if l.strip())
    assert hf_sums["HASH_LEDGER.csv.gz"] == inp_sha["hf_ledger"], "HASH_LEDGER.csv.gz does not match hf_verification_c12/SHA256SUMS"
    hf_summary = json.loads(IN["hf_summary"].read_text())
    assert hf_summary["revision"] == REV

    inv = rcsv(IN["c10_inventory"])
    c10m = json.loads(IN["c10_manifest"].read_text())
    ledger = rcsv(IN["hf_ledger"])
    L = {r["path"]: r for r in ledger}
    by_sha = defaultdict(list)
    for r in ledger:
        by_sha[r["computed_sha256"]].append(r["path"])
    copyreg = {r["copy_id"]: r for r in rcsv(IN["c5_copy_register"])}
    master = {r["source_id"]: r for r in rcsv(IN["c5_master_register"])}
    pres = {r["sha256"]: r for r in rcsv(IN["c11_preservation_inventory"])}
    src_manifest = {l.split()[0]: l.split(None, 1)[1] for l in IN["c11_source_manifest"].read_text().splitlines() if l.strip()}
    ident = {r["sha256"]: r for r in rcsv(IN["c11_identity_register"])}
    incplan = {r["sha256"]: r for r in rcsv(IN["c11_incomplete_plan"])}
    hfinc = {r["stored_sha256"]: r for r in rcsv(IN["hf_incomplete"])}
    retrieved = {r["hf_sha256"]: r for r in rcsv(IN["hf_retrieved"])}
    acq = rcsv(IN["c12_acquisition"])
    acq_by_sha = defaultdict(list)
    for r in acq:
        if r["sha256"]:
            acq_by_sha[r["sha256"]].append(r)
    local = {(r["group"], r["key"]): r for r in rcsv(IN["local_rehash"])} if IN["local_rehash"].exists() else {}
    hfpaths = {r["path"]: r for r in rcsv(IN["hf_paths"])}
    pkg_sums = {}
    for l in gzip.open(IN["hf_package_sums"], "rt").read().splitlines():
        if l.strip():
            h, p = l.split("  ", 1)
            pkg_sums[PRES_PREFIX + p[2:] if p.startswith("./") else PRES_PREFIX + p] = h
    # crawler manifest (HF data/manifest.csv, byte-identical to git ad77758d): doc ids per sha256
    man_ids = defaultdict(set)
    id_shas = defaultdict(set)
    for r in rcsv(IN["hf_manifest_csv"]):
        man_ids[r["sha256"]].add(r["doc_id"])
        id_shas[r["doc_id"]].add(r["sha256"])
    rawman = {r["sha256"]: r for r in rcsv(IN["hf_raw_manifest"])}
    # judicial recovery (post-baseline ingestion)
    jlog = {r["target"]: r for r in rcsv(IN["jr_ingestion_log"]) if r["target"].startswith("T5-")}
    jcommits = {r["label"]: r for r in rcsv(IN["jr_hf_commits"])}
    assert jcommits["B"]["hf_commit"] == REV_B and jcommits["A"]["hf_commit"] == REV_A
    assert jcommits["A"]["parent_commit"] == REV and jcommits["B"]["parent_commit"] == REV_A
    jver = rcsv(IN["jr_verification"])
    jver_by_sha = {r["expected_sha256"]: r for r in jver if r["hf_path"].startswith("data/raw/")}
    redl = {r["hf_path"]: r for r in rcsv(IN["hf_ingested_redownload"])}
    # C10 identity groups
    eq = rcsv(IN["c10_equivalence"])
    id_groups = defaultdict(list)  # sha -> [(group_id, classification)]
    for g in eq:
        if g["classification"] in ("SAME_DOC_ID_DIFFERENT_BYTES_REQUIRES_IDENTITY_REVIEW", "SAME_C5_SOURCE_ID_DIFFERENT_BYTES"):
            for s in split(g["sha256s"]):
                id_groups[s].append(g["group_id"])

    # ---------------------------------------------------------------- 1. per-copy manifest (baseline 4,103)
    inv_sha = {r["sha256"]: r for r in inv}
    rows, exceptions = [], []
    for r in sorted(inv, key=lambda x: x["sha256"]):
        s = r["sha256"]
        seg = r["presence"]
        reg_copy = r["c5_copy_ids"]
        crawler_ids = sorted(man_ids.get(s, set()))
        if reg_copy:
            source_id, copy_id = r["c5_source_ids"], reg_copy
            id_origin = "C5 source_copy_register (frozen; = AUTH-LEDGER v0000)"
        else:
            source_id = ";".join(crawler_ids) or rawman.get(s, {}).get("doc_id") or rawman.get(s, {}).get("parent_doc_id", "") or "NO_SOURCE_ID_RECORDED"
            copy_id = "C12CV-" + s[:16]
            id_origin = ("source_id: crawler data/manifest.csv doc_id(s)" if crawler_ids else
                         "source_id: crawler raw_manifest.csv parent_doc_id (no data/manifest.csv row)" if s in rawman else
                         "source_id: none recorded") + "; copy_id: not registered, derived key C12CV-<sha256[:16]>"
        # hosted path at the pinned revision
        if seg == "C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB":
            cands = [p for p in by_sha.get(s, []) if p.startswith(f"{PRES_PREFIX}{s[:2]}/{s}/") and not p.endswith(".meta.json")]
            hosted = cands[0] if len(cands) == 1 else ""
            origin = "C5 source_copy_register.csv sha256/bytes (C11 PRESERVATION_INVENTORY re-hash PRESENT_HASH_MATCH; C11 SOURCE_MANIFEST.sha256)"
            exp_size = copyreg[reg_copy]["bytes"] if reg_copy in copyreg else r["bytes"]
        elif seg == "HF_ONLY":
            hosted = r["hf_paths"]
            origin = f"C10 UNIFIED_CORPUS_INVENTORY sha256/bytes (HF-declared basis {r['hf_byte_verification']}" + \
                     ("; C5 source_copy_register" if reg_copy else "; no register row") + ")"
            exp_size = r["bytes"]
        else:
            hosted = r["hf_paths"]
            origin = "C10 UNIFIED_CORPUS_INVENTORY sha256/bytes = GitHub raw-data ad77758d re-hash (REHASHED_MATCH) = data/SHA256SUMS" + \
                     ("; C5 source_copy_register" if reg_copy else "")
            exp_size = r["bytes"]
        lr = L.get(hosted)
        comp = lr["computed_sha256"] if lr else ""
        act = lr["computed_size"] if lr else ""
        others = sorted(p for p in by_sha.get(s, []) if p != hosted)
        disc, disp = [], []
        # identity
        iflags = []
        if len(crawler_ids) > 1:
            iflags.append(f"SAME_SHA256_SEVERAL_CRAWLER_DOC_IDS({len(crawler_ids)})")
        multi = sorted(i for i in crawler_ids if len(id_shas[i]) > 1)
        if multi:
            iflags.append("CRAWLER_DOC_ID_SEVERAL_SHA256:" + ",".join(multi))
        if id_groups.get(s):
            iflags.append("C10_ID_SEVERAL_SHA256:" + ",".join(sorted(id_groups[s])))
        if others:
            iflags.append(f"SAME_SHA256_SEVERAL_HF_PATHS({len(others) + 1})")
        identity = "DUPLICATE_IDENTITY" if iflags else "UNIQUE"
        # byte status
        ev = f"{LEDGER_REL} row path={hosted}" if lr else ""
        if not lr:
            status = "MISSING_ON_HF"
            disc.append("no file at the expected hosted path in the revision-pinned ledger" + (f"; same sha256 at {others}" if others else ""))
            disp.append("Locate the copy; re-upload with owner approval if absent")
        elif comp != s:
            status = "HASH_MISMATCH"
            disc.append(f"computed {comp} != expected {s}")
            disp.append("Treat HF copy as unverified; compare with GitHub/working copy; owner decision before any replacement")
        elif str(act) != str(exp_size):
            status = "HASH_MISMATCH"
            disc.append(f"sha256 equal but size {act} != expected {exp_size}")
            disp.append("Size record error to investigate; bytes match")
        else:
            status = "BYTE_VERIFIED"
            if "BYTE_VERIFIED_SERVER_HASH_MATCH" not in lr["statuses"].split(";"):
                disc.append("ledger lacks BYTE_VERIFIED_SERVER_HASH_MATCH")
            j = ident.get(s)
            sc = j["source_completeness"] if j else ""
            if lr["is_pdf"] == "YES":
                opens, eof = lr["pdf_opens"].startswith("YES"), lr["trailing_eof"] == "YES"
                if sc == "STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING" or (not j and not (opens and eof)):
                    status = "BYTE_VERIFIED_INCOMPLETE_DOCUMENT"
                    disc.append(f"truncated PDF (opens={lr['pdf_opens'][:40]}; trailing %%EOF={lr['trailing_eof']}); C11 {sc or 'not classified'}")
                    p, a = incplan.get(s, {}), acq_by_sha.get(s, [])
                    disp.append("Hash matches the recorded copy; content incomplete. " +
                                (f"C11 plan: {p.get('complete_copy_status', '')} / {p.get('recovery_action', '')}. " if p else "") +
                                (f"C12 re-fetch: {a[0]['relation_to_existing_copy']}. " if a else "") +
                                "Next: seek a complete official copy (court portal) with owner approval; keep this file as the recorded copy; do not use for page anchors")
                elif sc == "STORED_COPY_TAIL_CUT_AFTER_EARLIER_EOF_BASE_REVISION_PRESENT":
                    status = "BYTE_VERIFIED_TRUNCATED_TAIL_BASE_REVISION_PRESENT"
                    disc.append(f"file tail cut inside a later signature update; earlier %%EOF and base revision present (C11 {j['version_role']}); trailing %%EOF={lr['trailing_eof']}")
                    disp.append("Hash matches; judgment pages readable from the base revision; signature update lost. Next: low priority re-fetch of a complete signed copy; usable for text with this caveat")
                elif sc == "NOT_AVAILABLE":
                    if opens and eof:
                        disc.append("C11 listed bytes NOT_AVAILABLE (UNKNOWN_BYTES_UNAVAILABLE); HF copy opens and ends with %%EOF")
                        disp.append("Superseded by C12: complete-structure HF copy byte-verified; local copy retrieved (HF_RETRIEVED_CANDIDATES). Next: update C11 identity status in a later overlay; text completeness not proven by structure checks")
                    else:
                        status = "BYTE_VERIFIED_INCOMPLETE_DOCUMENT"
                        disc.append("C11 NOT_AVAILABLE and HF copy fails structure checks")
                        disp.append("Seek complete copy")
            if status == "BYTE_VERIFIED" and not disp:
                disp.append("None required" if identity == "UNIQUE" else "Bytes verified; identity flag recorded (see INVESTIGATIONS_C12.csv)")
        if identity != "UNIQUE":
            disc.append("identity: " + "; ".join(iflags))
        rows.append(dict(
            source_id=source_id, copy_id=copy_id, title=r["title"], category=r["category"], hosted_path=hosted,
            dataset_revision=REV if lr else "", expected_sha256=s, expected_sha256_origin=origin, computed_sha256=comp,
            expected_size=exp_size, actual_size=act, verification_status=status, discrepancy=" | ".join(disc),
            disposition=" | ".join(disp), baseline_segment=seg, register_state=r["register_state"], id_origin=id_origin,
            crawler_doc_ids=";".join(crawler_ids), identity_status=identity, identity_flags=";".join(iflags),
            other_hf_paths_same_sha256=";".join(others), pdf_opens=(lr or {}).get("pdf_opens", "")[:60],
            pdf_trailing_eof=(lr or {}).get("trailing_eof", ""), c11_source_completeness=(ident.get(s) or {}).get("source_completeness", ""),
            verification_evidence=ev))
    MCOLS = ["source_id", "copy_id", "title", "category", "hosted_path", "dataset_revision", "expected_sha256",
             "expected_sha256_origin", "computed_sha256", "expected_size", "actual_size", "verification_status", "discrepancy",
             "disposition", "baseline_segment", "register_state", "id_origin", "crawler_doc_ids", "identity_status",
             "identity_flags", "other_hf_paths_same_sha256", "pdf_opens", "pdf_trailing_eof", "c11_source_completeness",
             "verification_evidence"]
    mrow = {r["expected_sha256"]: r for r in rows}

    # ---------------------------------------------------------------- 2. preservation overlay (48)
    reg_sha = inp_sha["c5_copy_register"]
    overlay = []
    for p in sorted(pres.values(), key=lambda x: x["copy_id"]):
        s = p["sha256"]
        m = mrow[s]
        cr = copyreg[p["copy_id"]]
        side = m["hosted_path"] + ".meta.json"
        ok = (m["verification_status"] == "BYTE_VERIFIED" and m["computed_sha256"] == s == cr["sha256"]
              and pkg_sums.get(m["hosted_path"]) == s and s in src_manifest
              and "C5_PACKAGE_SHA256SUMS_MATCH" in L[m["hosted_path"]]["statuses"].split(";") and side in L)
        overlay.append(dict(
            overlay_version=VERSION, copy_id=p["copy_id"], source_id=p["source_id"], title=p["title"], sha256=s,
            bytes=cr["bytes"], original_register="legal_knowledge/audit_work/SOURCE-LIBRARY-C5/registers/source_copy_register.csv",
            original_register_sha256=reg_sha, original_held_paths=cr["held_paths"], original_register_row="UNCHANGED",
            permanent_hosted_path=m["hosted_path"], sidecar_hosted_path=side if side in L else "", hf_repo=REPO,
            hf_revision=REV, computed_sha256=m["computed_sha256"], actual_size=m["actual_size"],
            package_sha256sums_match="YES" if pkg_sums.get(m["hosted_path"]) == s else "NO",
            c11_source_manifest_match="YES" if s in src_manifest else "NO",
            preservation_status="PRESERVED_HF_BYTE_VERIFIED" if ok else "PRESERVATION_NOT_VERIFIED",
            verification_evidence=f"{LEDGER_REL} (computed_sha256 of bytes downloaded at {REV[:8]}); hf_verification_c12/capture_refs PACKAGE_SHA256SUMS; C11 preservation/SOURCE_MANIFEST.sha256",
            copy_evidence_class_unchanged=cr["copy_evidence_class"], copy_effective_status_unchanged=cr["copy_effective_status"],
            status="PRESERVATION_RECORDED_DERIVATIVE_OVERLAY_ORIGINAL_UNCHANGED",
            verification="TECHNICAL_BYTE_INTEGRITY_CHECK_NOT_LEGAL_AUTHENTICATION"))
    OCOLS = list(overlay[0].keys())
    preserved = {o["sha256"] for o in overlay if o["preservation_status"] == "PRESERVED_HF_BYTE_VERIFIED"}

    # ---------------------------------------------------------------- 3. preservation-risk closure (274)
    cov = rcsv(IN["c10_citation_coverage"])
    pv = defaultdict(set)
    for x in rcsv(IN["c12_priority_verification"]):
        for s in split(x["copy_sha256"]):
            pv[x["item_id"]].add(s)
    im = {x["item_id"]: x for x in rcsv(IN["c12_improvement_matrix"])}
    sha_by_copy = {k: v["sha256"] for k, v in copyreg.items()}
    closure = []
    for c in cov:
        if c["A_availability_c10"] != "HELD_WORKING_STORE_ONLY_EPHEMERAL":
            continue
        deps = {}
        for e in split(c["A_registered_copies"]):
            cid, s12, store = e.split(":")
            s = sha_by_copy[cid]
            assert s.startswith(s12)
            deps[s] = (cid, "C10 A_registered_copies")
        for s in sorted(pv.get(c["item_id"], ())):
            if s not in deps:
                cid = next((k for k, v in sha_by_copy.items() if v == s), "")
                deps[s] = (cid, "C12 PRIORITY_VERIFICATION copy_sha256")
        parts, bad = [], []
        for s, (cid, o) in sorted(deps.items(), key=lambda kv: kv[1][0]):
            st = "PRESERVED_HF_BYTE_VERIFIED" if s in preserved else (mrow[s]["verification_status"] + "/" + mrow[s]["baseline_segment"] if s in mrow else "NOT_IN_INVENTORY")
            parts.append(f"{cid}:{s[:12]}:{st} [{o}]")
            if s not in preserved:
                bad.append(f"{cid or s[:12]} is {st}")
        imx = im.get(c["item_id"], {})
        closure.append(dict(
            item_id=c["item_id"], crosswalk_line=c["crosswalk_line"], knowledge_base_record_id=c["knowledge_base_record_id"],
            source_id=c["source_id"], provision_id=c["provision_id"], dependent_copies=" ; ".join(parts),
            dependent_copy_count=len(deps), preserved_verified_count=sum(s in preserved for s in deps),
            A_availability_c10_unchanged=c["A_availability_c10"],
            availability_risk_before="OPEN (C10: every registered copy held only in the ephemeral C5 working store)",
            availability_risk_c12="CLOSED" if not bad else "REMAINS_OPEN",
            closure_reason=("every copy the item depends on is PRESERVED_HF_BYTE_VERIFIED at " + REV[:8] + " (SOURCE_REGISTER_PRESERVATION_OVERLAY_C12.csv)") if not bad else "; ".join(bad),
            C_resolution_c10_unchanged=c["C_resolution_c10"], B_ledger_v0000_holding_state_unchanged=c["B_ledger_v0000_holding_state"],
            B_ledger_copy_evidence_classes_unchanged=c["B_ledger_copy_evidence_classes"],
            B_anchor_copy_effective_status_unchanged=c["B_anchor_copy_effective_status"], D_kb_status_unchanged=c["D_kb_status"],
            c12f_state_proposed_unchanged=imx.get("c12_state_proposed", ""), c12f_change_unchanged=imx.get("c12_change", ""),
            evidence_classification_change="NONE (availability-risk field only; authentication, evidence class, resolution and KB status unchanged)",
            overlay_version=VERSION, status="RISK_CLOSURE_DERIVATIVE_OVERLAY_ORIGINAL_UNCHANGED"))
    CCOLS = list(closure[0].keys())
    # items outside the 274 that depend on one of the 48 through C12 PRIORITY_VERIFICATION (should be none)
    cov_ids = {c["item_id"] for c in closure}
    outside = sorted(i for i, ss in pv.items() if i not in cov_ids and ss & set(pres))

    # ---------------------------------------------------------------- 4. post-baseline additions
    adds = []
    for p in sorted(x for x in L if "HF_ONLY" in L[x]["statuses"].split(";")):
        lr = L[p]
        s = lr["computed_sha256"]
        ext = p.rsplit(".", 1)[-1].lower() if "." in p.rsplit("/", 1)[-1] else ""
        if s in inv_sha and inv_sha[s]["presence"] == "HF_ONLY":
            cls, note = "BASELINE_HF_ONLY_SOURCE_COPY", "one of the 16 baseline HF-only copies (in the 4,103)"
        elif s in inv_sha and inv_sha[s]["presence"].startswith("C5_"):
            cls, note = "PRESERVED_COPY_OF_BASELINE_WS_ONLY_COPY", "new hosted path for one of the 48 baseline working-store-only copies (in the 4,103)"
        elif s in inv_sha:
            cls, note = "SECOND_PATH_OF_BASELINE_COPY", "same bytes as a baseline copy"
        elif p.startswith("legal_knowledge/preservation/"):
            cls, note = "PRESERVATION_PACKAGE_METADATA", "sidecar, checksum list or provenance file of the C12 preservation upload"
        elif ext in ("pdf", "doc", "docx", "zip", "tif", "tiff", "png", "jpg", "jpeg"):
            cls, note = "UNEXPECTED_SOURCE_BINARY_NOT_IN_INVENTORY", "binary not in the baseline inventory: investigate"
        else:
            cls, note = "NON_SOURCE_FILE", "documentation, derived data or configuration; not a source copy"
        adds.append(dict(addition_group="HF_ONLY_PATH_277", key=p, sha256=s, size=lr["computed_size"], classification=cls,
                         new_distinct_source_copy="NO" if cls != "UNEXPECTED_SOURCE_BINARY_NOT_IN_INVENTORY" else "UNDETERMINED",
                         byte_status="BYTE_VERIFIED" if "BYTE_VERIFIED_SERVER_HASH_MATCH" in lr["statuses"] else "NOT_VERIFIED",
                         hf_revision=REV, legal_knowledge_vs_staging=hfpaths.get(p, {}).get("legal_knowledge_vs_staging", ""),
                         status="ON_HF_BYTE_VERIFIED", note=note))
    for s, r in sorted(retrieved.items()):
        lo = local.get(("HF_RETRIEVED_4", s), {})
        adds.append(dict(addition_group="HF_RETRIEVED_4", key=r["saved_to"], sha256=s, size=r["bytes"],
                         classification="LOCAL_WORKING_COPY_OF_BASELINE_HF_ONLY_COPY", new_distinct_source_copy="NO",
                         byte_status=("BYTE_VERIFIED (HF) ; LOCAL_REHASH_MATCH" if lo.get("sha256") == s else
                                      f"BYTE_VERIFIED (HF) ; LOCAL_REHASH {'MISMATCH' if lo.get('sha256') else 'NOT_AVAILABLE'}"),
                         hf_revision=REV, status="IN_BASELINE_HF_ONLY; LOCAL_COPY_RETRIEVED",
                         note=f"HF path {r['hf_path']}; {r['status']}; {r['pages']} pages"))
    a25 = [r for r in acq if r["workstream_target"] == "5"]
    for r in sorted(a25, key=lambda x: x["target_id"]):
        s = r["sha256"]
        lo = local.get(("C12_ACQUISITION_25", r["target_id"]), {})
        ing = ingest_status(r, jlog, jver_by_sha, redl, lo)
        new = s not in inv_sha and s not in by_sha
        adds.append(dict(addition_group="C12_ACQUISITION_25", key=r["target_id"], sha256=s, size=r["bytes"],
                         classification="NEW_COPY_INGESTED_C12" if ing["status"] == "INGESTED_HF_BYTE_VERIFIED" else
                                        "NEW_COPY_ACQUIRED_EXCLUDED_NOT_RELEVANT" if ing["status"].startswith("EXCLUDED") else "NEW_COPY_ACQUIRED_C12",
                         new_distinct_source_copy=("YES" if new and ing["status"] == "INGESTED_HF_BYTE_VERIFIED" else
                                                   "NO (excluded; held locally only)" if new and ing["status"].startswith("EXCLUDED") else
                                                   "UNDETERMINED" if new else "NO"),
                         byte_status=ing["byte_status"], hf_revision=ing["hf_revision"], status=ing["status"],
                         note=f"{r['description']}; {r['completeness']}; {ing['note']}"))
    for v in sorted(jver, key=lambda x: (x["label"], x["hf_path"])):
        if v["hf_path"].startswith("data/raw/") or v["result"] != "MATCH":
            continue  # raw copies are rows above; tree-diff rows are not files
        adds.append(dict(addition_group=f"JUDICIAL_RECOVERY_DERIVED_{v['label']}", key=v["hf_path"], sha256=v["downloaded_sha256"],
                         size=v["bytes"], classification="DERIVED_OR_MANIFEST_FILE_NOT_SOURCE_COPY", new_distinct_source_copy="NO",
                         byte_status="BYTE_VERIFIED (judicial_recovery_c12 VERIFICATION.csv: re-downloaded hash " + v["result"] + ")",
                         hf_revision=v["hf_commit"], status="ON_HF_DERIVED",
                         note="derived text/meta for the 4 SC originals" if v["label"] == "A" else "text/meta/additive manifest for the 18 ingested judgments"))
    ACOLS = ["addition_group", "key", "sha256", "size", "classification", "new_distinct_source_copy", "byte_status",
             "hf_revision", "legal_knowledge_vs_staging", "status", "note"]

    # ---------------------------------------------------------------- 5. canonical inventory additions (48 + 4 + 25)
    canon = []
    for o in overlay:
        canon.append(dict(addition_group="C11_C12_PRESERVED_48", sha256=o["sha256"], id=o["copy_id"], title=o["title"],
                          in_canonical_inventory="YES", canonical_inventory_segment=inv_sha[o["sha256"]]["presence"],
                          hosted_path=o["permanent_hosted_path"], hf_revision=REV, computed_sha256=o["computed_sha256"],
                          local_rehash="", status="IN_CANONICAL_INVENTORY; " + o["preservation_status"],
                          next_action="None for availability. C10 inventory row stays frozen; a later inventory version should record the HF path"))
    for s, r in sorted(retrieved.items()):
        lo = local.get(("HF_RETRIEVED_4", s), {})
        m = mrow[s]
        canon.append(dict(addition_group="HF_RETRIEVED_4", sha256=s, id=m["copy_id"], title=m["title"],
                          in_canonical_inventory="YES" if s in inv_sha else "NO", canonical_inventory_segment=inv_sha.get(s, {}).get("presence", ""),
                          hosted_path=m["hosted_path"], hf_revision=REV, computed_sha256=m["computed_sha256"],
                          local_rehash=("MATCH " if lo.get("sha256") == s else "NO_MATCH ") + r["saved_to"],
                          status=f"IN_CANONICAL_INVENTORY; {m['verification_status']}; LOCAL_WORKING_COPY_RETRIEVED",
                          next_action="Record in C11 identity status (was NOT_AVAILABLE) via a later overlay; no new copy"))
    for r in sorted(a25, key=lambda x: x["target_id"]):
        s = r["sha256"]
        lo = local.get(("C12_ACQUISITION_25", r["target_id"]), {})
        did = (re.search(r"doc_id (\S+)", r["provenance"]) or [None, ""])[1]
        ing = ingest_status(r, jlog, jver_by_sha, redl, lo)
        canon.append(dict(addition_group="C12_ACQUISITION_25", sha256=s, id=f"{r['target_id']} / {did}", title=r["description"],
                          in_canonical_inventory=("YES (C10)" if s in inv_sha else
                                                  "ADDED_POST_BASELINE (HF data/manifest_additions/c12_2026-11-24_*; C10 inventory frozen)" if ing["status"] == "INGESTED_HF_BYTE_VERIFIED" else
                                                  "NO (excluded; listed here and in judicial_recovery_c12/INGESTION_LOG.csv)"),
                          canonical_inventory_segment=inv_sha.get(s, {}).get("presence", "") or ("crawler doc_id present in data/manifest.csv@5524c3d9" if did in id_shas else "doc_id not in data/manifest.csv@5524c3d9 (crawler-excluded title)"),
                          hosted_path=ing["hosted_path"], hf_revision=ing["hf_revision"], computed_sha256=ing["computed_sha256"],
                          local_rehash=("MATCH " if lo.get("sha256") == s else "NO_MATCH ") + r["stored_path"],
                          status=ing["status"], next_action=ing["next_action"]))
    KCOLS = list(canon[0].keys())

    # ---------------------------------------------------------------- 6. investigations
    inv_rows = []

    def add(kind, subject, n, detail, evidence, explanation, nxt):
        inv_rows.append(dict(investigation_id=f"CV12-{len(inv_rows) + 1:03d}", kind=kind, subject=subject, copies_affected=n,
                             detail=detail, evidence=evidence, explanation=explanation, next_action=nxt, change_made="NONE"))

    st = Counter(r["verification_status"] for r in rows)
    add("MISSING_ON_HF", "baseline copies", st.get("MISSING_ON_HF", 0), "copies with no file at the expected hosted path at " + REV[:8],
        LEDGER_REL, "None missing: every one of the 4,103 copies has a hosted file at the pinned revision" if not st.get("MISSING_ON_HF") else "see manifest rows",
        "None" if not st.get("MISSING_ON_HF") else "Locate and re-upload with owner approval")
    add("HASH_MISMATCH", "baseline copies", st.get("HASH_MISMATCH", 0), "computed sha256 or size differs from the expected value",
        LEDGER_REL, "No mismatch" if not st.get("HASH_MISMATCH") else "see manifest rows", "None" if not st.get("HASH_MISMATCH") else "Investigate before use")
    for r in rows:
        if r["verification_status"] == "BYTE_VERIFIED_INCOMPLETE_DOCUMENT":
            add("INCOMPLETE_DOCUMENT", r["expected_sha256"], 1, f"{r['title']} | {r['hosted_path']} | {r['discrepancy'].split(' | ')[0]}",
                "C11 JUDGMENT_IDENTITY_REGISTER; C11 INCOMPLETE_23_RECOVERY_PLAN; hf_verification_c12/INCOMPLETE_FILES_HF.csv; C12 acquisition re-fetch",
                "Stored, HF and (where re-fetched) remote copies are byte-identical and truncated; the hash proves the record, not completeness",
                r["disposition"].split(" | ")[0])
    tail = [r for r in rows if r["verification_status"] == "BYTE_VERIFIED_TRUNCATED_TAIL_BASE_REVISION_PRESENT"]
    add("TRUNCATED_TAIL_BASE_REVISION_PRESENT", ";".join(r["expected_sha256"][:12] for r in tail), len(tail),
        "PDFs whose last 1,024 bytes lack %%EOF but which open; C11 found an earlier %%EOF and the complete base revision",
        "C11 JUDGMENT_IDENTITY_REGISTER version_role BASE_REVISION_ONLY_SIGNATURE_UPDATE_CUT; ledger trailing_eof",
        "The crawler copy was cut inside an incremental (digital-signature) update; judgment pages are present",
        "Optional re-fetch of complete signed copies; flag signature as unverifiable; no anchor impact recorded")
    nonfour = [r for r in rows if r["c11_source_completeness"] == "NOT_AVAILABLE"]
    add("C11_BYTES_UNAVAILABLE_NOW_VERIFIED", ";".join(r["expected_sha256"][:12] for r in nonfour), len(nonfour),
        "C11 recorded these 4 HF-only SC copies as NOT_AVAILABLE (no local bytes); they are among the 16 baseline HF-only copies",
        "hf_verification_c12 INCOMPLETE_FILES_HF.csv verdict HF_ONLY_NO_LOCAL_BYTES_HF_COPY_OPENS_WITH_EOF_RETRIEVED; HF_RETRIEVED_CANDIDATES.csv",
        "HF bytes match the recorded sha256, open and end with %%EOF; saved locally as working copies",
        "Record in a later C11 identity overlay; no replacement; text completeness not proven by structure checks")
    # duplicate identity: same sha under several crawler doc ids
    multi_id = sorted((s, sorted(ids)) for s, ids in man_ids.items() if len(ids) > 1 and s in inv_sha)
    sc_year = [(s, ids) for s, ids in multi_id if all(i.startswith("sc-") for i in ids) and len({re.sub(r"^sc-\d{4}-", "", i) for i in ids}) == 1]
    other = [(s, ids) for s, ids in multi_id if (s, ids) not in sc_year]
    add("DUPLICATE_IDENTITY_SAME_SHA256_SEVERAL_IDS", ";".join(s[:12] for s, _ in sc_year), len(sc_year),
        "one SC file under two crawler doc_ids that differ only in the year prefix (e.g. " + (sc_year[0][1][0] + " / " + sc_year[0][1][1] if sc_year else "") + ")",
        "HF data/manifest.csv at " + REV[:8] + " (identical to git ad77758d)",
        "Crawler minted a doc_id per year bucket (judgment year vs. reporting year) for the same INSC citation; one copy, two metadata records",
        "Metadata de-duplication proposal (keep one doc_id, alias the other) for owner review; bytes unaffected")
    add("DUPLICATE_IDENTITY_SAME_SHA256_SEVERAL_IDS", ";".join(s[:12] for s, _ in other), len(other),
        f"one file under 2 to {max([len(i) for _, i in other] or [0])} crawler doc_ids: HC common orders (one order disposing several writs) and Tribunals Reforms Act/notification",
        "HF data/manifest.csv at " + REV[:8],
        "Expected for common judgments (one PDF, several case numbers); for act-the-tribunals-reforms-act-2021 / notif-tribunal-reforms one PDF filed as two document types",
        "Keep; record case-number aliases; check the Tribunals Reforms pair's doc_type in a metadata review")
    for g in eq:
        if g["classification"] in ("SAME_DOC_ID_DIFFERENT_BYTES_REQUIRES_IDENTITY_REVIEW", "SAME_C5_SOURCE_ID_DIFFERENT_BYTES"):
            add("DUPLICATE_IDENTITY_ONE_ID_SEVERAL_SHA256", g["group_id"], g["copies"], g["basis"][:300],
                "C10 COPY_EQUIVALENCE_REGISTER " + g["group_id"],
                "Attachments, language renditions or versions under one crawler doc_id / C5 source id (already flagged in C10); every copy byte-verified",
                g["review"][:200] + "; no change")
    nmulti_hf = sum(1 for r in rows if r["other_hf_paths_same_sha256"])
    add("DUPLICATE_IDENTITY_SAME_SHA256_SEVERAL_PATHS", "baseline copies", nmulti_hf,
        "baseline copies whose bytes appear at more than one HF path", LEDGER_REL,
        "None: each of the 4,103 copies is at exactly one HF path" if not nmulti_hf else "see identity_flags", "None")
    # unexpected files
    ucls = Counter(a["classification"] for a in adds if a["addition_group"] == "HF_ONLY_PATH_277")
    add("UNEXPECTED_FILES_HF_ONLY_PATHS", "HF-only paths vs git ad77758d", sum(ucls.values()),
        "; ".join(f"{k} {v}" for k, v in sorted(ucls.items())), "hf_verification_c12 HF_VS_GIT_PATHS.csv; POST_BASELINE_ADDITIONS_C12.csv",
        "No unexpected source binary. The 277 paths are the 16 baseline HF-only copies, the 48 preserved copies, the preservation package files and non-source documentation/derived files",
        "None for copy verification; staging/HF divergence of legal_knowledge/ is a separate governance item")
    dk = Counter(d["kind"] for d in rcsv(IN["hf_discrepancies"]))
    add("HF_VS_GIT_DISCREPANCIES", "README.md; data/raw_manifest.csv; schema/*.json; 21 raw JSON", sum(dk.values()),
        "; ".join(f"{k} {v}" for k, v in sorted(dk.items())), "hf_verification_c12 DISCREPANCIES.csv",
        "None is a source copy mismatch: 5 non-source files differ by design (HF README, column-reduced raw_manifest, newer schemas); 21 raw India Code JSON listings are byte-verified copies that data/manifest.csv does not list",
        "No copy action; consider listing the 21 JSON copies in the manifest in a later crawler release")
    add("ACCESS_MARKING_OWNER_ATTENTION", "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14", 1,
        "baseline copy (RAF 2000 India Code PDF) prints 'For Official Use Only'; byte-verified on the private HF dataset",
        "hf_verification_c12 MARKING_HITS.csv; COORDINATOR_NOTES.md", "Already hosted privately; not among the 48",
        "Owner decision on quarantine/visibility under repository governance; nothing changed here")
    ist = Counter(ingest_status(r, jlog, jver_by_sha, redl, local.get(("C12_ACQUISITION_25", r["target_id"]), {}))["status"] for r in a25)
    add("C12_ACQUISITIONS_INGESTION", "C12 acquisitions", len(a25), "; ".join(f"{k} {v}" for k, v in sorted(ist.items())),
        "judicial_recovery_c12 INGESTION_LOG.csv, HF_COMMITS.csv, VERIFICATION.csv; HF_INGESTED_REDOWNLOAD_C12.csv; LOCAL_REHASH_C12.csv",
        f"18 ingested additively at HF {REV_B[:8]} and byte-verified here by re-download; 7 excluded as not relevant (LLM relevance review, not legal review) and held only in the session working store",
        "Excluded 7: owner to confirm exclusion and decide whether to keep the local bytes; nothing deleted. Ingested 18: record in the next canonical inventory version")
    if outside:
        add("PRESERVATION_DEPENDENCY_OUTSIDE_274", ";".join(outside), len(outside), "items outside the 274 that cite one of the 48 via C12",
            "C12 PRIORITY_VERIFICATION", "", "Review")
    VCOLS = ["investigation_id", "kind", "subject", "copies_affected", "detail", "evidence", "explanation", "next_action", "change_made"]

    # ---------------------------------------------------------------- summary + README
    seg = Counter(r["baseline_segment"] for r in rows)
    reg_by_seg = Counter(r["baseline_segment"] for r in rows if r["register_state"] == "REGISTERED")
    clos = Counter(c["availability_risk_c12"] for c in closure)
    clos_src = Counter(c["source_id"] for c in closure)
    ident_c = Counter(r["identity_status"] for r in rows)
    vs_seg = Counter((r["baseline_segment"], r["verification_status"]) for r in rows)
    summary = dict(
        version=VERSION, hf_repo=REPO, hf_revision=REV, byte_evidence=LEDGER_REL,
        baseline=dict(source="C10 UNIFIED_CORPUS_INVENTORY.csv", rows=len(inv), distinct_sha256=len(inv_sha),
                      c10_manifest_distinct_copies=c10m["summary"]["distinct_copies"], segments=dict(sorted(seg.items())),
                      registered_by_segment=dict(sorted(reg_by_seg.items())), c5_copy_register_rows=len(copyreg),
                      equals_4103=(len(inv_sha) == 4103 and seg["HF_AND_GITHUB_RAW_DATA"] + seg["HF_ONLY"] + seg["C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB"] == 4103)),
        verification_status=dict(sorted(st.items())), verification_status_by_segment={f"{a}|{b}": n for (a, b), n in sorted(vs_seg.items())},
        identity_status=dict(sorted(ident_c.items())),
        preservation_overlay=dict(Counter(o["preservation_status"] for o in overlay)),
        risk_closure=dict(items=len(closure), outcome=dict(sorted(clos.items())), by_source=dict(sorted(clos_src.items())),
                          resolution=dict(sorted(Counter(c["C_resolution_c10_unchanged"] for c in closure).items())),
                          items_with_c12_extra_dependencies=sum(1 for c in closure if "C12 PRIORITY_VERIFICATION" in c["dependent_copies"]),
                          items_outside_274_depending_on_48=len(outside)),
        additions=dict(Counter(f"{a['addition_group']}|{a['classification']}" for a in adds)),
        canonical_additions=dict(Counter(f"{k['addition_group']}|{k['status']}" for k in canon)),
        new_distinct_copies_after_baseline=sum(1 for a in adds if a["new_distinct_source_copy"] == "YES"),
        distinct_source_copies_on_hf=dict(baseline=len(inv_sha), ingested_post_baseline=sum(1 for a in adds if a["new_distinct_source_copy"] == "YES"),
                                          total=len(inv_sha) + sum(1 for a in adds if a["new_distinct_source_copy"] == "YES"),
                                          equals_4121=len(inv_sha) + sum(1 for a in adds if a["new_distinct_source_copy"] == "YES") == 4121,
                                          excluded_held_locally_not_hosted=sum(1 for a in adds if a["new_distinct_source_copy"].startswith("NO (excluded")),
                                          revisions=dict(baseline=REV, derived_4_sc=REV_A, ingested_18=REV_B)),
        local_rehash_rows=len(local), investigations=len(inv_rows),
        inputs={k: dict(path=rel(v), sha256=inp_sha[k]) for k, v in sorted(IN.items())},
        frozen_registers_unchanged_check=dict(c5_copy_register_equals_auth_ledger_v0000=inp_sha["c5_copy_register"] == inp_sha["ledger_v0000_copy_register"],
                                              c10_inventory_equals_quality_snapshot=inp_sha["c10_inventory"] == inp_sha["c10_quality_inventory_snapshot"]))
    files = {
        "COPY_VERIFICATION_MANIFEST.csv": wcsv(rows, MCOLS),
        "SOURCE_REGISTER_PRESERVATION_OVERLAY_C12.csv": wcsv(overlay, OCOLS),
        "PRESERVATION_RISK_CLOSURE_C12.csv": wcsv(closure, CCOLS),
        "POST_BASELINE_ADDITIONS_C12.csv": wcsv(adds, ACOLS),
        "CANONICAL_INVENTORY_ADDITIONS_C12.csv": wcsv(canon, KCOLS),
        "INVESTIGATIONS_C12.csv": wcsv(inv_rows, VCOLS),
        "SUMMARY_C12.json": json.dumps(summary, indent=1, sort_keys=True) + "\n",
    }
    files["README.md"] = readme(summary, inv_rows, st, seg, reg_by_seg, clos, clos_src, adds, canon, ident_c, vs_seg)
    names = sorted(list(files) + ["LOCAL_REHASH_C12.csv", "HF_INGESTED_REDOWNLOAD_C12.csv", "tools/build_copy_verification_c12.py"])
    sums = ""
    for n in names:
        b = files[n].encode() if n in files else (OUT / n).read_bytes()
        sums += f"{hashlib.sha256(b).hexdigest()}  {n}\n"
    files["SHA256SUMS"] = sums
    return files


def readme(S, inv_rows, st, seg, reg_by_seg, clos, clos_src, adds, canon, ident_c, vs_seg):
    b = S["baseline"]
    t = lambda d: "\n".join(f"| `{k}` | {v:,} |" for k, v in sorted(d.items()))
    ac = Counter(f"{a['addition_group']} | {a['classification']}" for a in adds)
    kc = Counter(f"{k['addition_group']} | {k['status']}" for k in canon)
    ex = "\n".join(f"| {r['investigation_id']} | {r['kind']} | {r['copies_affected']} | {r['explanation'][:160]} | {r['next_action'][:140]} |" for r in inv_rows)
    vseg = "\n".join(f"| {a} | `{s}` | {n:,} |" for (a, s), n in sorted(vs_seg.items()))
    return f"""# C12 per-copy source verification (copy_verification_c12)

Generated by `tools/build_copy_verification_c12.py` (rebuild with `--check`). Owner directive, Cycle 12 closeout, 2026-11-24.
Database research only: **no frozen or original register, KB record, crawler file or HF file was changed**. Byte identity is
not authentication; no evidence class, holding state, resolution or KB status was changed.

- HF dataset `{REPO}` (private), revision **`{REV}`**.
- Byte evidence: `{LEDGER_REL}` (sha256 of every downloaded file; its own checksum is verified against
  `hf_verification_c12/SHA256SUMS` before use). Every `BYTE_VERIFIED*` status below rests on `computed_sha256` equal to the
  expected sha256. Declared hashes, LFS pointers or size matches alone are never treated as byte verification.

## 1. Baseline reconciliation: 4,103 (exact)

Defining register: C10 `UNIFIED_CORPUS_INVENTORY.csv` (one row per distinct sha256), counted in C10 `RECONCILIATION_MANIFEST.json`.

| Segment (C10 `presence`) | Copies | Cross-check |
|---|---|---|
| HF_AND_GITHUB_RAW_DATA (common GitHub/HF copies) | {seg['HF_AND_GITHUB_RAW_DATA']:,} | = 4,039 GitHub raw files re-hashed = 4,039 HF `data/raw` files = 4,039 `data/SHA256SUMS` entries |
| HF_ONLY (previously identified) | {seg['HF_ONLY']:,} | 8 SC/third-party judgments + 8 MML originals under `legal_knowledge/` |
| C5_WORKING_STORE_ONLY (newly preserved) | {seg['C5_WORKING_STORE_ONLY_NOT_IN_HF_OR_GITHUB']:,} | = C11 `PRESERVATION_INVENTORY.csv` rows = C10 `MISSING_SOURCE_EVIDENCE` REGISTERED_COPY_BYTES_NOT_IN_CANONICAL_STORE rows = 48 PDFs in the HF package |
| **Total** | **{b['rows']:,}** | {b['distinct_sha256']:,} distinct sha256; C10 manifest `distinct_copies` = {b['c10_manifest_distinct_copies']:,} |

4,039 + 16 + 48 = 4,103. The registered subset is the 67-row C5 `source_copy_register.csv` (identical to AUTH-LEDGER v0000):
{', '.join(f'{k} {v}' for k, v in sorted(reg_by_seg.items()))} = {sum(reg_by_seg.values())}. The other 4,036 baseline copies are unregistered (4,032 crawler raw copies and 4 HF-only SC copies).
The 50 C10 `SOURCE_NOT_HELD_IN_C5_REGISTER` rows are sources with no bytes anywhere, so they are not copies and are outside the 4,103.

## 2. Counts by verification status (baseline 4,103)

| Status | Copies |
|---|---|
{t(st)}

| Segment | Status | Copies |
|---|---|---|
{vseg}

`BYTE_VERIFIED_INCOMPLETE_DOCUMENT`: the hash matches the recorded copy but the PDF is truncated (C11 `STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING`).
`BYTE_VERIFIED_TRUNCATED_TAIL_BASE_REVISION_PRESENT`: the hash matches; the file tail was cut inside a later signature update, and the judgment's
base revision is complete (C11 `BASE_REVISION_ONLY_SIGNATURE_UPDATE_CUT`). `NOT_HOSTED_ON_HF` does not occur in the baseline: every one of the 4,103
copies is on HF at `{REV[:8]}`. Post-baseline: 18 of the 25 C12 acquisitions are `INGESTED_HF_BYTE_VERIFIED` at `{REV_B[:8]}`; 7 are
`EXCLUDED_NOT_RELEVANT_NOT_INGESTED` (still listed; local bytes kept).

Identity is a separate column, so that it does not mask the byte result: {', '.join(f'{k} {v:,}' for k, v in sorted(ident_c.items()))}.
`DUPLICATE_IDENTITY` covers one sha256 under several crawler doc_ids and one doc_id or C5 source id with several sha256 values.
No baseline sha256 appears at more than one HF path.

## 3. Additions after the baseline (accounted separately; `POST_BASELINE_ADDITIONS_C12.csv`)

| Group / classification | Rows |
|---|---|
{chr(10).join(f'| {k} | {v} |' for k, v in sorted(ac.items()))}

- **277 HF-only paths** (relative to git `ad77758d`) contain no new source copy: 16 are the baseline HF-only copies and 48 are the preserved copies (already in the 4,103).
  The rest are preservation package files and non-source files (documentation and derived data).
- **4 HF-only SC binaries retrieved**: these are local working copies of 4 of the 16 baseline HF-only copies. They are not new copies.
  HF `{REV_A[:8]}` added 8 derived text/meta files for them under `legal_knowledge/judgment_originals_derived/c12/`. These are derived files, not source copies.
- **25 C12 acquisitions** (judicial_recovery_c12, git `fe9f4332`):
  - **18 ingested** additively at HF `{REV_B[:8]}` under `data/raw/{{hc,sci}}/`, with `data/manifest_additions/c12_2026-11-24_*`. They are byte-verified here: re-downloaded at `{REV_B[:8]}` and hashed (`HF_INGESTED_REDOWNLOAD_C12.csv`), and cross-checked with `judicial_recovery_c12/VERIFICATION.csv` (downloaded_sha256).
  - **7 excluded as not relevant** (`EXCLUDED_NOT_RELEVANT_NOT_INGESTED`). They are kept in the lists, and their bytes remain only in the session working store.
  - The other 29 files of `{REV_B[:8]}` (text, meta, manifests) are derived or manifest files.
- **Distinct source copies on HF: {S['distinct_source_copies_on_hf']['baseline']:,} + {S['distinct_source_copies_on_hf']['ingested_post_baseline']} = {S['distinct_source_copies_on_hf']['total']:,}** (computed, not forced; equals 4,121: {S['distinct_source_copies_on_hf']['equals_4121']}).
  The 18 sha256 values are absent from the baseline inventory and from the `{REV[:8]}` ledger, and distinct from each other.
  Another {S['distinct_source_copies_on_hf']['excluded_held_locally_not_hosted']} distinct copies are held locally but not hosted. The 18 C12 re-fetches of truncated HC files produced no new sha256.

## 4. Preservation overlay (`SOURCE_REGISTER_PRESERVATION_OVERLAY_C12.csv`)

48 rows, one per preserved copy, versioned `{VERSION}`, status `PRESERVATION_RECORDED_DERIVATIVE_OVERLAY_ORIGINAL_UNCHANGED`. This follows the
C12 overlay convention (`..._DERIVATIVE_OVERLAY_ORIGINAL_UNCHANGED`). Outcome: {', '.join(f'{k} {v}' for k, v in S['preservation_overlay'].items())}.
`PRESERVED_HF_BYTE_VERIFIED` requires all of the following:
- the ledger `computed_sha256` equals the register sha256;
- the size matches;
- the HF `PACKAGE_SHA256SUMS` entry matches;
- the hash is in C11 `SOURCE_MANIFEST.sha256`;
- the ledger carries `C5_PACKAGE_SHA256SUMS_MATCH`;
- the sidecar is present.

The C5 register and AUTH-LEDGER v0000 are untouched. Their sha256 values are recorded in `SUMMARY_C12.json`.

## 5. Preservation-risk closure for dependent citation items (`PRESERVATION_RISK_CLOSURE_C12.csv`)

The 274 items are the C10 quality items with `A_availability_c10 = HELD_WORKING_STORE_ONLY_EPHEMERAL` (`citation_coverage_c10.csv`): 204 cite the Army Rules 1954 Gazette and 70 cite
12 SC judgments. Count reconciles exactly: **{S['risk_closure']['items']}**. Outcome: {', '.join(f'{k} {v}' for k, v in sorted(clos.items()))}.
Dependencies are the C10 `A_registered_copies` plus any further copy that C12 WS-F `PRIORITY_VERIFICATION` uses for the same item
({S['risk_closure']['items_with_c12_extra_dependencies']} items add 1961/amendment Gazette copies, all among the 48). Items outside the 274 that depend on one of the 48: {S['risk_closure']['items_outside_274_depending_on_48']}.
Unchanged by design: C resolution ({', '.join(f'{k} {v}' for k, v in S['risk_closure']['resolution'].items())}), ledger holding state, evidence classes, anchor status, KB status and the C12-F proposed state.
WS-F's condition "every promotion is conditional on preserving the anchoring copies" is met for these items. Nothing was promoted here.

By source: {', '.join(f'{k} {v}' for k, v in sorted(clos_src.items()))}.

## 6. Canonical inventory additions (`CANONICAL_INVENTORY_ADDITIONS_C12.csv`)

| Group / status | Rows |
|---|---|
{chr(10).join(f'| {k} | {v} |' for k, v in sorted(kc.items()))}

## 7. Exceptions and dispositions (`INVESTIGATIONS_C12.csv`; nothing changed)

| ID | Kind | Copies | Explanation | Next action |
|---|---|---|---|---|
{ex}

## Method

1. Baseline rows come from the frozen C10 inventory. The hosted path is the C10 HF path, or for the 48 the unique ledger path `{PRES_PREFIX}<sha[:2]>/<sha>/<filename>`.
2. Expected sha256/size come from the C10 inventory and the C5 register. The computed sha256/size come from the C12 ledger at the pinned revision.
3. Completeness for judgments comes from C11 `JUDGMENT_IDENTITY_REGISTER.source_completeness`. Other PDFs use the ledger's PyMuPDF open and trailing `%%EOF` checks.
   `.doc`/JSON completeness is not assessed.
4. Identity comes from HF `data/manifest.csv` (byte-identical to git) doc_ids per sha256, together with the C10 `COPY_EQUIVALENCE_REGISTER` one-id/several-bytes groups.
5. `rehash-local` re-hashes the 4 retrieved and 25 acquired working copies into `LOCAL_REHASH_C12.csv`.
   `rehash-hf-ingested` (network, read-only) re-downloads the 18 ingested raw files at `{REV_B[:8]}` and hashes them into `HF_INGESTED_REDOWNLOAD_C12.csv`.
   The build itself is offline and deterministic. Input sha256 values are in `SUMMARY_C12.json`.
6. Commits `{REV_A[:8]}` and `{REV_B[:8]}` are additive children of `{REV[:8]}`: judicial_recovery_c12 checked the tree diff, and found only staged paths added and nothing removed.
   Baseline copy rows therefore keep `dataset_revision` `{REV[:8]}`.
7. Limits:
   - A matching hash proves byte identity with the recorded copy. It does not prove authenticity, completeness of text or legal currency.
   - The 7 excluded acquisitions exist only in the session working store. The exclusion is an LLM relevance review, not a legal review.
"""


def ingest_status(r, jlog, jver_by_sha, redl, lo):
    s = r["sha256"]
    j = jlog.get(r["target_id"], {})
    act = j.get("action", "")
    if act == "INGESTED":
        v = jver_by_sha.get(s, {})
        d = redl.get(v.get("hf_path", ""), {})
        ok = bool(v) and d.get("computed_sha256") == s == v.get("downloaded_sha256") and v.get("hf_commit") == REV_B and d.get("size") == r["bytes"]
        return dict(status="INGESTED_HF_BYTE_VERIFIED" if ok else "INGESTED_NOT_BYTE_VERIFIED", hosted_path=v.get("hf_path", ""),
                    hf_revision=REV_B if v else "", computed_sha256=d.get("computed_sha256", ""),
                    byte_status=("BYTE_VERIFIED (re-downloaded at " + REV_B[:8] + " and hashed; = judicial_recovery VERIFICATION downloaded_sha256)") if ok else "NOT_VERIFIED",
                    note=f"doc_id {j.get('doc_id', '')}; ingested commit label B",
                    next_action="None for availability. Record in the next canonical inventory version (C10 inventory frozen)" if ok else "Re-verify")
    if act == "EXCLUDED_NOT_RELEVANT":
        return dict(status="EXCLUDED_NOT_RELEVANT_NOT_INGESTED", hosted_path="NOT_HOSTED_ON_HF (excluded as not relevant)", hf_revision="",
                    computed_sha256="", byte_status=("LOCAL_REHASH_MATCH" if lo.get("sha256") == s else "LOCAL_REHASH NOT_MATCHED") + "; NOT_HOSTED_ON_HF",
                    note="excluded: " + j.get("reason", "")[:200],
                    next_action="Owner to confirm the exclusion (LLM relevance review, not legal review); keep listed; local bytes not deleted")
    return dict(status="ACQUIRED_NOT_YET_INGESTED", hosted_path="NOT_HOSTED_ON_HF", hf_revision="", computed_sha256="",
                byte_status=("LOCAL_REHASH_MATCH" if lo.get("sha256") == s else "LOCAL_REHASH NOT_MATCHED") + "; NOT_HOSTED_ON_HF",
                note="no ingestion record", next_action="Owner-approved ingestion")


def main():
    a = sys.argv[1:]
    if a and a[0] == "rehash-local":
        return rehash_local()
    if a and a[0] == "rehash-hf-ingested":
        return rehash_hf_ingested()
    files = build()
    if "--check" in a:
        bad = [k for k, v in files.items() if not (OUT / k).exists() or (OUT / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED: " + ", ".join(bad) if bad else f"copy verification reproduces ({len(files)} files byte-identical)")
        return 1 if bad else 0
    for k, v in files.items():
        (OUT / k).write_text(v, encoding="utf-8")
    s = json.loads(files["SUMMARY_C12.json"])
    print(json.dumps({k: s[k] for k in ("baseline", "verification_status", "identity_status", "preservation_overlay", "risk_closure",
                                        "canonical_additions", "new_distinct_copies_after_baseline", "distinct_source_copies_on_hf")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
