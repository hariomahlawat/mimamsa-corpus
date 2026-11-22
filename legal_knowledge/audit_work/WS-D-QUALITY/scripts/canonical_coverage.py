#!/usr/bin/env python3
"""WS-D cycle 3, task 1: canonical coverage measures (owner-approved CP-01 / OQ-D-016).

Three SEPARATE measures per KB record (denominator 658), never blended into one score:
  citation_present   YES / NO. The record cites at least one citation code, statute token, statute locator
                     or case. Placeholders, editorial labels and unanchored locators are not citations.
  source_identified  ALL / PARTLY / NONE / NOT_APPLICABLE (no citation). Per citation item:
                     - codes: firm register class (RESOLVED_RECORD_EXPLICIT, CORROBORATED_OFFICIAL) AND a declared
                       corpus target (act-/rules-/DCLR-, not 'candidate'); co-citation codes are INFERRED and never
                       identified; register GAP targets and PROBABLE / CATEGORY_ONLY / UNRESOLVABLE codes are NONE;
                     - plain statute tokens: identified when the shared name map gives one specific corpus document;
                       an instrument known but without a corpus target (e.g. Constitution) is NONE with flag
                       IDENTITY_KNOWN_TARGET_ABSENT;
                     - plain case names: NONE until WS-B resolves them; a unique short-name lexicon match is
                       reported as INFERRED.
  source_searchable  ALL / PARTLY / NONE / NOT_CHECKED / NOT_APPLICABLE (nothing identified). Every identified
                     source exists in a searchable corpus: DCLR id in cases_53; doc_id in crawler data/meta; and,
                     where an Act section is cited, the section file exists.
Quality flags are reported alongside and are not gates inside the measures: NO_PINPOINT, PLACEHOLDER,
STRUCTURAL, AMBIGUOUS_LOCATOR, CASE_NAME_WITHOUT_CODE, UNANCHORED_LOCATOR, INFERRED_IDENTITY,
IDENTITY_KNOWN_TARGET_ABSENT. ANCHORED_FULL = citation_present AND identified ALL AND searchable ALL AND no flag.

Coverage locates cited sources. It is NOT legal correctness, currency, amendment completeness or verification.
Inputs are pinned by SHA-256 in canonical_coverage.json. Supersedes (but preserves) coverage_scorecard.* and
coverage_reconciliation.* as the definition of record-level coverage.
Usage: python3 canonical_coverage.py [--corpus-ref REF] [--check]
"""
import argparse, collections, csv, hashlib, importlib.util, io, json, re, subprocess, sys
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
AW = ROOT / "legal_knowledge/audit_work"
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
CASES = ROOT / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
INPUTS = {"kb": KB, "cases": CASES,
          "register": AW / "PILOT-01/registers/source_code_resolution_v3.csv",
          "wsc_inventory": AW / "WS-C-MML/kb658_source_coverage_inventory.csv",
          "wsc_lexicon": AW / "WS-C-MML/case_name_lexicon.csv",
          "plaintext_index": WSD / "plaintext_citation_index.csv",
          "scorecard_script": WSD / "scripts/coverage_scorecard.py",
          "index_script": WSD / "scripts/build_plaintext_index.py"}
FIRM = {"RESOLVED_RECORD_EXPLICIT", "CORROBORATED_OFFICIAL"}
# One shared name -> corpus document map for WS-D parser tokens and WS-C plain statute names.
NAME_DOC = [(r"^(AA|Army Act)$", "act-army-1950"), (r"^(AR|Army Rules?)$", "rules-army-rules-1954"),
            (r"^(AFT Act|AFT)$", "act-armed-forces-tribunal-2007"), (r"^BNSS$", "act-bnss-2023"), (r"^BNS$", "act-bns-2023"),
            (r"^(BSA|Bharatiya Sakshya Adhiniyam.*)$", "act-bsa-2023"), (r"^IPC$", "act-ipc-1860"),
            (r"^(CrPC|Cr\.?P\.?C)$", "act-crpc-1973"), (r"^(Evidence Act|IEA)$", "act-evidence-1872"),
            (r"^Air Force Act$", "act-air-force-1950"), (r"^Navy Act$", "act-navy-1957")]
KNOWN_NO_TARGET = re.compile(r"^(Constitution|Art\.?\s*\d+|Article\s*\d+|POCSO|ISO Act)", re.I)
STRUCTURAL = ("PROVISION_NOT_IN_HEADING_INDEX", "ARMY_ACT_OR_RULES_CITED_WITHOUT_PINPOINT", "URL_NON_OFFICIAL_HOST")
OUT = {"csv": WSD / "canonical_coverage.csv", "json": WSD / "canonical_coverage.json", "md": WSD / "canonical_coverage.md"}
OUT_JSON_PATH = OUT["json"]
LABEL = "canonical coverage"
COLS = ["record_id", "module", "family", "citation_present", "citation_kinds", "n_items", "source_identified",
        "n_identified", "n_inferred", "source_searchable", "n_searchable", "quality_flags", "anchored_full", "items"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def rows(p):
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))


def name_doc(name):
    return next((d for rx, d in NAME_DOC if re.match(rx, name.strip())), None)


def state(flags):
    if not flags:
        return "NOT_APPLICABLE"
    if all(flags):
        return "ALL"
    return "PARTLY" if any(flags) else "NONE"


def build(corpus_ref):
    bci = load("bci_cc", AW / "PILOT-01/build_code_inventory.py")
    cov = load("cov_cc", INPUTS["scorecard_script"])
    C = cov.corpus(corpus_ref)
    inv, _, _ = bci.inventory()
    reg = {r["code"]: r for r in rows(INPUTS["register"])}
    kb = [json.loads(l) for l in KB.read_text(encoding="utf-8").splitlines() if l.strip()]
    case_ids = {json.loads(l)["id"] for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()}
    wsc = {r["record_id"]: r for r in rows(INPUTS["wsc_inventory"])}
    lexkeys = collections.defaultdict(set)
    for x in rows(INPUTS["wsc_lexicon"]):
        lexkeys[x["key"]].add(x["case53_id"] or x["spec_key"])
    idx = collections.defaultdict(list)
    for r in rows(INPUTS["plaintext_index"]):
        idx[r["record_id"]].append(r)
    rec_codes = collections.defaultdict(set)
    for c, rs in inv.items():
        for r in rs:
            rec_codes[r].add(c)

    def target_exists(t):
        if t.startswith("DCLR-"):
            return t in case_ids
        if C is None:
            return None
        return t in C["meta"]

    out = []
    for rec in kb:
        rid = rec["id"]; w = wsc[rid]; items = []; flags = set()
        wflags = [f.strip() for f in w["broken_or_unresolved_flags"].split(" | ") if f.strip()]
        for c in sorted(rec_codes.get(rid, ())):
            g = reg[c]; cls = g["resolution_class"]
            t = g["corpus_target_or_gap"].strip()
            held = bool(re.match(r"^(act-|rules-|DCLR-)", t)) and "(candidate)" not in t
            tgt = (re.match(r"^(DCLR-[A-Z]+-\d{4}-[A-Z]?\d+|(?:act|rules)-[a-z0-9-]+)", t).group(1) if held else "")
            items.append({"kind": "code", "ref": c, "identified": cls in FIRM and held, "inferred": cls == "RESOLVED_CO_CITATION",
                          "target": tgt, "sections": []})
            if cls == "RESOLVED_CO_CITATION":
                flags.add("INFERRED_IDENTITY")
        code_targets = {i["target"] for i in items}
        if rid not in rec_codes:
            bykey = {s["seg_no"]: s for s in idx.get(rid, [])}
            for s in idx.get(rid, []):
                cat = s["category"]
                if "UNANCHORED_LOCATOR" in s["placeholder_flags"]:
                    flags.add("UNANCHORED_LOCATOR")
                if cat == "CASE_REFERENCE":
                    items.append({"kind": "case", "ref": s["exact_text"], "identified": False, "inferred": False, "target": "", "sections": []})
                    continue
                src = bykey.get(s["context_from_seg"]) if cat == "LOCATOR_CONTINUATION" else s
                if cat not in ("STATUTE_LOCATOR", "STATUTE_GENERIC") and not (cat == "LOCATOR_CONTINUATION" and src):
                    continue
                for a in cov.assess_plain_segment(s, src):
                    doc = name_doc(a["token"])
                    if a["ambiguous"]:
                        flags.add("AMBIGUOUS_LOCATOR")
                    if doc is None and KNOWN_NO_TARGET.match(a["token"]):
                        flags.add("IDENTITY_KNOWN_TARGET_ABSENT")
                    items.append({"kind": "statute", "ref": a["token"], "identified": doc is not None, "inferred": False,
                                  "target": doc or "", "sections": a["numbers"] if doc else []})
        else:
            for n in filter(None, w["other_statutes_plain"].split(";")):
                doc = name_doc(n)
                if doc and doc in code_targets:
                    continue
                if doc is None and KNOWN_NO_TARGET.match(n):
                    flags.add("IDENTITY_KNOWN_TARGET_ABSENT")
                items.append({"kind": "statute", "ref": n, "identified": doc is not None, "inferred": False, "target": doc or "", "sections": []})
            if any(f.startswith("PLAIN_CASE_CITATION_UNRESOLVED") for f in wflags):
                items.append({"kind": "case", "ref": "plain case citation (WS-C)", "identified": False, "inferred": False, "target": "", "sections": []})
        for f in wflags:
            if f.startswith("CASE_NAME_WITHOUT_CODE:"):
                flags.add("CASE_NAME_WITHOUT_CODE")
                for pair in f.split(":", 1)[1].split("/"):
                    name = pair.partition("->")[0]
                    case_items = [i for i in items if i["kind"] == "case" and name in i["ref"]]
                    uniq = len(lexkeys.get(name, ())) == 1
                    if case_items:
                        for i in case_items:
                            i["inferred"] = i["inferred"] or uniq
                    else:
                        items.append({"kind": "case", "ref": name, "identified": False, "inferred": uniq, "target": "", "sections": []})
                    if uniq:
                        flags.add("INFERRED_IDENTITY")
            elif f.startswith("PLACEHOLDER"):
                flags.add("PLACEHOLDER")
            elif f.startswith(STRUCTURAL):
                flags.add("STRUCTURAL")
        if any("VERIFY" in s["placeholder_flags"] for s in idx.get(rid, [])):
            flags.add("PLACEHOLDER")
        present = bool(items)
        if present and w["pinpoint_present"] == "NO":
            flags.add("NO_PINPOINT")
        ident = [i for i in items if i["identified"]]
        srch = []
        for i in ident:
            ex = target_exists(i["target"])
            if ex and i["sections"] and C is not None and C["sections"].get(i["target"]):
                ex = all(("s" + n.lower()) in C["sections"][i["target"]] for n in i["sections"])
            srch.append(ex)
        s_state = "NOT_APPLICABLE" if not ident else ("NOT_CHECKED" if None in srch else state(srch))
        i_state = state([i["identified"] for i in items]) if present else "NOT_APPLICABLE"
        full = present and i_state == "ALL" and s_state == "ALL" and not flags
        out.append({"record_id": rid, "module": rec.get("module", ""), "family": "CODED" if rid in rec_codes else "PLAINTEXT",
                    "citation_present": "YES" if present else "NO",
                    "citation_kinds": ";".join(sorted({i["kind"] for i in items})), "n_items": len(items),
                    "source_identified": i_state, "n_identified": len(ident), "n_inferred": sum(i["inferred"] for i in items),
                    "source_searchable": s_state, "n_searchable": sum(1 for x in srch if x),
                    "quality_flags": ";".join(sorted(flags)), "anchored_full": "YES" if full else "NO",
                    "items": " | ".join(f"{i['kind']}:{i['ref']}{'=>' + i['target'] if i['target'] else ''}"
                                        f"{'[id]' if i['identified'] else '[inferred]' if i['inferred'] else '[not-id]'}"
                                        f"{'#s' + ',s'.join(i['sections']) if i['sections'] else ''}" for i in items)})
    inputs = {k: {"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for k, p in INPUTS.items()}
    inputs["crawler_corpus"] = {"ref": corpus_ref if C else None, "commit": C["commit"] if C else None}
    return out, inputs


def summarise(out):
    n = len(out)
    cnt = lambda k: dict(sorted(collections.Counter(r[k] for r in out).items()))
    fl = collections.Counter(f for r in out for f in r["quality_flags"].split(";") if f)
    present = [r for r in out if r["citation_present"] == "YES"]
    return {"denominator_records": n, "citation_present": cnt("citation_present"), "source_identified": cnt("source_identified"),
            "source_searchable": cnt("source_searchable"), "anchored_full": cnt("anchored_full"),
            "quality_flags_records": dict(sorted(fl.items())),
            "by_family": {f: {"records": sum(r["family"] == f for r in out),
                              "identified_ALL": sum(r["family"] == f and r["source_identified"] == "ALL" for r in out),
                              "searchable_ALL": sum(r["family"] == f and r["source_searchable"] == "ALL" for r in out),
                              "anchored_full": sum(r["family"] == f and r["anchored_full"] == "YES" for r in out)}
                          for f in ("CODED", "PLAINTEXT")},
            "items": {"total": sum(r["n_items"] for r in out), "identified": sum(r["n_identified"] for r in out),
                      "inferred": sum(r["n_inferred"] for r in out), "searchable": sum(r["n_searchable"] for r in out)},
            "records_with_citation": len(present)}


def render(out, inputs, S):
    f = lambda d, k: d.get(k, 0)
    L = ["# Canonical coverage (CP-01 / OQ-D-016): three separate measures, denominator 658", "",
         "Generated by `scripts/canonical_coverage.py`. **Coverage locates cited sources. It is not legal correctness, currency, amendment completeness or verification, and no measure here approves any record.**", "",
         "Supersedes, as the definition of record-level coverage, `coverage_scorecard.*` (searchability only) and `coverage_reconciliation.*` (WS-C/WS-D comparison). Both are preserved unchanged for traceability.", "",
         "Inputs (SHA-256): " + "; ".join(f"`{k}` {v['sha256'][:12]}…" for k, v in inputs.items() if "sha256" in v)
         + f"; crawler corpus `{inputs['crawler_corpus']['ref']}` @ `{(inputs['crawler_corpus']['commit'] or 'n/a')[:12]}`.", "",
         "## Measures (records)", "", "| Measure | Values (denominator 658) |", "| --- | --- |",
         f"| citation_present | YES {f(S['citation_present'], 'YES')} · NO {f(S['citation_present'], 'NO')} |",
         "| source_identified | " + " · ".join(f"{k} {v}" for k, v in S["source_identified"].items()) + " |",
         "| source_searchable | " + " · ".join(f"{k} {v}" for k, v in S["source_searchable"].items()) + " |",
         f"| ANCHORED_FULL (derived) | YES {f(S['anchored_full'], 'YES')} · NO {f(S['anchored_full'], 'NO')} |", "",
         "source_searchable is computed over the identified items only (CP-01), so a record that is PARTLY identified can still be searchable ALL; read it together with source_identified, never alone.", "",
         f"Citation items: {S['items']['total']} total; {S['items']['identified']} identified; {S['items']['inferred']} inferred (co-citation codes, unique short case names; never counted as identified); {S['items']['searchable']} identified and searchable.", "",
         "## By family", "", "| Family | Records | identified ALL | searchable ALL | ANCHORED_FULL |", "| --- | --- | --- | --- | --- |"]
    L += [f"| {k} | {v['records']} | {v['identified_ALL']} | {v['searchable_ALL']} | {v['anchored_full']} |" for k, v in S["by_family"].items()]
    L += ["", "## Quality flags (records carrying each; reported alongside, not gates)", "", "| Flag | Records |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in S["quality_flags_records"].items()]
    L += ["", "## Definitions", ""] + [l for l in __doc__.split("\n\n")[1].splitlines()] + ["",
          "Per-record detail: `canonical_coverage.csv` (items column: `kind:ref=>target[id|inferred|not-id]#sections`).", ""]
    return "\n".join(L)


def outputs(corpus_ref):
    out, inputs = build(corpus_ref)
    S = summarise(out)
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n"); w.writeheader(); w.writerows(out)
    js = json.dumps({"artifact": "WS-D canonical coverage (CP-01)", "not_legal_correctness": True,
                     "supersedes_preserved": ["coverage_scorecard.json", "coverage_scorecard.md", "coverage_reconciliation.csv",
                                              "coverage_reconciliation.md", "coverage_reconciliation.meta.json"],
                     "inputs": inputs, "summary": S}, indent=1, ensure_ascii=False) + "\n"
    return {OUT["csv"]: buf.getvalue(), OUT["json"]: js, OUT["md"]: render(out, inputs, S)}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--corpus-ref", default="origin/raw-data"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check and subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", a.corpus_ref],
                                  capture_output=True).returncode != 0:
        # CI checkouts lack the crawler-corpus ref: verify the pinned input hashes only and say so.
        pinned = json.loads(OUT_JSON_PATH.read_text(encoding="utf-8"))["inputs"]
        bad = [k for k, v in pinned.items() if "sha256" in v and hashlib.sha256((ROOT / v["path"]).read_bytes()).hexdigest() != v["sha256"]]
        print("%s: corpus ref %s unavailable - regeneration NOT_CHECKED; pinned inputs %s"
              % (LABEL, a.corpus_ref, "MATCH" if not bad else f"CHANGED {bad} (regenerate)"))
        return 1 if bad else 0
    files = outputs(a.corpus_ref)
    if a.check:
        bad = [p.name for p, t in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != t]
        print("canonical coverage: " + ("MATCH" if not bad else f"DIFFERS {bad}"))
        return 1 if bad else 0
    for p, t in files.items():
        p.write_text(t, encoding="utf-8")
    print(json.dumps(summarise(build(a.corpus_ref)[0]), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
