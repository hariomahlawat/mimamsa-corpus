#!/usr/bin/env python3
"""WS-D deliverable 4: plain-text citation index for the KB records that carry NO citation code.

Read-only and deterministic. The record set is exactly the 'records_without_codes' list produced by
PILOT-01/build_code_inventory.py (269 at baseline). Each record's `references` field is split on ';'
into segments; every segment becomes one CSV row with its exact original text and its offsets.

Offsets: `ref_start`/`ref_end` are Python str (Unicode code point) offsets into the decoded JSON
string value of the record's `references` field, so references[ref_start:ref_end] == exact_text.
`body_start` is the code point offset of the same exact_text inside `body` when the whole references
string is embedded verbatim in the body (else empty). `references_sha256` is SHA-256 of the UTF-8
references value, so any reader can confirm they are slicing the same text.

`category` is a mechanical label, not a legal identification:
  STATUTE_LOCATOR       instrument token plus a section/rule/article/para locator
  STATUTE_GENERIC       instrument token without a precise locator ("AR trial rules")
  CASE_REFERENCE        neutral citation, "X v Y", a capitalised name with year/paras, or a case-number judgment
  LOCATOR_CONTINUATION  a bare locator continuing the previous segment ("§122", "r22", "paras 6-15");
                        `context_from_seg` names the segment whose instrument/case it most likely continues
  PLACEHOLDER           a pure uncertainty marker ("verify controlling law")
  INTERNAL_CROSS_REF    pointer to another KB record/module ("Workflow PEN-WF-02", "See linked ...")
  POLICY_GENERIC        unspecified policy/practice/law/provisions ("applicable policy", "service pension rules")
  NON_CITATION_LABEL    editorial label that cites nothing ("Drafting aid", "Original form only")
  UNCLASSIFIED          none of the above (should be reviewed)
`placeholder_flags` lists literal uncertainty markers found in the segment ([VERIFY], 'verify', 'missing'),
plus UNANCHORED_LOCATOR when a pinpoint has no instrument or case anywhere earlier in the references field.
`abbrev_hint` is a query-normalisation expansion only (cf. abbreviation lexicon v1.0); it is NOT legal
authority and does not establish which instrument or edition is meant.
"""
import csv, hashlib, importlib.util, io, json, re, sys
from pathlib import Path

WSD = Path(__file__).resolve().parents[1]
ROOT = WSD.parents[2]
spec = importlib.util.spec_from_file_location("bci", ROOT / "legal_knowledge/audit_work/PILOT-01/build_code_inventory.py")
BCI = importlib.util.module_from_spec(spec); spec.loader.exec_module(BCI)

# Ordered: longest/most specific first. Value = hint (not authority).
INSTRUMENTS = [
    (r"Bharatiya Sakshya Adhiniyam(?: 2023)?", "Bharatiya Sakshya Adhiniyam 2023"),
    (r"AFT Act|AFT(?= §)", "Armed Forces Tribunal Act 2007"),
    (r"Army Act|AA(?![A-Za-z])", "Army Act 1950"),
    (r"Army Rules?|AR(?![A-Za-z_])", "Army Rules 1954"),
    (r"BNSS", "Bharatiya Nagarik Suraksha Sanhita 2023"),
    (r"BNS(?!S)", "Bharatiya Nyaya Sanhita 2023"),
    (r"BSA", "Bharatiya Sakshya Adhiniyam 2023"),
    (r"POCSO", "Protection of Children from Sexual Offences Act 2012"),
    (r"Constitution", "Constitution of India"),
    (r"Procedure Rules?", "AMBIGUOUS: '(Procedure) Rules' not named; likely AFT (Procedure) Rules 2008 - unverified"),
    (r"(?:19|20)\d\d Rules?", "AMBIGUOUS: rules identified only by year - unverified"),
]
INSTR_RE = [(re.compile(p), h) for p, h in INSTRUMENTS]
LOCATOR = re.compile(r"(§§?\s*\d|\bss?\s*\d|\bs\d|\brr?\s*\d|\bRules?\s+\d|\bArt\.?\s*\d|\bparas?\s+\d|¶¶?\s*\d|\b(?:BNSS|BNS|BSA)\s+\d)")
CASE = [re.compile(p) for p in (r"\b(?:19|20)\d\d INSC \d+", r"\b[A-Z][\w.' ]+ v [A-Z][\w.' ]+",
                                 r"^[A-Z][A-Za-z.' ]+\(?\b(?:19|20)\d\d\)?", r"^[A-Z][A-Za-z.' ]+ (?:¶|paras?\b)",
                                 r"^(?:MA|OA|WP|CA|TA) \d+/\d{4} judgment")]
# Names that occur bare in the KB (no year/paras). Kept explicit so classification is reviewable.
BARE_CASE_NAMES = {"Prithi Pal Singh Bedi", "Randhir Singh", "Vishav Priya Singh"}
NON_CITATION = re.compile(r"^(Drafting aid|Original form only|Source-based original format|Research procedural checklist|EDITORIAL DESIGN|Command audit practice)$")
CROSS = re.compile(r"^(Workflow [A-Z]+-[A-Z]+-\d+|See linked .+)$")
POLICY = re.compile(r"\b(policy|policies|practice|permissions|Registry direction|investigative procedure|review|law|provisions|instructions|rules)\b", re.I)
PLACEHOLDER = re.compile(r"^verify\b", re.I)
FLAGS = [("VERIFY_TAG", re.compile(r"\[VERIFY\]")), ("VERIFY_WORD", re.compile(r"(?<!\[)\bverify\b", re.I)),
         ("MISSING", re.compile(r"\bmissing\b", re.I)), ("OMITTED_NOTE", re.compile(r"\bomitted\b", re.I)),
         ("HISTORIC_NOTE", re.compile(r"\bhistoric\b|\(\d{4} text\)", re.I))]
COLUMNS = ["record_id", "jsonl_line", "line_sha256", "module", "references_sha256", "seg_no", "ref_start", "ref_end",
           "body_start", "exact_text", "category", "instruments_mentioned", "abbrev_hint", "has_locator",
           "context_from_seg", "placeholder_flags"]


def classify(seg):
    instr = []
    for rx, hint in INSTR_RE:
        for m in rx.finditer(seg):
            if not any(m.start() < e and s < m.end() for s, e, _, _ in instr):
                instr.append((m.start(), m.end(), m.group(0), hint))
    instr.sort()
    has_loc = bool(LOCATOR.search(seg))
    leads_with_instrument = bool(instr) and instr[0][0] == 0 and " v " not in seg and "INSC" not in seg
    if NON_CITATION.match(seg):
        cat = "NON_CITATION_LABEL"
    elif PLACEHOLDER.match(seg):
        cat = "PLACEHOLDER"
    elif CROSS.match(seg):
        cat = "INTERNAL_CROSS_REF"
    elif leads_with_instrument:
        cat = "STATUTE_LOCATOR" if has_loc else "STATUTE_GENERIC"
    elif not instr and has_loc and not any(c.search(seg) for c in CASE):
        cat = "LOCATOR_CONTINUATION"
    elif any(c.search(seg) for c in CASE) or any(seg.startswith(n) for n in BARE_CASE_NAMES):
        cat = "CASE_REFERENCE"
    elif instr and has_loc:
        cat = "STATUTE_LOCATOR"
    elif POLICY.search(seg):
        cat = "POLICY_GENERIC"
    elif instr:
        cat = "STATUTE_GENERIC"
    else:
        cat = "UNCLASSIFIED"
    flags = [n for n, rx in FLAGS if rx.search(seg)]
    return cat, instr, has_loc, flags


def build():
    inv, uncoded, ph = BCI.inventory()
    want = set(uncoded)
    raw = BCI.KB.read_bytes()
    rows = []
    lines = [l for l in raw.split(b"\n") if l.strip()]
    for n, l in enumerate(lines, 1):
        r = json.loads(l)
        if r["id"] not in want:
            continue
        ref = r["references"] if isinstance(r["references"], str) else str(r["references"])
        body = r.get("body") or ""
        embedded = body.find(ref) if ref else -1
        pos = 0
        last_ctx = ""
        for k, part in enumerate(ref.split(";"), 1):
            lead = len(part) - len(part.lstrip())
            seg = part.strip()
            s = pos + lead; e = s + len(seg)
            pos += len(part) + 1
            if not seg:
                continue
            assert ref[s:e] == seg
            cat, instr, has_loc, flags = classify(seg)
            ctx = last_ctx if cat == "LOCATOR_CONTINUATION" else ""
            if cat == "LOCATOR_CONTINUATION" and not ctx:
                flags = flags + ["UNANCHORED_LOCATOR"]  # pinpoint with no instrument/case in the references field
            if cat in ("STATUTE_LOCATOR", "STATUTE_GENERIC", "CASE_REFERENCE"):
                last_ctx = str(k)
            rows.append({"record_id": r["id"], "jsonl_line": n, "line_sha256": hashlib.sha256(l).hexdigest(),
                         "module": r.get("module", ""), "references_sha256": hashlib.sha256(ref.encode("utf-8")).hexdigest(),
                         "seg_no": k, "ref_start": s, "ref_end": e,
                         "body_start": (embedded + s) if embedded >= 0 else "", "exact_text": seg, "category": cat,
                         "instruments_mentioned": "|".join(x[2] for x in instr),
                         "abbrev_hint": "|".join(dict.fromkeys(x[3] for x in instr)),
                         "has_locator": has_loc, "context_from_seg": ctx, "placeholder_flags": "|".join(flags)})
    return rows, uncoded


def main():
    rows, uncoded = build()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    out = WSD / "plaintext_citation_index.csv"
    out.write_text(buf.getvalue(), encoding="utf-8")
    from collections import Counter
    c = Counter(r["category"] for r in rows)
    print(json.dumps({"records": len({r['record_id'] for r in rows}), "expected_records": len(uncoded),
                      "segments": len(rows), "by_category": dict(sorted(c.items())),
                      "records_with_placeholder_flag": len({r['record_id'] for r in rows if r['placeholder_flags']}),
                      "csv_sha256": hashlib.sha256(buf.getvalue().encode()).hexdigest()}, indent=2))
    return 0 if len({r['record_id'] for r in rows}) == len(uncoded) else 1


if __name__ == "__main__":
    sys.exit(main())
