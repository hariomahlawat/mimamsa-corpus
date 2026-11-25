#!/usr/bin/env python3
"""C13-A0 generic scoring harness (pre-registered; PROTOCOL_C13.md s.5-6).

Scores frozen predictions against frozen reference annotations for one task (outcome, holdings, relations):
strict and family precision, coverage (recall), abstention, per-court / per-stratum / per-subset breakdowns,
Horvitz-Thompson weighted estimates with Kish-Wilson and stratified judgment-cluster bootstrap intervals, unweighted
Wilson intervals, evidence-anchor verification against page text, and a failure taxonomy.

  python -I -B c13_score.py --task outcome --holdout H-OUT-C13 --truth TRUTH.csv --pred PRED.csv \
      --out-dir DIR [--pages PAGES.jsonl] [--pred-adjudication ADJ.csv] [--store STORE_DIR]

Input formats (CSV, UTF-8):
  truth: item_id + the task's coding fields (as produced by c13_coding.py truth).
  pred:  item_id + the task's coding fields; an empty scored field or a value in ABSTAIN means "abstained".
         Optional pred_id column (else assigned).  pages: JSONL {"sha256":..., "page": n, "text": ...}.
  pred-adjudication (holdings only): pred_id,label with label in CORRECT / INCORRECT / UNCLEAR (blind adjudication
  of predicted items; gives true precision; without it holdings precision is a reference-match LOWER BOUND).
`--check` runs the built-in synthetic self-test (no corpus needed).
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import OUT, read_csv, render_csv, render_json, sha256_file  # noqa: E402
from c13_tasks import TASKS, norm_ws  # noqa: E402
from c13_coding import align, group, verify_store  # noqa: E402
import c13_stats as S  # noqa: E402

ABSTAIN = {"", "ABSTAIN", "ABSTAINED", "OUTCOME_UNVERIFIED", "unclear"}
TARGETS = {"outcome": {"precision": 0.95, "coverage": 0.85},
           "holdings": {"precision": 0.80, "coverage": 0.60},       # interim research milestone, not acceptance
           "relations": {"precision": None, "coverage": None}}       # no owner target: reported only
BOOT_REPS = 2000


# ------------------------------------------------------------------------------------------------ anchors
def anchor_status(pred, pages_by_sha, sha):
    page, ex = (pred.get("page") or "").strip(), norm_ws(pred.get("excerpt"))
    if not page or not ex:
        return "NO_ANCHOR"
    pages = pages_by_sha.get(sha)
    if pages is None:
        return "PAGE_TEXT_UNAVAILABLE"
    probe = ex[:120]
    if page.isdigit() and probe in norm_ws(pages.get(int(page), "")):
        return "ANCHOR_OK"
    if any(probe in norm_ws(t) for t in pages.values()):
        return "ANCHOR_WRONG_PAGE"
    return "ANCHOR_NOT_FOUND"


def load_pages(path):
    out = defaultdict(dict)
    if not path:
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            out[o["sha256"]][int(o["page"])] = o["text"]
    return out


# ------------------------------------------------------------------------------------------------ estimators
def estimate(units, seed):
    """units: list of (cluster, stratum, weight, y, x). Unweighted Wilson + bootstrap; weighted HT + Kish-Wilson +
    weighted bootstrap."""
    units = [u for u in units if u[4] > 0]
    k = sum(u[3] for u in units)
    n = sum(u[4] for u in units)
    p, lo, hi = S.wilson(k, n)
    blo, bhi = S.stratified_cluster_bootstrap(units, BOOT_REPS, seed + "|u", weighted=False)
    wp, wlo, whi = S.weighted_wilson(units)
    wblo, wbhi = S.stratified_cluster_bootstrap(units, BOOT_REPS, seed + "|w", weighted=True)
    return dict(k=S.rnd(k, 3), n=S.rnd(n, 3), clusters=len(units),
                unweighted=S.rnd(p), unweighted_wilson95=[S.rnd(lo), S.rnd(hi)],
                unweighted_cluster_bootstrap95=[S.rnd(blo), S.rnd(bhi)],
                weighted=S.rnd(wp), weighted_kish_wilson95=[S.rnd(wlo), S.rnd(whi)],
                weighted_cluster_bootstrap95=[S.rnd(wblo), S.rnd(wbhi)])


def target_status(est, target):
    if target is None or est["weighted"] is None:
        return "NO_TARGET" if target is None else "NOT_ESTIMABLE"
    met_point = est["weighted"] >= target and est["unweighted"] >= target
    lb = est["weighted_cluster_bootstrap95"][0]
    return ("MET_LOWER_BOUND" if met_point and lb is not None and lb >= target else
            "MET_POINT_ONLY" if met_point else "NOT_MET")


# ------------------------------------------------------------------------------------------------ keyed tasks
def score_keyed(task, truth, pred, design, pages_by_sha):
    G, P = group(truth), group(pred)
    rows = []
    for iid in sorted(design):
        d = design[iid]
        g = [r for r in G.get(iid, []) if not task.is_null_row(r)]
        p = [r for r in P.get(iid, []) if not task.is_null_row(r)]
        for gr, pr in align(task, g, p):
            row = dict(item_id=iid, court=d["court"], stratum=d["stratum"], weight=d["weight"],
                       unit=task.unit_key(gr or pr), gold_multi_unit=len(g) > 1,
                       gold_party_specific=bool(gr and (gr.get("party_specific") or "").strip()))
            row["anchor"] = anchor_status(pr, pages_by_sha, d["sha256"]) if pr else ""
            for f in task.scored_fields:
                gv = (gr.get(f) or "").strip() if gr else None
                pv = (pr.get(f) or "").strip() if pr else None
                if f == "target":
                    gv = norm_ws(gv).upper() if gv is not None else None
                    pv = norm_ws(pv).upper() if pv is not None else None
                answered = pv is not None and pv not in ABSTAIN
                determinable = gv is not None and gv not in task.unscorable and gv != ""
                if gr is None:
                    cat = "EXTRA_UNIT_NO_GOLD" if answered else "EXTRA_UNIT_ABSTAINED"
                elif not answered:
                    cat = ("MISSED" if pr is None else "ABSTAINED") if determinable else "GOLD_UNDETERMINABLE_NO_PRED"
                elif not determinable:
                    cat = "PRED_ON_UNDETERMINABLE"
                elif pv == gv:
                    cat = "CORRECT"
                elif task.family(f, pv) == task.family(f, gv):
                    cat = "WRONG_LABEL_SAME_FAMILY"
                else:
                    cat = "WRONG_FAMILY"
                row.update({f"{f}__gold": gv if gv is not None else "", f"{f}__pred": pv if pv is not None else "",
                            f"{f}__answered": answered, f"{f}__determinable": determinable, f"{f}__category": cat,
                            f"{f}__strict": cat == "CORRECT",
                            f"{f}__family": cat in ("CORRECT", "WRONG_LABEL_SAME_FAMILY"),
                            f"{f}__covered": determinable and answered})
            rows.append(row)
    return rows


def aggregate(task, rows, design, label, subset=lambda r: True):
    res = {}
    for f in task.scored_fields:
        sel = [r for r in rows if subset(r)]
        per = defaultdict(lambda: [0, 0, 0, 0, 0])   # strict, family, answered, covered, determinable
        for r in sel:
            a = per[r["item_id"]]
            a[0] += r[f"{f}__strict"]; a[1] += r[f"{f}__family"]; a[2] += r[f"{f}__answered"]
            a[3] += r[f"{f}__covered"]; a[4] += r[f"{f}__determinable"]
        def units(i_num, i_den):
            return [(iid, design[iid]["stratum"], design[iid]["weight"], v[i_num], v[i_den]) for iid, v in per.items()]
        seed = f"c13-score|{task.name}|{label}|{f}"
        res[f] = dict(strict_precision=estimate(units(0, 2), seed + "|sp"),
                      family_precision=estimate(units(1, 2), seed + "|fp"),
                      coverage=estimate(units(3, 4), seed + "|cov"),
                      categories=dict(Counter(r[f"{f}__category"] for r in sel)),
                      abstained=sum(r[f"{f}__category"] == "ABSTAINED" for r in sel))
    return res


# ------------------------------------------------------------------------------------------------ holdings
def score_holdings(task, truth, pred, design, pages_by_sha, adjudication):
    G, P = group(truth), group(pred)
    rows = []
    for iid in sorted(design):
        d = design[iid]
        g = [r for r in G.get(iid, []) if not task.is_null_row(r)]
        p = [r for r in P.get(iid, []) if not task.is_null_row(r)]
        for gr, pr in align(task, g, p):
            r = dict(item_id=iid, court=d["court"], stratum=d["stratum"], weight=d["weight"],
                     pred_id=(pr or {}).get("pred_id", ""), gold_type=(gr or {}).get("item_type", ""),
                     pred_type=(pr or {}).get("item_type", ""), gold_opinion=(gr or {}).get("opinion", ""),
                     pred_opinion=(pr or {}).get("opinion", ""), matched=bool(gr and pr),
                     anchor=anchor_status(pr, pages_by_sha, d["sha256"]) if pr else "")
            r["strict"] = r["matched"] and r["gold_type"] == r["pred_type"] and \
                task.family("opinion", r["gold_opinion"]) == task.family("opinion", r["pred_opinion"])
            r["category"] = ("MISSED" if not pr else "UNMATCHED_PREDICTION" if not gr else
                             "CORRECT" if r["strict"] else
                             "WRONG_TYPE" if r["gold_type"] != r["pred_type"] else "WRONG_OPINION")
            rows.append(r)
    return rows


def aggregate_holdings(task, rows, design, adjudication, label, subset=lambda r: True):
    sel = [r for r in rows if subset(r)]
    out = {}
    for t in ("holding", "question_of_law"):
        rec = defaultdict(lambda: [0, 0, 0])
        prc = defaultdict(lambda: [0, 0, 0])
        for r in sel:
            if r["gold_type"] == t:
                rec[r["item_id"]][0] += r["matched"] and r["pred_type"] == t
                rec[r["item_id"]][1] += 1
                rec[r["item_id"]][2] += r["strict"]
            if r["pred_type"] == t:
                prc[r["item_id"]][0] += r["matched"] and r["gold_type"] == t
                prc[r["item_id"]][1] += 1
                prc[r["item_id"]][2] += r["strict"]
        def U(d, i, j):
            return [(k, design[k]["stratum"], design[k]["weight"], v[i], v[j]) for k, v in d.items()]
        seed = f"c13-score|holdings|{label}|{t}"
        out[t] = dict(recall=estimate(U(rec, 0, 1), seed + "|r"), recall_strict=estimate(U(rec, 2, 1), seed + "|rs"),
                      precision_reference_match_LOWER_BOUND=estimate(U(prc, 0, 1), seed + "|p"))
        if adjudication:
            adj = defaultdict(lambda: [0, 0])
            for r in sel:
                lab = adjudication.get(r["pred_id"]) if r["pred_type"] == t else None
                if lab in ("CORRECT", "INCORRECT"):
                    adj[r["item_id"]][0] += lab == "CORRECT"
                    adj[r["item_id"]][1] += 1
            out[t]["precision_true_adjudicated"] = estimate(U(adj, 0, 1), seed + "|pt")
        # judgment-level macro recall beside the pooled figure
        mac = [v[0] / v[1] for v in rec.values() if v[1]]
        out[t]["recall_macro_unweighted"] = S.rnd(sum(mac) / len(mac)) if mac else None
    out["categories"] = dict(Counter(r["category"] for r in sel))
    return out


# ------------------------------------------------------------------------------------------------ driver
def load_design(holdout, sample_path=None, item_map_path=None):
    sample = read_csv(sample_path or OUT / "holdouts" / holdout / "SAMPLE.csv")
    imap = read_csv(item_map_path or OUT / "holdouts" / holdout / "ITEM_MAP.csv")
    by_unit = {(r["judgment_key"], r["page"]): r for r in sample}
    design = {}
    for m in imap:
        s = by_unit[(m["judgment_key"], m["page"])]
        design[m["item_id"]] = dict(court=s["court"], stratum=s["stratum"], weight=float(s["design_weight"]),
                                    sha256=s["rep_sha256"])
    return design


def run(task_name, holdout, truth, pred, design, pages_by_sha=None, adjudication=None):
    task = TASKS[task_name]
    pages_by_sha = pages_by_sha or {}
    unknown = ({r["item_id"] for r in truth} | {r["item_id"] for r in pred}) - set(design)
    if unknown:
        raise ValueError(f"{len(unknown)} item(s) not in the holdout design, e.g. {sorted(unknown)[:3]}")
    for i, r in enumerate(pred):
        r.setdefault("pred_id", f"P{i + 1:05d}")
        if not r["pred_id"]:
            r["pred_id"] = f"P{i + 1:05d}"
    tgt = TARGETS[task_name]
    res = dict(task=task_name, holdout=holdout, items=len(design), status_note="AUTOMATED_CANDIDATE_NOT_VERIFIED "
               "outputs scored against AI-coded reference annotations unless the store manifest says otherwise",
               targets=tgt)
    if task_name == "holdings":
        rows = score_holdings(task, truth, pred, design, pages_by_sha, adjudication)
        agg = lambda lab, sub=lambda r: True: aggregate_holdings(task, rows, design, adjudication, lab, sub)  # noqa
        res["overall"] = agg("overall")
        h = res["overall"]["holding"]
        prec = h.get("precision_true_adjudicated") or h["precision_reference_match_LOWER_BOUND"]
        res["milestone"] = dict(precision_basis=("true (blind adjudication)" if "precision_true_adjudicated" in h
                                                 else "reference-match LOWER BOUND (no adjudication supplied)"),
                                precision=target_status(prec, tgt["precision"]),
                                recall=target_status(h["recall"], tgt["coverage"]),
                                note="Interim research milestone (P>=80%, R>=60%); not operational acceptance.")
    else:
        rows = score_keyed(task, truth, pred, design, pages_by_sha)
        agg = lambda lab, sub=lambda r: True: aggregate(task, rows, design, lab, sub)  # noqa
        res["overall"] = agg("overall")
        res["targets_status"] = {f: dict(strict_precision=target_status(v["strict_precision"], tgt["precision"]),
                                         coverage=target_status(v["coverage"], tgt["coverage"]))
                                 for f, v in res["overall"].items()}
        res["subsets"] = dict(gold_multi_proceeding=agg("multi", lambda r: r["gold_multi_unit"]),
                              gold_party_specific=agg("party", lambda r: r["gold_party_specific"]))
        if task_name == "relations":
            res["by_predicted_relation_type"] = {
                t: agg(f"type={t}", lambda r, t=t: r.get("relation_type__pred") == t)
                for t in sorted({r.get("relation_type__pred") for r in rows if r.get("relation_type__pred")})}
    res["by_court"] = {c: agg(f"court={c}", lambda r, c=c: r["court"] == c) for c in sorted({r["court"] for r in rows})}
    res["by_stratum"] = {s: agg(f"stratum={s}", lambda r, s=s: r["stratum"] == s)
                         for s in sorted({r["stratum"] for r in rows})}
    anc = Counter(r["anchor"] for r in rows if r["anchor"])
    n_anc = sum(anc.values())
    res["evidence_anchor"] = dict(counts=dict(anc), ok_rate=S.rnd(anc["ANCHOR_OK"] / n_anc) if n_anc else None,
                                  ok_wilson95=[S.rnd(x) for x in S.wilson(anc["ANCHOR_OK"], n_anc)[1:]])
    return res, rows


def self_test():
    """Synthetic end-to-end check of the harness (no corpus, no holdout text)."""
    design = {f"HO13-{i:010x}": dict(court="SC" if i < 4 else "DEL", stratum="A" if i % 2 else "B",
                                      weight=1.0 if i < 4 else 5.0, sha256="0" * 64) for i in range(8)}
    ids = sorted(design)
    truth = [dict(item_id=i, proceeding="CA 1/2020", printed_disposal="dismissed", substantive_result="relief_refused",
                  page="2", excerpt="the appeal is dismissed") for i in ids]
    pred = [dict(item_id=i, proceeding="CA 1/2020", printed_disposal="dismissed" if n != 1 else "dismissed_as_withdrawn",
                 substantive_result="relief_refused" if n != 2 else "", page="2", excerpt="the appeal is dismissed")
            for n, i in enumerate(ids)]
    pages = {"0" * 64: {2: "... The appeal is   dismissed. No costs."}}
    res, rows = run("outcome", "SELFTEST", truth, pred, design, pages)
    pd = res["overall"]["printed_disposal"]
    assert pd["strict_precision"]["k"] == 7 and pd["strict_precision"]["n"] == 8, pd
    assert pd["family_precision"]["k"] == 8
    assert res["overall"]["substantive_result"]["coverage"]["k"] == 7
    assert res["overall"]["substantive_result"]["abstained"] == 1
    assert res["evidence_anchor"]["counts"] == {"ANCHOR_OK": 8}
    assert abs(pd["strict_precision"]["weighted"] - (1 * 3 + 5 * 4) / (1 * 4 + 5 * 4)) < 1e-4, pd
    assert res["targets_status"]["printed_disposal"]["strict_precision"] == "NOT_MET"
    print("c13_score self-test OK")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--check" in argv:
        return self_test()
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=sorted(TASKS)); ap.add_argument("--holdout", required=True)
    ap.add_argument("--truth", required=True); ap.add_argument("--pred", required=True)
    ap.add_argument("--out-dir", required=True); ap.add_argument("--pages"); ap.add_argument("--pred-adjudication")
    ap.add_argument("--store", help="annotation store root; the truth file must be listed in a verified manifest")
    a = ap.parse_args(argv)
    if a.store:
        probs = verify_store(a.store)
        if probs:
            print("annotation store does not verify:\n" + "\n".join(probs)); return 1
        h = sha256_file(a.truth)
        if not any(h in Path(m).read_text(encoding="utf-8") for m in Path(a.store).glob("*/v*/MANIFEST.json")):
            print("truth file is not a stored, versioned annotation set"); return 1
    adj = {r["pred_id"]: r["label"] for r in read_csv(a.pred_adjudication)} if a.pred_adjudication else None
    res, rows = run(a.task, a.holdout, read_csv(a.truth), read_csv(a.pred), load_design(a.holdout),
                    load_pages(a.pages), adj)
    res["inputs"] = dict(truth_sha256=sha256_file(a.truth), pred_sha256=sha256_file(a.pred),
                         harness_sha256=sha256_file(__file__))
    od = Path(a.out_dir); od.mkdir(parents=True, exist_ok=True)
    (od / "RESULTS.json").write_text(render_json(res), encoding="utf-8")
    (od / "ROWS.csv").write_text(render_csv(rows) if rows else "", encoding="utf-8")
    print(f"scored {len(rows)} unit rows -> {od}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
