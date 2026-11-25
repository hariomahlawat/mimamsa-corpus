#!/usr/bin/env python3
"""C13-A3 frozen predictions for a C13-A0 holdout packet (item pointers only).

  python3.11 -I -B predict_holdout_c13.py --packet <CODER_SHEET.csv> --out <PRED.csv>

Reads ONLY the pointer columns of the blank coder packet (`item_id`, `rep_sha256`); no coding field is read.
Each item's representative copy (rep_sha256) is located in the corpus register (judgment_id with that sha256),
or, failing that, through the C10 metadata audit (doc_id of that sha256 with a text layer at the commit).
The frozen extractor runs on that copy's text layer and its items are written in the c13_score.py holdings
format: item_id, pred_id, item_type, opinion, judge, page, para, excerpt, legal_issue, certainty, notes.

Mapping
  holding (court-side opinion)       -> item_type holding, opinion sole / lead / concurring / separate
  dissent_holding_candidate          -> item_type holding, opinion dissent
  split_opinion_holding_candidate    -> item_type holding, opinion separate (split verdict: no majority)
  question_of_law                    -> item_type question_of_law
  obiter / operative_direction       -> not emitted (outside the holdings vocabulary)
  certainty: p >= 0.85 certain, p >= 0.60 probable, else uncertain (holding head; issue head for QoL)
  notes: c13 item type, opinion role, court_status, status AUTOMATED_CANDIDATE_NOT_VERIFIED
Items without a readable text layer get one row with notes NO_PREDICTION:<reason> and blank fields.
"""
import argparse
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c13_corpus as cc  # noqa: E402
import c13_extract as cx  # noqa: E402
import c13_features as cf  # noqa: E402

COLS = ["item_id", "pred_id", "item_type", "opinion", "judge", "page", "para", "excerpt", "legal_issue", "certainty", "notes"]
ROLE_TO_OPINION = {"sole": "sole", "lead_majority": "lead", "lead": "lead", "court_order": "lead", "concurring": "concurring",
                   "separate": "separate", "dissent": "dissent", "split_opinion": "separate"}


def certainty(p):
    if p is None:
        return "uncertain"
    return "certain" if p >= 0.85 else "probable" if p >= 0.60 else "uncertain"


def locate(J, sha, ts):
    jids = sorted(j for j, v in J.items() if v["sha256"] == sha and v["text_doc"])
    if jids:
        j = jids[0]
        return {"judgment_id": j, "sha256": sha, "court": J[j]["court"], "text_doc": J[j]["text_doc"]}, "REGISTER"
    audit = cc.read_csv(cc.c12drv.INPUT_FILES["metadata_audit"])
    for r in sorted((r for r in audit if r["sha256"] == sha), key=lambda r: r["doc_id"]):
        text, _ = ts.get(r["doc_id"])
        if text:
            return {"judgment_id": "SHA-" + sha[:16], "sha256": sha, "court": r.get("court", ""), "text_doc": r["doc_id"]}, "METADATA_AUDIT"
    return None, "NO_TEXT_LAYER_FOR_SHA"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default=cc.DEF_REPO)
    ap.add_argument("--commit", default=cc.DEF_COMMIT)
    ap.add_argument("--model", default=os.path.join(os.path.dirname(HERE), "model", "c13_holdings_model.json"))
    a = ap.parse_args(argv)
    with open(a.packet, encoding="utf-8", newline="") as f:
        pointers = [(r["item_id"], r["rep_sha256"]) for r in csv.DictReader(f)]
    model = cf.Model(a.model)
    J = cc.load_corpus(a.repo, a.commit)
    ts = cc.TextStore(a.repo, a.commit)
    rows = []
    for iid, sha in pointers:
        if sha in cc.EXCLUDED_SHA256:
            rows.append({"item_id": iid, "notes": "NO_PREDICTION:RESTRICTED_FOUO_COPY"})
            continue
        meta, how = locate(J, sha, ts)
        if meta is None:
            rows.append({"item_id": iid, "notes": "NO_PREDICTION:" + how})
            continue
        text, _ = ts.get(meta["text_doc"])
        _, items, _, _ = cx.analyze(text, meta, model)
        n = 0
        for it in items:
            if it["item_type"] in ("holding", "dissent_holding_candidate", "split_opinion_holding_candidate"):
                typ, p = "holding", it["p_holding"]
            elif it["item_type"] == "question_of_law":
                typ, p = "question_of_law", it["p_issue"]
            else:
                continue
            n += 1
            rows.append({"item_id": iid, "pred_id": it["item_id"], "item_type": typ,
                         "opinion": ROLE_TO_OPINION.get(it["opinion_role"], "unclear"),
                         "judge": it["opinion_author"] or "", "page": it["page"],
                         "para": it["anchor"]["paragraph"] if it["anchor"]["paragraph"] is not None else "",
                         "excerpt": it["excerpt"], "legal_issue": it["legal_issue"] or "", "certainty": certainty(p),
                         "notes": "c13_item_type=%s;opinion_role=%s;court_status=%s;located_by=%s;text_doc=%s;status=%s" % (
                             it["item_type"], it["opinion_role"], it["court_status"], how, meta["text_doc"], it["status"])})
        if n == 0:
            rows.append({"item_id": iid, "notes": "NO_HOLDING"})
    ts.close()
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=COLS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in COLS})
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        f.write(s.getvalue())
    items_n = len(set(i for i, _ in pointers))
    print("%d items; %d prediction rows; %d items with >=1 prediction" % (
        items_n, len(rows), len(set(r["item_id"] for r in rows if r.get("pred_id")))))


if __name__ == "__main__":
    main()
