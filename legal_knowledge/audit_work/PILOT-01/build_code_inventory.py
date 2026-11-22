#!/usr/bin/env python3
"""Deterministic citation-code inventory over the frozen 658 records and coverage from the v3 register.
Read-only on originals. Fails (exit 1) if any code used in the records is missing from the register."""
import collections, csv, json, re, sys
from pathlib import Path

B = Path(__file__).resolve().parent
KB = B.parents[1] / "curated_originals" / "knowledge_base" / "v0.9" / "records_658.jsonl"
REG = B / "registers" / "source_code_resolution_v3.csv"
FIRM = {"CORROBORATED_OFFICIAL", "RESOLVED_RECORD_EXPLICIT"}


def inventory():
    inv, uncoded, placeholders = collections.defaultdict(set), [], collections.defaultdict(set)
    for line in KB.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line); ref = str(r["references"]); found = False
        codes = re.findall(r"'source_id': '([^']+)'", ref)
        for c in re.findall(r"\[([A-Z][A-Z0-9_\-]{1,20})(?=[\]:\s])", ref):
            (placeholders[c].add(r["id"]) if c == "VERIFY" else codes.append(c))
        codes += re.findall(r"\b(V\d-S\d+)\b", ref)
        m = re.match(r"\s*([A-Z][A-Z_]{2,})\s+(?:paras?|discussion|Judgment|judgment)", ref)
        if m:
            codes.append(m.group(1))
        codes += list(r.get("sources") or [])
        for c in codes:
            inv[c].add(r["id"]); found = True
        if not found:
            uncoded.append(r["id"])
    return inv, uncoded, placeholders


def main():
    inv, uncoded, ph = inventory()
    reg = {r["code"]: r for r in csv.DictReader(REG.open(encoding="utf-8"))}
    missing = sorted(set(inv) - set(reg)); extra = sorted(set(reg) - set(inv))
    cls = collections.Counter(reg[c]["resolution_class"] for c in inv if c in reg)
    n = len(inv); firm = sum(cls[k] for k in FIRM); inc = firm + cls["RESOLVED_CO_CITATION"]
    links = collections.Counter()
    for c, recs in inv.items():
        if c in reg:
            links[reg[c]["resolution_class"]] += len(recs)
    L = sum(links.values()); lf = sum(links[k] for k in FIRM)
    out = {"codes_used": n, "missing_from_register": missing, "register_codes_not_used": extra,
           "by_class": dict(cls), "firm_pct": round(100 * firm / n, 1), "inclusive_pct": round(100 * inc / n, 1),
           "usage_links": L, "usage_firm_pct": round(100 * lf / L, 1),
           "usage_inclusive_pct": round(100 * (lf + links["RESOLVED_CO_CITATION"]) / L, 1),
           "records_without_codes": len(uncoded), "placeholders": {k: sorted(v) for k, v in ph.items()}}
    print(json.dumps(out, indent=2))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
