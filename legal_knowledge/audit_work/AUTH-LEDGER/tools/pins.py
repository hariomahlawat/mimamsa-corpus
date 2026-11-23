"""Frozen-input pins. Every historical file the overlay reads is listed with its sha256 in ../frozen_inputs.json.
Any mismatch fails closed (LedgerError). `python pins.py --write` regenerates the file and is used ONLY when the pin
set itself is deliberately changed in a reviewed PR; the manifest genesis line pins the sha256 of frozen_inputs.json,
so a silent re-pin breaks the ledger chain."""
import argparse, glob, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AW, PKG, REPO, LedgerError, sha256_file  # noqa: E402

# Files read by the frozen Cycle 5 builder (traced with an open() hook on 2026-11-23 at staging 939a128a), plus the two
# frozen code modules it executes. Rule version 1 runs this frozen code for master rows, crosswalk and counts.
C5_BUILD_INPUTS = [
    "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv", "ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv",
    "ARMY-RULES-CHAIN-01/official_note_discrepancies.csv", "CALIBRATION-02/adviser/legal_adviser_questions.csv",
    "CALIBRATION-02/reconciliation/disagreements.csv", "CALIBRATION-02/registers/held_sources_scratchpad.csv",
    "CALIBRATION-02/registers/rule_index_spec/compilation_rule_presence.csv", "CALIBRATION-02/registers/source_authentication_register.csv",
    "CALIBRATION-02/registers/source_conflicts_c4.csv", "SOURCE-CONFLICTS-01/conflict_determinations.csv",
    "SOURCE-CONFLICTS-01/conflict_determinations_update_2026-11-22b.csv", "SOURCE-CONFLICTS-01/conflict_determinations_update_2026-11-22c.csv",
    "SOURCE-CONFLICTS-01/conflict_determinations_update_2026-11-22e.csv", "SOURCE-CONFLICTS-01/conflict_split_2026-11-22d.csv",
    "SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv", "SOURCE-LIBRARY-C5/discovery/A_candidates.csv",
    "SOURCE-LIBRARY-C5/discovery/B_candidates.csv", "SOURCE-LIBRARY-C5/discovery/C_candidates.csv", "SOURCE-LIBRARY-C5/discovery/D_candidates.csv",
    "SOURCE-LIBRARY-C5/inputs/acquisition_batches.csv", "SOURCE-LIBRARY-C5/inputs/amendment_register_additions.csv",
    "SOURCE-LIBRARY-C5/inputs/case_source_map.csv", "SOURCE-LIBRARY-C5/inputs/conflict_additions.csv",
    "SOURCE-LIBRARY-C5/inputs/copy_annotations.csv", "SOURCE-LIBRARY-C5/inputs/corpus_source_map.csv",
    "SOURCE-LIBRARY-C5/inputs/target_publications.csv", "WS-A-STATUTORY/army_act_amendment_chain.csv",
    "WS-A-STATUTORY/army_act_amendment_chain_addendum_cycle3.csv", "WS-A-STATUTORY/provision_change_log.csv",
    "WS-A-STATUTORY/provision_change_log_supersessions_cycle3.csv", "WS-A-STATUTORY/statutory_version_completeness_cycle3.csv",
    "WS-B-JUDGMENTS/open_inconsistencies_cycle3.csv", "WS-D-QUALITY/canonical_coverage.csv",
    "SOURCE-LIBRARY-C5/tools/build_registers.py", "CALIBRATION-02/tools/evidence_classification.py",
]
REPO_INPUTS = ["legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl",
               "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"]
# The frozen Cycle 5 outputs that v0000 must reproduce byte-for-byte.
C5_REGISTERS = ["SOURCE-LIBRARY-C5/registers/" + n for n in (
    "source_copy_register.csv", "source_master_register.csv", "corpus_crosswalk.csv", "coverage_summary.json",
    "acquisition_register.csv", "amendment_register.csv", "provision_amendment_chain.csv", "provision_register.csv",
    "source_conflict_register.csv", "legal_adviser_evidence_index.csv")]
# Evidence registers that strength.py reads to judge ledger entries (no C6-01 code is used).
EVIDENCE_INPUTS = sorted(
    [str(Path(p).relative_to(AW)) for p in glob.glob(str(AW / "PILOT-01/sources/*.json")) + glob.glob(str(AW / "R23-VERIFY-01/sources/*.json"))]
    + ["PILOT-01/registers/source_code_resolution_v3.csv", "PILOT-01/registers/source_discovery_2026-11-22.csv",
       "ACQ-02/supplement_inventory.csv", "ACQ-02/page_image_checks_acq02.csv", "WS-A-STATUTORY/identity_transcription_register.csv",
       "ARMY-RULES-CHAIN-01/page_image_checks_chain.csv", "R23-VERIFY-01/registers/page_image_checks.csv",
       "CALIBRATION-02/reviews/A/page_image_checks_A.csv", "CALIBRATION-02/reviews/C/page_image_checks_C.csv",
       "SOURCE-LIBRARY-C5/inputs/page_image_checks_c5.csv", "C6-01-PROVENANCE/inputs/page_image_checks_c6.csv",
       "WS-B-JUDGMENTS/tools/held_copies.csv", "R23-VERIFY-01/registers/amendment_search_2026-11-22.csv",
       "ACQ-01/archive_org_metadata_snapshot.json", "ACQ-02/archive_org_metadata_snapshot_acq02.json",
       "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv"])


def current():
    out = {}
    for rel in C5_BUILD_INPUTS + C5_REGISTERS + EVIDENCE_INPUTS:
        out["legal_knowledge/audit_work/" + rel] = sha256_file(AW / rel)
    for rel in REPO_INPUTS:
        out[rel] = sha256_file(REPO / rel)
    for rel in ("evidence/copy_facts.csv", "evidence/copy_structure.csv"):
        out["legal_knowledge/audit_work/AUTH-LEDGER/" + rel] = sha256_file(PKG / rel)
    return dict(sorted(out.items()))


def verify(root=PKG):
    """Fail closed if any pinned file is missing or differs from its pin (pins read from <root>/frozen_inputs.json)."""
    pins = json.loads((Path(root) / "frozen_inputs.json").read_text(encoding="utf-8"))["files"]
    bad = []
    for rel, sha in pins.items():
        p = REPO / rel
        if not p.is_file():
            bad.append(f"missing {rel}")
        elif sha256_file(p) != sha:
            bad.append(f"hash mismatch {rel}")
    if set(current()) != set(pins):
        bad.append("pin set differs from the declared frozen-input list")
    if bad:
        raise LedgerError("frozen inputs: " + "; ".join(bad))
    return len(pins)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.write:
        (PKG / "frozen_inputs.json").write_text(json.dumps({
            "description": "sha256 pins of every historical file the AUTH-LEDGER overlay reads; any mismatch fails closed",
            "pinned_at_base": "legal-knowledge/v2.5-staging 939a128af242abf268b759b2dff9abf8a2adc585",
            "files": current()}, indent=1) + "\n", encoding="utf-8")
    print(f"pins ok: {verify()} files")


if __name__ == "__main__":
    main()
