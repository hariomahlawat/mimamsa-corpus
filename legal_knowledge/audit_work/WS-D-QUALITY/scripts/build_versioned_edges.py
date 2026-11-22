#!/usr/bin/env python3
"""WS-D cycle 3, task 3: version- and date-bounded statutory edges (extension of the relation graph).

Edges: KB record -> provision VERSION, for every Army Act section / Army Rules rule a record cites, to every
version or change event registered for that provision in:
  * ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv   (provision versions; determination state carried)
  * WS-A-STATUTORY/provision_change_log.csv                    (Army Rules change events by instrument)
  * WS-A-STATUTORY/army_act_amendment_chain.csv                (Army Act change events; sections_affected)
Citations per record: plain-text records via the shared WS-D parser (build_plaintext_index.instrument_locators
through coverage_scorecard.assess_plain_segment); coded records via the WS-C inventory aa_sections / ar_rules.

The KB records do not say which version they mean, so every edge is a CANDIDATE-version edge with its date
bounds. Owner date rule: valid_from is the effective date only when the register states commencement
(effective_date_status STATED_IN_INSTRUMENT); otherwise valid_from is empty and the edge carries the flag
EFFECTIVE_DATE_UNSTATED plus the register's status. Nothing is inferred from publication dates.
Rows that are not versions (no amendment located, notes, declarations, NOT_APPLICABLE chain rows) are excluded.
Further flags: VALID_TO_UNSTATED (a later version exists but has no stated commencement), SUBPROVISION_VERSION
(the version concerns a sub-rule/sub-section of the cited provision), TEXT_OR_OCR_EVIDENCE_ONLY.
Determination states (e.g. r.23(3) CONFLICTING, r.193 OPEN, r.194 PROPOSAL) are carried unchanged.
Structural only: an edge says a record cites a provision that has this registered version, not that the
version applies to the record or that the record is correct.
Outputs: relation_graph_versioned_edges.csv, relation_graph_versioned_report.md (+ .json summary).
Usage: python3 build_versioned_edges.py [--check]
"""
import argparse, collections, csv, hashlib, importlib.util, io, json, re, sys
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
AW = ROOT / "legal_knowledge/audit_work"
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
INPUTS = {"kb": KB, "version_register": AW / "ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv",
          "wsa_change_log": AW / "WS-A-STATUTORY/provision_change_log.csv",
          "wsa_aa_chain": AW / "WS-A-STATUTORY/army_act_amendment_chain.csv",
          "wsc_inventory": AW / "WS-C-MML/kb658_source_coverage_inventory.csv",
          "plaintext_index": WSD / "plaintext_citation_index.csv"}
OUT_CSV, OUT_MD, OUT_JSON = (WSD / "relation_graph_versioned_edges.csv", WSD / "relation_graph_versioned_report.md",
                             WSD / "relation_graph_versioned_summary.json")
STATED = "STATED_IN_INSTRUMENT"
NOT_A_CHANGE = re.compile(r"NO AMENDMENT|\(no amendment\)|\(not amendment\)", re.I)
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COLS = ["record_id", "instrument", "provision", "cited_via", "version_id", "version_source", "change_or_version",
        "publication_date", "effective_date_status", "valid_from", "valid_to", "determination_state", "conflict_id", "flags"]


def rows(p):
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def norm(n):
    return n.strip().upper() if re.fullmatch(r"\d+[A-Za-z]?", n.strip()) else None


def versions():
    """{(instrument, provision_number): [version dict]} from the three registers."""
    V = collections.defaultdict(list)

    def add(inst, num, **kw):
        k = norm(num)
        if k:
            V[(inst, k)].append(kw)

    for r in rows(INPUTS["version_register"]):
        m = re.match(r"r\.(\d+[A-Za-z]?)", r["provision"])
        if m:
            add("AR", m.group(1), version_id=f"{r['provision']}@{r['version']}", source="ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv",
                change=r["version"], sub=bool(re.match(r"r\.\d+[A-Za-z]?\s*[\(\s]", r["provision"])), ocr=False, pub=r["publication_date"], eff=r["effective_date"], status=r["effective_date_status"],
                det=r["determination_state"], conflict=r["conflict_id"] if r["conflict_id"] not in ("", "-") else "")
    for r in rows(INPUTS["wsa_change_log"]):
        nums = re.findall(r"r\.(\d+[A-Za-z]?)", r["provision"])
        if "itself" in r["provision"] or NOT_A_CHANGE.search(r["change_type"]):
            continue  # not a version: search findings, notes, declarations
        for n in dict.fromkeys(nums):
            add("AR", n, version_id=r["change_id"], source="WS-A-STATUTORY/provision_change_log.csv",
                change=f"{r['change_type']} ({r['instrument'][:60]})",
                sub=bool(re.search(r"r\.%s\s*\(" % re.escape(n), r["provision"])), ocr="OCR" in r["change_type"] or "OCR" in r.get("evidence_level", ""), pub=r["publication_date"], eff=r["effective_date"],
                status=r["effective_date_status"], det="", conflict="")
    for r in rows(INPUTS["wsa_aa_chain"]):
        for n in dict.fromkeys(re.findall(r"\bss?\.\s*(\d+[A-Za-z]?)", r["sections_affected"])):
            if NOT_A_CHANGE.search(r["change_as_printed"]) or (r["effective_date_status"] or "").startswith("NOT_APPLICABLE"):
                continue
            add("AA", n, version_id=r["chain_id"], source="WS-A-STATUTORY/army_act_amendment_chain.csv",
                change=f"{r['instrument'][:60]}", sub=bool(re.search(r"s\.\s*%s\s*\(" % re.escape(n), r["sections_affected"])),
                ocr=r["evidence_level"].startswith(("HINT", "TEXT_LAYER", "REQUIRES_VERIFICATION")), pub=r["publication_date"], eff=r["effective_date"],
                status=r["effective_date_status"], det="", conflict="")
    for k in V:
        V[k].sort(key=lambda v: (v["pub"] if ISO.match(v["pub"] or "") else "9999", v["version_id"]))
    return V


def citations():
    """{record_id: {(instrument, provision): cited_via}}"""
    cov = load("cov_ve", WSD / "scripts/coverage_scorecard.py")
    idx = collections.defaultdict(list)
    for r in rows(INPUTS["plaintext_index"]):
        idx[r["record_id"]].append(r)
    out = collections.defaultdict(dict)
    for rid, segs in idx.items():
        by = {s["seg_no"]: s for s in segs}
        for s in segs:
            cat = s["category"]
            src = by.get(s["context_from_seg"]) if cat == "LOCATOR_CONTINUATION" else s
            if cat not in ("STATUTE_LOCATOR",) and not (cat == "LOCATOR_CONTINUATION" and src):
                continue
            for a in cov.assess_plain_segment(s, src):
                if a["doc"] == "act-army-1950":
                    for n in a["numbers"]:
                        out[rid][("AA", n.upper())] = "WS-D plain-text parser"
                if a["doc"] == "rules-army-rules-1954":
                    for n in a["rule_numbers"]:
                        out[rid][("AR", n.upper())] = "WS-D plain-text parser"
    for r in rows(INPUTS["wsc_inventory"]):
        if r["record_id"] in idx:
            continue
        for inst, col in (("AA", "aa_sections"), ("AR", "ar_rules")):
            for n in filter(None, r[col].split(";")):
                if norm(n):
                    out[r["record_id"]].setdefault((inst, norm(n)), "WS-C inventory parser")
    return out


def build():
    V = versions(); C = citations()
    edges = []
    for rid in sorted(C):
        for (inst, num), via in sorted(C[rid].items()):
            vs = V.get((inst, num), [])
            for i, v in enumerate(vs):
                stated = (v["status"] or "").startswith(STATED) and ISO.match(v["eff"] or "")
                nxt = next((w for w in vs[i + 1:] if (w["status"] or "").startswith(STATED) and ISO.match(w["eff"] or "")), None)
                flags = []
                if not stated:
                    flags.append("EFFECTIVE_DATE_UNSTATED")
                if vs[i + 1:] and not nxt:
                    flags.append("VALID_TO_UNSTATED")
                if v["sub"]:
                    flags.append("SUBPROVISION_VERSION")
                if v["ocr"]:
                    flags.append("TEXT_OR_OCR_EVIDENCE_ONLY")
                if v["det"] and v["det"].split()[0] in ("CONFLICTING", "OPEN", "PROPOSAL"):
                    flags.append("DETERMINATION_" + v["det"].split()[0])
                edges.append({"record_id": rid, "instrument": "Army Act 1950" if inst == "AA" else "Army Rules 1954",
                              "provision": ("s." if inst == "AA" else "r.") + num, "cited_via": via, "version_id": v["version_id"],
                              "version_source": v["source"], "change_or_version": v["change"], "publication_date": v["pub"],
                              "effective_date_status": v["status"], "valid_from": v["eff"] if stated else "",
                              "valid_to": nxt["eff"] if nxt else "", "determination_state": v["det"], "conflict_id": v["conflict"],
                              "flags": ";".join(flags)})
    cited = {(r, k) for r in C for k in C[r]}
    with_versions = {(r, k) for r, k in cited if V.get(k)}
    S = {"records_citing_aa_or_ar_provisions": len(C), "record_provision_citations": len(cited),
         "citations_with_registered_versions": len(with_versions), "edges": len(edges),
         "edges_with_stated_effective_date": sum("EFFECTIVE_DATE_UNSTATED" not in e["flags"] for e in edges),
         "edges_effective_date_unstated_flagged": sum("EFFECTIVE_DATE_UNSTATED" in e["flags"] for e in edges),
         "provisions_with_versions": len(V), "by_version_source": dict(sorted(collections.Counter(e["version_source"] for e in edges).items())),
         "determination_flags": dict(sorted(collections.Counter(f for e in edges for f in e["flags"].split(";") if f.startswith("DETERMINATION_")).items()))}
    inputs = {k: {"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for k, p in INPUTS.items()}
    return edges, S, inputs


def render(edges, S, inputs):
    prov = collections.Counter(e["provision"] for e in edges)
    L = ["# Versioned statutory edges (relation-graph extension)", "",
         "Generated by `scripts/build_versioned_edges.py`. Each edge: KB record -> a registered version or change event of an Army Act section or Army Rules rule that the record cites. **Records do not state which version they mean, so these are candidate-version edges. They say nothing about which version applies or whether the record is correct.**", "",
         "Owner date rule: `valid_from` is filled only when the register states commencement (`STATED_IN_INSTRUMENT`); otherwise it is empty and the edge is flagged `EFFECTIVE_DATE_UNSTATED` with the register's status. No date is inferred from a publication date. Determination states (r.23(3) CONFLICTING, r.193 OPEN, r.194 PROPOSAL) are carried unchanged.", "",
         "Inputs (SHA-256): " + "; ".join(f"`{k}` {v['sha256'][:12]}…" for k, v in inputs.items()), "",
         "| Measure | Value |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in S.items()]
    L += ["", "## Provisions with the most candidate-version edges", "", "| Provision | Edges |", "| --- | --- |"]
    L += [f"| {p} | {n} |" for p, n in sorted(prov.items(), key=lambda x: (-x[1], x[0]))[:25]]
    return "\n".join(L) + "\n"


def outputs():
    edges, S, inputs = build()
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n"); w.writeheader(); w.writerows(edges)
    return {OUT_CSV: buf.getvalue(), OUT_MD: render(edges, S, inputs),
            OUT_JSON: json.dumps({"artifact": "WS-D versioned statutory edges", "structural_only": True, "inputs": inputs, "summary": S},
                                 indent=1) + "\n"}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    files = outputs()
    if a.check:
        bad = [p.name for p, t in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != t]
        print("versioned edges: " + ("MATCH" if not bad else f"DIFFERS {bad}"))
        return 1 if bad else 0
    for p, t in files.items():
        p.write_text(t, encoding="utf-8")
    print(json.dumps(json.loads(files[OUT_JSON])["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
