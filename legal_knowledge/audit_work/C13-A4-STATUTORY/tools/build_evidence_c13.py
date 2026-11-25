#!/usr/bin/env python3
"""C13 A4: further evidence improvement over the 983 frozen citation items (proposals only).

Re-runs the reviewed C12F-v1.1 evidence engine (C12-CONSOLIDATION/statutory_citations/tools/build_c12f.py,
imported unchanged) with two differences only:

  1. the curated page evidence is the C12 file PLUS inputs/page_evidence_c13.csv (21 new page-image checks of the
     held 1954 Gazette and S.R.O. 17(E)/1993, rendered from the HF preservation copies); every new row passes the
     same engine checks (sha256 of the copy, text-layer probes, 1954 heading-index/page agreement, page ranges);
  2. a stricter C13 gate: a NEW promotion is kept only if every 1954 principal page behind every cited rule is
     image-checked (C12 or C13 row) - no promotion rests on a text-layer-only 1954 page.

Everything else (blockers F-01..F-07, reserved conflicts, open alleged amendments, record scope) is the C12F logic.
Outputs are written to ../outputs/ and are proposals: nothing in any register or the KB is changed.

Usage: build_evidence_c13.py [--check]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict

from c13a4_common import (AW, C12F_TOOLS, HELD_BASE, PKG, REPO, assert_no_restricted, csv_bytes, prepare_held_base,
                          read_csv, require_env, sha256_bytes, sha256_file, verify_frozen)

VERSION = "C13A4-EV-v1"
OUT = PKG / "outputs"
PE_C13_REL = "legal_knowledge/audit_work/C13-A4-STATUTORY/inputs/page_evidence_c13.csv"
PE_C12_REL = "legal_knowledge/audit_work/C12-CONSOLIDATION/statutory_citations/tools/page_evidence_c12.csv"
C12F_MATRIX = AW / "C12-CONSOLIDATION/statutory_citations/outputs/IMPROVEMENT_MATRIX.csv"
STATES = ("EXACT_ANCHOR", "PARTIAL_MATCH", "MISSING_EVIDENCE")

MATRIX_FIELDS = ["item_id", "crosswalk_line", "kb_record_id", "volume_family", "source_id", "provision_id", "tier", "primary_subject",
                 "baseline_state", "c12f_state_proposed", "c13_state_proposed", "c13_change", "c13_gate", "record_level_state_c13",
                 "exact_scope_c13", "blockers_c13", "improvement_action", "verification_ids_c13", "new_page_evidence_ids"]
PROP_FIELDS = ["proposal_id", "version", "proposal_type", "item_id", "kb_record_id", "provision_id", "current_state_c12f", "proposed_state",
               "instrument_edition_pages", "copy_sha256", "page_evidence_ids", "render_png_sha256", "record_scope", "conditions",
               "reviewer_required", "status"]
VERIF_FIELDS = ["verification_id", "item_id", "kb_record_id", "provision", "source_copy_id", "copy_sha256", "edition_or_version", "pdf_page",
                "printed_page", "page_evidence_method", "excerpt", "excerpt_source", "amendment_evidence", "commencement_evidence",
                "supersession", "temporal_applicability", "reserved_conflict", "blockers", "status", "applicability_note"]


def load_engine():
    sys.path.insert(0, str(C12F_TOOLS))
    import build_c12f as b  # noqa: PLC0415
    if b.VERSION != "C12F-v1.1":
        raise SystemExit(f"unexpected C12F engine version {b.VERSION}")
    b.SCRATCH = HELD_BASE
    b.INPUTS["page_evidence_c13"] = PE_C13_REL
    orig = b.read_csv

    def read_csv_merged(rel):
        if rel == PE_C12_REL:
            return orig(PE_C12_REL) + orig(PE_C13_REL)
        return orig(rel)
    b.read_csv = read_csv_merged
    return b


def build():
    frozen = verify_frozen()
    prov = prepare_held_base()
    b = load_engine()
    matrix, verif, _xv, _props, summary = b.build()
    c12 = {r["item_id"]: r for r in read_csv(C12F_MATRIX)}
    pe13 = read_csv(REPO / PE_C13_REL)
    pe_ids13 = {e["evidence_id"] for e in pe13}
    pe_by_id = {e["evidence_id"]: e for e in read_csv(REPO / PE_C12_REL) + pe13}
    vby = {}
    for v in verif:
        vby.setdefault(v["item_id"], []).append(v)

    rows, proposals = [], []
    for r in sorted(matrix, key=lambda x: x["item_id"]):
        old = c12[r["item_id"]]
        if old["baseline_state"] != r["baseline_state"]:
            raise SystemExit(f"baseline drift {r['item_id']}")
        vs = vby.get(r["item_id"], [])
        used13 = sorted({i for v in vs for i in pe_ids13 if i in (v.get("page_evidence_method") or "")})
        state, change, gate = r["c12_state_proposed"], "NONE", ""
        if state != old["c12_state_proposed"]:
            if old["c12_state_proposed"] == "PARTIAL_MATCH" and state == "EXACT_ANCHOR":
                text_only = [v["provision"] for v in vs if "text layer only" in (v.get("page_evidence_method") or "")]
                if text_only:
                    state, change, gate = "PARTIAL_MATCH", "NONE", "C13_GATE_BLOCKED: 1954 page text-layer only for " + "; ".join(text_only)
                else:
                    change, gate = "PROMOTE_PARTIAL_TO_EXACT_PROPOSED_C13", "C13_GATE_PASSED: every 1954 principal page and every amending page image-checked"
            else:
                raise SystemExit(f"unexpected state movement {r['item_id']}: {old['c12_state_proposed']} -> {state}")
        elif used13:
            change = "PAGE_EVIDENCE_ADDED_C13"
        rows.append({"item_id": r["item_id"], "crosswalk_line": r["crosswalk_line"], "kb_record_id": r["kb_record_id"],
                     "volume_family": r["volume_family"], "source_id": r["source_id"], "provision_id": r["provision_id"], "tier": r["tier"],
                     "primary_subject": r["primary_subject"], "baseline_state": r["baseline_state"], "c12f_state_proposed": old["c12_state_proposed"],
                     "c13_state_proposed": state, "c13_change": change, "c13_gate": gate, "blockers_c13": r["c12_blockers"],
                     "improvement_action": r["improvement_action"], "verification_ids_c13": r["verification_ids"],
                     "new_page_evidence_ids": ";".join(used13)})

    # record-level state (F-04 rule, recomputed on C13 states)
    rank = {"MISSING_EVIDENCE": 0, "PARTIAL_MATCH": 1, "EXACT_ANCHOR": 2}
    byrec = {}
    for r in rows:
        byrec.setdefault(r["kb_record_id"], []).append(r)
    for rid, rs in byrec.items():
        rls = min((x["c13_state_proposed"] for x in rs), key=lambda s: rank[s])
        for x in rs:
            x["record_level_state_c13"] = rls
            if x["c13_state_proposed"] == "EXACT_ANCHOR":
                x["exact_scope_c13"] = "CITATION_AND_RECORD" if rls == "EXACT_ANCHOR" else f"CITATION_LOCATOR_ONLY: record-level state {rls}"

    n = 0
    for r in rows:
        if r["c13_change"] != "PROMOTE_PARTIAL_TO_EXACT_PROPOSED_C13":
            continue
        n += 1
        vs = vby[r["item_id"]]
        ids = sorted({i for v in vs for i in pe_by_id if i in (v.get("page_evidence_method") or "")})
        proposals.append({
            "proposal_id": f"C13A4-EP{n:03d}", "version": VERSION, "proposal_type": "EVIDENCE_STATE_PROMOTION", "item_id": r["item_id"],
            "kb_record_id": r["kb_record_id"], "provision_id": r["provision_id"], "current_state_c12f": r["c12f_state_proposed"],
            "proposed_state": "EXACT_ANCHOR",
            "instrument_edition_pages": " | ".join(f"{v['provision']}: {v['edition_or_version']}; PDF p.{v['pdf_page']}; printed p.{v['printed_page']}" for v in vs),
            "copy_sha256": ";".join(sorted({s for v in vs for s in v["copy_sha256"].split(";") if s})),
            "page_evidence_ids": ";".join(ids),
            "render_png_sha256": ";".join(f"{i}={pe_by_id[i]['render_png_sha256']}" for i in ids),
            "record_scope": r.get("exact_scope_c13", ""),
            "conditions": ("Anchor is to the version text on the instruments located so far (1954 as notified + S.R.O. 17(E)/1993); currency after the located "
                           "instruments, authentication of the archival facsimiles, commencement of the 1954 principal (AQ-05) and legal applicability are NOT "
                           "established. Citation-level only; no record wording changes. Chain gaps AR-001, AR-030, AR-036 and unopened hints remain."),
            "reviewer_required": "independent evidence reviewer (page images) + legal adviser before any application", "status": "PROPOSED_NOT_APPLIED"})

    def counts(key):
        return {s: sum(1 for r in rows if r[key] == s) for s in STATES}
    by_source = OrderedDict()
    for r in rows:
        d = by_source.setdefault(r["source_id"], {k: Counter() for k in ("baseline", "c12f", "c13")})
        d["baseline"][r["baseline_state"]] += 1
        d["c12f"][r["c12f_state_proposed"]] += 1
        d["c13"][r["c13_state_proposed"]] += 1
    ba = []
    for s in STATES:
        ba.append({"evidence_state": s, "baseline_c5_c10": counts("baseline_state")[s], "c12f_v1_1_proposed": counts("c12f_state_proposed")[s],
                   "c13_a4_proposed": counts("c13_state_proposed")[s],
                   "change_vs_c12f": counts("c13_state_proposed")[s] - counts("c12f_state_proposed")[s]})
    for src, d in sorted(by_source.items()):
        for s in STATES:
            if d["baseline"][s] or d["c12f"][s] or d["c13"][s]:
                ba.append({"evidence_state": f"{src}:{s}", "baseline_c5_c10": d["baseline"][s], "c12f_v1_1_proposed": d["c12f"][s],
                           "c13_a4_proposed": d["c13"][s], "change_vs_c12f": d["c13"][s] - d["c12f"][s]})
    vrows = [v for v in verif if v["item_id"] in {r["item_id"] for r in rows if r["new_page_evidence_ids"]}]
    summ = OrderedDict([
        ("workstream", "C13 A4 statutory evidence"), ("version", VERSION), ("engine", "C12F-v1.1 build_c12f.py (unchanged, imported)"),
        ("frozen_originals_verified", frozen), ("citation_items", len(rows)),
        ("before_after", {"baseline": counts("baseline_state"), "c12f_v1_1": counts("c12f_state_proposed"), "c13_a4": counts("c13_state_proposed")}),
        ("c13_changes", dict(sorted(Counter(r["c13_change"] for r in rows).items()))),
        ("c13_gate_blocked", sorted(f"{r['item_id']} {r['c13_gate']}" for r in rows if r["c13_gate"].startswith("C13_GATE_BLOCKED"))),
        ("c13_promotions", [f"{p['item_id']} {p['kb_record_id']} {p['provision_id']}" for p in proposals]),
        ("c13_page_evidence_rows", len(pe13)),
        ("page_evidence_validation_c13", {k: v for k, v in summary["page_evidence_validation"].items() if k in pe_ids13}),
        ("c12_promotions_all_retained", all(r["c13_state_proposed"] == "EXACT_ANCHOR" for r in rows if r["c12f_state_proposed"] == "EXACT_ANCHOR")),
        ("anchoring_copy_provenance", {k: v for k, v in sorted(prov.items()) if "ARMY-RULES-1954~" in k or "AR-029" in k}),
        ("pymupdf_version", __import__("pymupdf").VersionBind),
        ("input_sha256", {"page_evidence_c13": sha256_file(REPO / PE_C13_REL), "page_evidence_c12": sha256_file(REPO / PE_C12_REL),
                          "c12f_matrix": sha256_file(C12F_MATRIX), "engine": sha256_file(C12F_TOOLS / "build_c12f.py")}),
        ("honesty_notes", [
            "All C13 states are PROPOSALS. corpus_crosswalk.csv, C10/C12 outputs and the KB are unchanged.",
            "Promotions come only from new page-image checks of held registered eligible copies; no blocker rule was relaxed; MISSING items are never promoted.",
            "The C13 gate is stricter than C12F: no new promotion rests on a text-layer-only 1954 page.",
            "Image readings are by an AI agent and are not human-confirmed; an independent reviewer must re-read the 21 new page rows.",
        ]),
    ])
    files = OrderedDict()
    files["EVIDENCE_MATRIX_C13.csv"] = csv_bytes(rows, MATRIX_FIELDS)
    files["EVIDENCE_PROPOSALS_C13.csv"] = csv_bytes(proposals, PROP_FIELDS)
    files["BEFORE_AFTER_MATRIX_C13.csv"] = csv_bytes(ba, ["evidence_state", "baseline_c5_c10", "c12f_v1_1_proposed", "c13_a4_proposed", "change_vs_c12f"])
    files["VERIFICATION_CHANGED_ITEMS_C13.csv"] = csv_bytes(vrows, VERIF_FIELDS)
    files["EVIDENCE_SUMMARY_C13.json"] = (json.dumps(summ, indent=1, ensure_ascii=False) + "\n").encode()
    for k, v in files.items():
        assert_no_restricted(k, v)
    return files


def main(argv=None):
    require_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    files = build()
    if a.check:
        bad = [n for n, bts in files.items() if not (OUT / n).exists() or (OUT / n).read_bytes() != bts]
        if bad:
            print("CHECK FAILED: " + ", ".join(bad))
            return 1
        print(f"CHECK OK: {len(files)} evidence outputs reproduce byte-for-byte")
        return 0
    OUT.mkdir(exist_ok=True)
    for n, bts in files.items():
        (OUT / n).write_bytes(bts)
    print(json.loads(files["EVIDENCE_SUMMARY_C13.json"])["before_after"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
