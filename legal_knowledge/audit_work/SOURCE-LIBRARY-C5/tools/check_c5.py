"""Cycle 5 package validator (stdlib). Structural, provenance and integrity checks only: it decides no legal question.

Checks:
 1. originals unchanged (records_658, cases_53 SHA-256 equal the frozen baseline);
 2. every register has exactly its contracted header (build_registers.COLS) and rebuilds byte-identically;
 3. controlled vocabularies (publication_type, holding_state, discovery_state, approval_state, crosswalk statuses);
 4. HELD_* rows carry sha256 present in the frozen held manifest; NOT_HELD rows carry none;
 5. no source is described as legally approved / in force without an amendment-chain basis
    (currency_status may only be one of the controlled values; IN_FORCE_* requires amendment_chain_status
    CHECKED_FOR_RELEVANT_PERIOD, which no row in this package has);
 6. every acquisition item is NOT_APPROVED and names a required approval;
 7. discovery request logs exist for every candidate file and never touch blocked hosts; v2 logs (content type, payload
    class, robots state) are validated by discovery_guard.validate_log_v2; v1 logs can only show method and URL, so a GET
    to a document-like URL (extension or filename/showfile query) is reported as a warning, not proven absent;
    copy-level: exact anchors and HELD_PRIMARY need a copy with its own documented provenance;
 8. reserved conflict states equal the owner's reserved list; committed page renders match their recorded hashes;
 9. with --verify-files <held-root>: every held path re-hashes to its manifest value.
Exit 0 when clean; 1 with a list of errors otherwise."""
import argparse, csv, hashlib, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_registers as B  # noqa: E402

PKG = B.PKG
REPO = B.REPO
VOCAB = {
    "publication_type": {"STATUTE", "SUBORDINATE_LEGISLATION", "REGULATION", "ADMINISTRATIVE_INSTRUCTION", "MANUAL",
                         "GAZETTE_NOTIFICATION", "JUDICIAL", "SECONDARY_COMMENTARY", "CATALOGUE_RECORD", "COMPILATION", "PARLIAMENTARY_RECORD"},
    "holding_state": {"HELD_PRIMARY_GAZETTE_FACSIMILE", "HELD_PRIMARY_GAZETTE_GOVERNMENT_SCAN", "HELD_PRIMARY_OFFICIAL_COURT_COPY",
                      "HELD_AUTHENTICATION_PENDING", "HELD_GOVERNMENT_COMPILATION", "HELD_GOVERNMENT_COMPILATION_EXTRACT",
                      "HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED", "HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED",
                      "HELD_UNVERIFIED_MANUAL", "NOT_HELD_CANDIDATE_LOCATED", "NOT_HELD_LEAD_ONLY",
                      "NOT_HELD_NOT_FOUND_IN_SEARCHED_SOURCES", "NOT_HELD_NOT_CHECKED", "NOT_HELD_BLOCKED_ACCESS",
                      "NOT_HELD_RESTRICTED_SUSPECTED"},
    # evidence_stage is derived (build_registers.evidence_stage). DOCUMENT_AUTHENTICATED and AMENDMENT_CHAIN_COMPLETE are
    # reserved values that no evidence in this package reaches (no custodian authentication; no chain checked for a period).
    "evidence_stage": {"NOT_CHECKED", "BLOCKED_ACCESS", "NOT_FOUND_IN_SEARCHED_SOURCES", "LEAD_ONLY", "OFFICIAL_CANDIDATE_LOCATED",
                       "ARCHIVAL_OR_THIRD_PARTY_CANDIDATE_LOCATED", "RESTRICTED_MARKING_SUSPECTED", "DOCUMENT_ACQUIRED",
                       "DOCUMENT_AUTHENTICATED"},
    "currency_status": {"HISTORICAL_SUPERSEDED", "HISTORICAL_VERSION", "CURRENCY_NOT_ESTABLISHED", "NOT_APPLICABLE_JUDGMENT",
                        "AMENDMENT_INSTRUMENT", "DECLARATION_INSTRUMENT", "CORRIGENDUM_INSTRUMENT", "NOT_APPLICABLE_RECORD"},
    "amendment_chain_status": {"NOT_CHECKED", "PARTIAL", "NOT_APPLICABLE", "CHECKED_FOR_RELEVANT_PERIOD"},  # policy v1; brief label AMENDMENT_CHAIN_INCOMPLETE is a parenthesised qualifier
    "discovery_state": {"FOUND_CANDIDATE", "NOT_FOUND", "NOT_CHECKED", "BLOCKED_ACCESS", "RESTRICTED_MARKING_SUSPECTED"},
    "evidence_status": {"EXACT_ANCHOR", "PARTIAL_MATCH", "MISSING_EVIDENCE"},
}
BLOCKED_HOSTS = ("aftjabalpur.in",)
EXPECTED_RESERVED = {"C5-CF-C-01": "CONFLICTING (r.23(3))", "C5-CF-C-08": "OPEN (r.193)", "C5-CF-C-09": "PROPOSAL (r.194)",
                     "C5-CF-SC4-01": "OPEN (r.182)"}


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-files")
    a = ap.parse_args()
    err, warn = [], []
    base = json.load(open(PKG / "baseline/frozen_baseline_manifest.json"))
    for k, rel in {"records_658": "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl",
                   "cases_53": "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"}.items():
        if sha(REPO / rel) != base["original_corpus_sha256"][k]:
            err.append(f"original {k} changed")
    texts = B.build()
    for k, t in texts.items():
        p = PKG / "registers" / k
        if not p.exists() or p.read_text(encoding="utf-8") != t:
            err.append(f"registers/{k} differs from rebuild")
    for k, cols in B.COLS.items():
        with open(PKG / "registers" / k, newline="", encoding="utf-8") as f:
            hdr = next(csv.reader(f))
        if hdr != cols:
            err.append(f"registers/{k} header differs from contract")
    held = {}
    for h in read(PKG / "baseline/held_binaries_manifest.csv"):
        held.setdefault(h["rehashed_sha256"], []).append(h)
        if h["hash_check"] != "MATCH":
            err.append(f"baseline held file {h['held_path']} hash_check={h['hash_check']}")
    master = read(PKG / "registers/source_master_register.csv")
    ids = set()
    for r in master:
        sid = r["source_id"]
        if sid in ids:
            err.append(f"duplicate source_id {sid}")
        ids.add(sid)
        if r["direct_verification_state"] not in B.DIRECT_VERIFICATION:
            err.append(f"{sid}: direct_verification_state not in vocabulary")
        if r["evidence_stage"] == "OFFICIAL_CANDIDATE_LOCATED" and r["direct_verification_state"] == "BLOCKED_ACCESS" and "BLOCKED_ACCESS" not in r["verification_limitations"]:
            err.append(f"{sid}: BLOCKED_ACCESS direct verification not explained in verification_limitations")
        if r["evidence_stage"] == "DOCUMENT_AUTHENTICATED":
            err.append(f"{sid}: DOCUMENT_AUTHENTICATED is not supported by any custodian authentication in this package")
        if r["evidence_stage"] != B.evidence_stage(r):
            err.append(f"{sid}: evidence_stage not derived from holding_state/carrier")
        for col in ("publication_type", "holding_state", "currency_status", "amendment_chain_status", "evidence_stage"):
            v = r[col].split(" ")[0]
            if v not in VOCAB[col]:
                err.append(f"{sid}: {col}={r[col]!r} not in vocabulary")
        for d in [x for x in r["discovery_state"].split(";") if x]:
            if d not in VOCAB["discovery_state"]:
                err.append(f"{sid}: discovery_state {d} not in vocabulary")
        shas = [s for s in r["sha256"].split(";") if s]
        if r["holding_state"].startswith("HELD") != bool(shas):
            err.append(f"{sid}: holding_state/sha256 inconsistent")
        for s in shas:
            if s not in held:
                err.append(f"{sid}: sha256 {s[:12]} not in frozen held manifest")
        if re.search(r"\b(LEGALLY_APPROVED|JAG_APPROVED|CURRENT_IN_FORCE|IN_FORCE_VERIFIED)\b", " ".join(r.values())):
            err.append(f"{sid}: forbidden approval/currency term present")
        if r["amendment_chain_status"].split(" ")[0] == "CHECKED_FOR_RELEVANT_PERIOD":
            err.append(f"{sid}: CHECKED_FOR_RELEVANT_PERIOD is not established by any evidence in this package")
    copies = read(PKG / "registers/source_copy_register.csv")
    by_src = {}
    for c in copies:
        by_src.setdefault(c["source_id"], []).append(c)
        if c["sha256"] not in held:
            err.append(f"{c['copy_id']}: copy sha256 not in frozen held manifest")
        if (c["eligible_for_exact_anchor"] == "YES") != (c["copy_effective_status"] == "EFFECTIVE_PRIMARY_VERIFIED"):
            err.append(f"{c['copy_id']}: eligibility does not follow the copy's own effective status")
        if c["c4_register_state"] != "PROVENANCE_DOCUMENTED" and c["eligible_for_exact_anchor"] == "YES":
            err.append(f"{c['copy_id']}: eligible without its own PROVENANCE_DOCUMENTED register row")
    for r in master:
        cs = by_src.get(r["source_id"], [])
        if sorted(c["sha256"] for c in cs) != sorted(x for x in r["sha256"].split(";") if x):
            err.append(f"{r['source_id']}: copy register does not match source sha256 list")
        if r["holding_state"].startswith("HELD_PRIMARY") != any(c["eligible_for_exact_anchor"] == "YES" for c in cs):
            err.append(f"{r['source_id']}: HELD_PRIMARY state not backed by a documented-primary copy (or vice versa)")
    eligible = {c["copy_id"]: c for c in copies if c["eligible_for_exact_anchor"] == "YES"}
    for r in read(PKG / "registers/acquisition_register.csv"):
        if r["approval_state"] != "NOT_APPROVED" or not r["required_approval"].strip():
            err.append(f"{r['acq_c5_id']}: approval fields invalid")
        if r["source_id"] not in ids:
            err.append(f"{r['acq_c5_id']}: unknown source")
        if any(h in r["exact_location"] for h in BLOCKED_HOSTS):
            err.append(f"{r['acq_c5_id']}: blocked host in location")
    for r in read(PKG / "registers/corpus_crosswalk.csv"):
        if r["evidence_status"] == "EXACT_ANCHOR" and (r["anchor_copy_id"] not in eligible or eligible[r["anchor_copy_id"]]["source_id"] != r["source_id"]):
            err.append(f"crosswalk: EXACT_ANCHOR without an eligible copy of the same source ({r['source_id']})")
        if r["evidence_status"] != "EXACT_ANCHOR" and r["anchor_copy_id"]:
            err.append("crosswalk: anchor_copy_id on a non-exact row")
        if r["evidence_status"] not in VOCAB["evidence_status"]:
            err.append(f"crosswalk: bad evidence_status {r['evidence_status']}")
        if r["source_id"] not in ("UNMAPPED", "NONE") and r["source_id"] not in ids:
            err.append(f"crosswalk: unknown source {r['source_id']}")
    conf = {r["conflict_id"]: r for r in read(PKG / "registers/source_conflict_register.csv")}
    for cid, st in EXPECTED_RESERVED.items():
        if cid not in conf or conf[cid]["reserved_status"] != st:
            err.append(f"reserved state for {cid} missing or changed")
    for r in read(PKG / "inputs/page_image_checks_c5.csv"):
        f = PKG / r["render_file"]
        if not re.fullmatch(r"[0-9a-f]{64}", r["render_png_sha256"]) or not f.exists() or sha(f) != r["render_png_sha256"]:
            err.append(f"{r['check_id']}: render file missing or hash mismatch")
    disc = PKG / "discovery"
    import discovery_guard as DG
    for cf in sorted(disc.glob("*_candidates.csv")):
        stem = cf.name.replace("_candidates.csv", "")
        v1, v2 = disc / f"{stem}_requests.tsv", disc / f"{stem}_requests_v2.tsv"
        if v2.exists():
            with open(v2, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f, delimiter="\t"))
            err += [f"{v2.name}: {e}" for e in DG.validate_log_v2([r for r in rows if r["method"] != "WEBSEARCH"])]
        elif v1.exists():
            rows = [l.rstrip("\n").split("\t") for l in open(v1, encoding="utf-8")]
            e1, sus = DG.legacy_log_findings(rows)
            err += [f"{v1.name}: {e}" for e in e1]
            warn += [f"{v1.name}: {x}" for x in sus]
            # legacy (v1) logs record no content type: they show method and URL only, not the absence of document payloads
        else:
            err.append(f"{cf.name}: request log missing")
    if a.verify_files:
        root = Path(a.verify_files)
        for s, hs in held.items():
            for h in hs:
                p = root / h["held_path"]
                if not p.exists():
                    err.append(f"held file missing: {h['held_path']}")
                elif sha(p) != s:
                    err.append(f"held file hash mismatch: {h['held_path']}")
    print(json.dumps({"errors": len(err), "warnings": len(warn), "sources": len(master)}, sort_keys=True))
    for e in err:
        print("ERROR", e)
    for w in warn:
        print("WARN", w)
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
