#!/usr/bin/env python3
"""Score extract_v2 on the 50 Cycle 10 reviewed judgments (DEV set, used for tuning).

Writes outputs/DEV_EVALUATION_ROWS.csv and prints a summary (JSON). Precision is measured on
non-abstained judgments; coverage = non-abstained / scorable. A judgment with mixed per-proceeding
gold counts as correct only if v2 emits per-proceeding rows that all match.
"""
import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract_v2  # noqa: E402
import v2core  # noqa: E402


def score(gold, rows):
    outs = [r["outcome"] for r in rows]
    if all(o == v2core.UNVERIFIED for o in outs):
        return "ABSTAIN_CORRECT" if gold.get("expect_abstain") else "ABSTAIN"
    if gold.get("expect_abstain"):
        return "WRONG"
    if gold.get("mixed"):
        if len(rows) < 2:
            return "WRONG"
        covered = set()
        for r in rows:
            hay = (r["proceeding"] + " " + r["excerpt"]).lower()
            hit = [i for i, (rx, o) in enumerate(gold["mixed"]) if re.search(rx, hay) and o == r["outcome"]]
            if not hit:
                return "WRONG"
            covered.update(hit)
        return "CORRECT" if len(covered) == len(gold["mixed"]) else "PARTIAL_WRONG"
    return "CORRECT" if all(o in gold["accept"] for o in outs) else "WRONG"


def main():
    gold = json.load(open(os.path.join(HERE, "dev_gold.json")))
    J, order = extract_v2.load_inputs()
    store = extract_v2.TextStore()
    res = []
    for jid in sorted(k for k in gold if not k.startswith("_")):
        rows, _ = extract_v2.process_one(J[jid], store)
        verdict = score(gold[jid], rows)
        res.append({"judgment_id": jid, "court": J[jid]["court"], "gold_accept": "|".join(gold[jid].get("accept", [])),
                    "gold_mixed": json.dumps(gold[jid].get("mixed", [])), "v2_rows": " || ".join(
                        "%s=%s" % (r["proceeding"][:70], r["outcome"]) for r in rows),
                    "v2_method": rows[0]["method"], "abstain_reason": rows[0]["abstain_reason"], "page": rows[0]["page"],
                    "excerpt": rows[-1]["excerpt"][:300], "crawler": J[jid]["crawler_outcome"], "old": J[jid]["old_candidate"],
                    "verdict": verdict, "note": gold[jid].get("note", "")})
    store.close()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(res[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(res)
    open(os.path.join(extract_v2.OUT, "DEV_EVALUATION_ROWS.csv"), "w", encoding="utf-8").write(buf.getvalue())
    n = len(res)
    pred = [r for r in res if r["verdict"] in ("CORRECT", "WRONG", "PARTIAL_WRONG")]
    cor = [r for r in pred if r["verdict"] == "CORRECT"]
    summ = {"extractor": v2core.VERSION, "n": n, "predicted": len(pred), "correct": len(cor),
            "precision": round(len(cor) / len(pred), 4) if pred else None, "coverage": round(len(pred) / n, 4),
            "abstained": sum(1 for r in res if r["verdict"].startswith("ABSTAIN")),
            "abstain_correct": sum(1 for r in res if r["verdict"] == "ABSTAIN_CORRECT")}
    for subset, rr in (("review_AB_30", [r for r in res if r["judgment_id"] in RAB]), ("ws_random_20", [r for r in res if r["judgment_id"] not in RAB])):
        p = [r for r in rr if r["verdict"] in ("CORRECT", "WRONG", "PARTIAL_WRONG")]
        c = [r for r in p if r["verdict"] == "CORRECT"]
        summ[subset] = {"n": len(rr), "predicted": len(p), "correct": len(c),
                        "precision": round(len(c) / len(p), 4) if p else None, "coverage": round(len(p) / len(rr), 4) if rr else None}
    print(json.dumps(summ, indent=1))
    if "-v" in sys.argv:
        for r in res:
            print(r["verdict"], r["judgment_id"], r["court"][:12], "|", r["gold_accept"], r["gold_mixed"][:60], "|", r["v2_rows"][:160], "|", r["v2_method"], r["abstain_reason"], "p", r["page"])
            if "-vv" in sys.argv:
                print("    ", r["excerpt"][:250])


RAB = set()
for fn in ("review_A.csv", "review_B.csv"):
    for row in csv.DictReader(open(os.path.join(extract_v2.C10, "review", fn), encoding="utf-8")):
        RAB.add(row["judgment_id"])

if __name__ == "__main__":
    main()
