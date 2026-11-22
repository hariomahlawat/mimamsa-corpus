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
Rows that are not versions (no amendment located, notes, declarations, NOT_APPLICABLE chain rows, Bills /
'proposed' sections) are excluded. Provision lists are expanded fully (expand_provisions: comma and slash lists,
hyphen/en-dash ranges, letter suffixes) and each expanded number is verified against the register text.
Duplicate descriptions of one amendment event (same provision + amending-instrument key + publication date,
e.g. seed r.177 v2003 and change-log PCL-8E-2003) are grouped into one version carrying all evidence_refs;
predecessor/successor bounds are computed over events, and zero-length or reversed intervals are rejected
(flag VALIDITY_INTERVAL_REJECTED; never emitted).
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
COLS = ["record_id", "instrument", "provision", "cited_via", "version_id", "event_key", "evidence_refs", "version_source", "change_or_version",
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


# ---- provision-list expansion (review fix PR #25 #1) --------------------------------------------------
# 'rr.134,135,136', 'rr.172-176' (hyphen or en-dash), 'rr.170A,170B', 'r.16A,16B,16C', 'ss.137/151',
# 'r.15B; r.16A(4) ...'. Sub-provision brackets ('r.14(4),(5)') never create new provisions. Every expanded
# number is verified against the original text (literal token or inside an explicit range): nothing invented.
_NUM = r"\d+[A-Z]?"
_ITEM = rf"{_NUM}(?:\s*\([^)]*\))*"


def expand_provisions(text, unit):
    """Provision numbers for unit 'r' (Army Rules) or 's' (Army Act) found in a register text, in order."""
    lead = rf"(?<![A-Za-z]){unit}{{1,2}}\.\s*"
    pat = re.compile(rf"{lead}({_ITEM}(?:\s*(?:,|/|&|\band\b|[–-]|\bto\b)\s*(?:{unit}{{1,2}}\.\s*)?{_ITEM})*)")
    out = []
    for m in pat.finditer(text):
        body = re.sub(r"\([^)]*\)", "", m.group(1))
        tokens = re.findall(rf"{_NUM}|[–-]|\bto\b", body)
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if re.fullmatch(_NUM, t):
                if i + 2 < len(tokens) and tokens[i + 1] in ("-", "–", "to") and re.fullmatch(_NUM, tokens[i + 2]):
                    a, b = t, tokens[i + 2]
                    if a.isdigit() and b.isdigit() and 0 < int(b) - int(a) <= 60:
                        out += [str(k) for k in range(int(a), int(b) + 1)]
                    else:
                        out += [a, b]
                    i += 3
                    continue
                out.append(t)
            i += 1
    seen, res = set(), []
    for n in out:
        if n not in seen:
            seen.add(n); res.append(n)
    for n in res:  # verification against the original text
        literal = re.search(rf"(?<![\dA-Za-z]){re.escape(n)}(?![\dA-Za-z])", text)
        in_range = any(int(a) <= int(re.match(r"\d+", n).group()) <= int(b) for a, b in re.findall(r"(\d+)\s*(?:[–-]|to)\s*(\d+)", text))
        if not (literal or in_range):
            raise ValueError(f"expanded provision {n!r} not supported by text {text!r}")
    return res


# ---- amendment-event identity (review fix PR #25 #2) ---------------------------------------------------
# One amendment EVENT = same instrument (AA/AR) + same provision number + same amending-instrument key
# (S.R.O. number/year or Act number/year, normalised from the register text) + same publication date where both
# rows state one. Duplicate descriptions of one event (seed register + change log) are grouped; all evidence
# references are kept; a group is never treated as a successor of itself.
def instrument_key(*texts):
    t = " ".join(x or "" for x in texts)
    m = re.search(r"S\.R\.O\.\s*(\d+)\s*(\(E\))?\s*/\s*(\d{4})", t)
    if m:
        return f"SRO-{m.group(1)}{'E' if m.group(2) else ''}-{m.group(3)}"
    m = re.search(r"\bAct\s+(\d+)\s+of\s+(\d{4})|\b(\d+)\s+of\s+(\d{4})", t)
    if m:
        return f"ACT-{m.group(1) or m.group(3)}-{m.group(2) or m.group(4)}"
    return ""


def group_events(entries):
    groups = []
    for e in entries:
        tgt = None
        for g in groups:
            if e["ikey"] and g["ikey"] == e["ikey"] and (not (ISO.match(e["pub"] or "") and ISO.match(g["pub"] or "")) or e["pub"] == g["pub"]):
                tgt = g; break
        if tgt is None:
            groups.append(dict(e, evidence_ids=[e["version_id"]], sources=[e["source"]], members=[e],
                               event_key=e["ikey"] or e["version_id"]))
        else:
            tgt["evidence_ids"].append(e["version_id"]); tgt["sources"].append(e["source"]); tgt["members"].append(e)
    for g in groups:
        ms = g["members"]
        seed = [m for m in ms if m["source"].startswith("ARMY-RULES-CHAIN-01")]
        rep = seed[0] if seed else ms[0]
        stated = sorted({m["eff"] for m in ms if (m["status"] or "").startswith(STATED) and ISO.match(m["eff"] or "")})
        pubs = sorted({m["pub"] for m in ms if ISO.match(m["pub"] or "")})
        g.update(version_id=rep["version_id"], change=rep["change"], det=next((m["det"] for m in seed if m["det"]), ""),
                 conflict=next((m["conflict"] for m in seed if m["conflict"]), ""), sub=any(m["sub"] for m in ms),
                 ocr=all(m["ocr"] for m in ms), pub=pubs[0] if pubs else rep["pub"],
                 conflicts=(["EVIDENCE_EFFECTIVE_DATE_CONFLICT"] if len(stated) > 1 else []) + (["EVIDENCE_PUBLICATION_DATE_CONFLICT"] if len(pubs) > 1 else []))
        if len(stated) == 1:
            g["eff"] = stated[0]
            g["status"] = next(m["status"] for m in ([rep] + ms) if m["eff"] == stated[0] and (m["status"] or "").startswith(STATED))
        else:
            g["eff"] = ""
            g["status"] = rep["status"] if not stated else "CONFLICTING_EVIDENCE: " + " / ".join(stated)
        g["source"] = ";".join(dict.fromkeys(g["sources"]))
        del g["members"]
    return groups


def successor_bound(vs, i):
    """(valid_to, flag) for version i: the next version with a stated commencement after i's own valid_from.
    Zero-length or reversed intervals are rejected (never emitted)."""
    v = vs[i]
    nxt = next((w for w in vs[i + 1:] if (w["status"] or "").startswith(STATED) and ISO.match(w["eff"] or "")), None)
    if not nxt:
        return "", ("VALID_TO_UNSTATED" if vs[i + 1:] else "")
    vf = v["eff"] if (v["status"] or "").startswith(STATED) and ISO.match(v["eff"] or "") else ""
    if vf and nxt["eff"] <= vf:
        return "", "VALIDITY_INTERVAL_REJECTED"
    return nxt["eff"], ""


def versions():
    """{(instrument, provision_number): [event group]} from the three registers."""
    raw = collections.defaultdict(list)

    def add(inst, num, **kw):
        k = norm(num)
        if k:
            raw[(inst, k)].append(kw)

    for r in rows(INPUTS["version_register"]):
        m = re.match(r"r\.(\d+[A-Za-z]?)", r["provision"])
        if m:
            add("AR", m.group(1), version_id=f"{r['provision']}@{r['version']}", source="ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv",
                change=r["version"], sub=bool(re.match(r"r\.\d+[A-Za-z]?\s*[\(\s]", r["provision"])), ocr=False,
                pub=r["publication_date"], eff=r["effective_date"], status=r["effective_date_status"],
                det=r["determination_state"], conflict=r["conflict_id"] if r["conflict_id"] not in ("", "-") else "",
                ikey=instrument_key(r["text_source_instrument"]))
    for r in rows(INPUTS["wsa_change_log"]):
        if "itself" in r["provision"] or NOT_A_CHANGE.search(r["change_type"]):
            continue  # not a version: search findings, notes, declarations
        for n in expand_provisions(r["provision"], "r"):
            add("AR", n, version_id=r["change_id"], source="WS-A-STATUTORY/provision_change_log.csv",
                change=f"{r['change_type']} ({r['instrument'][:60]})",
                sub=bool(re.search(r"r{1,2}\.\s*%s\s*\(" % re.escape(n), r["provision"])),
                ocr="OCR" in r["change_type"] or "OCR" in r.get("evidence_level", ""),
                pub=r["publication_date"], eff=r["effective_date"], status=r["effective_date_status"], det="", conflict="",
                ikey=instrument_key(r["instrument"], r["gazette_identity"]))
    for r in rows(INPUTS["wsa_aa_chain"]):
        if (NOT_A_CHANGE.search(r["change_as_printed"]) or (r["effective_date_status"] or "").startswith("NOT_APPLICABLE")
                or r["sections_affected"].strip().lower().startswith(("proposed", "none", "unknown", "all", "as act"))):
            continue  # not an enacted change to identified sections
        for n in expand_provisions(r["sections_affected"], "s"):
            add("AA", n, version_id=r["chain_id"], source="WS-A-STATUTORY/army_act_amendment_chain.csv",
                change=f"{r['instrument'][:60]}", sub=bool(re.search(r"ss?\.\s*%s\s*\(" % re.escape(n), r["sections_affected"])),
                ocr=r["evidence_level"].startswith(("HINT", "TEXT_LAYER", "REQUIRES_VERIFICATION")),
                pub=r["publication_date"], eff=r["effective_date"], status=r["effective_date_status"], det="", conflict="",
                ikey=instrument_key(r["instrument"], r["number_year"], r["gazette_identity"]) or r["chain_id"].rsplit("-s", 1)[0])
    V = {}
    for k, entries in raw.items():
        entries.sort(key=lambda v: (v["pub"] if ISO.match(v["pub"] or "") else "9999", v["version_id"]))
        V[k] = group_events(entries)
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
                valid_to, bound_flag = successor_bound(vs, i)
                flags = []
                if not stated:
                    flags.append("EFFECTIVE_DATE_UNSTATED")
                if bound_flag:
                    flags.append(bound_flag)
                flags += v["conflicts"]
                if v["sub"]:
                    flags.append("SUBPROVISION_VERSION")
                if v["ocr"]:
                    flags.append("TEXT_OR_OCR_EVIDENCE_ONLY")
                if v["det"] and v["det"].split()[0] in ("CONFLICTING", "OPEN", "PROPOSAL"):
                    flags.append("DETERMINATION_" + v["det"].split()[0])
                edges.append({"record_id": rid, "instrument": "Army Act 1950" if inst == "AA" else "Army Rules 1954",
                              "provision": ("s." if inst == "AA" else "r.") + num, "cited_via": via, "version_id": v["version_id"],
                              "event_key": v["event_key"], "evidence_refs": ";".join(v["evidence_ids"]),
                              "version_source": v["source"], "change_or_version": v["change"], "publication_date": v["pub"],
                              "effective_date_status": v["status"], "valid_from": v["eff"] if stated else "",
                              "valid_to": valid_to, "determination_state": v["det"], "conflict_id": v["conflict"],
                              "flags": ";".join(flags)})
    cited = {(r, k) for r in C for k in C[r]}
    with_versions = {(r, k) for r, k in cited if V.get(k)}
    S = {"records_citing_aa_or_ar_provisions": len(C), "record_provision_citations": len(cited),
         "citations_with_registered_versions": len(with_versions), "edges": len(edges),
         "edges_with_stated_effective_date": sum("EFFECTIVE_DATE_UNSTATED" not in e["flags"] for e in edges),
         "edges_effective_date_unstated_flagged": sum("EFFECTIVE_DATE_UNSTATED" in e["flags"] for e in edges),
         "provisions_with_versions": len(V), "amendment_events": sum(len(v) for v in V.values()),
         "events_grouping_duplicate_evidence": sum(1 for v in V.values() for g in v if len(g["evidence_ids"]) > 1),
         "edges_zero_length_or_reversed": sum(1 for e in edges if e["valid_from"] and e["valid_to"] and e["valid_to"] <= e["valid_from"]),
         "by_version_source": dict(sorted(collections.Counter(e["version_source"] for e in edges).items())),
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
