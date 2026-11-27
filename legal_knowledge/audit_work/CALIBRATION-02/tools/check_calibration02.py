"""CALIBRATION-02 validator (stdlib). Exit 1 on any error.

Checks every reviewer findings file reviews/<R>/findings.csv against propositions.csv:
- each reviewer covers every proposition (at least one row per proposition_id) and no unknown IDs;
- enums: evidence_state, severity, defect_class, dimension;
- VERIFIED_AGAINST_HELD_PRIMARY_SOURCE needs a non-empty locator and a source_sha256 that is in
  registers/held_sources_scratchpad.csv AND identifies a non-derived primary file (pdf/doc/docx, not under a
  'secondary' path); derived text (.txt/.json/.html) and mirror copies cannot verify;
- P1/P2 'missing_evidence' or 'proposed_correction' must be substantive (>= 10 non-space characters);
- no field claims legal approval (state tokens JAG_VALIDATED / LEGALLY_VERIFIED / LEGAL_APPROVED / ADJUDICATED /
  APPROVED unless negated as NOT_...);
- severity P1/P2 needs a defect_class other than NONE and either a proposed_correction or missing_evidence;
- no row claims legal approval (APPROVED / JAG_VALIDATED / LEGALLY_VERIFIED / ADJUDICATED as a state);
- reviewer field equals the directory name; finding_id unique within the file.
Evidence: VERIFIED claims are classified by the shared rule in evidence_classification.py. Protocol errors (not held,
derived text, mirror/secondary, hash mismatch, missing pinpoint) fail; AUTHENTICATION_PENDING / PROVENANCE_UNKNOWN are
reported as warnings: the reviewer's claim is preserved but never counted as primary downstream.
Usage: check_calibration02.py [--require A,B,C,D] [--verify-files <scratchpad root>]"""
import csv, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_classification as EC  # noqa: E402  shared rule with reconcile.py

C2 = Path(__file__).resolve().parents[1]
STATES = {"VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "SOURCE_NOT_HELD",
          "HISTORICAL_VERSION_UNRESOLVED", "CONTRADICTORY_EVIDENCE", "INTERPRETATION_REQUIRES_LEGAL_ADVICE",
          "UNSUPPORTED", "NOT_YET_REVIEWED", "NOT_A_LEGAL_PROPOSITION"}
SEV = {"P1", "P2", "P3", "NONE"}
DEFECT = {"NONE", "WRONG_AUTHORITY", "WRONG_PROVISION", "WORDING_ERROR", "HISTORICAL_VERSION", "OMISSION",
          "UNSUPPORTED_GENERALISATION", "MISSING_EXCEPTION", "MISLINKED_CASE_OR_CODE", "PROCEDURAL_ERROR",
          "CROSS_VOLUME_INCONSISTENCY", "CITATION_ERROR", "METADATA_OR_TRANSCRIPTION", "SOURCE_GAP"}
DIM = {"STATUTORY", "JUDICIAL", "PROCEDURE", "CROSS_VOLUME", "EVIDENCE_QUALITY"}
COLS = ["finding_id", "reviewer", "record_id", "proposition_id", "dimension", "evidence_state", "defect_class",
        "severity", "source_identity", "source_sha256", "locator", "version_or_date_note", "finding",
        "proposed_correction", "rationale", "missing_evidence", "legal_advisor_question", "uncertainty", "method"]
APPROVAL = re.compile(r"(?<!NOT_)(?<![A-Z_])(JAG_VALIDATED|LEGALLY_VERIFIED|LEGAL_APPROVED|LEGALLY_APPROVED|ADJUDICATED|APPROVED)(?![A-Z_])")
def substantive(x):
    return len(re.sub(r"\s", "", x)) >= 10


def rows(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def check(require=(), verify_root=None):
    err = []
    ev = EC.Evidence.from_dir(C2, root=verify_root)
    effective = Counter()
    props = list(csv.DictReader(open(C2 / "propositions.csv", newline="", encoding="utf-8")))
    pid = {p["proposition_id"]: p["record_id"] for p in props}
    found = sorted(d.name for d in (C2 / "reviews").iterdir() if (d / "findings.csv").exists()) if (C2 / "reviews").exists() else []
    for r in require:
        if r not in found:
            err.append(f"reviewer {r}: findings.csv missing")
    for rv in found:
        data = rows(C2 / "reviews" / rv / "findings.csv")
        if not data or data[0] != COLS:
            err.append(f"{rv}: header must be exactly {COLS}")
            continue
        seen, ids = set(), set()
        for i, row in enumerate(data[1:], 2):
            if len(row) != len(COLS):
                err.append(f"{rv}:{i} wrong column count"); continue
            d = dict(zip(COLS, row))
            tag = f"{rv}:{i} {d['finding_id']}"
            if d["finding_id"] in ids: err.append(f"{tag} duplicate finding_id")
            ids.add(d["finding_id"])
            if d["reviewer"] != rv: err.append(f"{tag} reviewer field != {rv}")
            if d["proposition_id"] not in pid: err.append(f"{tag} unknown proposition_id"); continue
            if pid[d["proposition_id"]] != d["record_id"]: err.append(f"{tag} record_id mismatch")
            seen.add(d["proposition_id"])
            if d["evidence_state"] not in STATES: err.append(f"{tag} bad evidence_state {d['evidence_state']}")
            if d["severity"] not in SEV: err.append(f"{tag} bad severity")
            if d["defect_class"] not in DEFECT: err.append(f"{tag} bad defect_class")
            if d["dimension"] not in DIM: err.append(f"{tag} bad dimension")
            if d["evidence_state"] == EC.VERIFIED:
                st, detail = ev.classify_finding(d)
                effective[st] += 1
                if st in EC.PROTOCOL_ERRORS:
                    err.append(f"{tag} VERIFIED claim fails the shared evidence rule: {st} ({detail})")
            if d["severity"] in ("P1", "P2"):
                if d["defect_class"] == "NONE": err.append(f"{tag} {d['severity']} with defect_class NONE")
                if not (substantive(d["proposed_correction"]) or substantive(d["missing_evidence"])): err.append(f"{tag} {d['severity']} without correction or missing_evidence")
            if any(APPROVAL.search(v) for v in d.values()): err.append(f"{tag} approval claim")
        missing = sorted(set(pid) - seen)
        if missing: err.append(f"{rv}: {len(missing)} propositions not covered, e.g. {missing[:5]}")
    warn = []
    for rv in found:
        for d in csv.DictReader(open(C2 / "reviews" / rv / "findings.csv", newline="", encoding="utf-8")):
            if d.get("evidence_state") == EC.VERIFIED:
                st, detail = ev.classify_finding(d)
                if st in EC.NOT_EFFECTIVE_PRIMARY:
                    warn.append(f"{rv} {d['finding_id']} claimed VERIFIED; effective {st} ({detail}); claim preserved, not counted as primary")
    print(f"propositions={len(pid)} reviewers={found} errors={len(err)} warnings={len(warn)} effective_status_of_VERIFIED_claims={dict(sorted(effective.items()))}"
          + (f" files_hashed={sum(1 for h in ev._hash_cache.values() if h)} files_missing={sum(1 for h in ev._hash_cache.values() if h is None)}" if verify_root else ""))
    for w in warn: print("WARNING", w)
    for e in err[:200]: print("ERROR", e)
    return 1 if err else 0


if __name__ == "__main__":
    req = []
    if "--require" in sys.argv: req = sys.argv[sys.argv.index("--require") + 1].split(",")
    root = sys.argv[sys.argv.index("--verify-files") + 1] if "--verify-files" in sys.argv else None
    sys.exit(check(req, root))
