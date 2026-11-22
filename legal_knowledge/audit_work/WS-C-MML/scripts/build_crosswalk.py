#!/usr/bin/env python3
"""Build mml_provision_crosswalk.csv: MML locator -> Army Act section / Army Rule (+ ARMY-RULES-CHAIN-01 events)
-> KB record IDs citing that provision. Stdlib only; deterministic; reads committed files only:
provision_index.csv, mml1_para_index.csv (this folder), records_658.jsonl, PILOT-01 crosswalk, AR chain chronology.
Triples (record, MML file, provision) already in the PILOT-01 63-row crosswalk are excluded from kb_record_ids_new
and listed separately so the pilot is extended, not duplicated.
Run from repo root: python3 legal_knowledge/audit_work/WS-C-MML/scripts/build_crosswalk.py"""
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent; W = HERE.parent; ROOT = W.parents[2]
sys.path.insert(0, str(HERE))
import kb_citations as K

KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
PILOT = ROOT / "legal_knowledge/audit_work/PILOT-01/registers/mml_crosswalk_pilot.csv"
CHRON = ROOT / "legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv"
SHA = {"MML 1.doc": "3a2e3a4f70669483678cdb96e1dd29d901c6c0ffc43a04a794a00d3ef0c3d1ed",
       "MML 2.pdf": "db2119182ed2e4ccca22dd225d955327f6398ee98303e1c94615ba85b4396f65",
       "MML vol 2(AA).doc.doc": "73fd304227ca680ebf3c8512dfd4aafa0eb2e16952558bb8b1c1edee637a455d",
       "MML vol 2(AA).pdf": "c8a791a1e3a4d8fee412cae1b0c2daa4517438bf926c9f9e27fffd81cada1ec9",
       "MML vol 2(AR).doc-1.doc": "8bb17d8255ea1be2b975a96b3c739d002264df3da8a56086d29d2a1961f3a162",
       "MML vol 2(AR).doc.doc": "ed1d8a7fc1f4088f8d0fb7db6855c195b205b251874a70f611ced5c3fdb494a2"}


FIXED = {("AR", "23"): "Fixed determination: r.23(3) CONFLICTING (unchanged)",
         ("AR", "193"): "r.193 = C-08 OPEN (unchanged)", ("AR", "194"): "r.194 = C-09 PROPOSAL pending legal review (unchanged)"}


def nums(text, prefix):
    out = set()
    for m in re.finditer(prefix + r"\s*(\d{1,3}[A-Z]?(?:\s*[-–]\s*\d{1,3})?(?:\s*,\s*\d{1,3}[A-Z]?)*)", text):
        for part in re.split(r"\s*,\s*", m.group(1)):
            r = re.match(r"(\d+)\s*[-–]\s*(\d+)", part)
            if r and 0 < int(r.group(2)) - int(r.group(1)) <= 30:
                out |= {str(i) for i in range(int(r.group(1)), int(r.group(2)) + 1)}
            else:
                out.add(re.match(r"\d+[A-Z]?", part).group())
    return out


def pilot_triples():
    t = set()
    for r in csv.DictReader(open(PILOT, encoding="utf-8")):
        if not r["mml_file"]:
            continue
        txt = r["pdf_page_or_doc_lines"] + " " + r["reason"]
        for n in nums(txt, r"\bss?\.") | nums(txt, r"\bAA\s*s\.?"):
            t.add((r["record_id"], r["mml_file"], "AA", n))
        for n in nums(txt, r"\brr?\.") | nums(txt, r"\bAR\s*r?\.?"):
            t.add((r["record_id"], r["mml_file"], "AR", n))
        if "MML 1" in r["mml_file"]:
            for n in nums(txt, r"paras?"):
                t.add((r["record_id"], r["mml_file"], "PARA", n))
    return t


def chain():
    ev = defaultdict(list)
    for r in csv.DictReader(open(CHRON, encoding="utf-8")):
        p = r["provision"]
        for n in nums(p, r"\brr?\.") | {x for x in re.findall(r"(?<=,)(\d{1,3}[A-Z]?)", p)}:
            ev[n].append(r)
    return ev


def main():
    recs = [json.loads(l) for l in KB.read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = {r["id"] for r in recs}
    cites = defaultdict(set)
    for r in recs:
        p = K.parse(r, ids)
        for n in p["aa"]:
            cites[("AA", n)].add(r["id"])
        for n in p["ar"]:
            cites[("AR", n)].add(r["id"])
    pt = pilot_triples(); ch = chain()
    idx = list(csv.DictReader(open(W / "provision_index.csv", encoding="utf-8")))
    rows = []
    def add(inst, n, f, loc, printed, role, extra="", pkey=None):
        all_ids = sorted(cites.get((inst, n), ()))
        if not all_ids:
            return
        k2 = pkey or (inst, n)
        cov = sorted(i for i in all_ids if (i, f) + tuple(k2) in pt)
        new = [i for i in all_ids if i not in cov]
        if not new:
            return
        evs = ch.get(n, []) if inst == "AR" else []
        rows.append({
            "instrument": "Army Act 1950" if inst == "AA" else "Army Rules 1954",
            "provision": ("s." if inst == "AA" else "r.") + n, "mml_file": f, "mml_file_sha256": SHA[f],
            "mml_locator": loc, "printed_page": printed, "content_role": role,
            "ar_chain_events": " | ".join((f"{e['instrument_id']} {e['instrument']} {e['event']}" if e["instrument_id"] else e["event"]) for e in evs),
            "ar_chain_publication_dates": " | ".join(e["publication_date"] or "n/a" for e in evs),
            "ar_chain_commencement_as_printed": " | ".join(e["commencement_as_printed"] or "n/a" for e in evs),
            "ar_chain_effective_date_status": ("NOT_DETERMINED (WS-C makes no effective-date determination; see AR chain and AQ-05)" if any(e["instrument_id"] for e in evs) else ""),
            "kb_record_ids_new": ";".join(new), "n_new": len(new), "kb_record_ids_pilot_covered": ";".join(cov),
            "link_status": "PROVISION_LOCATED" if role != "MANUAL_COMMENTARY" else "PARA_CITES_PROVISION",
            "verification_state": "REQUIRES_VERIFICATION (locator from text layer; wording not relied on)",
            "notes": "; ".join(x for x in (extra, FIXED.get((inst, n), "")) if x)})
    for r in idx:
        inst = "AA" if r["instrument"].startswith("Army Act") else "AR"
        n = r["provision"][2:]
        add(inst, n, "MML 2.pdf", f"PDF p.{r['mml2_pdf_page']} (heading start)", r["mml2_pdf_page"], "MANUAL_REPRODUCED_LEGAL_TEXT")
        if inst == "AA":
            for f in ("MML vol 2(AA).pdf", "MML vol 2(AA).doc.doc"):
                if r[f]:
                    add(inst, n, f, r[f] + " (heading start)", "", "MANUAL_REPRODUCED_LEGAL_TEXT")
        else:
            for f in ("MML vol 2(AR).doc.doc", "MML vol 2(AR).doc-1.doc"):
                if r[f]:
                    add(inst, n, f, "derived line " + r[f] + " (heading start)",
                        r["doc1_embedded_printed_page"] if f.endswith("-1.doc") else "", "MANUAL_REPRODUCED_LEGAL_TEXT")
    for p in csv.DictReader(open(W / "mml1_para_index.csv", encoding="utf-8")):
        for inst, col in (("AA", "aa_sections_cited"), ("AR", "ar_rules_cited")):
            for prov in filter(None, p[col].split(";")):
                n = prov[2:]
                # pilot MML 1 rows are recorded by para (chapter not parsed), so exclude per record by para
                add(inst, n, "MML 1.doc", f"Part I Ch {p['chapter']} para {p['para']} ({p['para_heading_short']}); derived line {p['derived_line']}",
                    "", "MANUAL_COMMENTARY", "Commentary paragraph cites the provision; relevance to each KB record not assessed", ("PARA", p["para"]))
    rows.sort(key=lambda r: (r["instrument"], int(re.match(r"\d+", r["provision"][2:]).group()), r["provision"], r["mml_file"], r["mml_locator"]))
    for i, r in enumerate(rows, 1):
        r["xw_id"] = f"XW-C-{i:04d}"
    cols = ["xw_id", "instrument", "provision", "mml_file", "mml_file_sha256", "mml_locator", "printed_page", "content_role",
            "ar_chain_events", "ar_chain_publication_dates", "ar_chain_commencement_as_printed", "ar_chain_effective_date_status",
            "kb_record_ids_new", "n_new", "kb_record_ids_pilot_covered", "link_status", "verification_state", "notes"]
    with open(W / "mml_provision_crosswalk.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    recs_linked = {i for r in rows for i in r["kb_record_ids_new"].split(";") if i}
    provs = {(r["instrument"], r["provision"]) for r in rows}
    cited = {k for k in cites}
    located = {("AA" if r["instrument"].startswith("Army Act") else "AR", r["provision"][2:]) for r in idx}
    print(json.dumps({"rows": len(rows), "distinct_provisions": len(provs), "kb_records_linked_new": len(recs_linked),
                      "provisions_cited_in_kb": len(cited), "cited_not_in_mml_index": sorted("%s %s" % k for k in cited - located),
                      "mml_provisions_not_cited_by_kb": len(located - cited), "pilot_triples": len(pt)}, indent=1))


if __name__ == "__main__":
    main()
