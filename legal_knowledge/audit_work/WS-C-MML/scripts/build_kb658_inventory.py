#!/usr/bin/env python3
"""READ-ONLY source-coverage inventory of the frozen 658 KB records (stdlib only, deterministic).
NOT a legal-correctness audit: no record is judged right or wrong. It reports which citations are present,
whether they resolve to an identified source held in the corpus, pinpoints, MML anchors, broken/unresolved
citation flags, duplicate-claim flags and a coverage_state.
Inputs (committed): records_658.jsonl (sha 9a8f0d19...), PILOT-01 source_code_resolution_v3.csv, pilot-manifest.json,
PILOT-01 mml_crosswalk_pilot.csv, cases_53.jsonl, WS-C mml_provision_crosswalk.csv and provision_index.csv,
ARMY-RULES-CHAIN-01 chronology.
Outputs: kb658_source_coverage_inventory.csv, kb658_coverage_summary.json.
Run from repo root: python3 legal_knowledge/audit_work/WS-C-MML/scripts/build_kb658_inventory.py"""
import csv, hashlib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent; W = HERE.parent; ROOT = W.parents[2]
sys.path.insert(0, str(HERE))
import kb_citations as K

KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
KB_SHA = "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1"
P1 = ROOT / "legal_knowledge/audit_work/PILOT-01"
FIRM = {"CORROBORATED_OFFICIAL", "RESOLVED_RECORD_EXPLICIT"}
HELD_PLAIN = {"bsa", "bnss", "bns", "crpc", "evidence act", "aft act", "aft (procedure) rules", "procedure rules",
              "air force act", "navy act"}
LEGACY = re.compile(r"\b(IPC|CrPC|Cr\.?P\.?C|Evidence Act|IEA)\b")
# Provisions shown omitted, with the evidence relied on for the flag (informational only; the record may discuss the omission).
OMITTED = {("AA", "75"): "Act 37 of 1992 s.2 (PILOT PIC-07, Gazette image)", ("AA", "76"): "Act 37 of 1992 s.2 (PILOT PIC-07)",
           ("AA", "127"): "MML 2 p.92 fn and India Code note (Gazette not image-checked here)",
           ("AR", "25"): "S.R.O. 17(E)/1993 (AR chain AR-029)", ("AR", "59A"): "S.R.O. 17(E)/1993 (AR chain AR-029)"}


def held(target):
    t = (target or "").strip()
    return t.startswith(("act-", "rules-", "DCLR-")) and "(candidate)" not in t


def main():
    raw = KB.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == KB_SHA, "records_658.jsonl hash mismatch"
    lines = [l for l in raw.split(b"\n") if l.strip()]
    recs = [json.loads(l) for l in lines]
    ids = {r["id"] for r in recs}
    reg = {r["code"]: r for r in csv.DictReader(open(P1 / "registers/source_code_resolution_v3.csv", encoding="utf-8"))}
    pilot_ids = {r["record_id"] for r in json.load(open(P1 / "pilot-manifest.json"))["records"]}
    pxw = defaultdict(set)
    for r in csv.DictReader(open(P1 / "registers/mml_crosswalk_pilot.csv", encoding="utf-8")):
        pxw[r["record_id"]].add(r["link_status"])
    wxw = defaultdict(set)
    for r in csv.DictReader(open(W / "mml_provision_crosswalk.csv", encoding="utf-8")):
        for i in filter(None, r["kb_record_ids_new"].split(";")):
            wxw[i].add(r["mml_file"])
    mml_keys = {("AA" if r["instrument"].startswith("Army Act") else "AR", r["provision"][2:])
                for r in csv.DictReader(open(W / "provision_index.csv", encoding="utf-8"))}
    # duplicate-claim detection
    norm = lambda t: re.sub(r"\W+", " ", t.lower()).strip()
    tgroups = defaultdict(list)
    for r in recs:
        tgroups[norm(r["title"])].append(r["id"])
    def sh(t):
        w = re.findall(r"[a-z0-9]+", t.lower()); return {" ".join(w[i:i + 3]) for i in range(max(0, len(w) - 2))}
    S = {r["id"]: sh(r["title"] + " " + r["body"]) for r in recs}
    near = defaultdict(list); order = [r["id"] for r in recs]
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            a, b = S[order[i]], S[order[j]]
            if a and b:
                jac = len(a & b) / len(a | b)
                if jac >= 0.25:
                    near[order[i]].append(f"{order[j]}({jac:.2f})"); near[order[j]].append(f"{order[i]}({jac:.2f})")
    rows = []
    for n, (line, r) in enumerate(zip(lines, recs), 1):
        p = K.parse(r, ids); ref = str(r["references"])
        firm_held, gap, unres, cocit = [], [], [], []
        for c in p["codes"]:
            g = reg.get(c)
            if not g:
                unres.append(c + ":NOT_IN_REGISTER")
            elif g["resolution_class"] in FIRM:
                (firm_held if held(g["corpus_target_or_gap"]) else gap).append(c)
            elif g["resolution_class"] == "RESOLVED_CO_CITATION":
                (cocit if held(g["corpus_target_or_gap"]) else gap).append(c)
            else:
                unres.append(c + ":" + g["resolution_class"])
        plain_held = [s for s in p["stat_other"] if s.lower() in HELD_PLAIN]
        plain_gap = [s for s in p["stat_other"] if s.lower() not in HELD_PLAIN]
        has_case_code = any(reg.get(c, {}).get("corpus_target_or_gap", "").startswith(("DCLR-", "GAP: not in cases_53", "GAP: HC"))
                            for c in p["codes"])
        broken = []
        if p["placeholders"]:
            broken.append("PLACEHOLDER:" + "/".join(p["placeholders"]))
        broken += ["CODE_" + u for u in unres]
        uncoded_names = [f"{k}->{cid or 'no-id'}" for k, cid, kc in p["case_names"]
                         if not set(filter(None, kc.split(";"))) & set(p["codes"])]
        if uncoded_names:
            broken.append("CASE_NAME_WITHOUT_CODE:" + "/".join(uncoded_names))
        elif p["case_pattern"] and not has_case_code:
            broken.append("PLAIN_CASE_CITATION_UNRESOLVED")
        for inst, lst in (("AA", p["aa"]), ("AR", p["ar"])):
            for x in lst:
                if (inst, x) not in mml_keys:
                    broken.append(f"PROVISION_NOT_IN_HEADING_INDEX:{inst} {x}")
        if re.search(r"\b(AA|AR)\b|Army Act|Army Rules?", ref) and not (p["aa"] or p["ar"]):
            broken.append("ARMY_ACT_OR_RULES_CITED_WITHOUT_PINPOINT")
        url = r.get("url") or ""
        if url and not re.search(r"\.(gov|nic)\.in/", url):
            broken.append("URL_NON_OFFICIAL_HOST")
        info = []
        for inst, lst in (("AA", p["aa"]), ("AR", p["ar"])):
            for x in lst:
                if (inst, x) in OMITTED:
                    info.append(f"INFO_CITES_PROVISION_SHOWN_OMITTED:{inst} {x} [{OMITTED[(inst, x)]}]")
        if LEGACY.search(ref):
            info.append("INFO_LEGACY_CODE_CITED (IPC/CrPC/IEA; temporal scope to check)")
        if cocit:
            info.append("CODE_RESOLVED_BY_CO_CITATION_ONLY:" + "/".join(cocit))
        if p["internal_links"]:
            info.append("INTERNAL_KB_LINKS:" + "/".join(p["internal_links"]))
        if p["noncitation_text"]:
            info.append("REFERENCES_FIELD_IS_NON_CITATION_TEXT")
        dup = []
        if len(tgroups[norm(r["title"])]) > 1:
            dup.append("DUP_TITLE:" + "/".join(x for x in tgroups[norm(r["title"])] if x != r["id"]))
        if near[r["id"]]:
            dup.append("NEAR_DUP_TEXT_J3>=0.25:" + "/".join(near[r["id"]]))
        pin = bool(p["aa"] or p["ar"] or p["other_numbered"] or re.search(r"(para|paras|¶|reg|regs|Chapter|locator|Rule|r)\s*\.?\s*\d", ref))
        stat_anchor = bool(p["aa"] or p["ar"] or plain_held or any(reg.get(c, {}).get("corpus_target_or_gap", "").startswith(("act-", "rules-")) for c in firm_held))
        anchors = len(firm_held) + len(cocit) + len(p["aa"]) + len(p["ar"]) + len(plain_held)
        gaps = len(gap) + len(plain_gap)
        n_unres = len(unres) + len(p["placeholders"]) + (1 if "PLAIN_CASE_CITATION_UNRESOLVED" in broken else 0) + len(uncoded_names)
        has_any = bool(p["codes"] or p["aa"] or p["ar"] or p["stat_other"] or p["case_pattern"])
        if not has_any:
            state = "NO_CITATION"
        elif anchors == 0:
            state = "SOURCE_GAP" if gaps else "UNRESOLVED"
        elif n_unres == 0 and gaps == 0 and not cocit and pin and not [b for b in broken if b.startswith(("PROVISION_NOT", "ARMY_ACT_OR", "URL_"))]:
            state = "FULL"
        else:
            state = "PARTIAL"
        mml_link = ("PILOT_" + "/".join(sorted(pxw[r["id"]]))) if r["id"] in pxw else ""
        if r["id"] in wxw:
            mml_link = (mml_link + ";" if mml_link else "") + "WSC_PROVISION_LOCATED(" + str(len(wxw[r["id"]])) + " files)"
        rows.append({
            "record_id": r["id"], "source_line": n, "module": r["module"], "kind": r["kind"], "status_as_recorded": r["status"],
            "record_sha256": hashlib.sha256(line).hexdigest(), "in_pilot01": "YES" if r["id"] in pilot_ids else "NO",
            "codes": ";".join(p["codes"]), "codes_resolved_held": ";".join(firm_held), "codes_resolved_gap": ";".join(gap), "codes_co_citation_only": ";".join(cocit),
            "codes_unresolved": ";".join(unres), "aa_sections": ";".join(p["aa"]), "ar_rules": ";".join(p["ar"]),
            "other_statutes_plain": ";".join(p["stat_other"]), "case_citation_pattern": "YES" if p["case_pattern"] else "NO",
            "case_names_matched": ";".join(f"{k}->{cid or 'no-id'}" for k, cid, kc in p["case_names"]),
            "pinpoint_present": "YES" if pin else "NO", "statutory_anchor_present": "YES" if stat_anchor else "NO",
            "mml_anchor_in_record": "YES" if p["mml_mention"] else "NO", "mml_crosswalk_link": mml_link or "NONE",
            "broken_or_unresolved_flags": " | ".join(broken), "info_flags": " | ".join(info), "duplicate_claim_flags": " | ".join(dup),
            "coverage_state": state})
    cols = list(rows[0])
    with open(W / "kb658_source_coverage_inventory.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    N = len(rows)
    cnt = lambda key, val: sum(1 for x in rows if x[key] == val)
    summ = {"denominator_records": N, "kb_sha256": KB_SHA, "not_a_correctness_audit": True,
            "coverage_state": dict(Counter(x["coverage_state"] for x in rows)),
            "coverage_state_by_module": {m: dict(Counter(x["coverage_state"] for x in rows if x["module"] == m)) for m in sorted({x["module"] for x in rows})},
            "records_with_any_code": sum(1 for x in rows if x["codes"]),
            "records_with_aa_pinpoint": sum(1 for x in rows if x["aa_sections"]), "records_with_ar_pinpoint": sum(1 for x in rows if x["ar_rules"]),
            "statutory_anchor_present": cnt("statutory_anchor_present", "YES"), "pinpoint_present": cnt("pinpoint_present", "YES"),
            "mml_anchor_in_record": cnt("mml_anchor_in_record", "YES"),
            "mml_crosswalk_link_any": sum(1 for x in rows if x["mml_crosswalk_link"] != "NONE"),
            "records_with_broken_or_unresolved_flag": sum(1 for x in rows if x["broken_or_unresolved_flags"]),
            "flag_counts": dict(Counter(re.sub(r":.*", "", f).strip() for x in rows for f in x["broken_or_unresolved_flags"].split(" | ") if f)),
            "info_flag_counts": dict(Counter(re.sub(r":.*|\s*\(.*", "", f).strip() for x in rows for f in x["info_flags"].split(" | ") if f)),
            "records_with_duplicate_flag": sum(1 for x in rows if x["duplicate_claim_flags"]),
            "in_pilot01": cnt("in_pilot01", "YES")}
    (W / "kb658_coverage_summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summ["coverage_state"]), N)


if __name__ == "__main__":
    main()
