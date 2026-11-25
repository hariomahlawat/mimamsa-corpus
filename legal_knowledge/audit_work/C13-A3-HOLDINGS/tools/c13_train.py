#!/usr/bin/env python3
"""C13-A3 training: fit the holding and question-of-law heads on spent sets only (CPU, scikit-learn).

  python -I -B c13_train.py [--exclude-ids FILE] [--out ../model/c13_holdings_model.json]

Steps
1. Load spent labels (c13_labels.load_labels) and drop every judgment in --exclude-ids (fresh-set ids).
2. Segment each labelled judgment (c13_segment) and build features (c13_features) for court-voice sentences.
3. Targets per sentence (C12 pre-registered primary matcher between sentence and label excerpt):
     holding = matches a positive holding label; explicit negative = matches a holding-negative label
     (adjudicated/hand-checked as not a holding, or a reference question/reasoning row) and no positive.
     issue   = matches a positive question_of_law label; explicit negatives likewise.
   Unlabelled sentences are negatives with weight 1; explicit negatives weight 3 (positive-unlabelled setting:
   the references are not exhaustive).
4. Grouped 5-fold cross-validation by judgment chooses the regularisation C and records out-of-fold
   probabilities (written to the training report for the dev evaluation).
5. Fit on all data, export weights to JSON (no pickle), record hashes, versions and licences.

scikit-learn (BSD-3-Clause), numpy and scipy (BSD-3-Clause) are used for training only; the extractor runs on the
standard library with the exported JSON. Nothing is sent to any external service.
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c13_corpus as cc  # noqa: E402
import c13_features as cf  # noqa: E402
import c13_labels as cl  # noqa: E402
import c13_segment as sg  # noqa: E402

c12 = sg.c12
ROOT = os.path.dirname(HERE)
DEF_OUT = os.path.join(ROOT, "model", "c13_holdings_model.json")
SEED = 13
CS = [0.01, 0.03, 0.1]
MIN_DF = 3


def build_dataset(exclude):
    labels = [r for r in cl.load_labels() if r["judgment_id"] not in exclude]
    by_j = {}
    for r in labels:
        by_j.setdefault(r["judgment_id"], []).append(r)
    J = cc.load_corpus(cc.DEF_REPO, cc.DEF_COMMIT)
    ts = cc.TextStore(cc.DEF_REPO, cc.DEF_COMMIT)
    X, yh, yi, wh, wi, groups, meta = [], [], [], [], [], [], []
    skipped = []
    for jid in sorted(by_j):
        if jid not in J or not J[jid]["text_doc"] or J[jid]["sha256"] in cc.EXCLUDED_SHA256:
            skipped.append(jid)
            continue
        text, _ = ts.get(J[jid]["text_doc"])
        if not text:
            skipped.append(jid)
            continue
        seg = sg.segment(text, {"court": J[jid]["court"]})
        ops = seg["opinions"]
        labs = by_j[jid]
        for i, r in enumerate(seg["recs"]):
            if r["voice"] != "court":
                continue
            cs = cl.content(r["sent"])
            plo, phi = c12.page_at(seg["pidx"], r["s"]), c12.page_at(seg["pidx"], r["e"])
            hpos = hneg = ipos = ineg = False
            srcs = []
            for lab in labs:
                if not cl.sentence_matches(cs, plo, phi, lab):
                    continue
                srcs.append("%s:%s:%+d" % (lab["src"], lab["kind"], lab["polarity"]))
                if lab["kind"] == "holding":
                    hpos |= lab["polarity"] > 0
                    hneg |= lab["polarity"] < 0
                elif lab["kind"] == "question_of_law":
                    ipos |= lab["polarity"] > 0
                    ineg |= lab["polarity"] < 0
                    if lab["polarity"] > 0:
                        hneg = True
                elif lab["kind"] in ("reasoning", "operative"):
                    hneg = True
            X.append(sorted(cf.features(seg, i, lambda oi: ops[oi]["role"])))
            yh.append(1 if hpos else 0)
            wh.append(1.0 if hpos else (3.0 if hneg else 1.0))
            yi.append(1 if ipos else 0)
            wi.append(1.0 if ipos else (3.0 if ineg else 1.0))
            groups.append(jid)
            meta.append({"judgment_id": jid, "s": r["s"], "e": r["e"], "page": plo, "page_end": phi, "srcs": srcs, "sent": r["sent"],
                         "role": ops[r["oi"]]["role"], "opinion_id": ops[r["oi"]]["opinion_id"]})
    ts.close()
    return labels, X, yh, yi, wh, wi, groups, meta, skipped


def vectorize(X, vocab=None):
    import numpy as np
    from scipy.sparse import csr_matrix
    if vocab is None:
        df = {}
        for fs in X:
            for f in fs:
                df[f] = df.get(f, 0) + 1
        vocab = {f: k for k, f in enumerate(sorted(f for f, n in df.items() if n >= MIN_DF))}
    rows, cols = [], []
    for i, fs in enumerate(X):
        for f in fs:
            j = vocab.get(f)
            if j is not None:
                rows.append(i)
                cols.append(j)
    M = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(X), len(vocab)))
    return M, vocab


def fit(M, y, w, C):
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(C=C, solver="liblinear", class_weight="balanced", max_iter=2000, random_state=SEED)
    clf.fit(M, y, sample_weight=w)
    return clf


def oof(X, y, w, groups, C):
    import numpy as np
    from sklearn.model_selection import GroupKFold
    y = np.array(y)
    w = np.array(w)
    p = np.zeros(len(y))
    gkf = GroupKFold(n_splits=5)
    for tr, te in gkf.split(np.zeros(len(y)), y, groups):
        Mtr, vocab = vectorize([X[i] for i in tr])
        Mte, _ = vectorize([X[i] for i in te], vocab)
        clf = fit(Mtr, y[tr], w[tr], C)
        p[te] = clf.predict_proba(Mte)[:, 1]
    return p


def ap_score(y, p):
    from sklearn.metrics import average_precision_score
    return float(average_precision_score(y, p))


def export(clf, vocab, prune=1e-4):
    inv = {k: f for f, k in vocab.items()}
    coef = clf.coef_[0]
    w = {inv[k]: round(float(c), 6) for k, c in enumerate(coef) if abs(c) >= prune}
    return {"bias": round(float(clf.intercept_[0]), 6), "w": dict(sorted(w.items()))}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude-ids", default="")
    ap.add_argument("--out", default=DEF_OUT)
    ap.add_argument("--report", default=os.path.join(ROOT, "model", "TRAINING_REPORT.json"))
    ap.add_argument("--oof", default=os.path.join(ROOT, "model", "OOF_PREDICTIONS.jsonl"))
    a = ap.parse_args(argv)
    exclude = set(cc.read_ids(a.exclude_ids))
    labels, X, yh, yi, wh, wi, groups, meta, skipped = build_dataset(exclude)
    import numpy as np
    import scipy
    import sklearn
    res = {"heads": {}}
    oofp = {}
    for head, y, w in (("holding", yh, wh), ("issue", yi, wi)):
        scores = {}
        for C in CS:
            p = oof(X, y, w, groups, C)
            scores[C] = (ap_score(np.array(y), p), p)
        bestC = max(CS, key=lambda c: (round(scores[c][0], 4), -c))
        oofp[head] = scores[bestC][1]
        M, vocab = vectorize(X)
        clf = fit(M, np.array(y), np.array(w), bestC)
        res["heads"][head] = export(clf, vocab)
        res.setdefault("cv", {})[head] = {"C_grid": {str(c): round(scores[c][0], 4) for c in CS}, "chosen_C": bestC,
                                          "metric": "out-of-fold average precision (grouped 5-fold by judgment)",
                                          "n_pos": int(sum(y)), "n": len(y), "n_features": len(res["heads"][head]["w"])}
    res["thresholds"] = {"holding": 0.80, "holding_over_operative": 0.95, "holding_floor": 0.40, "floor_min_court_sentences": 15, "issue": 0.80}
    res["model_family"] = "L2 logistic regression (liblinear), class_weight=balanced, binary sparse features"
    res["training_sets"] = sorted(set(r["src"] for r in labels))
    res["n_training_judgments"] = len(set(groups))
    res["excluded_ids"] = sorted(exclude)
    res["excluded_ids_sha256"] = sha256_file(a.exclude_ids) if a.exclude_ids else None
    res["skipped_no_text"] = skipped
    res["label_files_sha256"] = {k: sha256_file(p) for k, p in cl.FILES.items()}
    res["software"] = {"python": sys.version.split()[0], "scikit-learn": sklearn.__version__, "numpy": np.__version__, "scipy": scipy.__version__,
                       "licences": {"scikit-learn": "BSD-3-Clause", "numpy": "BSD-3-Clause", "scipy": "BSD-3-Clause"}}
    res["external_calls"] = "none"
    thr_file = os.path.join(ROOT, "model", "THRESHOLDS.json")
    if os.path.exists(thr_file):
        with open(thr_file, encoding="utf-8") as f:
            res["thresholds"] = json.load(f)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, sort_keys=True, indent=0)
        f.write("\n")
    with open(a.oof, "w", encoding="utf-8") as f:
        for k, m in enumerate(meta):
            row = {k: v for k, v in m.items() if k != "sent"}
            row["y_holding"], row["y_issue"] = yh[k], yi[k]
            row["oof_holding"], row["oof_issue"] = round(float(oofp["holding"][k]), 5), round(float(oofp["issue"][k]), 5)
            f.write(json.dumps(row, sort_keys=True) + "\n")
    with open(os.path.splitext(a.oof)[0] + "_TEXTS.jsonl", "w", encoding="utf-8") as f:
        for m in meta:
            f.write(json.dumps({"judgment_id": m["judgment_id"], "s": m["s"], "sent": m["sent"]}, ensure_ascii=False) + "\n")
    rep = {k: v for k, v in res.items() if k != "heads"}
    rep["model_sha256"] = sha256_file(a.out)
    with open(a.report, "w", encoding="utf-8") as f:
        json.dump(rep, f, sort_keys=True, indent=1)
        f.write("\n")
    print(json.dumps(rep["cv"], indent=1), rep["n_training_judgments"], "judgments; model", rep["model_sha256"][:16])


if __name__ == "__main__":
    main()
