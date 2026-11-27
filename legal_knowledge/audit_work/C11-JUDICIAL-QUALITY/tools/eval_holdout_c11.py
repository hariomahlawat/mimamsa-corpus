#!/usr/bin/env python3
"""C11 blinded-holdout evaluation of the frozen outcome extractor (c11-extract-v2/1.0.0).

Ground truth: holdout/ground_truth_A.csv + ground_truth_B.csv (two blind Fable 5.2 reviewers; one row per proceeding).
Predictions: evaluation/holdout_predictions/OUTCOMES_V2.csv, produced by
  python3.11 extraction/tools/extract_v2.py ids --ids-file <judgment ids of holdout/HOLDOUT_SAMPLE.csv> --out evaluation/holdout_predictions
Rules (fixed before scoring):
  * unit = judgment. GT outcomes = set over that judgment's proceeding rows.
  * GT containing only 'other'/'unclear' -> GT_NOT_SCORABLE (excluded from precision, reported).
  * prediction OUTCOME_UNVERIFIED -> ABSTAINED (counts against coverage, not precision).
  * prediction with proceeding ALL/blank: CORRECT iff GT has exactly one scorable outcome and it equals the prediction;
    a single outcome for differently decided proceedings is INCORRECT_MIXED.
  * if every GT proceeding has the same scorable outcome, each non-abstained prediction is compared with it directly;
    otherwise prediction rows naming proceedings are compared with the GT row of the same normalised case number.
  * a prediction row naming several case numbers is compared with every GT proceeding it names; if those were decided
    differently the row is INCORRECT_MIXED. GT labels are compared by their first token ('other (...)' -> other).
  * STRICT = exact label; LENIENT adds only {remanded, set_aside_and_remanded}.
  python -I -B eval_holdout_c11.py [--check]"""
import argparse, csv, io, json, math, re, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "evaluation"
EQUIV = [{"remanded", "set_aside_and_remanded"}]
UNSCORABLE = {"other", "unclear", ""}


def norm_case(s):
    m = re.findall(r"(\d{1,6})(?:\s*-\s*\d{1,6})?\s*(?:/|-|of|OF)\s*(\d{4})", s or "")
    return {f"{int(a)}-{b}" for a, b in m}


def label(x):
    """'other (explanation)' -> 'other'; ground-truth labels are compared by their first token."""
    return (x or "").strip().lower().split(" ")[0].split("(")[0]


def numbers(s):
    """Every case-number token (2-6 digits, not a 4-digit year 19xx/20xx) named in a proceeding string."""
    return {n.lstrip("0") for n in re.findall(r"\b(\d{2,6})\b", s or "") if not re.fullmatch(r"(?:19|20)\d\d", n)}


def same(a, b, lenient):
    return a == b or (lenient and any(a in e and b in e for e in EQUIV))


def wilson_lower(k, n, z=1.6449):  # one-sided 95%
    if n == 0:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def build():
    gt = defaultdict(list)
    for f in ("ground_truth_A.csv", "ground_truth_B.csv"):
        for r in csv.DictReader(open(PKG / "holdout" / f, encoding="utf-8")):
            gt[r["judgment_id"]].append(r)
    hold = list(csv.DictReader(open(PKG / "holdout" / "HOLDOUT_SAMPLE.csv", encoding="utf-8")))
    pred = defaultdict(list)
    for r in csv.DictReader(open(OUT / "holdout_predictions" / "OUTCOMES_V2.csv", encoding="utf-8")):
        pred[r["judgment_id"]].append(r)
    rows = []
    for h in hold:
        j = h["judgment_id"]
        g = gt[j]
        gouts = {label(x["outcome"]) for x in g}
        scorable = gouts - UNSCORABLE
        ps = pred.get(j, [])
        for lenient in (False, True):
            pass
        if not ps:
            res = "MISSING_PREDICTION"
        elif all(p["outcome"] == "OUTCOME_UNVERIFIED" for p in ps):
            res = "ABSTAINED"
        elif not scorable:
            res = "GT_NOT_SCORABLE"
        else:
            res = None
        rec = dict(holdout_id=h["holdout_id"], judgment_id=j, court=h["court"], stratum=h["stratum"],
                   gt_outcomes=";".join(sorted(gouts)), gt_proceedings=len(g),
                   predicted=";".join(f"{p['proceeding'] or 'ALL'}={p['outcome']}" for p in ps),
                   abstain_reason=";".join(p["abstain_reason"] for p in ps if p["abstain_reason"]))
        for tag, lenient in (("strict", False), ("lenient", True)):
            r2 = res
            if r2 is None:
                ok = True
                for p in ps:
                    if p["outcome"] == "OUTCOME_UNVERIFIED":
                        continue
                    pc = norm_case(p["proceeding"])
                    if len(scorable) == 1:  # every proceeding decided alike: the proceeding label does not matter
                        ok = ok and same(p["outcome"], next(iter(scorable)), lenient)
                    elif pc or numbers(p["proceeding"]):
                        pn = numbers(p["proceeding"])
                        match = [x for x in g if numbers(x["proceeding"]) & pn]
                        if not match:
                            ok = False
                            continue
                        mouts = {label(m["outcome"]) for m in match} - UNSCORABLE
                        if len(mouts) > 1:  # one predicted outcome covering proceedings decided differently
                            r2 = "INCORRECT_MIXED"; ok = False; break
                        ok = ok and all(same(p["outcome"], o, lenient) for o in mouts)
                    else:
                        if len(scorable) > 1:
                            r2 = "INCORRECT_MIXED"; ok = False; break
                        ok = ok and same(p["outcome"], next(iter(scorable)), lenient)
                r2 = r2 or ("CORRECT" if ok else "INCORRECT")
            rec[f"result_{tag}"] = r2
        rec["gt_notes"] = " | ".join(x["notes"][:200] for x in g[:2] if x["notes"])
        rows.append(rec)
    def stats(tag, subset=None):
        rs = [r for r in rows if subset is None or subset(r)]
        att = [r for r in rs if r[f"result_{tag}"] in ("CORRECT", "INCORRECT", "INCORRECT_MIXED")]
        k = sum(1 for r in att if r[f"result_{tag}"] == "CORRECT")
        return dict(judgments=len(rs), attempted_scorable=len(att), correct=k,
                    precision=round(k / len(att), 4) if att else None, precision_lower95=round(wilson_lower(k, len(att)), 4),
                    abstained=sum(1 for r in rs if r[f"result_{tag}"] == "ABSTAINED"),
                    gt_not_scorable=sum(1 for r in rs if r[f"result_{tag}"] == "GT_NOT_SCORABLE"),
                    coverage=round(sum(1 for r in rs if r[f"result_{tag}"] not in ("ABSTAINED", "MISSING_PREDICTION")) / len(rs), 4) if rs else None)
    # baselines on the same ground truth: crawler outcome and the C10 extractor candidate (both judgment-level)
    def baseline(col):
        k = n = 0
        for h in hold:
            j = h["judgment_id"]
            scorable = {label(x["outcome"]) for x in gt[j]} - UNSCORABLE
            vals = {p[col] for p in pred.get(j, []) if p[col] and p[col] != "NOT_FOUND"}
            if not vals or not scorable:
                continue
            n += 1
            k += 1 if (len(scorable) == 1 and vals == scorable) else 0
        return dict(attempted_scorable=n, correct=k, precision=round(k / n, 4) if n else None, precision_lower95=round(wilson_lower(k, n), 4))
    summ = {"extractor": "c11-extract-v2/1.0.0",
            "baseline_crawler_outcome": baseline("crawler_outcome"), "baseline_c10_extractor": baseline("old_candidate"), "bar": "precision >= 0.95 with an independently reviewed representative sample",
            "strict": stats("strict"), "lenient": stats("lenient"),
            "by_court_strict": {c: stats("strict", lambda r, c=c: r["court"] == c) for c in sorted({r["court"] for r in rows})},
            "by_stratum_strict": {s: stats("strict", lambda r, s=s: r["stratum"] == s) for s in sorted({r["stratum"] for r in rows})}}
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(rows[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    return {"HOLDOUT_EVALUATION_ROWS.csv": s.getvalue(), "HOLDOUT_EVALUATION_SUMMARY.json": json.dumps(summ, indent=1, sort_keys=True) + "\n"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    out = build()
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED: " + ", ".join(bad) if bad else f"holdout evaluation reproduces ({len(out)} files)"); return 1 if bad else 0
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(out["HOLDOUT_EVALUATION_SUMMARY.json"][:1500]); return 0


if __name__ == "__main__":
    sys.exit(main())
