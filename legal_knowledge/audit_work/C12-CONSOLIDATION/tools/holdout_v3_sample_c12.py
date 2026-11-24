#!/usr/bin/env python3
"""C12 fresh blinded holdout for outcome extractor V3 (deterministic, stratified, double-coded).
Excludes: the C10 dev judgments (30 + 20) and the C11 holdout (56), which are spent. One representative file per
distinct judgment (identity register revision 2), complete-structure copies only, text layer present.
Strata: court x {batch_or_multi, disagreement, pension_or_disciplinary, other}; quotas give the Supreme Court and each
High Court enough rows for per-court intervals. Selection = lowest SHA-256(seed + judgment_key) within each stratum.
Output carries NO extracted values (reviewers stay blind).   python -I -B holdout_v3_sample_c12.py [--check]"""
import csv, hashlib, io, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
C11 = PKG.parent / "C11-JUDICIAL-QUALITY"
J10 = PKG.parent / "C10-HF-JUDGMENTS"
SEED = "mimamsa-c12-holdout-v3"
QUOTA = {"Supreme": 40, "Delhi": 30, "Punjab": 30, "Jammu": 25, "Allahabad": 25}
PARTS = {"batch_or_multi": 0.30, "disagreement": 0.25, "pension_or_disciplinary": 0.25}


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def main():
    spent = set()
    for f in ("review_A.csv", "review_B.csv", "WS_REVIEW_SAMPLE20_3257ebb9.csv"):
        spent |= {r["judgment_id"] for r in rows(J10 / "review" / f)}
    spent |= {r["judgment_id"] for r in rows(C11 / "holdout" / "HOLDOUT_SAMPLE.csv")}
    reg = rows(C11 / "identity" / "outputs" / "JUDGMENT_IDENTITY_REGISTER.csv")
    copies = {r["sha256"]: r for r in rows(J10 / "outputs" / "HF_JUDGMENT_COPY_REGISTER.csv")}
    meta = defaultdict(list)
    for m in rows(J10 / "outputs" / "HF_JUDGMENT_METADATA_AUDIT.csv"):
        meta[m["sha256"]].append(m)
    topics = {}
    import json
    for l in open(J10 / "outputs" / "HF_JUDGMENT_LEGAL_ISSUES.jsonl", encoding="utf-8"):
        o = json.loads(l)
        topics[o["sha256"]] = set((o.get("topics") or {}).keys())
    by_key = defaultdict(list)
    for r in reg:
        by_key[r["judgment_key"]].append(r)
    strata = defaultdict(list)
    for key, rs in by_key.items():
        rs = sorted(rs, key=lambda r: r["sha256"])
        rep = next((r for r in rs if copies.get(r["sha256"], {}).get("disposition") == "PROCESSED"
                    and copies[r["sha256"]].get("source_completeness") == "COMPLETE_FILE_STRUCTURE"), None)
        if not rep or rep["judgment_id_c10"] in spent or any(r["judgment_id_c10"] in spent for r in rs):
            continue
        court = next((c for c in QUOTA if c in rep["court"]), None)
        if not court:
            continue
        ms = meta.get(rep["sha256"], [])
        t = topics.get(rep["sha256"], set())
        kind = ("batch_or_multi" if len(rs) > 1 or len(ms) > 1 or any(len([x for x in m["case_numbers_text_p1_3"].split(";") if x]) > 1 for m in ms) else
                "disagreement" if any("crawler outcome" in m["contradictions"] for m in ms) else
                "pension_or_disciplinary" if t & {"disability_pension", "court_martial", "pension", "summary_court_martial", "dismissal_discharge"} else "other")
        strata[(court, kind)].append((key, rep))
    out = []
    for court, q in QUOTA.items():
        want = {k: round(q * f) for k, f in PARTS.items()}
        want["other"] = q - sum(want.values())
        short = 0
        for kind in ("batch_or_multi", "disagreement", "pension_or_disciplinary", "other"):
            n = want[kind] + (short if kind == "other" else 0)
            cand = sorted(strata[(court, kind)], key=lambda x: hashlib.sha256((SEED + x[0]).encode()).hexdigest())
            take = cand[:n]
            short += max(0, n - len(take)) if kind != "other" else 0
            for key, rep in take:
                out.append(dict(holdout_id=f"V3H{len(out)+1:03d}", judgment_key=key, judgment_id=rep["judgment_id_c10"], sha256=rep["sha256"],
                                court=rep["court"], stratum=kind, raw_path=copies[rep["sha256"]]["path"],
                                doc_ids=";".join(sorted(m["doc_id"] for m in meta.get(rep["sha256"], [])))))
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(out[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(out)
    target = PKG / "holdout_v3" / "HOLDOUT_V3_SAMPLE.csv"
    if "--check" in sys.argv[1:]:
        ok = target.is_file() and target.read_text(encoding="utf-8") == s.getvalue()
        print("holdout v3 reproduces" if ok else "CHECK FAILED"); sys.exit(0 if ok else 1)
    target.write_text(s.getvalue(), encoding="utf-8")
    from collections import Counter
    print(len(out), dict(Counter((x["court"].split()[-1], x["stratum"]) for x in out)))


if __name__ == "__main__":
    main()
