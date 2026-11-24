#!/usr/bin/env python3
"""C12: inter-coder agreement on the V3 holdout and the adjudication list (judgment level and proceeding level).
Judgment-level label = the set of (printed_disposal) and the set of (substantive_result) over that judgment's main rows.
Proceeding level (strict, C12 review F02): single-row judgments match directly; otherwise the multiset of
(normalised case-number key, printed_disposal, substantive_result) must be identical for both coders. A judgment is
AGREE only if the label sets, the row count and the proceeding-level multisets all agree.
  python -I -B holdout_v3_agreement_c12.py [--check]"""
import csv, io, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
D = PKG / "holdout_v3" / "coding"


def key(s):
    m = re.findall(r"(\d{1,6})\s*(?:/|-|\s+of\s+|\s+OF\s+)\s*((?:19|20)\d\d)", s or "")
    return ";".join(sorted({f"{int(a)}-{b}" for a, b in m})) or (s or "").strip().upper()


def load(coder):
    rows = defaultdict(list)
    for seg in (1, 2, 3):
        for r in csv.DictReader(open(D / f"coder_{coder}_seg{seg}.csv", encoding="utf-8")):
            rows[r["holdout_id"]].append(r)
    return rows


def lab(x):
    return (x or "").strip().lower().split(" ")[0]


def build():
    A, B = load("A"), load("B")
    ids = sorted(set(A) | set(B))
    out, stats = [], Counter()
    for h in ids:
        a, b = A.get(h, []), B.get(h, [])
        pa, pb = {lab(r["printed_disposal"]) for r in a}, {lab(r["printed_disposal"]) for r in b}
        sa, sb = {lab(r["substantive_result"]) for r in a}, {lab(r["substantive_result"]) for r in b}
        agree_p, agree_s = pa == pb, sa == sb
        agree_rows = len(a) == len(b)
        if len(a) == 1 and len(b) == 1:
            agree_proc = agree_p and agree_s
        else:
            ms = lambda rs: Counter((key(r["proceeding"]), lab(r["printed_disposal"]), lab(r["substantive_result"])) for r in rs)
            agree_proc = ms(a) == ms(b)
        status = "AGREE" if agree_p and agree_s and agree_rows and agree_proc else "DISAGREE"
        stats[("printed", agree_p)] += 1; stats[("substantive", agree_s)] += 1; stats[("rowcount", agree_rows)] += 1
        stats[("proceeding", agree_proc)] += 1; stats[status] += 1
        out.append(dict(holdout_id=h, judgment_id=(a or b)[0]["judgment_id"], rows_A=len(a), rows_B=len(b),
                        printed_A=";".join(sorted(pa)), printed_B=";".join(sorted(pb)), substantive_A=";".join(sorted(sa)),
                        substantive_B=";".join(sorted(sb)), agree_printed=agree_p, agree_substantive=agree_s,
                        agree_rowcount=agree_rows, agree_proceeding=agree_proc, status=status))
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(out[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(out)
    n = len(out)
    summ = dict(judgments=n, agree_all=stats["AGREE"], disagree=stats["DISAGREE"],
                printed_agreement=round(stats[("printed", True)] / n, 4), substantive_agreement=round(stats[("substantive", True)] / n, 4),
                rowcount_agreement=round(stats[("rowcount", True)] / n, 4),
                proceeding_agreement=round(stats[("proceeding", True)] / n, 4))
    return {"AGREEMENT.csv": s.getvalue(), "AGREEMENT_SUMMARY.json": json.dumps(summ, indent=1, sort_keys=True) + "\n"}


def main():
    out = build(); d = PKG / "holdout_v3"
    if "--check" in sys.argv[1:]:
        bad = [k for k, v in out.items() if (d / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED" if bad else "agreement reproduces"); return 1 if bad else 0
    for k, v in out.items():
        (d / k).write_text(v, encoding="utf-8")
    print(out["AGREEMENT_SUMMARY.json"]); return 0


if __name__ == "__main__":
    sys.exit(main())
