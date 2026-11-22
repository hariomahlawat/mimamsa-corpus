#!/usr/bin/env python3
"""WS-D deliverable 7: source-searchable coverage scorecard with explicit denominators.

'Searchable' means the cited source (instrument, section or judgment) exists as a document in a
corpus the database can search: cases_53, or the crawler corpus (data/meta, data/sections) read
from a LOCAL git ref via `git ls-tree` / `git cat-file` (default origin/raw-data; no network).
It does NOT mean the text was verified, that the version is right for the record's date, or that
the record states the law correctly. Without the ref, corpus-dependent measures are NOT_CHECKED.

Writes coverage_scorecard.json and coverage_scorecard.md into WS-D-QUALITY/.
"""
import argparse, collections, csv, hashlib, importlib.util, io, json, re, subprocess, sys
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
AW = ROOT / "legal_knowledge/audit_work"
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
CASES = ROOT / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
REG = AW / "PILOT-01/registers/source_code_resolution_v3.csv"
INDEX = WSD / "plaintext_citation_index.csv"
# instrument token (as it appears in plain text) -> crawler doc_id. Query-normalisation mapping only.
DOC_FOR = [(re.compile(r"^(AFT Act|AFT)$"), "act-armed-forces-tribunal-2007"),
           (re.compile(r"^(Army Act|AA)$"), "act-army-1950"),
           (re.compile(r"^(Army Rules?|AR)$"), "rules-army-rules-1954"),
           (re.compile(r"^BNSS$"), "act-bnss-2023"), (re.compile(r"^BNS$"), "act-bns-2023"),
           (re.compile(r"^(BSA|Bharatiya Sakshya Adhiniyam.*)$"), "act-bsa-2023")]
OFFICIAL_HOST = re.compile(r"^https://([a-z0-9.-]+\.)?(sci\.gov\.in|nic\.in|gov\.in)/", re.I)


def git(*args, inp=None):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True,
                          input=inp, text=True).stdout


def corpus(ref):
    if not ref:
        return None
    try:
        commit = git("rev-parse", ref).strip()
        names = git("ls-tree", "-r", "--name-only", ref, "data/meta", "data/sections").split()
    except (OSError, subprocess.CalledProcessError):
        return None
    meta = {Path(n).stem for n in names if n.startswith("data/meta/") and n.endswith(".json")}
    sections = collections.defaultdict(set)
    for n in names:
        if n.startswith("data/sections/") and n.endswith(".json"):
            _, _, doc, f = n.split("/", 3)
            sections[doc].add(Path(f).stem)
    sc = sorted(n for n in names if n.startswith("data/meta/sc-"))
    urls = {}
    if sc:
        out = subprocess.run(["git", "-C", str(ROOT), "cat-file", "--batch"], check=True, capture_output=True,
                             input="".join(f"{ref}:{n}\n" for n in sc).encode()).stdout
        pos = 0
        for n in sc:
            hdr_end = out.index(b"\n", pos)
            hdr = out[pos:hdr_end].split()
            if len(hdr) < 3:  # "<name> missing"
                pos = hdr_end + 1
                continue
            size = int(hdr[2])
            body = out[hdr_end + 1: hdr_end + 1 + size]  # sizes are in bytes
            pos = hdr_end + 1 + size + 1
            try:
                m = json.loads(body.decode("utf-8"))
            except ValueError:
                continue
            for u in [m.get("source_url")] + list(m.get("source_aliases") or []):
                if u:
                    urls[u.strip()] = m.get("doc_id")
    return {"ref": ref, "commit": commit, "meta": meta, "sections": sections, "sc_urls": urls}


def section_status(ref, doc, sec):
    try:
        return json.loads(git("show", f"{ref}:data/sections/{doc}/{sec}.json")).get("status")
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def cited_numbers(text):
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", text)
    out = []
    for a, b in re.findall(r"(\d+[A-Za-z]?)(?:\s*[–-]\s*(\d+[A-Za-z]?))?", t):
        if b and a.isdigit() and b.isdigit() and 0 < int(b) - int(a) <= 60:
            out += [str(i) for i in range(int(a), int(b) + 1)]
        else:
            out += [a] + ([b] if b and b[0].isdigit() else [])
    return out


def pct(n, d):
    return {"numerator": n, "denominator": d, "pct": round(100 * n / d, 1) if d else None}


def build(ref):
    C = corpus(ref)
    spec = importlib.util.spec_from_file_location("bci", AW / "PILOT-01/build_code_inventory.py")
    bci = importlib.util.module_from_spec(spec); spec.loader.exec_module(bci)
    inv, uncoded, _ = bci.inventory()
    reg = {r["code"]: r for r in csv.DictReader(io.StringIO(REG.read_text(encoding="utf-8"), newline=""))}
    cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    case_ids = {c["id"] for c in cases}
    case_re = re.compile(r"\bDCLR-[A-Z]+-\d{4}-[A-Z]?\d+\b")
    doc_re = re.compile(r"^((?:act|rules|regs?)-[a-z0-9-]+)")
    out = {"artifact": "WS-D coverage scorecard", "definition": __doc__.strip().split("\n\n")[1],
           "inputs": {"kb_sha256": hashlib.sha256(KB.read_bytes()).hexdigest(),
                      "cases_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(),
                      "register_sha256": hashlib.sha256(REG.read_bytes()).hexdigest(),
                      "plaintext_index_sha256": hashlib.sha256(INDEX.read_bytes()).hexdigest(),
                      "corpus_ref": ref if C else None, "corpus_commit": C["commit"] if C else None}}
    # (A) codes
    code_state = {}
    for c in inv:
        t = (reg[c].get("corpus_target_or_gap") or "").strip()
        m = case_re.search(t)
        if m and not t.upper().startswith("GAP"):
            code_state[c] = "IN_CASES_53" if m.group(0) in case_ids else "CASE_TARGET_MISSING"
        elif doc_re.match(t):
            d = doc_re.match(t).group(1)
            code_state[c] = "NOT_CHECKED" if C is None else ("IN_CRAWLER_CORPUS" if d in C["meta"] else "DOC_TARGET_MISSING")
        else:
            code_state[c] = "GAP_OR_NON_LEGAL"
    cs = collections.Counter(code_state.values())
    searchable = {"IN_CASES_53", "IN_CRAWLER_CORPUS"}
    n = len(inv)
    out["codes"] = {"denominator_codes": n, "by_state": dict(sorted(cs.items())),
                    "searchable": pct(sum(cs[k] for k in searchable), n),
                    "official_copy_identified_url_and_sha": pct(sum(1 for c in inv if reg[c]["official_sha256"].strip()
                                                                     and reg[c]["official_corroboration_url"].strip()), n),
                    "gap_codes": sorted(c for c, s in code_state.items() if s == "GAP_OR_NON_LEGAL")}
    L = sum(len(v) for v in inv.values())
    out["record_code_links"] = {"denominator_links": L,
                                "searchable": pct(sum(len(v) for c, v in inv.items() if code_state[c] in searchable), L)}
    rec_codes = collections.defaultdict(set)
    for c, recs in inv.items():
        for r in recs:
            rec_codes[r].add(c)
    allc = sum(1 for cs_ in rec_codes.values() if all(code_state[c] in searchable for c in cs_))
    anyc = sum(1 for cs_ in rec_codes.values() if any(code_state[c] in searchable for c in cs_))
    out["coded_records"] = {"denominator_records": len(rec_codes), "all_codes_searchable": pct(allc, len(rec_codes)),
                            "at_least_one_code_searchable": pct(anyc, len(rec_codes))}
    # (B) plain-text records
    rows = list(csv.DictReader(io.StringIO(INDEX.read_text(encoding="utf-8"), newline="")))
    by_rec = collections.defaultdict(list)
    for r in rows:
        by_rec[r["record_id"]].append(r)
    seg_cat = collections.Counter(r["category"] for r in rows)
    sect_total = sect_found = 0; sect_missing = []; non_current = collections.defaultdict(set)
    instr_seg = instr_found = 0; rec_inst = {}
    for rid, segs in sorted(by_rec.items()):
        bykey = {s["seg_no"]: s for s in segs}
        states = []
        for s in segs:
            cat = s["category"]
            src = bykey.get(s["context_from_seg"]) if cat == "LOCATOR_CONTINUATION" else s
            if cat not in ("STATUTE_LOCATOR", "STATUTE_GENERIC") and not (cat == "LOCATOR_CONTINUATION" and src):
                continue
            toks = (src or {}).get("instruments_mentioned", "").split("|")
            doc = next((d for rx, d in DOC_FOR for t in toks[:1] if rx.match(t)), None)
            instr_seg += 1
            if doc is None or C is None:
                states.append(False if doc is None else None)
                continue
            ok = doc in C["meta"]; instr_found += ok; states.append(ok)
            if cat != "STATUTE_GENERIC" and doc.startswith("act-") and C["sections"].get(doc):
                text = s["exact_text"]
                if src is s and toks[0]:
                    text = text.split(toks[0], 1)[-1]
                for num in cited_numbers(text):
                    sect_total += 1
                    key = "s" + num.lower()
                    if key in C["sections"][doc]:
                        sect_found += 1
                        st = section_status(ref, doc, key)
                        if st not in (None, "in_force"):
                            non_current[f"{doc}#{key} ({st})"].add(rid)
                    else:
                        sect_missing.append(f"{rid}: {doc}#{key}")
        rec_inst[rid] = states
    with_statute = [r for r, st in rec_inst.items() if st]
    out["plaintext_records"] = {
        "denominator_records": len(by_rec), "segments": len(rows), "segments_by_category": dict(sorted(seg_cat.items())),
        "records_with_statute_reference": pct(len(with_statute), len(by_rec)),
        "records_without_any_statute_or_case_reference": sorted(r for r, segs in by_rec.items()
                                                               if not any(s["category"] in ("STATUTE_LOCATOR", "STATUTE_GENERIC", "CASE_REFERENCE", "LOCATOR_CONTINUATION") for s in segs)),
        "statute_segments_instrument_searchable": "NOT_CHECKED" if C is None else pct(instr_found, instr_seg),
        "records_all_statute_instruments_searchable": "NOT_CHECKED" if C is None else pct(sum(1 for r in with_statute if all(rec_inst[r])), len(with_statute)),
        "cited_act_sections_present_in_corpus": "NOT_CHECKED" if C is None else pct(sect_found, sect_total),
        "cited_act_sections_missing": sect_missing,
        "army_rules_rule_level": "NOT_CHECKED: crawler corpus has no section files for rules-army-rules-1954",
        "case_reference_segments": seg_cat["CASE_REFERENCE"],
        "case_reference_resolution": "NOT_CHECKED: plain-text case names are leads (WS-B owns identity resolution)",
        "cited_sections_with_non_current_corpus_status": {k: sorted(v) for k, v in sorted(non_current.items())},
    }
    # (C) cases
    off = sum(1 for c in cases if OFFICIAL_HOST.match(c.get("primary_source_url") or ""))
    sha = sum(1 for c in cases if re.fullmatch(r"[0-9a-f]{64}", c.get("original_pdf_sha256") or ""))
    arch = sum(1 for c in cases if c.get("original_pdf_archived") is True)
    matched = []
    if C:
        for c in cases:
            for u in (c.get("primary_source_url"), c.get("accessible_source_url")):
                if u and u.strip() in C["sc_urls"]:
                    matched.append(f"{c['id']} -> {C['sc_urls'][u.strip()]}"); break
    out["cases"] = {"denominator_cases": len(cases),
                    "official_host_primary_url": pct(off, len(cases)),
                    "original_pdf_sha256_recorded": pct(sha, len(cases)),
                    "original_pdf_archived_flag": pct(arch, len(cases)),
                    "same_url_in_crawler_corpus": "NOT_CHECKED" if C is None else pct(len(matched), len(cases)),
                    "matched": matched,
                    "by_record_type": dict(sorted(collections.Counter(c.get("record_type") for c in cases).items()))}
    out["kb_overall"] = {"denominator_records": 658, "coded": len(rec_codes), "plaintext_only": len(by_rec),
                         "coded_all_searchable_over_658": pct(allc, 658),
                         "plaintext_all_statute_instruments_searchable_over_658": "NOT_CHECKED" if C is None else pct(sum(1 for r in with_statute if all(rec_inst[r])), 658)}
    return out


def render(o):
    def f(x):
        return x if isinstance(x, str) else f"{x['numerator']}/{x['denominator']} ({x['pct']}%)"
    c, l, cr, p, k, kb = o["codes"], o["record_code_links"], o["coded_records"], o["plaintext_records"], o["cases"], o["kb_overall"]
    nc = p["cited_sections_with_non_current_corpus_status"]
    return f"""# Coverage scorecard (source-searchable, explicit denominators)

Generated by `scripts/coverage_scorecard.py`. Corpus ref `{o['inputs']['corpus_ref']}` @ `{(o['inputs']['corpus_commit'] or 'n/a')[:12]}` (read locally with git; no network).

**Searchable is not verified.** A searchable source exists as a document the database can search. It does not show that the text was checked, that the version fits the record's date, or that the record is legally correct.

## Citation codes (denominator = {c['denominator_codes']} codes)
| Measure | Value |
| --- | --- |
| Target searchable (cases_53 or crawler corpus) | {f(c['searchable'])} |
| By state | {', '.join(f'{a}: {b}' for a, b in c['by_state'].items())} |
| Official copy identified (URL + SHA-256 in register) | {f(c['official_copy_identified_url_and_sha'])} |
| Record-code links with searchable target (denominator = {l['denominator_links']}) | {f(l['searchable'])} |
| Coded records with every code searchable (denominator = {cr['denominator_records']}) | {f(cr['all_codes_searchable'])} |
| Coded records with at least one searchable code | {f(cr['at_least_one_code_searchable'])} |

Gap / non-legal codes: {', '.join(c['gap_codes'])}.

## Plain-text records (denominator = {p['denominator_records']} records, {p['segments']} segments)
| Measure | Value |
| --- | --- |
| Records with a statute reference | {f(p['records_with_statute_reference'])} |
| Statute segments whose instrument is in the crawler corpus | {f(p['statute_segments_instrument_searchable'])} |
| Records whose every statute instrument is in the corpus | {f(p['records_all_statute_instruments_searchable'])} |
| Cited Act sections present as corpus section files | {f(p['cited_act_sections_present_in_corpus'])} |
| Army Rules rule-level | {p['army_rules_rule_level']} |
| Plain-text case references ({p['case_reference_segments']} segments) | {p['case_reference_resolution']} |

Records with no statute or case reference at all ({len(p['records_without_any_statute_or_case_reference'])}): {', '.join(p['records_without_any_statute_or_case_reference'])}.

Cited Act sections not found as corpus section files ({len(p['cited_act_sections_missing'])}): {', '.join(p['cited_act_sections_missing']) or 'none'}.

Cited sections the corpus marks non-current (lead only; a record may discuss an omitted provision deliberately): {'; '.join(f'{a}: {", ".join(b)}' for a, b in nc.items()) or 'none'}.

## Cases (denominator = {k['denominator_cases']})
| Measure | Value |
| --- | --- |
| Primary URL on an official host | {f(k['official_host_primary_url'])} |
| Original PDF SHA-256 recorded | {f(k['original_pdf_sha256_recorded'])} |
| original_pdf_archived = true | {f(k['original_pdf_archived_flag'])} |
| Same URL present in crawler corpus (sc-* meta) | {f(k['same_url_in_crawler_corpus'])} |
| By record type | {', '.join(f'{a}: {b}' for a, b in k['by_record_type'].items())} |

## Whole KB (denominator = 658)
| Measure | Value |
| --- | --- |
| Coded records with every code searchable | {f(kb['coded_all_searchable_over_658'])} |
| Plain-text records with every statute instrument searchable | {f(kb['plaintext_all_statute_instruments_searchable_over_658'])} |
"""


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--corpus-ref", default="origin/raw-data"); ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    o = build(a.corpus_ref)
    if not a.no_write:
        (WSD / "coverage_scorecard.json").write_text(json.dumps(o, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (WSD / "coverage_scorecard.md").write_text(render(o), encoding="utf-8")
    print(render(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
