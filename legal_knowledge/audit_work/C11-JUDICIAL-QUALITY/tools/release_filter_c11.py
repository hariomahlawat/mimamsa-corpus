#!/usr/bin/env python3
"""C11 release filter over the frozen extractor output (review F01, P1). The frozen extractor is not changed.

A batch judgment's text is stored under many judgment ids (one PDF per connected case). v2 gives every copy the batch's
last disposition, so copies filed under petitions that were allowed or partly allowed read 'dismissed'. Until
per-proceeding splitting exists, any outcome row whose judgment shares its text with another file, or whose proceeding
label names more than one case number, is released as OUTCOME_UNVERIFIED with the original value preserved.
  python -I -B release_filter_c11.py [--check]"""
import argparse, csv, glob, io, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "extraction" / "release"
BATCHES = PKG.parent / "C10-HF-JUDGMENTS" / "work" / "batches"


def jid(sha):
    return "J-" + sha[:16]


def numbers(s):
    return {n for n in re.findall(r"\b(\d{2,6})\b", s or "") if not re.fullmatch(r"(?:19|20)\d\d", n)}


def case_pairs(s):
    """Distinct (number, year) case references named in a proceeding label; repeats of one case in different formats count once."""
    return {(int(a), b) for a, b in re.findall(r"(\d{1,6})\s*(?:/|-|\s+of\s+|\s+OF\s+)\s*((?:19|20)\d\d)\b", s or "")}


def build():
    by_text = defaultdict(set)
    for bp in sorted(glob.glob(str(BATCHES / "batch_*.jsonl"))):
        with open(bp, encoding="utf-8") as fh:
            next(fh)
            for line in fh:
                r = json.loads(line)
                if r.get("text_sha256"):
                    by_text[r["text_sha256"]].add(r["sha256"])
    shared = {jid(s) for g in by_text.values() if len(g) > 1 for s in g}
    # review C-01: also every file in a multi-copy judgment of the identity register (revision 2), not only exact-text copies
    keyed = defaultdict(set)
    for r in csv.DictReader(open(PKG / "identity" / "outputs" / "JUDGMENT_IDENTITY_REGISTER.csv", encoding="utf-8")):
        keyed[r["judgment_key"]].add(r["sha256"])
    multi = {jid(s) for g in keyed.values() if len(g) > 1 for s in g}
    rows = list(csv.DictReader(open(PKG / "extraction" / "outputs" / "OUTCOMES_V2.csv", encoding="utf-8")))
    out, why = [], Counter()
    for r in rows:
        r = dict(r)
        r["v2_outcome_original"] = r["outcome"]
        reason = ""
        if r["outcome"] != "OUTCOME_UNVERIFIED":
            if r["judgment_id"] in shared:
                reason = "SHARED_BATCH_TEXT_PER_PROCEEDING_SPLIT_REQUIRED"
            elif r["judgment_id"] in multi:
                reason = "MULTI_COPY_JUDGMENT_PER_PROCEEDING_SPLIT_REQUIRED"
            elif len(case_pairs(r["proceeding"])) > 1 or (len(numbers(r["proceeding"])) > 1 and "," in r["proceeding"] and ";" not in r["proceeding"]):
                reason = "MULTI_NUMBER_PROCEEDING_LABEL"
        if reason:
            r["outcome"] = "OUTCOME_UNVERIFIED"
            why[reason] += 1
        r["release_filter"] = reason
        r["release_status"] = "AUTOMATED_CANDIDATE_NOT_VERIFIED"
        out.append(r)
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(out[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(out)
    summ = dict(rows=len(out), shared_text_judgment_ids=len(shared), multi_copy_judgment_ids=len(multi), downgraded=dict(why),
                released_outcomes=dict(sorted(Counter(x["outcome"] for x in out).items())),
                note="v2 outcomes remain AUTOMATED_CANDIDATE_NOT_VERIFIED; blinded holdout precision 84.1% (below the 95% bar)")
    return {"OUTCOMES_V2_RELEASE.csv": s.getvalue(), "RELEASE_FILTER_SUMMARY.json": json.dumps(summ, indent=1, sort_keys=True) + "\n"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    out = build()
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED: " + ", ".join(bad) if bad else f"release filter reproduces ({len(out)} files)"); return 1 if bad else 0
    OUT.mkdir(exist_ok=True)
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(out["RELEASE_FILTER_SUMMARY.json"]); return 0


if __name__ == "__main__":
    sys.exit(main())
