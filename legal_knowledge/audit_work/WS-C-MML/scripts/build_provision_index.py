#!/usr/bin/env python3
"""Locator index: Army Act section / Army Rule -> location in each MML file.
Inputs (private, scratchpad): MML originals (MML 2.pdf for bold-heading detection, needs pymupdf) and the
PILOT-01 derived text layer (repro1/*, hashes in PILOT-01/mml_derived_manifest.json).
Output: provision_index.csv with LOCATORS ONLY (no MML wording).
Method: (1) MML 2.pdf headings = lines whose first span is bold and starts '<n>[A]. '; strays dropped by
longest strictly increasing subsequence; gaps filled by regex on the text layer. (2) Other files: regex heading
candidates (number, title, dash) aligned to the MML 2 key order by longest common subsequence.
All locators are TEXT-LAYER derived (evidence level LOCATOR_TEXT_ONLY); they are not wording checks.
Usage: <venv-python> -I build_provision_index.py <scratchpad> <out_csv>"""
import csv, re, sys
from pathlib import Path

SP = Path(sys.argv[1]); OUT = Path(sys.argv[2])
R = SP / "repro1"; O = SP / "mml_x/originals"
HEAD = re.compile(r"^\s{0,20}[\[\(]?\s*(\d{1,3})\s*[-–]?\s*([A-Z]{1,2})?\s*(?:\.|(?<=[A-Z])\s)\s*\[?\s*([A-Z\(][^\n]{0,200})")
DASH = re.compile(r"(—|–|\.-|\. -|--|\.—)")


def key(n, s):
    return (int(n), s or "")


def lis(seq):
    """longest strictly increasing subsequence by key; seq items (key, loc)."""
    import bisect
    tails, idx, prev = [], [], [-1] * len(seq)
    for i, (k, _) in enumerate(seq):
        j = bisect.bisect_left([seq[t][0] for t in tails], k)
        if j == len(tails):
            tails.append(i)
        else:
            tails[j] = i
        prev[i] = tails[j - 1] if j else -1
    out, i = [], tails[-1] if tails else -1
    while i >= 0:
        out.append(seq[i]); i = prev[i]
    return out[::-1]


def lcs(cands, expected):
    """align candidate (key,loc) in doc order to expected key order; returns dict key->loc"""
    n, m = len(cands), len(expected)
    pos = {k: i for i, k in enumerate(expected)}
    # LIS over expected-index of candidates whose key is expected == LCS since expected keys unique
    seq = [((pos[k],), (k, loc)) for k, loc in cands if k in pos]
    best = lis([(a, b) for a, b in seq])
    return {b[0]: b[1] for _, b in best}


def pdf_pages(fn):
    t = (R / fn).read_text(encoding="utf-8")
    parts = re.split(r"=== PDF_PAGE (\d+) / file=[^\n]*===\n", t)
    for i in range(1, len(parts), 2):
        yield int(parts[i]), parts[i + 1]


def doc_lines(fn):
    for l in (R / fn).read_text(encoding="utf-8").splitlines():
        m = re.match(r"L(\d{5})\| ?(.*)", l)
        if m:
            yield int(m.group(1)), m.group(2)


def cands_from(items, lo=0, hi=10 ** 9, need_dash=True):
    out = []
    for loc, l in items:
        if not lo <= loc <= hi:
            continue
        m = HEAD.match(l)
        if not m:
            continue
        if need_dash and not DASH.search(l[:220]) and not re.search(r"omitted|repealed", l[:80], re.I):
            continue
        if re.search(r"(\.\s*){3,}\d+\s*$|\t\.\t", l):  # TOC dot leaders
            continue
        out.append((key(m.group(1), m.group(2)), loc))
    return out


def mml2_bold():
    import pymupdf
    d = pymupdf.open(O / "MML 2.pdf")
    pat = re.compile(r"^\s*\[?\s*(\d{1,3})\s*[-–]?\s*([A-Z]{1,2})?\s*(?:\.|(?<=[A-Z])\s)\s*")
    res = {"AA": [], "AR": []}
    for pno in range(d.page_count):
        p = pno + 1
        inst = "AA" if p <= 123 else ("AR" if p <= 229 else None)
        if not inst:
            continue
        for b in d[pno].get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                sp = [s for s in ln["spans"] if s["text"].strip()]
                if not sp:
                    continue
                m = pat.match("".join(s["text"] for s in sp))
                if m and ("Bold" in sp[0]["font"] or sp[0]["flags"] & 16):
                    res[inst].append((key(m.group(1), m.group(2)), p))
    return {k: dict(lis(v)) for k, v in res.items()}


def main():
    b = mml2_bold()
    items = [(p, l) for p, body in pdf_pages("MML 2.pdf.pages.txt") for l in body.split("\n")]
    # gap fill on text layer (non-bold headings, e.g. bracketed substituted rules)
    method = {}
    for inst, lo, hi in (("AA", 1, 123), ("AR", 124, 229)):
        for k in b[inst]:
            method[(inst, k)] = "MML2_BOLD_HEADING"
        merged = sorted(set(b[inst].items()) | set(cands_from(items, lo, hi)), key=lambda x: (x[1], x[0]))
        # keep bold ones fixed; add text candidates that fit between neighbours
        keys = sorted(b[inst])
        for k, p in cands_from(items, lo, hi):
            if k in b[inst]:
                continue
            lower = [b[inst][x] for x in keys if x < k]; upper = [b[inst][x] for x in keys if x > k]
            if (not lower or p >= max(lower)) and (not upper or p <= min(upper)):
                if k not in b[inst] or p < b[inst][k]:
                    b[inst][k] = p; method[(inst, k)] = "MML2_TEXT_GAPFILL"
                    keys = sorted(b[inst])
    exp = {inst: sorted(b[inst]) for inst in b}
    files = {
        "AA": [("MML vol 2(AA).pdf", "pdf", "MML vol 2(AA).pdf.pages.txt"),
               ("MML vol 2(AA).doc.doc", "doc", "MML vol 2(AA).doc.lines.txt")],
        "AR": [("MML vol 2(AR).doc.doc", "doc", "MML vol 2(AR).doc.lines.txt"),
               ("MML vol 2(AR).doc-1.doc", "doc", "MML vol 2(AR).doc-1.lines.txt")],
    }
    loc = {}
    for inst, fl in files.items():
        for name, kind, fn in fl:
            its = ([(p, l) for p, body in pdf_pages(fn) for l in body.split("\n")] if kind == "pdf" else list(doc_lines(fn)))
            found = lcs(cands_from(its), exp[inst])
            # second pass: undashed heading candidates strictly between located neighbours
            loose = cands_from(its, need_dash=False)
            for k in exp[inst]:
                if k in found:
                    continue
                lo_ = max([v for kk, v in found.items() if kk < k], default=-1)
                hi_ = min([v for kk, v in found.items() if kk > k], default=10 ** 9)
                hits = [l for kk, l in loose if kk == k and lo_ <= l <= hi_]
                if len(hits) >= 1:
                    found[k] = hits[0]
            loc[(inst, name)] = found
    # embedded printed page numbers in the doc-1 revision: last standalone 3-digit line before the heading
    pg_lines = [(n, int(t.strip())) for n, t in doc_lines("MML vol 2(AR).doc-1.lines.txt") if re.fullmatch(r"\s*[3-5]\d\d\s*", t)]
    def printed(n):
        prev = [p for ln, p in pg_lines if ln <= n]
        return prev[-1] if prev else ""
    rows = []
    for inst in ("AA", "AR"):
        for k in exp[inst]:
            prov = ("s." if inst == "AA" else "r.") + f"{k[0]}{k[1]}"
            r = {"instrument": "Army Act 1950" if inst == "AA" else "Army Rules 1954", "provision": prov,
                 "sort_num": k[0], "suffix": k[1], "mml2_pdf_page": b[inst][k], "mml2_method": method.get((inst, k), "")}
            for name, kind, _ in files[inst]:
                v = loc[(inst, name)].get(k)
                r[name] = ("PDF p.%d" % v if kind == "pdf" else "L%05d" % v) if v else ""
            v = loc.get(("AR", "MML vol 2(AR).doc-1.doc"), {}).get(k) if inst == "AR" else None
            r["doc1_embedded_printed_page"] = printed(v) if v else ""
            rows.append(r)
    cols = ["instrument", "provision", "sort_num", "suffix", "mml2_pdf_page", "mml2_method", "MML vol 2(AA).pdf",
            "MML vol 2(AA).doc.doc", "MML vol 2(AR).doc.doc", "MML vol 2(AR).doc-1.doc", "doc1_embedded_printed_page"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["evidence_level"], restval="")
        w.writeheader()
        for r in rows:
            r["evidence_level"] = "LOCATOR_TEXT_ONLY"
            w.writerow(r)
    for inst in ("AA", "AR"):
        print(inst, len(exp[inst]), {n: sum(1 for k in exp[inst] if loc[(inst, n)].get(k)) for n, _, _ in files[inst]})


if __name__ == "__main__":
    main()
