#!/usr/bin/env python3
"""Freeze WS-C-MML inputs: SHA-256 of every input file (originals, extractions, registers).
Stdlib only. Run from the repository root:  python3 legal_knowledge/audit_work/WS-C-MML/scripts/build_input_manifest.py <scratchpad>
Scratchpad files are private (never committed); only their hashes are recorded here."""
import csv, hashlib, json, sys
from pathlib import Path

ROOT = Path.cwd()
SP = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = ROOT / "legal_knowledge/audit_work/WS-C-MML/input_manifest.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def entry(p, role, base, **kw):
    p = Path(p)
    e = {"path": str(p.relative_to(base)) if base else str(p), "role": role,
         "bytes": p.stat().st_size, "sha256": sha(p)}
    e.update(kw)
    return e


def main():
    repo = []
    for rel, role in [
        ("legal_knowledge/manual_sources/MML_Originals_Manifest.csv", "mml_originals_manifest"),
        ("legal_knowledge/manual_sources/UPLOAD_RECEIPT_2026-11-22.md", "mml_upload_receipt"),
        ("legal_knowledge/manual_sources/README.md", "mml_readme"),
        ("legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl", "kb_658_original_readonly"),
        ("legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl", "cases_53_original_readonly"),
        ("legal_knowledge/audit_work/PILOT-01/registers/mml_crosswalk_pilot.csv", "pilot_crosswalk_63"),
        ("legal_knowledge/audit_work/PILOT-01/registers/mml_edition_notes.csv", "pilot_edition_notes"),
        ("legal_knowledge/audit_work/PILOT-01/registers/mml_version_diffs.csv", "pilot_version_diffs"),
        ("legal_knowledge/audit_work/PILOT-01/registers/volume_mapping_verification.csv", "pilot_volume_mapping_inferred"),
        ("legal_knowledge/audit_work/PILOT-01/registers/cross_volume_matrix.csv", "pilot_cross_volume_matrix"),
        ("legal_knowledge/audit_work/PILOT-01/registers/page_image_checks.csv", "pilot_page_image_checks_PIC01_11"),
        ("legal_knowledge/audit_work/PILOT-01/registers/source_code_resolution_v3.csv", "code_resolution_v3_87"),
        ("legal_knowledge/audit_work/PILOT-01/registers/code_inventory_snapshot.json", "code_inventory_snapshot"),
        ("legal_knowledge/audit_work/PILOT-01/mml_derived_manifest.json", "pilot_mml_derived_manifest"),
        ("legal_knowledge/audit_work/PILOT-01/ADVISOR_REVIEW_PACKET.md", "pilot_advisor_packet"),
        ("legal_knowledge/audit_work/PILOT-01/record_outcomes.csv", "pilot_record_outcomes"),
        ("legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv", "ar_chain_instruments_37"),
        ("legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv", "ar_chain_chronology_46"),
        ("legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/official_note_discrepancies.csv", "ar_chain_note_discrepancies"),
        ("legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv", "ar_chain_version_seed"),
        ("legal_knowledge/audit_work/SOURCE-CONFLICTS-01/conflict_determinations.csv", "conflicts"),
        ("docs/legal-audit/SOURCE_AUTHORITY_POLICY.md", "policy_v1"),
        ("docs/legal-audit/EVIDENCE_STANDARD.md", "evidence_standard"),
        ("legal_knowledge/audit_work/COORDINATION/WORKSTREAM_CHARTERS.md", "charters"),
    ]:
        repo.append(entry(ROOT / rel, role, ROOT))
    out = {"batch": "WS-C-MML", "frozen_on": "2026-11-22", "source_authority_policy_version": "v1",
           "note": "Scratchpad entries are private working copies; paths are relative to the session scratchpad. "
                   "Hashes prove byte identity of the examined copy only, not authenticity or legal currency.",
           "repo_inputs": repo, "scratchpad_inputs": []}
    if SP:
        man = {r["filename"]: r["sha256"] for r in csv.DictReader(open(ROOT / "legal_knowledge/manual_sources/MML_Originals_Manifest.csv", encoding="utf-8"))}
        for p in sorted((SP / "mml_x/originals").iterdir()):
            out["scratchpad_inputs"].append(entry(p, "mml_original", SP, manifest_sha256=man.get(p.name),
                                                  matches_manifest=(sha(p) == man.get(p.name))))
        out["scratchpad_inputs"].append(entry(SP / "mml_x/MML_Originals_Manifest.csv", "manifest_copy_in_transport_zip", SP,
                                              note="differs from repo copy in bytes (line endings); same rows after CR stripping"))
        out["scratchpad_inputs"].append(entry(SP / "mml_zip/mml.zip", "transport_zip", SP,
                                              receipt_sha256="9d82b9c5cb9ac56f41fd6ca74ed0a4704a5897fd26a239fdbafe0377e511f31c"))
        pil = {f["derived"]: f["derived_sha256"] for f in json.load(open(ROOT / "legal_knowledge/audit_work/PILOT-01/mml_derived_manifest.json"))["files"]}
        for p in sorted((SP / "repro1").iterdir()):
            out["scratchpad_inputs"].append(entry(p, "mml_derived_text_USED", SP, pilot_manifest_sha256=pil.get(p.name),
                                                  matches_pilot_manifest=(sha(p) == pil.get(p.name))))
        for p in sorted((SP / "derived/mml").iterdir()):
            m = sha(p) == pil.get(p.name)
            out["scratchpad_inputs"].append(entry(p, "mml_derived_text_NOT_USED", SP, matches_pilot_manifest=m,
                                                  note=None if m else "differs from PILOT-01 derived manifest; not used"))
        for p in sorted((SP / "ws-c/odt/docpdf").iterdir()):
            out["scratchpad_inputs"].append(entry(p, "doc_rendered_to_pdf_by_LibreOffice_24.2.7.2 (render aid only)", SP))
        for n in ["act-army-1950.txt", "rules-army-rules-1954.txt", "act-army-1950.json", "rules-army-rules-1954.json"]:
            out["scratchpad_inputs"].append(entry(SP / "derived/statutes" / n, "india_code_compilation_text (comparison only)", SP))
    if SP and (SP / "ws-c/pcl.csv").exists():
        out["scratchpad_inputs"].append(entry(SP / "ws-c/pcl.csv", "wsa_provision_change_log (git show origin/claude/ws-a-statutory:legal_knowledge/audit_work/WS-A-STATUTORY/provision_change_log.csv @ 74530be9)", SP))
    if SP and (SP / "ws-c/wsb_ids.csv").exists():
        out["scratchpad_inputs"].append(entry(SP / "ws-c/wsb_ids.csv", "wsb_identity_resolution (git show origin/claude/ws-b-judgments:legal_knowledge/audit_work/WS-B-JUDGMENTS/identity_resolution.csv @ 97de40b3)", SP))
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    bad = [e["path"] for e in out["scratchpad_inputs"] if e.get("matches_manifest") is False]
    print("inputs:", len(repo), "+", len(out["scratchpad_inputs"]), "originals mismatching manifest:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
