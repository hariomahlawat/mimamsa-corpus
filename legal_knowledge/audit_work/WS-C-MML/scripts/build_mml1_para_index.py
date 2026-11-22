#!/usr/bin/env python3
"""MML 1.doc (Part I commentary) paragraph index: chapter / para / derived line -> Army Act sections and Army Rules
cited in that paragraph. Stdlib only. Input: PILOT-01 derived lines file (private scratchpad, repro1/MML 1.lines.txt,
sha d56c9849...). Output keeps only locators, a heading of <= 60 characters, and provision numbers.
Usage: python3 build_mml1_para_index.py <scratchpad> <out_csv>"""
import csv, re, sys
from pathlib import Path

SP = Path(sys.argv[1]); OUT = Path(sys.argv[2])
NUM = r"\d{1,3}[A-Z]?(?:\s*\(\s*[0-9a-z]{1,4}\s*\))*"
LIST = rf"{NUM}(?:\s*(?:,|and|to|&|-|–)\s*{NUM})*"
AA = re.compile(rf"\bAA\s*\.?\s*ss?\s*\.?\s*({LIST})")
AR = re.compile(rf"\bA\.?Rs?\s*\.?\s*(?:rr?\.?\s*)?({LIST})")


def expand(lst):
    out = []
    toks = re.split(r"\s*(,|and|&)\s*", lst)
    for t in toks:
        if t in (",", "and", "&") or not t.strip():
            continue
        m = re.match(rf"\s*(\d{{1,3}})([A-Z]?)(?:\s*\(.*?\))*\s*(?:to|-|–)\s*(\d{{1,3}})", t)
        if m and int(m.group(3)) > int(m.group(1)) and int(m.group(3)) - int(m.group(1)) <= 30:
            out += [str(i) for i in range(int(m.group(1)), int(m.group(3)) + 1)]
        else:
            m = re.match(r"\s*(\d{1,3}[A-Z]?)", t)
            if m:
                out.append(m.group(1))
    return out


def main():
    rows, chap, title, sub = [], "", "", ""
    lines = []
    for l in (SP / "repro1/MML 1.lines.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"L(\d{5})\| ?(.*)", l)
        if m:
            lines.append((int(m.group(1)), m.group(2).strip()))
    i = 0
    while i < len(lines):
        n, t = lines[i]
        mc = re.match(r"CHAPTER\s+([IVXL]+)\s*$", t)
        if mc:
            chap = mc.group(1); title = lines[i + 1][1][:60] if i + 1 < len(lines) else ""; sub = ""
        ms = re.match(r"\(([ivx]+)\)\s+(.{1,60})$", t)
        if ms:
            sub = ms.group(0)[:60]
        mp = re.match(r"(\d{1,3})\s*\.\s*(.*)", t)
        if mp and chap:
            head = re.split(r"\s*[—–-]{1,2}\s*|\.\s*[—–-]", mp.group(2), maxsplit=1)[0][:60]
            aa = sorted({x for g in AA.findall(t) for x in expand(g)}, key=lambda x: (int(re.match(r"\d+", x).group()), x))
            ar = sorted({x for g in AR.findall(t) for x in expand(g)}, key=lambda x: (int(re.match(r"\d+", x).group()), x))
            rows.append({"file": "MML 1.doc", "part": "I", "chapter": chap, "chapter_title": title, "sub_heading": sub,
                         "para": mp.group(1), "para_heading_short": head, "derived_line": "L%05d" % n,
                         "aa_sections_cited": ";".join("s." + x for x in aa), "ar_rules_cited": ";".join("r." + x for x in ar),
                         "evidence_level": "LOCATOR_TEXT_ONLY"})
        i += 1
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("paras", len(rows), "with AA", sum(1 for r in rows if r["aa_sections_cited"]), "with AR", sum(1 for r in rows if r["ar_rules_cited"]))


if __name__ == "__main__":
    main()
