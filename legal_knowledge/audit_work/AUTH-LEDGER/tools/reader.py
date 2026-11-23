"""Effective-state reader (rule version 1). Baseline + approved ledger entries -> copy states -> source states ->
crosswalk and coverage. Offline and deterministic.

Rule 1 = the Cycle 5 state machine exactly as frozen: the overlay computes copy statuses with its own rules_v1 (never
the frozen Cycle 4 module), then runs the hash-pinned frozen Cycle 5 functions master_rows, check_holding_vs_copies,
crosswalk and the row builders on those statuses. The frozen Cycle 5 builder is imported only after every pin verifies,
and its build() is never called. Source holding states are derived by the explicit transition table in
derive_holding(); no source-status register is kept by hand. With zero entries the outputs are byte-identical to the
frozen Cycle 5 registers (tested)."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AW, PKG, LedgerError, csv_text, read_csv  # noqa: E402
import ledger as L  # noqa: E402
import pins  # noqa: E402
import rules_v1 as R  # noqa: E402

OUT_NAMES = ["source_copy_register.csv", "source_master_register.csv", "corpus_crosswalk.csv", "coverage_summary.json",
             "source_states.csv", "transitions.json", "newly_withdrawn.json"]  # logs are JSON arrays (may be empty; CSV must not be header-only)
FROZEN_EQUAL = {"source_copy_register.csv", "source_master_register.csv", "corpus_crosswalk.csv", "coverage_summary.json"}


def frozen_builder(root=PKG):
    pins.verify(root)  # fail closed before any frozen code runs
    sys.path.insert(0, str(AW / "SOURCE-LIBRARY-C5/tools"))
    import build_registers as B
    return B


def _held_index():
    held = defaultdict(list)
    for r in read_csv(AW / "CALIBRATION-02/registers/held_sources_scratchpad.csv"):
        held[r["sha256"]].append(r["scratchpad_relative_path"])
    return held


def copy_rows(B, master, held_c5, held_c4, eff):
    """Same columns and values as the frozen copy_rows, with status from rules_v1 on the effective register."""
    ann = {(r["source_id"], r["sha256"]): r for r in read_csv(AW / "SOURCE-LIBRARY-C5/inputs/copy_annotations.csv")}
    rows = []
    for m in master:
        for i, s in enumerate([x for x in m["sha256"].split(";") if x], 1):
            hs = held_c5[s]
            reg = eff.get(s)
            st, _ = R.copy_status(s, held_c4.get(s, []), reg)
            a = ann.get((m["source_id"], s), {})
            reg = reg or {}
            rows.append({
                "copy_id": f'{m["source_id"]}~C{i}', "source_id": m["source_id"], "sha256": s,
                "held_paths": ";".join(sorted(h["held_path"] for h in hs)), "bytes": hs[0]["bytes"], "pages": hs[0]["pages"],
                "text_layer_class": hs[0]["text_layer_class"], "copy_role": a.get("copy_role", "COPY"),
                "page_equivalent_to": a.get("page_equivalent_to", ""), "equivalence_basis": a.get("equivalence_basis", ""),
                "copy_carrier_provenance": a.get("copy_carrier_provenance", "") or m["carrier_provenance"],
                "acquisition_provenance": reg.get("provenance_references", "") or a.get("acquisition_provenance", "") or "NOT_DOCUMENTED",
                "c4_register_state": reg.get("authentication_state", "NO_REGISTER_ROW"),
                "c4_effective_source_class": reg.get("effective_source_class", ""),
                "copy_effective_status": st, "copy_evidence_class": R.COPY_CLASS.get(st, "NOT_CLASSIFIED"),
                "eligible_for_exact_anchor": "YES" if st == R.EFFECTIVE_PRIMARY else "NO"})
    return rows


def derive_holding(frozen, copies, touched, publication_type):
    """Explicit transition table (INTEGRATION_ARCHITECTURE.md rev 2, s.4.3). Unrecognised combinations fail closed."""
    prim = sorted({c["c4_effective_source_class"] for c in copies if c["copy_effective_status"] == R.EFFECTIVE_PRIMARY})
    pend = any(c["copy_effective_status"] == R.PENDING for c in copies)
    if prim:
        subs = sorted({L.SUBTYPE.get(c) for c in prim})
        if None in subs:
            raise LedgerError(f"unsupported primary class among {prim}")
        if frozen in subs:
            return frozen, "unchanged (primary copy of the same class)"
        if len(subs) == 1 and frozen.startswith(("HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED", "HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED",
                                                 "HELD_AUTHENTICATION_PENDING", "HELD_PRIMARY_")):
            return subs[0], f"effective primary copy of class {prim[0]}"
        raise LedgerError(f"ambiguous or unsupported primary transition from {frozen} with classes {prim}")
    if pend:
        if not frozen.startswith("HELD"):
            raise LedgerError(f"pending copy on a source whose frozen state is {frozen}")
        return "HELD_AUTHENTICATION_PENDING", "a pending copy and no primary copy"
    if frozen.startswith("HELD_PRIMARY") or frozen == "HELD_AUTHENTICATION_PENDING":
        if not touched:
            raise LedgerError(f"frozen {frozen} but no primary/pending copy and no WITHDRAW/CORRECTION touched this source")
        return ("HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED" if publication_type == "JUDICIAL"
                else "HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED"), "primary/pending copy withdrawn or corrected; basis from publication type"
    return frozen, "unchanged"


def summary(B, master, copies, cw, out):
    """Identical structure to the frozen build() summary. c4_register_* count the real Cycle 4 register rows only."""
    kb = defaultdict(set)
    for r in cw:
        if r["knowledge_base_record_id"]:
            kb[r["knowledge_base_record_id"]].add(r["evidence_status"])
    rec_class = lambda s: "ALL_EXACT" if s == {"EXACT_ANCHOR"} else "NO_EXACT_ANCHOR" if "EXACT_ANCHOR" not in s else "SOME_EXACT"
    reg = read_csv(AW / "CALIBRATION-02/registers/source_authentication_register.csv")
    docs = {c["source_id"] for c in copies if c["copy_effective_status"] == R.EFFECTIVE_PRIMARY}
    pend = {c["source_id"] for c in copies if c["copy_effective_status"] == R.PENDING}
    return {
        "authentication": {
            "c4_register_rows": len(reg),
            "c4_register_by_state_and_class": dict(sorted(Counter(f'{r["authentication_state"]}/{r["effective_source_class"]}' for r in reg).items())),
            "copies_total": len(copies),
            "copies_by_evidence_class": dict(sorted(Counter(c["copy_evidence_class"] for c in copies).items())),
            "documented_primary_copies": sum(1 for c in copies if c["copy_effective_status"] == R.EFFECTIVE_PRIMARY),
            "authentication_pending_copies": sum(1 for c in copies if c["copy_effective_status"] == R.PENDING),
            "sources_with_documented_primary_copy": len(docs),
            "sources_authentication_pending_only": len(pend - docs),
        },
        "master_by_evidence_stage": dict(sorted(Counter(r["evidence_stage"] for r in master).items())),
        "master_sources": len(master),
        "master_by_priority": dict(sorted(Counter(r["priority"] for r in master).items())),
        "master_by_holding_state": dict(sorted(Counter(r["holding_state"].split(" ")[0] for r in master).items())),
        "acquisition_items": len(out["acquisition"]),
        "amendment_rows": len(out["amendment"]), "provision_chain_rows": len(out["chain"]),
        "provision_register_rows": len(out["provision"]), "conflict_rows": len(out["conflict"]),
        "crosswalk_rows": len(cw),
        "crosswalk_kb_items_by_status": dict(sorted(Counter(r["evidence_status"] for r in cw if r["knowledge_base_record_id"]).items())),
        "crosswalk_case_rows_by_status": dict(sorted(Counter(r["evidence_status"] for r in cw if r["case_id"]).items())),
        "kb_records_in_crosswalk": len(kb),
        "kb_records_by_anchor_class": dict(sorted(Counter(rec_class(s) for s in kb.values()).items())),
        "kb_items_by_source": dict(sorted(Counter(r["source_id"] for r in cw if r["knowledge_base_record_id"]).items())),
    }


def effective_state(root=PKG, as_of=None):
    """Return {output name: text} for the ledger at `root` as of version `as_of` (default: HEAD)."""
    B = frozen_builder(root)
    held_c5, by_name = defaultdict(list), {}
    for h in read_csv(AW / "SOURCE-LIBRARY-C5/baseline/held_binaries_manifest.csv"):
        held_c5[h["rehashed_sha256"]].append(h)
        by_name.setdefault(h["held_path"].rsplit("/", 1)[-1], h["rehashed_sha256"])
    cands = {}
    for p in sorted((AW / "SOURCE-LIBRARY-C5/discovery").glob("*_candidates.csv")):
        for r in read_csv(p):
            cands[r["candidate_id"]] = r
    baseline = {r["sha256"]: r for r in read_csv(AW / "CALIBRATION-02/registers/source_authentication_register.csv")}
    targets = read_csv(AW / "SOURCE-LIBRARY-C5/inputs/target_publications.csv")
    frozen_master = B.master_rows(held_c5, cands, baseline, targets)
    master_by = {m["source_id"]: m for m in frozen_master}
    c5_copies = {r["sha256"]: r for r in read_csv(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv")}
    held_c4 = _held_index()
    ctx = L.Context(held_c4, baseline, c5_copies, master_by)
    eff, transitions, withdrawn, lines = L.apply_ledger(root, ctx, as_of)
    copies = copy_rows(B, frozen_master, held_c5, held_c4, eff)
    touched = {c5_copies[t["sha256"]]["source_id"] for t in transitions
               if t["effect"] == "APPLIED" and t["entry_type"] in ("WITHDRAW", "CORRECTION") and t["sha256"] in c5_copies}
    states, new_targets = [], []
    for t in targets:
        cs = [c for c in copies if c["source_id"] == t["source_id"]]
        hs, why = derive_holding(t["holding_state"], cs, t["source_id"] in touched, master_by[t["source_id"]]["publication_type"])
        states.append({"source_id": t["source_id"], "frozen_holding_state": t["holding_state"], "effective_holding_state": hs, "basis": why})
        new_targets.append(dict(t, holding_state=hs))
    master = B.master_rows(held_c5, cands, eff, new_targets)
    B.check_holding_vs_copies(master, copies)  # the frozen consistency rule stays on
    cw = B.crosswalk(master, copies)
    out = {"acquisition": B.acquisition_rows(master), "amendment": B.amendment_rows(), "chain": B.chain_rows(),
           "provision": B.provision_rows(by_name), "conflict": B.conflict_rows()}
    texts = {
        "source_copy_register.csv": B.csv_text(B.COLS["source_copy_register.csv"], copies),
        "source_master_register.csv": B.csv_text(B.COLS["source_master_register.csv"], master),
        "corpus_crosswalk.csv": B.csv_text(B.COLS["corpus_crosswalk.csv"], cw),
        "coverage_summary.json": json.dumps(summary(B, master, copies, cw, out), indent=1, sort_keys=True) + "\n",
        "source_states.csv": csv_text(["source_id", "frozen_holding_state", "effective_holding_state", "basis"], states),
        "transitions.json": json.dumps(transitions, indent=1) + "\n",
        "newly_withdrawn.json": json.dumps(withdrawn, indent=1) + "\n",
    }
    return texts, lines
