"""CALIBRATION-02 validator (stdlib). Exit 1 on any error.

Checks every reviewer findings file reviews/<R>/findings.csv against propositions.csv:
- each reviewer covers every proposition (at least one row per proposition_id) and no unknown IDs;
- enums: evidence_state, severity, defect_class, dimension;
- VERIFIED_AGAINST_HELD_PRIMARY_SOURCE needs a 64-hex source_sha256 and a non-empty locator;
- severity P1/P2 needs a defect_class other than NONE and either a proposed_correction or missing_evidence;
- no row claims legal approval (APPROVED / JAG_VALIDATED / LEGALLY_VERIFIED / ADJUDICATED as a state);
- reviewer field equals the directory name; finding_id unique within the file.
Usage: check_calibration02.py [--require A,B,C,D]"""
import csv, re, sys
from pathlib import Path

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
APPROVAL = re.compile(r"\b(JAG[_ ]VALIDATED|LEGALLY[_ ]VERIFIED|LEGAL[_ ]APPROVED|ADJUDICATED)\b")


def rows(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def check(require=()):
    err = []
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
            if d["evidence_state"] == "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE":
                if not re.fullmatch(r"[0-9a-f]{64}", d["source_sha256"]): err.append(f"{tag} VERIFIED without full source_sha256")
                if not d["locator"].strip(): err.append(f"{tag} VERIFIED without locator")
            if d["severity"] in ("P1", "P2"):
                if d["defect_class"] == "NONE": err.append(f"{tag} {d['severity']} with defect_class NONE")
                if not (d["proposed_correction"].strip() or d["missing_evidence"].strip()): err.append(f"{tag} {d['severity']} without correction or missing_evidence")
            if APPROVAL.search(d["evidence_state"] + " " + d["defect_class"]): err.append(f"{tag} approval claim")
        missing = sorted(set(pid) - seen)
        if missing: err.append(f"{rv}: {len(missing)} propositions not covered, e.g. {missing[:5]}")
    print(f"propositions={len(pid)} reviewers={found} errors={len(err)}")
    for e in err[:200]: print("ERROR", e)
    return 1 if err else 0


if __name__ == "__main__":
    req = []
    if "--require" in sys.argv: req = sys.argv[sys.argv.index("--require") + 1].split(",")
    sys.exit(check(req))
