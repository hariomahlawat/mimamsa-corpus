#!/usr/bin/env python3
"""DOC-vs-PDF provision text comparison (stdlib). Reads the PRIVATE derived text layer (scratchpad repro1) and the
committed provision_index.csv; prints/writes only diff TOKENS (a few words) per provision, never full text.
Pairs: Army Act -> vol 2(AA).doc vs MML 2.pdf and vol 2(AA).doc vs vol 2(AA).pdf; Army Rules -> each vol 2(AR) DOC vs MML 2.pdf.
Statutory text only: each block runs from the provision heading to the first NOTE/NOTES line; running heads and
footnote lines are dropped. A diff is 'consequential' if it touches a negation, modal, proviso/exception word,
number/time word, conjunction (and/or) or authority word. Text-layer output is a SCREEN; consequential diffs must
then be page-image checked (render SHA-256 recorded in doc_pdf_fidelity_register.csv).
Usage: python3 doc_pdf_diff.py <scratchpad> <provisions comma-separated e.g. s.125,r.22> <out_csv>"""
import csv, difflib, re, sys
from pathlib import Path

SP = Path(sys.argv[1]); PROVS = sys.argv[2].split(","); OUT = Path(sys.argv[3])
W = Path(__file__).resolve().parent.parent
R = SP / "repro1"
CONSEQ = re.compile(r"^(not|no|nor|never|none|shall|may|must|unless|except|provided|proviso|only|any|all|or|and|without|within|"
                    r"before|after|exceed\w*|less|more|days?|months?|years?|hours?|weeks?|\d+[a-z]?|one|two|three|four|five|six|seven|"
                    r"eight|nine|ten|fourteen|twenty\w*|thirty|forty\w*|officer\w*|commanding|chief|government|court\w*|authority|"
                    r"convening|confirm\w*|discretion|witness\w*|accused)$")


def pdf_items(fn):
    t = (R / fn).read_text(encoding="utf-8")
    parts = re.split(r"=== PDF_PAGE (\d+) / file=[^\n]*===\n", t)
    out = []
    for i in range(1, len(parts), 2):
        for j, l in enumerate(parts[i + 1].split("\n")):
            out.append((int(parts[i]), j, l))
    return out


def doc_items(fn):
    out = []
    for l in (R / fn).read_text(encoding="utf-8").splitlines():
        m = re.match(r"L(\d{5})\| ?(.*)", l)
        if m:
            out.append((int(m.group(1)), 0, m.group(2)))
    return out


HEADRE = lambda n, s: re.compile(rf"^\s*[\[\(]?\s*\d?\s*{n}\s*[-–]?\s*{s}\s*(?:\.|(?<=[A-Z])\s)")


def block(items, start_loc, n, s, nxt):
    """items ordered; start at first line at/after start_loc matching heading; stop at NOTE(S) or next heading."""
    hr = HEADRE(n, s); out, on = [], False
    nr = HEADRE(*nxt) if nxt else None
    for loc, j, l in items:
        if loc < start_loc:
            continue
        if not on:
            if hr.match(l):
                on = True
            else:
                continue
        elif nr and nr.match(l):
            break
        st = l.strip()
        if re.fullmatch(r"NOTES?\.?", st, re.I):
            break
        if re.match(r"^(THE ARMY (ACT|RULES)|\d{1,3}\s*$|[¹²³⁴⁵\d]\s*(Subs|Omitted|Inserted|Substituted|sub vide|See)|2188|\[Common)", st):
            continue
        out.append(st)
        if len(out) > 400:
            break
    return " ".join(out)


def norm(t):
    t = t.replace("—", " - ").replace("–", " - ").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\](\s*)\d\b", "]", t)          # footnote markers after brackets
    t = re.sub(r"[\[\]¹²³⁴⁵]", " ", t)
    return re.findall(r"[a-z0-9]+(?:\([a-z0-9]+\))?|\(|\)", t.lower())


def main():
    idx = {r["provision"]: r for r in csv.DictReader(open(W / "provision_index.csv", encoding="utf-8"))}
    keys = list(idx)
    items = {"MML 2.pdf": pdf_items("MML 2.pdf.pages.txt"), "MML vol 2(AA).pdf": pdf_items("MML vol 2(AA).pdf.pages.txt"),
             "MML vol 2(AA).doc.doc": doc_items("MML vol 2(AA).doc.lines.txt"),
             "MML vol 2(AR).doc.doc": doc_items("MML vol 2(AR).doc.lines.txt"),
             "MML vol 2(AR).doc-1.doc": doc_items("MML vol 2(AR).doc-1.lines.txt")}
    rows = []
    for pv in PROVS:
        r = idx[pv]; n, s = r["sort_num"], r["suffix"]
        k = keys.index(pv); nx = idx[keys[k + 1]] if k + 1 < len(keys) and idx[keys[k + 1]]["instrument"] == r["instrument"] else None
        nxt = (nx["sort_num"], nx["suffix"]) if nx else None
        def loc(f):
            if f == "MML 2.pdf":
                return int(r["mml2_pdf_page"])
            v = r.get(f, "")
            return int(re.sub(r"\D", "", v)) if v else None
        pairs = ([("MML vol 2(AA).doc.doc", "MML 2.pdf"), ("MML vol 2(AA).doc.doc", "MML vol 2(AA).pdf")]
                 if r["instrument"].startswith("Army Act") else
                 [("MML vol 2(AR).doc.doc", "MML 2.pdf"), ("MML vol 2(AR).doc-1.doc", "MML 2.pdf")])
        for a, b in pairs:
            la, lb = loc(a), loc(b)
            if la is None or lb is None:
                rows.append({"provision": pv, "file_a": a, "file_b": b, "op": "NO_LOCATOR"}); continue
            ta, tb = norm(block(items[a], la, n, s, nxt)), norm(block(items[b], lb, n, s, nxt))
            sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
            rows.append({"provision": pv, "file_a": a, "loc_a": la, "file_b": b, "loc_b": lb, "op": "SUMMARY",
                         "len_a": len(ta), "len_b": len(tb), "similarity": round(sm.ratio(), 3)})
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op == "equal":
                    continue
                da, db = ta[i1:i2], tb[j1:j2]
                if len(da) > 12 or len(db) > 12:
                    da, db = da[:6] + ["…"], db[:6] + ["…"]
                cons = any(CONSEQ.match(x) for x in ta[i1:i2] + tb[j1:j2])
                ctx = " ".join(ta[max(0, i1 - 4):i1])
                rows.append({"provision": pv, "file_a": a, "loc_a": la, "file_b": b, "loc_b": lb, "op": op,
                             "tokens_a": " ".join(da), "tokens_b": " ".join(db), "context_before": ctx,
                             "consequential_screen": "YES" if cons else "NO", "len_a": len(ta), "len_b": len(tb),
                             "similarity": round(sm.ratio(), 3)})
    cols = ["provision", "file_a", "loc_a", "file_b", "loc_b", "op", "tokens_a", "tokens_b", "context_before",
            "consequential_screen", "len_a", "len_b", "similarity"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval=""); w.writeheader(); w.writerows(rows)
    print(len(rows), "diff ops;", sum(1 for x in rows if x.get("consequential_screen") == "YES"), "consequential (screen)")


if __name__ == "__main__":
    main()
