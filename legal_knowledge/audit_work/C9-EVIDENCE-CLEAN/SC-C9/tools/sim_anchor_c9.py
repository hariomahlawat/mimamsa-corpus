"""SIMULATION ONLY (Cycle 9): exact-anchor recalculation for the 8 Supreme Court primary candidates of the C6-01 draft
addendum, plus option (b) of P-D3 applied consistently (PPS Bedi baseline row demoted in a TEMPORARY ledger).

Synthetic approval records are written ONLY in temporary directories under <tmp_parent>, each deleted after its run.
Nothing is written to the snapshot (bytecode writing is disabled before the snapshot tools are imported). Not a ledger
version, not an approval, not evidence of owner or legal approval. No result here says anything about whether any
judgment is good law, binding, followed or overruled.

usage: python -I sim_anchor_c9.py <snapshot_audit_work_dir> <tmp_parent> <out_json> [--check]
  --check  recompute and compare with the existing <out_json>; exit 1 on any difference (nothing is written).

Uses the snapshot's own AUTH-LEDGER/tools/reader.py effective_state (rule version 1), ledger.py and strength.py. The
Sim/to_entry pattern is that of C8 SC-T2/tools/sim_anchor.py (itself from AUTH-LEDGER/tranches/tools/build_tranche1.py)."""
import sys
sys.dont_write_bytecode = True
import csv, io, json, shutil, tempfile
from collections import Counter
from pathlib import Path

args = [a for a in sys.argv[1:] if a != "--check"]
CHECK = "--check" in sys.argv[1:]
AWD, TMP, OUT = Path(args[0]).resolve(), Path(args[1]).resolve(), Path(args[2])
PKG = AWD / "AUTH-LEDGER"
sys.path.insert(0, str(PKG / "tools"))
from common import LedgerError, read_csv, sha256_file, sha256_text, csv_text  # noqa: E402
import ledger as L  # noqa: E402
import reader  # noqa: E402
import strength  # noqa: E402

CLS = "PRIMARY_OFFICIAL_COURT_COPY"
RENDITION = "NON_PRIMARY_OFFICIAL_COURT_RENDITION"
SIM_DATE = "2026-11-23"
DRAFT = AWD / "C6-01-PROVENANCE/addendum/authentication_addendum_v1_draft.csv"
JUDIS3 = ("RANJIT", "MUKHERJEE", "NAVJOT")
BEDI_SHA = "211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca"
LABEL = ("SIMULATION ONLY: synthetic approval records in temporary directories, deleted after each run. Not a ledger version, "
         "not an approval, not evidence of owner or legal approval. The committed ledger stays at version 0. "
         "Says nothing about precedent status.")


def to_entry(d, n, cp, cls=None):
    cls = cls or d["proposed_class"]
    e = {k: "" for k in L.COLS}
    e.update({"entry_id": f"AL-v0001-{n:03d}", "entry_version": "0001", "entry_type": "ADD", "sha256": d["sha256"],
              "source_id": d["source_id"], "copy_id": d["copy_id"], "document_identity": d["document_identity"],
              "evidence_refs": d["evidence_refs"], "first_class_record_ref": d["first_class_record_ref"],
              "identity_refs": d["identity_refs"].replace("T:C6-01-PROVENANCE/inputs/held_copy_facts.csv#", "T:AUTH-LEDGER/evidence/copy_facts.csv#"),
              "proposed_authentication_state": "PROVENANCE_DOCUMENTED", "proposed_class": cls,
              "carrier": cp[d["sha256"]]["copy_carrier_provenance"],
              "official_locator_recorded": strength._first_class(d["first_class_record_ref"], d["sha256"])[2],
              "limitations": d["limitations"], "justification": d["justification"], "rule_version": "1", "owner_decision": ""})
    return e


def bedi_demotion(n, cp, variant):
    """Synthetic demotion of the PPS Bedi BASELINE row (option (b)). Evidence references are the two records the frozen
    Cycle 4 register itself cites for this copy."""
    c = cp[BEDI_SHA]
    e = {k: "" for k in L.COLS}
    e.update({"entry_id": f"AL-v0001-{n:03d}", "entry_version": "0001", "sha256": BEDI_SHA, "source_id": c["source_id"],
              "copy_id": c["copy_id"], "document_identity": "Lt Col Prithi Pal Singh Bedi v Union of India, SC 25-08-1982 (JUDIS 9884)",
              "target_entry_id": "BASELINE:" + BEDI_SHA,
              "evidence_refs": "L1:PILOT-01/registers/source_code_resolution_v3.csv#SC_PPS; WSB:WS-B-JUDGMENTS/tools/held_copies.csv#PPS_BEDI",
              "carrier": c["copy_carrier_provenance"], "rule_version": "1", "owner_decision": "",
              "limitations": "SIMULATION: JUDIS typed-text rendition (Ghostscript 7.05; database fields; HEADNOTE pp.1-7; no signature/date block)",
              "justification": "SIMULATION of P-D3 option (b): JUDIS typed-text database renditions are court-system renditions, non-primary"})
    if variant == "CORRECTION_NON_PRIMARY_DOCUMENTED":
        e.update({"entry_type": "CORRECTION", "proposed_authentication_state": "PROVENANCE_DOCUMENTED", "proposed_class": RENDITION,
                  "first_class_record_ref": "PILOT-01/registers/source_code_resolution_v3.csv#SC_PPS",
                  "official_locator_recorded": strength._first_class("PILOT-01/registers/source_code_resolution_v3.csv#SC_PPS", BEDI_SHA)[2],
                  "identity_refs": f"T:AUTH-LEDGER/evidence/copy_facts.csv#{c['copy_id']}"})
    elif variant == "CORRECTION_PENDING":
        e.update({"entry_type": "CORRECTION", "proposed_authentication_state": "AUTHENTICATION_PENDING", "proposed_class": "AUTHENTICATION_PENDING"})
    elif variant == "WITHDRAW_PENDING":
        e.update({"entry_type": "WITHDRAW", "withdrawal_reason": "CLASSIFICATION_ERROR", "resulting_state": "AUTHENTICATION_PENDING"})
    else:
        raise ValueError(variant)
    return e


class Sim:
    def __init__(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(prefix="c9_sc_sim_", dir=TMP))
        shutil.copy(PKG / "frozen_inputs.json", self.dir / "frozen_inputs.json")
        (self.dir / "ledger").mkdir()
        (self.dir / "decisions").mkdir()
        shutil.copy(PKG / "ledger/manifest.jsonl", self.dir / "ledger/manifest.jsonl")
        shutil.copy(PKG / "ledger/HEAD", self.dir / "ledger/HEAD")

    def run(self, entries):
        es = [dict(e, owner_decision="APPROVED") for e in entries]
        for i, e in enumerate(es):  # renumber so any subset is a valid version file
            e["entry_id"] = f"AL-v0001-{i + 1:03d}"
        pairs = ";".join(f"{e['entry_id']}={e['sha256']}:{L.entry_digest(e)}" for e in es)
        recs = {}
        for name, body in (("D-v0001.md", f"decision_id: D-v0001\ndecision: APPROVED\nledger_version: 0001\nentries: {pairs}\ndecided_by: simulation owner\n"
                                          f"date: {SIM_DATE}\nscope: AUTHENTICATION_PROVENANCE_ONLY\nlegal_approval: NOT_GIVEN\n"),
                           ("R-v0001.md", f"review_id: R-v0001\nverdict: ACCEPT\nledger_version: 0001\nentries: {pairs}\nreviewer: simulation reviewer\n"
                                          f"date: {SIM_DATE}\nscope: TECHNICAL_AND_EVIDENCE_REVIEW\nlegal_approval: NOT_GIVEN\n")):
            (self.dir / "decisions" / name).write_text(body, encoding="utf-8")
            recs[name] = sha256_file(self.dir / "decisions" / name)
        for e in es:
            e["decision_record_ref"], e["decision_record_sha256"] = "decisions/D-v0001.md", recs["D-v0001.md"]
            e["reviewer_ref"], e["reviewer_record_sha256"] = "decisions/R-v0001.md", recs["R-v0001.md"]
        (self.dir / "ledger/v0001.csv").write_text(csv_text(L.COLS, es), encoding="utf-8")
        prev = sha256_text((self.dir / "ledger/manifest.jsonl").read_text(encoding="utf-8").split("\n")[-2])
        line = {"version": 1, "prev": prev, "date": SIM_DATE, "rule_version": 1, "frozen_inputs_sha256": sha256_file(self.dir / "frozen_inputs.json"),
                "file": "ledger/v0001.csv", "file_sha256": sha256_file(self.dir / "ledger/v0001.csv"),
                "decisions": {"decisions/D-v0001.md": recs["D-v0001.md"]}, "reviews": {"decisions/R-v0001.md": recs["R-v0001.md"]},
                "effective_sha256": "", "note": "SIMULATION"}
        s = L.canonical_line(line)
        with open(self.dir / "ledger/manifest.jsonl", "a", encoding="utf-8") as fh:
            fh.write(s + "\n")
        (self.dir / "ledger/HEAD").write_text(f"1 {sha256_text(s)}\n", encoding="utf-8")
        texts, _ = reader.effective_state(self.dir, 1, require_binding=False)
        return texts

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def rows(t):
    return list(csv.DictReader(io.StringIO(t)))


def keyed(cw):
    out, seen = {}, Counter()
    for r in cw:
        k = (r["source_id"], r["provision_id"], r["knowledge_base_record_id"], r["case_id"], r["relationship_type"])
        seen[k] += 1
        out[k + (seen[k],)] = r
    return out


def summarize(texts):
    cw = rows(texts["corpus_crosswalk.csv"])
    case = [r for r in cw if r["case_id"]]
    return {"crosswalk_rows": len(cw),
            "case_rows_by_status": dict(sorted(Counter(r["evidence_status"] for r in case).items())),
            "exact_anchor_case_count": len({r["case_id"] for r in case if r["evidence_status"] == "EXACT_ANCHOR"}),
            "exact_anchor_cases": sorted({(r["case_id"], r["source_id"], r["anchor_copy_id"]) for r in case if r["evidence_status"] == "EXACT_ANCHOR"}),
            "kb_rows_by_status": dict(sorted(Counter(r["evidence_status"] for r in cw if r["knowledge_base_record_id"]).items())),
            "coverage_crosswalk_case_rows_by_status": json.loads(texts["coverage_summary.json"])["crosswalk_case_rows_by_status"]}


def diff(base, after):
    b, a = keyed(rows(base["corpus_crosswalk.csv"])), keyed(rows(after["corpus_crosswalk.csv"]))
    ch = []
    for k in sorted(set(b) | set(a)):
        rb, ra = b.get(k), a.get(k)
        if rb is None or ra is None or any(rb[c] != ra[c] for c in rb):
            cols = sorted(c for c in (rb or ra) if (rb or {}).get(c) != (ra or {}).get(c))
            ch.append({"case_id": k[3], "source_id": k[0], "kb_id": k[2], "relationship": k[4], "changed_columns": cols,
                       "evidence_status": [(rb or {}).get("evidence_status"), (ra or {}).get("evidence_status")],
                       "anchor_copy_id": [(rb or {}).get("anchor_copy_id"), (ra or {}).get("anchor_copy_id")]})
    bc = {r["sha256"]: r for r in rows(base["source_copy_register.csv"])}
    ac = {r["sha256"]: r for r in rows(after["source_copy_register.csv"])}
    copies = [{"copy_id": ac[s]["copy_id"], "before": bc[s]["copy_effective_status"], "after": ac[s]["copy_effective_status"],
               "eligible_for_exact_anchor": ac[s]["eligible_for_exact_anchor"]} for s in sorted(bc) if bc[s]["copy_effective_status"] != ac[s]["copy_effective_status"]]
    bs = {r["source_id"]: r for r in rows(base["source_states.csv"])}
    as_ = {r["source_id"]: r for r in rows(after["source_states.csv"])}
    src = [{"source_id": k, "before": bs[k]["effective_holding_state"], "after": as_[k]["effective_holding_state"]} for k in sorted(bs)
           if bs[k]["effective_holding_state"] != as_[k]["effective_holding_state"]]
    return {"crosswalk_row_changes": ch, "copy_status_changes": copies, "source_holding_changes": src}


def attempt(base, entries, note):
    sim = Sim()
    try:
        t = sim.run(entries)
        s = summarize(t)
        return {"result": "PASS", "note": note, "entries": [f"{e['entry_type']} {e['copy_id']} ({e['proposed_class'] or e['resulting_state']})" for e in entries],
                "exact_anchor_case_count": s["exact_anchor_case_count"], "summary": s, "diff": diff(base, t)}
    except (LedgerError, KeyError, ValueError) as ex:
        msg = str(ex).replace(str(sim.dir), "<tmp>")[:600]
        return {"result": "FAIL (validator rejected the synthetic version)", "note": note,
                "entries": [f"{e['entry_type']} {e['copy_id']}" for e in entries], "reason": msg}
    finally:
        sim.close()


def main():
    drafts = sorted([r for r in read_csv(DRAFT) if r["proposed_class"] == CLS], key=lambda d: d["source_id"])
    cp = {r["sha256"]: r for r in read_csv(AWD / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv")}
    entries = [to_entry(d, i + 1, cp) for i, d in enumerate(drafts)]
    judis = lambda e: any(x in e["copy_id"] for x in JUDIS3)
    base, _ = reader.effective_state(PKG, 0)
    frozen = {n: (AWD / "SOURCE-LIBRARY-C5/registers" / n).read_text(encoding="utf-8") for n in ("corpus_crosswalk.csv", "coverage_summary.json")}
    v0 = summarize(base)
    res = {"label": LABEL, "candidates": [{"copy_id": e["copy_id"], "sha256": e["sha256"]} for e in entries],
           "version0": {"exact_anchor_case_count": v0["exact_anchor_case_count"], "summary": v0,
                        "equals_frozen_c5_registers": {n: base[n] == frozen[n] for n in frozen}},
           "single": {}, "joint": {}, "option_b": {}}
    for e in entries:
        res["single"][e["copy_id"]] = attempt(base, [e], "option (a): this candidate alone")
    excl = lambda *xs: [e for e in entries if not any(x in e["copy_id"] for x in xs)]
    res["joint"]["all_8"] = attempt(base, entries, "option (a): all 8 candidates jointly")
    res["joint"]["without_judis3"] = attempt(base, excl(*JUDIS3), "all 8 minus Ranjit, S N Mukherjee, Navjot (PPS Bedi baseline row untouched)")
    res["joint"]["without_navjot_mullikote"] = attempt(base, excl("NAVJOT", "MULLIKOTE"), "C8 preparer recommendation (keep Navjot and Mullikote PARTIAL)")
    res["joint"]["without_judis3_and_mullikote"] = attempt(base, excl(*JUDIS3, "MULLIKOTE"), "context (C8 subset)")
    non_judis = [e for e in entries if not judis(e)]
    n = len(entries) + 1
    res["option_b"]["b0_bedi_demotion_only_correction_pending"] = attempt(base, [bedi_demotion(n, cp, "CORRECTION_PENDING")], "demotion of PPS Bedi alone, from version 0")
    res["option_b"]["b1_correction_to_non_primary_documented"] = attempt(base, non_judis + [bedi_demotion(n, cp, "CORRECTION_NON_PRIMARY_DOCUMENTED")],
                                                                         "5 non-JUDIS candidates + PPS Bedi CORRECTION to NON_PRIMARY_OFFICIAL_COURT_RENDITION (documented)")
    res["option_b"]["b2_correction_to_pending"] = attempt(base, non_judis + [bedi_demotion(n, cp, "CORRECTION_PENDING")],
                                                          "5 non-JUDIS candidates + PPS Bedi CORRECTION to AUTHENTICATION_PENDING")
    res["option_b"]["b3_withdraw_to_pending"] = attempt(base, non_judis + [bedi_demotion(n, cp, "WITHDRAW_PENDING")],
                                                        "5 non-JUDIS candidates + PPS Bedi WITHDRAW (CLASSIFICATION_ERROR, resulting AUTHENTICATION_PENDING)")
    rend = [to_entry(d, 50 + i, cp, RENDITION) for i, d in enumerate(drafts) if any(x in d["copy_id"] for x in JUDIS3)]
    res["option_b"]["b4_b2_plus_judis3_added_as_non_primary_rendition"] = attempt(
        base, non_judis + rend + [bedi_demotion(n, cp, "CORRECTION_PENDING")],
        "b2 plus the 3 JUDIS drafts ADDed as NON_PRIMARY_OFFICIAL_COURT_RENDITION (fully consistent class for all four renditions)")
    res["option_b"]["b5_b2_without_mullikote"] = attempt(base, [e for e in non_judis if "MULLIKOTE" not in e["copy_id"]] + [bedi_demotion(n, cp, "CORRECTION_PENDING")],
                                                         "context: option (b) and Mullikote kept PARTIAL")
    res["option_c_count_proxy"] = {
        "note": "Rule 1 cannot express option (c) (judgment-text scope, page-range anchors). These runs are COUNT PROXIES only: the "
                "JUDIS condition 'no later order known' withholds Ranjit (review order of 10.8.88 known, not held); PPS Bedi stays as at "
                "version 0. They do not model headnote exclusion.",
        "c1_all_8_minus_ranjit": attempt(base, excl("RANJIT"), "count proxy for (c): Ranjit withheld"),
        "c2_minus_ranjit_navjot_mullikote": attempt(base, excl("RANJIT", "NAVJOT", "MULLIKOTE"), "count proxy for (c) with the C8 keep-PARTIAL recommendations")}
    text = json.dumps(res, indent=1, sort_keys=True) + "\n"
    counts = {"v0": v0["exact_anchor_case_count"],
              **{f"single:{k}": v.get("exact_anchor_case_count", v["result"]) for k, v in res["single"].items()},
              **{f"joint:{k}": v.get("exact_anchor_case_count", v["result"]) for k, v in res["joint"].items()},
              **{f"option_b:{k}": v.get("exact_anchor_case_count", v["result"]) for k, v in res["option_b"].items()},
              **{f"option_c_proxy:{k}": v.get("exact_anchor_case_count", v["result"]) for k, v in res["option_c_count_proxy"].items() if k != "note"}}
    print(json.dumps(counts, indent=1))
    if CHECK:
        same = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print("CHECK", "OK: output reproduces" if same else "DIFFERS")
        sys.exit(0 if same else 1)
    OUT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
