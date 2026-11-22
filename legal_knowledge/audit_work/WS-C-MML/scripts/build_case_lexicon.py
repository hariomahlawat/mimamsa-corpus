#!/usr/bin/env python3
"""Build case_name_lexicon.csv: short-title name keys for case-citation detection in the 658 KB references.
Sources (read-only): cases_53.jsonl (committed) and WS-B identity_resolution.csv (passed as a path; read from
origin/claude/ws-b-judgments). Keys = party names with ranks, honorifics, 'Union of India', 'and Others' etc. removed.
Stdlib; deterministic. Usage: python3 build_case_lexicon.py <ws-b identity_resolution.csv>"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; W = HERE.parent; ROOT = W.parents[2]
C53 = ROOT / "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
PREFIX = r"(?:Lt\.? Col|Lt Cdr|Col|Maj(?:or)? Gen(?:eral)?|Major|Brig|Capt|Wg Cdr|Wing Commander|Ex Sep|Ex Cfn|Ex Havildar|Ex Hav|Sgt|Nk|Hav|Sep|Dr|IC-\d+|Retd)\.?"
GENERIC = {"union of india", "state", "others", "another", "cbi", "secretary", "south indian bank", "state of punjab",
           "state of haryana", "state of himachal pradesh", "state of maharashtra", "state of sikkim", "ministry of defence",
           "cda", "controller of defence accounts", "army hq", "additional director general"}


def keys_from(title):
    t = re.sub(r"\(.*?\)", " ", title)
    t = re.split(r"\s+-\s+|,\s*(?:MA|W\.P|20\d\d|\(|SC|Delhi)", t)[0]
    out = []
    for side in re.split(r"\s+v\.?\s+|\s+/\s+", t):
        s = re.sub(r"\b(and (Others|Another)|and connected cases|etc\.?)\b", " ", side)
        s = re.sub(r"^(Secretary, Ministry of Defence|Controller of Defence Accounts|CDA)\b", " ", s.strip())
        prev = None
        while prev != s:
            prev = s; s = re.sub(rf"^\s*{PREFIX}\s+", "", s.strip())
        s = re.sub(r"\s+", " ", s).strip(" ,.")
        if not s or s.lower() in GENERIC or s.lower().startswith(("union of india", "state of", "state (")):
            continue
        if re.search(r"\d|^Unidentified", s):
            continue
        if len(s.split()) >= 2 or (len(s) >= 6 and s[0].isupper()):
            out.append(s)
    return out


def main():
    rows = {}
    for l in C53.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            for k in keys_from(r["title"]):
                rows.setdefault(k, {"key": k, "case53_id": r["id"], "spec_key": "", "kb_source_codes": "", "source": "cases_53"})
    for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
        for k in keys_from(r["ws_b_label"]) + keys_from(r.get("curated_title") or ""):
            e = rows.setdefault(k, {"key": k, "case53_id": r["case53_id"], "spec_key": r["spec_key"], "kb_source_codes": r["kb_source_codes"], "source": "ws-b identity_resolution"})
            e["spec_key"] = e["spec_key"] or r["spec_key"]; e["kb_source_codes"] = e["kb_source_codes"] or r["kb_source_codes"]
            e["case53_id"] = e["case53_id"] or r["case53_id"]
    out = sorted(rows.values(), key=lambda x: x["key"])
    with open(W / "case_name_lexicon.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["key", "case53_id", "spec_key", "kb_source_codes", "source"]); w.writeheader(); w.writerows(out)
    print(len(out), "keys")


if __name__ == "__main__":
    main()
