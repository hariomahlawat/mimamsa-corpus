"""SIMULATION ONLY: exact-anchor recalculation for the 8 primary Supreme Court candidates of the C6-01 draft addendum.

Synthetic approval records are written ONLY in a temporary directory under <tmp_parent>, which is deleted after each
run. Nothing is written to the snapshot (bytecode writing is disabled before the snapshot tools are imported). Not a
ledger version, not an approval, not evidence of owner or legal approval.

usage: python sim_anchor.py <snapshot_audit_work_dir> <tmp_parent> <out_json>
Pattern reused from AUTH-LEDGER/tranches/tools/build_tranche1.py (class Sim, to_entry), adapted to class
PRIMARY_OFFICIAL_COURT_COPY with T: identity refs rewritten to T:AUTH-LEDGER/evidence/copy_facts.csv#<copy_id>."""
import sys
sys.dont_write_bytecode = True
import csv, io, json, shutil, tempfile
from collections import Counter
from pathlib import Path

AWD, TMP, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3])
PKG = AWD / "AUTH-LEDGER"
sys.path.insert(0, str(PKG / "tools"))
from common import LedgerError, read_csv, sha256_file, sha256_text, csv_text  # noqa: E402
import ledger as L  # noqa: E402
import reader  # noqa: E402
import strength  # noqa: E402

CLS = "PRIMARY_OFFICIAL_COURT_COPY"
SIM_DATE = "2026-11-23"
DRAFT = AWD / "C6-01-PROVENANCE/addendum/authentication_addendum_v1_draft.csv"


def to_entry(d, n, cp):
    e = {k: "" for k in L.COLS}
    e.update({"entry_id": f"AL-v0001-{n:03d}", "entry_version": "0001", "entry_type": "ADD", "sha256": d["sha256"],
              "source_id": d["source_id"], "copy_id": d["copy_id"], "document_identity": d["document_identity"],
              "evidence_refs": d["evidence_refs"], "first_class_record_ref": d["first_class_record_ref"],
              "identity_refs": d["identity_refs"].replace("T:C6-01-PROVENANCE/inputs/held_copy_facts.csv#", "T:AUTH-LEDGER/evidence/copy_facts.csv#"),
              "proposed_authentication_state": "PROVENANCE_DOCUMENTED", "proposed_class": d["proposed_class"],
              "carrier": cp[d["sha256"]]["copy_carrier_provenance"],
              "official_locator_recorded": strength._first_class(d["first_class_record_ref"], d["sha256"])[2],
              "limitations": d["limitations"], "justification": d["justification"], "rule_version": "1", "owner_decision": ""})
    return e


class Sim:
    def __init__(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(prefix="c8_sc_sim_", dir=TMP))
        shutil.copy(PKG / "frozen_inputs.json", self.dir / "frozen_inputs.json")
        (self.dir / "ledger").mkdir()
        (self.dir / "decisions").mkdir()
        shutil.copy(PKG / "ledger/manifest.jsonl", self.dir / "ledger/manifest.jsonl")
        shutil.copy(PKG / "ledger/HEAD", self.dir / "ledger/HEAD")

    def run(self, entries):
        es = [dict(e, owner_decision="APPROVED") for e in entries]
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
            ch.append({"key": list(k), "before": rb, "after": ra,
                       "changed_columns": sorted(c for c in (rb or ra) if (rb or {}).get(c) != (ra or {}).get(c))})
    bc = {r["sha256"]: r for r in rows(base["source_copy_register.csv"])}
    ac = {r["sha256"]: r for r in rows(after["source_copy_register.csv"])}
    copies = [{"copy_id": ac[s]["copy_id"], "before": bc[s]["copy_effective_status"], "after": ac[s]["copy_effective_status"],
               "eligible_for_exact_anchor": ac[s]["eligible_for_exact_anchor"]} for s in bc if bc[s]["copy_effective_status"] != ac[s]["copy_effective_status"]]
    bs = {r["source_id"]: r for r in rows(base["source_states.csv"])}
    as_ = {r["source_id"]: r for r in rows(after["source_states.csv"])}
    src = [{"source_id": k, "before": bs[k]["effective_holding_state"], "after": as_[k]["effective_holding_state"]} for k in bs
           if bs[k]["effective_holding_state"] != as_[k]["effective_holding_state"]]
    return {"crosswalk_row_changes": ch, "copy_status_changes": copies, "source_holding_changes": src}


def main():
    drafts = sorted([r for r in read_csv(DRAFT) if r["proposed_class"] == CLS], key=lambda d: d["source_id"])
    cp = {r["sha256"]: r for r in read_csv(AWD / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv")}
    entries = [to_entry(d, i + 1, cp) for i, d in enumerate(drafts)]
    base, _ = reader.effective_state(PKG, 0)
    frozen = {n: (AWD / "SOURCE-LIBRARY-C5/registers" / n).read_text(encoding="utf-8") for n in ("corpus_crosswalk.csv", "coverage_summary.json")}
    res = {"label": "SIMULATION ONLY: synthetic approval records in a temporary directory, deleted after each run. Not a ledger version, "
                    "not an approval, not evidence of owner or legal approval. The committed ledger stays at version 0.",
           "candidates": [{"entry_id": e["entry_id"], "copy_id": e["copy_id"], "sha256": e["sha256"]} for e in entries],
           "version0": summarize(base),
           "version0_equals_frozen_c5_registers": {n: base[n] == frozen[n] for n in frozen},
           "single": {}, "joint_all_8": None}
    for e in entries:
        sim = Sim()
        try:
            t = sim.run([e])
            res["single"][e["copy_id"]] = {"rule1": "PASS", "summary": summarize(t), "diff": diff(base, t)}
        except (LedgerError, KeyError, ValueError) as ex:
            res["single"][e["copy_id"]] = {"rule1": "FAIL", "reason": str(ex)[:500]}
        finally:
            sim.close()
    sim = Sim()
    try:
        t = sim.run(entries)
        res["joint_all_8"] = {"rule1": "PASS", "summary": summarize(t), "diff": diff(base, t)}
    except (LedgerError, KeyError, ValueError) as ex:
        res["joint_all_8"] = {"rule1": "FAIL", "reason": str(ex)[:500]}
    finally:
        sim.close()
    subsets = {"joint_excluding_3_judis_text_renditions (Ranjit, S N Mukherjee, Navjot)": ("RANJIT", "MUKHERJEE", "NAVJOT"),
               "joint_excluding_navjot_and_mullikote (C8 recommendation to keep PARTIAL)": ("NAVJOT", "MULLIKOTE"),
               "joint_excluding_3_judis_text_renditions_and_mullikote": ("RANJIT", "MUKHERJEE", "NAVJOT", "MULLIKOTE")}
    res["subsets"] = {}
    for name, excl in subsets.items():
        sub = [e for e in entries if not any(x in e["copy_id"] for x in excl)]
        sim = Sim()
        try:
            t = sim.run(sub)
            res["subsets"][name] = {"rule1": "PASS", "copies": [e["copy_id"] for e in sub], "summary": summarize(t)}
        except (LedgerError, KeyError, ValueError) as ex:
            res["subsets"][name] = {"rule1": "FAIL", "reason": str(ex)[:500]}
        finally:
            sim.close()
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"v0": res["version0"]["exact_anchor_case_count"],
                      "single": {k: (v.get("summary") or {}).get("exact_anchor_case_count", v.get("reason")) for k, v in res["single"].items()},
                      "joint": (res["joint_all_8"].get("summary") or {}).get("exact_anchor_case_count", res["joint_all_8"].get("reason")),
                      "subsets": {k: (v.get("summary") or {}).get("exact_anchor_case_count", v.get("reason")) for k, v in res["subsets"].items()}}, indent=1))


if __name__ == "__main__":
    main()
