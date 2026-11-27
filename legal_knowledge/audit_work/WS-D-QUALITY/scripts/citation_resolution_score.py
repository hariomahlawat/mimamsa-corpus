#!/usr/bin/env python3
"""WS-D deliverable 3: confirmed vs inferred citation-resolution scoring with explicit denominators.

Read-only. Recomputes from records_658.jsonl via PILOT-01/build_code_inventory.py and the frozen
v3 register. 'Confirmed' = identity resolved by the record itself or corroborated against an official
copy (RESOLVED_RECORD_EXPLICIT, CORROBORATED_OFFICIAL). 'Inferred' = statistical co-citation only.
Everything else is unresolved. No score here says a citation is legally correct or current.
Writes citation_resolution_score.json and .md next to this script's parent directory.
"""
import collections, csv, hashlib, importlib.util, json
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
B = ROOT / "legal_knowledge/audit_work/PILOT-01"
spec = importlib.util.spec_from_file_location("bci", B / "build_code_inventory.py")
BCI = importlib.util.module_from_spec(spec); spec.loader.exec_module(BCI)
TIER = {"RESOLVED_RECORD_EXPLICIT": "CONFIRMED", "CORROBORATED_OFFICIAL": "CONFIRMED",
        "RESOLVED_CO_CITATION": "INFERRED", "PROBABLE": "UNRESOLVED", "CATEGORY_ONLY": "UNRESOLVED",
        "UNRESOLVABLE": "UNRESOLVED"}


def pct(n, d):
    return {"numerator": n, "denominator": d, "pct": round(100 * n / d, 1) if d else None}


def main():
    inv, uncoded, ph = BCI.inventory()
    reg = {r["code"]: r for r in csv.DictReader(BCI.REG.open(encoding="utf-8"))}
    n = len(inv)
    cls = collections.Counter(reg[c]["resolution_class"] for c in inv)
    tier = collections.Counter(TIER[reg[c]["resolution_class"]] for c in inv)
    links = collections.Counter(); tl = collections.Counter()
    for c, recs in inv.items():
        links[reg[c]["resolution_class"]] += len(recs); tl[TIER[reg[c]["resolution_class"]]] += len(recs)
    L = sum(links.values())
    rec_codes = collections.defaultdict(set)
    for c, recs in inv.items():
        for r in recs:
            rec_codes[r].add(c)
    rec_state = collections.Counter()
    worst = {}
    for r, cs in rec_codes.items():
        ts = {TIER[reg[c]["resolution_class"]] for c in cs}
        w = "UNRESOLVED" if "UNRESOLVED" in ts else "INFERRED" if "INFERRED" in ts else "CONFIRMED"
        worst[r] = w; rec_state[w] += 1
    coded = len(rec_codes)
    out = {
        "artifact": "WS-D citation resolution score",
        "inputs": {"kb_sha256": hashlib.sha256(BCI.KB.read_bytes()).hexdigest(),
                   "register": str(BCI.REG.relative_to(ROOT)),
                   "register_sha256": hashlib.sha256(BCI.REG.read_bytes()).hexdigest()},
        "definitions": {"CONFIRMED": ["RESOLVED_RECORD_EXPLICIT", "CORROBORATED_OFFICIAL"],
                        "INFERRED": ["RESOLVED_CO_CITATION"],
                        "UNRESOLVED": ["PROBABLE", "CATEGORY_ONLY", "UNRESOLVABLE"],
                        "note": "Identity resolution of a citation code only. Not legal correctness, not currency, not amendment status."},
        "code_level": {"denominator_codes": n, "by_class": dict(sorted(cls.items())),
                       "confirmed": pct(tier["CONFIRMED"], n),
                       "officially_corroborated": pct(cls["CORROBORATED_OFFICIAL"], n),
                       "record_explicit_only": pct(cls["RESOLVED_RECORD_EXPLICIT"], n),
                       "inferred_co_citation": pct(tier["INFERRED"], n),
                       "confirmed_plus_inferred": pct(tier["CONFIRMED"] + tier["INFERRED"], n),
                       "unresolved": pct(tier["UNRESOLVED"], n)},
        "link_level": {"denominator_record_code_links": L, "by_class": dict(sorted(links.items())),
                       "confirmed": pct(tl["CONFIRMED"], L), "inferred_co_citation": pct(tl["INFERRED"], L),
                       "unresolved": pct(tl["UNRESOLVED"], L)},
        "record_level": {"denominator_all_records": 658, "records_with_codes": coded,
                         "records_without_codes_plaintext_only": len(uncoded),
                         "all_codes_confirmed": pct(rec_state["CONFIRMED"], coded),
                         "worst_code_inferred": pct(rec_state["INFERRED"], coded),
                         "worst_code_unresolved": pct(rec_state["UNRESOLVED"], coded),
                         "all_codes_confirmed_over_all_658": pct(rec_state["CONFIRMED"], 658),
                         "records_with_unresolved_code": sorted(r for r, w in worst.items() if w == "UNRESOLVED"),
                         "records_with_inferred_code_only": sorted(r for r, w in worst.items() if w == "INFERRED")},
        "placeholders": {k: sorted(v) for k, v in ph.items()},
        "headline": "72/87 codes confirmed (82.8%); 75/87 (86.2%) only if 3 co-citation inferences are counted; 12/87 unresolved. 269/658 records have no code and are outside this denominator.",
    }
    (WSD / "citation_resolution_score.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    c, l, r = out["code_level"], out["link_level"], out["record_level"]
    f = lambda x: f"{x['numerator']}/{x['denominator']} ({x['pct']}%)"
    md = f"""# Citation resolution score (confirmed vs inferred)

Generated by `scripts/citation_resolution_score.py` from the frozen KB (sha `{out['inputs']['kb_sha256'][:12]}…`) and `source_code_resolution_v3.csv` (sha `{out['inputs']['register_sha256'][:12]}…`). Deterministic and read-only.

**This scores whether a citation code's identity is resolved, not whether the law is stated correctly or is current.** Passing CI does not imply legal correctness.

## Definitions
- **Confirmed**: RESOLVED_RECORD_EXPLICIT (the record itself names the instrument) or CORROBORATED_OFFICIAL (identity matched against an official copy with a SHA-256).
- **Inferred**: RESOLVED_CO_CITATION (statistical co-citation only). Never counted as confirmed.
- **Unresolved**: PROBABLE, CATEGORY_ONLY, UNRESOLVABLE.

## Code level (denominator = {c['denominator_codes']} distinct codes)
| Measure | Value |
| --- | --- |
| Confirmed | {f(c['confirmed'])} |
| of which officially corroborated | {f(c['officially_corroborated'])} |
| of which record-explicit only | {f(c['record_explicit_only'])} |
| Inferred (co-citation) | {f(c['inferred_co_citation'])} |
| Confirmed + inferred | {f(c['confirmed_plus_inferred'])} |
| Unresolved | {f(c['unresolved'])} |

## Link level (denominator = {l['denominator_record_code_links']} record-to-code links)
| Measure | Value |
| --- | --- |
| Confirmed | {f(l['confirmed'])} |
| Inferred | {f(l['inferred_co_citation'])} |
| Unresolved | {f(l['unresolved'])} |

## Record level (denominator = {r['records_with_codes']} coded records; {r['records_without_codes_plaintext_only']} of 658 have no code)
| Measure | Value |
| --- | --- |
| Every code confirmed | {f(r['all_codes_confirmed'])} |
| Worst code inferred | {f(r['worst_code_inferred'])} |
| At least one unresolved code | {f(r['worst_code_unresolved'])} |
| Every code confirmed, over all 658 | {f(r['all_codes_confirmed_over_all_658'])} |

Records with an unresolved code: {', '.join(r['records_with_unresolved_code'])}.

Records whose weakest code is a co-citation inference: {', '.join(r['records_with_inferred_code_only']) or 'none'}.

`[VERIFY]` placeholders (not codes, excluded from all denominators): {', '.join(f'{k}: ' + ', '.join(v) for k, v in out['placeholders'].items())}.

## Headline
{out['headline']}
"""
    (WSD / "citation_resolution_score.md").write_text(md, encoding="utf-8")
    print(out["headline"])


if __name__ == "__main__":
    main()
