#!/usr/bin/env python3
"""Estimate how many PROVISION_FILES_ABSENT records could become technically searchable after verified
provision-level (rule-level) indexing (CALIBRATION-02 / Cycle 4 planning; DATABASE ONLY).

Stdlib only, no network, read-only. Deterministic: sorted output, no timestamps; two runs are byte-identical
while the inputs and the git ref are unchanged.

Inputs
  legal_knowledge/audit_work/WS-D-QUALITY/canonical_coverage.csv   (the 193 records flagged PROVISION_FILES_ABSENT,
                                                                     with their resolved citation items)
  legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl    (case targets; read-only)
  git origin/raw-data: data/meta (doc ids), data/sections (provision files for Acts), and the held compilation
  texts data/text/rules-army-rules-1954.txt, rules-aft-procedure-rules-2008.txt,
  rules-aft-amendment-procedure-rules-2011.txt (with their data/meta sha256).

Method
  1. Rule headings are located in each compilation text after its first "1. Short title" line (or from the top):
     a line "N." / "N-A." / "N. Heading" / "N to M." whose number continues the rule sequence (monotonic window:
     the same number with a later letter suffix, or a number up to 10 above the last accepted rule). Sub-rule
     and note numbering restarts low and is therefore rejected. "Omitted"/"Cancelled" within three lines marks
     an OMITTED_MARKER rule. The page is the last "[[page N]]" marker before the heading.
  2. For an amending instrument, a principal rule is also "referenced" when the text renumbers or inserts it
     ("rule 7", quoted "12A."). A key of the principal that only an amending instrument in the corpus inserts is
     resolvable VIA_AMENDING_INSTRUMENT (a point-in-time version, not the principal text).
  3. Each identified citation item of a flagged record is re-checked exactly as WS-D canonical_coverage does
     (Act sections against data/sections; target existence against data/meta and cases_53). Rule keys are then
     checked against step 1/2. Keys that are not rule numbers of the instrument (e.g. a year read as a rule:
     r1993, r2011) are INVALID_KEY and never resolve.
  4. Outcome per record: BECOMES_PROVISION_SEARCHABLE (every provision key resolves), PARTIAL_IMPROVEMENT (some
     absent keys resolve), NO_CHANGE. A conservative count also excludes OMITTED_MARKER and VIA_AMENDING_INSTRUMENT
     resolutions and keys found only in an instrument whose text layer is bilingual or garbled (AFT 2008).

Assumptions (stated, not verified): the held compilation text is comparison-grade only (India Code / MoD
compilation, SOURCE_AUTHORITY_POLICY v1), never Gazette authority; every resolved provision still needs
verification against Gazette page images and the amendment chain before it is relied on. "Technically
searchable" means a provision record would exist; it says nothing about legal correctness or currency.
Usage: python3 estimate_rule_index_coverage.py [--out DIR]
"""
from __future__ import annotations
import argparse, csv, io, json, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
AW = ROOT / "legal_knowledge" / "audit_work"
COV = AW / "WS-D-QUALITY" / "canonical_coverage.csv"
CASES = ROOT / "legal_knowledge" / "curated_originals" / "case_law" / "v0.9" / "cases_53.jsonl"
REF = "origin/raw-data"
RULE_DOCS = ["rules-army-rules-1954", "rules-aft-procedure-rules-2008", "rules-aft-amendment-procedure-rules-2011"]
AMENDING = {"rules-aft-procedure-rules-2008": ["rules-aft-amendment-procedure-rules-2011"]}
PRINCIPAL_OF = {"rules-aft-amendment-procedure-rules-2011": "rules-aft-procedure-rules-2008"}
# Text-layer quality as observed in the held files (bilingual Hindi/English Gazette with garbled OCR-like text
# layer); used only for the conservative count.
LOW_QUALITY_TEXT = {"rules-aft-procedure-rules-2008", "rules-aft-amendment-procedure-rules-2011"}
MAX_JUMP = 6
MAX_RULE = {"rules-army-rules-1954": 205, "rules-aft-procedure-rules-2008": 40,
            "rules-aft-amendment-procedure-rules-2011": 40}
HEAD_RX = re.compile(r"^\s*(\d{1,3})\s*(?:-\s*)?([A-Z]{0,2})\.(?:\s+(.*))?$")
RANGE_RX = re.compile(r"^\s*(\d{1,3})\s+to\s+(\d{1,3})\.\s*$")
OMIT_RX = re.compile(r"\b(Omitted|Cancelled|Deleted)\b", re.I)
PAGE_RX = re.compile(r"^\[\[page (\d+)\]\]$")


def git(*a) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a], check=True, capture_output=True).stdout.decode("utf-8")


def rows(p: Path):
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))


def key_of(num: str, suf: str) -> str:
    return f"r{int(num)}{suf.lower()}"


def locate_rules(doc: str, text: str):
    """key -> (page, basis, line_no). basis: HEADING or OMITTED_MARKER."""
    lines = text.splitlines()
    start = 0
    for i, ln in enumerate(lines):
        if re.match(r"(?i)^\s*1\.\s*Short title", ln):
            start = i
            break
    page, found = None, {}
    last = (0, "")
    for i, ln in enumerate(lines):
        m = PAGE_RX.match(ln.strip())
        if m:
            page = int(m.group(1))
            continue
        if i < start:
            continue
        window = " ".join(lines[i:i + 4])
        r = RANGE_RX.match(ln)
        if r:
            a, b = int(r.group(1)), int(r.group(2))
            if last[0] < a <= last[0] + MAX_JUMP and a < b <= a + 20:
                for n in range(a, b + 1):
                    found.setdefault(f"r{n}", (page, "OMITTED_MARKER" if OMIT_RX.search(window) else "HEADING", i + 1))
                last = (b, "")
            continue
        h = HEAD_RX.match(ln)
        if not h:
            continue
        n, suf = int(h.group(1)), h.group(2) or ""
        if n > MAX_RULE[doc]:
            continue
        ok = (n == last[0] and suf > last[1]) or (last[0] < n <= last[0] + MAX_JUMP)
        tail = (h.group(3) or "").strip()
        # a rule heading line carries the number alone, a short heading ending in a full stop, or
        # "Heading.-text" (dash after the heading); a long sentence after the number is note numbering
        heading_like = (not tail or (len(tail) <= 70 and tail.endswith("."))
                        or re.match(r"^[A-Z][^.]{2,60}\.\s*[-\u2014]", tail))
        if not ok or not heading_like:
            continue
        rest = (h.group(3) or "") + " " + " ".join(lines[i + 1:i + 4])
        found.setdefault(key_of(n, suf), (page, "OMITTED_MARKER" if OMIT_RX.search(rest[:160]) else "HEADING", i + 1))
        last = (n, suf)
    return found


def referenced_principal_rules(text: str):
    """Principal-rule keys an amending instrument renumbers, amends or inserts (English text only)."""
    out = {}
    for m in re.finditer(r"\b[Rr]ules?\s+(\d{1,3}[A-Z]?)\b", text):
        out.setdefault(f"r{m.group(1).lower()}", "REFERENCED")
    for m in re.finditer(r"[“\"*](\d{1,3}[A-Z])\.", text):
        out[f"r{m.group(1).lower()}"] = "INSERTED_TEXT"
    return out


def build():
    commit = git("rev-parse", REF).strip()
    names = git("ls-tree", "-r", "--name-only", REF, "data/meta", "data/sections").split()
    meta = {Path(n).stem for n in names if n.startswith("data/meta/") and n.endswith(".json")}
    sections = defaultdict(set)
    for n in names:
        if n.startswith("data/sections/") and n.endswith(".json"):
            _, _, d, f = n.split("/", 3)
            sections[d].add(Path(f).stem)
    case_ids = {json.loads(l)["id"] for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()}
    rules, refs, docinfo = {}, {}, {}
    for d in RULE_DOCS:
        txt = git("show", f"{REF}:data/text/{d}.txt")
        m = json.loads(git("show", f"{REF}:data/meta/{d}.json"))
        rules[d] = locate_rules(d, txt)
        refs[d] = referenced_principal_rules(txt) if d in PRINCIPAL_OF else {}
        docinfo[d] = {"meta_sha256": m.get("sha256"), "source_url": m.get("source_url"), "page_count": m.get("page_count"),
                      "text_method": m.get("text_method"), "text_chars": len(txt), "rule_keys_found": len(rules[d])}

    def target_exists(t):
        return t in case_ids if t.startswith("DCLR-") else t in meta

    def resolve(doc, k):
        """(resolves: bool, basis, page)"""
        if not re.fullmatch(r"r\d{1,3}[a-z]{0,2}", k) or int(re.match(r"r(\d+)", k).group(1)) > MAX_RULE.get(doc, 999):
            return False, "INVALID_KEY", ""
        if k in rules.get(doc, {}):
            pg, basis, _ = rules[doc][k]
            return True, f"RULE_{basis}", str(pg or "")
        if doc in PRINCIPAL_OF and k in refs.get(doc, {}):
            return True, f"AMENDED_PROVISION_{refs[doc][k]}", ""
        for a in AMENDING.get(doc, []):
            if refs.get(a, {}).get(k) == "INSERTED_TEXT":
                return True, f"VIA_AMENDING_INSTRUMENT ({a})", ""
        return False, "RULE_NOT_FOUND_IN_TEXT_LAYER", ""

    cov = rows(COV)
    flagged = [r for r in cov if "PROVISION_FILES_ABSENT" in r["quality_flags"].split(";")]
    out, keyrows = [], []
    agree = 0
    for r in sorted(flagged, key=lambda x: x["record_id"]):
        items = [x for x in r["items"].split(" | ") if x.strip()]
        base_srch, base_absent, after_ok, cons_ok = [], False, [], []
        n_abs_keys = n_res = n_res_cons = 0
        bases = Counter()
        for it in items:
            m = re.search(r"=>([^\[]+)\[(\w+)\](?:#(.*))?$", it)
            if not m or m.group(2) != "id":
                continue
            tgt, keys = m.group(1), [k for k in (m.group(3) or "").split(",") if k]
            ex = target_exists(tgt)
            if not ex:
                base_srch.append(False); after_ok.append(False); cons_ok.append(False)
                continue
            if not keys:
                base_srch.append(True); after_ok.append(True); cons_ok.append(True)
                continue
            idx = sections.get(tgt, set())
            miss = [k for k in keys if k.lower() not in idx]
            base_srch.append(not miss)
            if miss:
                base_absent = True
            ok_all, ok_cons = True, True
            for k in sorted(set(miss)):
                n_abs_keys += 1
                if tgt.startswith("act-"):
                    res, basis, pg = False, "SECTION_FILE_ABSENT (Act; outside rule indexing)", ""
                elif tgt in RULE_DOCS:
                    res, basis, pg = resolve(tgt, k.lower())
                else:
                    res, basis, pg = False, "NO_HELD_COMPILATION_TEXT", ""
                cons = res and basis == "RULE_HEADING" and tgt not in LOW_QUALITY_TEXT
                n_res += res
                n_res_cons += cons
                ok_all &= res
                ok_cons &= cons
                bases[basis.split(" (")[0]] += 1
                keyrows.append({"record_id": r["record_id"], "target_doc": tgt, "provision_key": k,
                                "resolution_basis": basis, "compilation_page": pg,
                                "resolves_after_indexing": "YES" if res else "NO",
                                "resolves_conservative": "YES" if cons else "NO"})
            after_ok.append(ok_all)
            cons_ok.append(ok_cons)
        if base_absent:
            agree += 1
        prov_after = all(after_ok) if after_ok else False
        prov_cons = all(cons_ok) if cons_ok else False
        if prov_after:
            outcome = "BECOMES_PROVISION_SEARCHABLE"
        elif n_res:
            outcome = "PARTIAL_IMPROVEMENT"
        else:
            outcome = "NO_CHANGE"
        out.append({"record_id": r["record_id"], "module": r["module"], "family": r["family"],
                    "source_searchable_now": r["source_searchable"],
                    "absent_provision_keys": str(n_abs_keys), "keys_resolving": str(n_res),
                    "keys_resolving_conservative": str(n_res_cons),
                    "outcome": outcome,
                    "outcome_conservative": "BECOMES_PROVISION_SEARCHABLE" if prov_cons else (
                        "PARTIAL_IMPROVEMENT" if n_res_cons else "NO_CHANGE"),
                    "resolution_bases": ";".join(f"{k}={v}" for k, v in sorted(bases.items())),
                    "other_quality_flags": ";".join(f for f in r["quality_flags"].split(";") if f and f != "PROVISION_FILES_ABSENT"),
                    "items": r["items"]})
    summary = {
        "flagged_records": len(flagged),
        "flag_reproduced_by_recheck": agree,
        "outcome": dict(sorted(Counter(o["outcome"] for o in out).items())),
        "outcome_conservative": dict(sorted(Counter(o["outcome_conservative"] for o in out).items())),
        "becomes_searchable_with_no_other_flag": sum(o["outcome"] == "BECOMES_PROVISION_SEARCHABLE" and not o["other_quality_flags"] for o in out),
        "becomes_searchable_conservative_with_no_other_flag": sum(o["outcome_conservative"] == "BECOMES_PROVISION_SEARCHABLE" and not o["other_quality_flags"] for o in out),
        "by_target_outcome": {d: dict(sorted(Counter(o["outcome"] for o in out if d in o["items"]).items())) for d in RULE_DOCS},
        "absent_keys_by_basis": dict(sorted(Counter(k["resolution_basis"].split(" (")[0] for k in keyrows).items())),
        "absent_keys_by_target": dict(sorted(Counter(k["target_doc"] for k in keyrows).items())),
        "raw_data_commit": commit,
        "compilations": docinfo,
        "assumptions": [
            "Held compilation texts are comparison-grade (government compilation / India Code), never Gazette authority.",
            "Every resolved provision still requires verification against Gazette page images and the amendment chain.",
            "Technically searchable means a provision record would exist; it is not legal correctness or currency.",
            "A rule heading found in the text layer is evidence of presence in that compilation only; omitted-marker "
            "and via-amending-instrument resolutions are excluded from the conservative count.",
        ],
    }
    pres = []
    for d in RULE_DOCS:
        for k, (pg, basis, ln) in sorted(rules[d].items(), key=lambda x: (int(re.match(r"r(\d+)", x[0]).group(1)), x[0])):
            pres.append({"doc_id": d, "rule_key": k, "basis": basis, "page": str(pg or ""), "text_line": str(ln)})
        for k, b in sorted(refs[d].items()):
            pres.append({"doc_id": d, "rule_key": k, "basis": f"PRINCIPAL_RULE_{b}", "page": "", "text_line": ""})
    return out, keyrows, pres, summary


def write_csv(p: Path, data, cols):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(data)
    p.write_text(buf.getvalue(), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE)
    a = ap.parse_args(argv)
    out, keyrows, pres, summ = build()
    a.out.mkdir(parents=True, exist_ok=True)
    write_csv(a.out / "rule_index_coverage_estimate.csv", out, list(out[0].keys()))
    write_csv(a.out / "rule_index_coverage_keys.csv",
              sorted(keyrows, key=lambda x: (x["record_id"], x["target_doc"], x["provision_key"])), list(keyrows[0].keys()))
    write_csv(a.out / "compilation_rule_presence.csv", pres, list(pres[0].keys()))
    (a.out / "rule_index_coverage_summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": summ["outcome"], "conservative": summ["outcome_conservative"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
