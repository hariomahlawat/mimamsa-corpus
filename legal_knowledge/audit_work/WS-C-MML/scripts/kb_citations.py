#!/usr/bin/env python3
"""Deterministic citation parser for the frozen 658 KB records (stdlib only; read-only).
Parses the `references` field (and the `sources` list) only. It extracts:
  * citation codes (PILOT-01 v3 grammar: structured source_id, [CODE...], V#-S##, leading digest code, sources field);
  * Army Act sections and Army Rules cited in plain text or under AA/AR-type codes;
  * other statute mentions, case-citation patterns, internal KB-id links, placeholders.
No legal judgement is made; this is a source-coverage parser."""
import json, re

AA_CODES = {"AA", "SRC-AA", "V8-S01", "V9-S02"}
AR_CODES = {"AR", "SRC-AR", "SRC-AR184", "SRC-AR185", "SRC-AR186", "V8-S02", "V9-S03"}
OTHER_HINT = re.compile(r"\b(BSA|BNSS|BNS|IPC|CrPC|Cr\.?P\.?C|IEA|Evidence Act|AFT|Tribunal|Procedure Rules|Practice Rules|"
                        r"Constitution|Art\.?|Article|POCSO|ISO|Regs?|Regulations|Pension|GMO|Entitlement|Air Force|AFA|"
                        r"Navy|NA\b|Territorial|MV Act|Motor|UAPA|NDPS|Official Secrets|ER\b|V[67]-S\d+|V8-S0[3-9]|V8-S1\d|"
                        r"V9-S0[14-8]|V6-S\d+|SRC-AFT|SRC-ISO|SRC-ISOR|SRC-RA|SRC-AO|AO\b|Army Orders?|para)", re.I)
AA_HINT = re.compile(r"(\bAA\b|Army Act|SRC-AA\b|V8-S01\b|V9-S02\b)")
AR_HINT = re.compile(r"(\bAR\b|Army Rules?|SRC-AR\d*\b|V8-S02\b|V9-S03\b|\bAR_ALT\b)")
NUM = r"\d{1,3}(?:-?[A-Z](?![a-z]))?(?:\s*\(\s*[0-9a-zA-Z]{1,5}\s*\))*"
PAREN = r"\(\s*[0-9a-zA-Z]{1,5}\s*\)"
QUAL = r"(?:\s+(?:proviso|provisos|note|notes|explanation|exception|onwards|as applicable|et seq))?"
ITEM = rf"(?:{NUM}{QUAL}|{PAREN})"
SEC = re.compile(rf"(?:§§?|(?<![-\w])[sS]{{1,2}}(?:\b|(?=\d))\.?|\bsections?\b|\bSection\b)\s*({NUM}{QUAL}(?:\s*(?:,|and|&|–|-|to)\s*(?:s\s*)?{ITEM})*)", re.I)
RUL = re.compile(rf"(?:(?<![-\w])RR(?:\b|(?=\d))|(?<![-\w])rr?(?:\b|(?=\d))\.?|\brules?\b|\bRule\b|\bRules\b)\s*({NUM}{QUAL}(?:\s*(?:,|and|&|–|-|to)\s*(?:r\s*)?{ITEM})*)")
CASE = re.compile(r"(¶|\bv\.?\s+[A-Z]|\bvs\.?\s+[A-Z]|\bINSC\b|\bSCC\b|\bAIR\s+\d{4}|\bSCR\b|\bUOI\b|\bUnion of India\b|"
                  r"\b(?:OA|MA|CA|WP|TA|Crl\.?A|SLP)\s*(?:No\.?\s*)?\d+\s*/\s*\d{4}|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+\((?:19|20)\d\d\))")
STAT_OTHER = re.compile(r"\b(BSA|BNSS|BNS|IPC|CrPC|Evidence Act|AFT Act|AFT \(Procedure\) Rules|Procedure Rules|Practice Rules|"
                        r"Constitution|Art\.?\s*\d+|Article\s*\d+|POCSO|Pension Regulations|Regulations for the Army|Regs Army|"
                        r"Air Force Act|Navy Act|Territorial Army Act|Entitlement Rules|GMO|ISO Act)\b", re.I)
PLACEHOLDER = re.compile(r"(\[VERIFY\]|\bverify\b|\bTBD\b|\bexact rule verify\b)", re.I)
NONCIT = re.compile(r"^(EDITORIAL( DESIGN)?|Research procedural checklist|See linked module provisions|Source-based original format|"
                    r"Original form only.*|Workflow [A-Z0-9-]+)$", re.I)


_LEX = None


def lexicon():
    """case_name_lexicon.csv (short-title keys from cases_53 and WS-B identity_resolution)."""
    global _LEX
    if _LEX is None:
        import csv
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "case_name_lexicon.csv"
        _LEX = []
        if p.exists():
            for r in csv.DictReader(open(p, encoding="utf-8")):
                _LEX.append((re.compile(r"(?<![A-Za-z])" + re.escape(r["key"]).replace("\\ ", r"\s+") + r"(?![a-z])"), r))
    return _LEX


def case_names(ref):
    return [(r["key"], r["case53_id"] or r["spec_key"], r["kb_source_codes"]) for rx, r in lexicon() if rx.search(ref)]


def codes_v3(r):
    ref = str(r.get("references", ""))
    codes = re.findall(r"'source_id': '([^']+)'", ref)
    ph = []
    for c in re.findall(r"\[([A-Z][A-Z0-9_\-]{1,20})(?=[\]:\s])", ref):
        (ph.append(c) if c == "VERIFY" else codes.append(c))
    codes += re.findall(r"\b(V\d-S\d+)\b", ref)
    m = re.match(r"\s*([A-Z][A-Z_]{2,})\s+(?:paras?|discussion|Judgment|judgment)", ref)
    if m:
        codes.append(m.group(1))
    codes += list(r.get("sources") or [])
    seen, out = set(), []
    for c in codes:
        if c not in seen:
            seen.add(c); out.append(c)
    return out, ph


def _expand(lst):
    """Expand a list such as '23(1),(3),24', '15-A', '167–169A', '177-182, 22(1) proviso, 23'."""
    out = []
    lst = re.sub(r"\b(proviso|provisos|note|notes|explanation|exception|onwards|as applicable|et seq)\b", " ", lst)
    lst = re.sub(r"(\d)-([A-Z])(?![a-z])", r"\1\2", lst)          # 15-A -> 15A
    for t in re.split(r"\s*(?:,|and|&)\s*", lst):
        t = re.sub(r"^[sr]\s*", "", t.strip())
        if not t or t.startswith("("):
            continue                                            # bare sub-clause continuation, e.g. ',(3)'
        m = re.match(r"(\d{1,3})([A-Z]?)(?:\s*\(.*?\))*\s*(?:–|-|to)\s*(\d{1,3})([A-Z]?)", t)
        if m and 0 < int(m.group(3)) - int(m.group(1)) <= 40:
            out += [str(i) for i in range(int(m.group(1)), int(m.group(3)) + 1)]
            if m.group(2):
                out.append(m.group(1) + m.group(2))
            if m.group(4):
                out.append(m.group(3) + m.group(4))
            continue
        m = re.match(r"(\d{1,3}[A-Z]?)", t)
        if m:
            out.append(m.group(1))
    return out


def provisions(ref):
    """Return (aa_sections, ar_rules, other_numbered) from a references string by left-to-right context tracking."""
    aa, ar, other = [], [], 0
    segs = re.split(r"(?<=[;\]\|])|(?=\[)|(?=V\d-S\d+\|)", ref)
    carry = None
    for seg in segs:
        # instrument context = first hint in the segment, falling back to previous context
        tokens = []
        for m in AA_HINT.finditer(seg):
            tokens.append((m.start(), "AA"))
        for m in AR_HINT.finditer(seg):
            tokens.append((m.start(), "AR"))
        for m in OTHER_HINT.finditer(seg):
            if not AA_HINT.match(seg, m.start()) and not AR_HINT.match(seg, m.start()):
                tokens.append((m.start(), "OTHER"))
        tokens.sort()
        def ctx_at(pos):
            c = carry
            for p, k in tokens:
                if p <= pos:
                    c = k
            return c
        for m in SEC.finditer(seg):
            c = ctx_at(m.start())
            if c == "AA":
                aa += _expand(m.group(1))
            elif c == "AR":
                # 's' under an AR context is unusual: record as AA only if an AA hint exists earlier in segment
                other += 1
            else:
                other += 1
        for m in RUL.finditer(seg):
            c = ctx_at(m.start())
            if c in ("AA", "AR"):
                ar += _expand(m.group(1))
            else:
                other += 1
        if tokens:
            carry = tokens[-1][1]
        if seg.lstrip().startswith("[") or re.match(r"\s*V\d-S\d+\|", seg):
            pass
    key = lambda x: (int(re.match(r"\d+", x).group()), x)
    return sorted(set(aa), key=key), sorted(set(ar), key=key), other


def parse(r, known_ids=()):
    ref = str(r.get("references", ""))
    codes, ph = codes_v3(r)
    aa, ar, other_num = provisions(ref)
    internal = sorted({x for x in re.findall(r"\b([A-Z]{1,4}\d?(?:-[A-Z]{1,4})?-\d{1,3}|SC\d{2}|J-\d{2})\b", ref) if x in known_ids and x != r["id"]})
    return {"codes": codes, "placeholders": ph + (["verify-text"] if re.search(r"\bverify\b", ref, re.I) and "VERIFY" not in ph else []),
            "aa": aa, "ar": ar, "other_numbered": other_num,
            "stat_other": sorted({m.group(1).strip() for m in STAT_OTHER.finditer(ref)}),
            "case_pattern": bool(CASE.search(ref)) or bool(case_names(ref)), "case_names": case_names(ref), "internal_links": internal,
            "noncitation_text": bool(NONCIT.match(ref.strip())), "mml_mention": bool(re.search(r"\bMML\b|Manual of Military Law", ref + " " + str(r.get("body", "")), re.I)),
            "mml_in_refs": bool(re.search(r"\bMML\b|Manual of Military Law", ref, re.I))}


if __name__ == "__main__":
    import sys
    for l in open(sys.argv[1], encoding="utf-8"):
        r = json.loads(l); print(r["id"], parse(r))
