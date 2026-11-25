#!/usr/bin/env python3
"""C13-A0 generic scoring harness (pre-registered; PROTOCOL_C13.md s.5-6).

Scores frozen predictions against frozen reference annotations for one task (outcome, holdings, relations):
strict and family precision, coverage (recall), abstention, per-court / per-stratum / per-subset breakdowns,
Horvitz-Thompson weighted estimates with Kish-Wilson and stratified judgment-cluster bootstrap intervals, unweighted
Wilson intervals, evidence-anchor verification against page text, and a failure taxonomy.

  python -I -B c13_score.py --task outcome --holdout H-OUT-C13 --truth TRUTH.csv --pred PRED.csv \
      --store STORE_DIR --out-dir DIR [--pages PAGES.jsonl] [--pred-adjudication ADJ.csv] [--reserve-open all]

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
from c13_tasks import TASKS, norm_ws, uncodable_code  # noqa: E402
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
def collapse(units):
    """Sum units sharing (stratum/design cell, cluster): judgment clusters for H-REL pages (GA0 review F10)."""
    agg = {}
    for c, h, w, y, x in units:
        a = agg.setdefault((h, c), [c, h, w, 0.0, 0.0])
        a[3] += y; a[4] += x
    return [tuple(v) for _, v in sorted(agg.items())]


def estimate(units, seed):
    """units: (cluster, design cell, weight, y, x) for every sampled item in the domain (zeros included).
    Headline interval (v1.1): design-effect Clopper-Pearson (`c13_stats.design_cp`), coverage-validated by
    c13_ci_sim.py. Kish-Wilson and stratified judgment-cluster bootstrap intervals are reported as secondary."""
    units = collapse(units)
    pos = [u for u in units if u[4] > 0]
    k = sum(u[3] for u in pos)
    n = sum(u[4] for u in pos)
    p, lo, hi = S.wilson(k, n)
    blo, bhi = S.stratified_cluster_bootstrap(pos, BOOT_REPS, seed + "|u", weighted=False)
    wp, wlo, whi = S.weighted_wilson(pos)
    wblo, wbhi = S.stratified_cluster_bootstrap(pos, BOOT_REPS, seed + "|w", weighted=True)
    cp = S.design_cp(units)
    return dict(k=S.rnd(k, 3), n=S.rnd(n, 3), clusters=len(pos),
                unweighted=S.rnd(p), unweighted_wilson95=[S.rnd(lo), S.rnd(hi)],
                unweighted_cluster_bootstrap95=[S.rnd(blo), S.rnd(bhi)],
                weighted=S.rnd(wp), weighted_design_cp95=[S.rnd(cp["lo"]), S.rnd(cp["hi"])],
                weighted_design_cp_n_eff=S.rnd(cp.get("n_eff"), 1),
                weighted_kish_wilson95_secondary=[S.rnd(wlo), S.rnd(whi)],
                weighted_cluster_bootstrap95_secondary_not_for_pass_rule=[S.rnd(wblo), S.rnd(wbhi)])


def target_status(est, target, descriptive=False):
    """v1.1 met rule: MET_POINT_ONLY when the weighted and unweighted point estimates reach the target;
    MET_LOWER_BOUND when, in addition, the validated design-CP lower bound reaches it; else NOT_MET."""
    if descriptive:
        return "DESCRIPTIVE_ONLY"
    if target is None or est["weighted"] is None:
        return "NO_TARGET" if target is None else "NOT_ESTIMABLE"
    met_point = est["weighted"] >= target and est["unweighted"] >= target
    lb = est["weighted_design_cp95"][0]
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


def aggregate(task, rows, design, label, subset=lambda r: True, items=None, uncodable=()):
    """Domain estimation: every design item in `items` (default: all) enters with zeros unless it has rows in the
    domain. Uncodable items are outside the scored denominators and are reported (counted separately)."""
    items = sorted(design) if items is None else sorted(items)
    unc = [i for i in items if i in set(uncodable)]
    items = [i for i in items if i not in set(uncodable)]
    res = {}
    for f in task.scored_fields:
        sel = [r for r in rows if subset(r) and r["item_id"] in set(items)]
        per = {iid: [0, 0, 0, 0, 0] for iid in items}   # strict, family, answered, covered, determinable
        for r in sel:
            a = per[r["item_id"]]
            a[0] += r[f"{f}__strict"]; a[1] += r[f"{f}__family"]; a[2] += r[f"{f}__answered"]
            a[3] += r[f"{f}__covered"]; a[4] += r[f"{f}__determinable"]

        def units(i_num, i_den, extra=()):
            return [(design[i]["cluster"], design[i]["cell"], design[i]["weight"], v[i_num], v[i_den])
                    for i, v in per.items()] + list(extra)
        seed = f"c13-score|{task.name}|{label}|{f}"
        cats = Counter(r[f"{f}__category"] for r in sel)
        res[f] = dict(strict_precision=estimate(units(0, 2), seed + "|sp"),
                      family_precision=estimate(units(1, 2), seed + "|fp"),
                      coverage=estimate(units(3, 4), seed + "|cov"),
                      coverage_counting_uncodable_items_as_not_covered=estimate(
                          units(3, 4, [(design[i]["cluster"], design[i]["cell"], design[i]["weight"], 0, 1)
                                       for i in unc]), seed + "|cov_u"),
                      gold_units_undeterminable=cats["PRED_ON_UNDETERMINABLE"] + cats["GOLD_UNDETERMINABLE_NO_PRED"],
                      items_uncodable=len(unc), categories=dict(cats),
                      abstained=cats["ABSTAINED"])
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


def aggregate_holdings(task, rows, design, adjudication, label, subset=lambda r: True, items=None, uncodable=()):
    items_all = [i for i in (sorted(design) if items is None else sorted(items)) if i not in set(uncodable)]
    sel = [r for r in rows if subset(r) and r["item_id"] in set(items_all)]
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
            return [(design[k]["cluster"], design[k]["cell"], design[k]["weight"], d[k][i] if k in d else 0,
                     d[k][j] if k in d else 0) for k in items_all]
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
    out["items_uncodable"] = len([i for i in (sorted(design) if items is None else items) if i in set(uncodable)])
    return out


# ------------------------------------------------------------------------------------------------ driver
def load_design(holdout, sample_path=None, item_map_path=None, reserve_open=None):
    """Item -> design info. reserve_open (H-HOLD only; GA0 F11): None, "all", or {design_cell: k} opening the first k
    reserve ranks of a cell; n_h, inclusion probability and weight are recomputed for the whole cell."""
    sample = read_csv(sample_path or OUT / "holdouts" / holdout / "SAMPLE.csv")
    imap = read_csv(item_map_path or OUT / "holdouts" / holdout / "ITEM_MAP.csv")
    rows = [dict(r, _reserve=False) for r in sample]
    if reserve_open:
        if holdout != "H-HOLD-C13":
            raise ValueError("only H-HOLD-C13 has a reserve")
        res = read_csv(OUT / "holdouts" / holdout / "RESERVE.csv")
        imap += read_csv(OUT / "holdouts" / holdout / "ITEM_MAP_RESERVE.csv")
        base_n = Counter(r["design_cell"] for r in sample)
        for r in res:
            k = r["design_cell"]
            want = int(r["n_h"]) - base_n[k] if reserve_open == "all" else reserve_open.get(k, 0)
            if int(r["rank_in_stratum"]) - base_n[k] <= want:
                rows.append(dict(r, _reserve=True))
    n_cell = Counter(r["design_cell"] for r in rows)
    by_unit = {(r["judgment_key"], r["page"]): r for r in rows}
    design = {}
    for m in imap:
        s_ = by_unit.get((m["judgment_key"], m["page"]))
        if s_ is None:
            continue                     # unopened reserve item
        N, n = int(s_["N_h"]), n_cell[s_["design_cell"]]
        design[m["item_id"]] = dict(court=s_["court"], stratum=s_["stratum"], cell=s_["design_cell"],
                                    weight=N / n, inclusion_probability=n / N, cluster=s_["judgment_key"],
                                    sha256=s_["rep_sha256"], reserve=s_["_reserve"])
    return design


def run(task_name, holdout, truth, pred, design, pages_by_sha=None, adjudication=None, pre_exposed=None):
    """pre_exposed: {judgment_key: {categories}} (c13_sensitivity.load_subset); every headline is also reported
    without the PRIMARY subset and, for outcome, without CASE_NUMBER_REVIEWED (GA0 review F04/F06)."""
    task = TASKS[task_name]
    pages_by_sha = pages_by_sha or {}
    for iid, d in design.items():
        d.setdefault("cluster", iid)
        d.setdefault("cell", d["stratum"])
    unknown = ({r["item_id"] for r in truth} | {r["item_id"] for r in pred}) - set(design)
    if unknown:
        raise ValueError(f"{len(unknown)} item(s) not in the holdout design, e.g. {sorted(unknown)[:3]}")
    for i, r in enumerate(pred):
        r.setdefault("pred_id", f"P{i + 1:05d}")
        if not r["pred_id"]:
            r["pred_id"] = f"P{i + 1:05d}"
    # UNCODABLE items (GA0 F05): all truth rows of the item are UNCODABLE rows. Kept, counted, never replaced.
    G = group(truth)
    uncodable = sorted(i for i, rs in G.items() if rs and all(task.is_uncodable_row(r) for r in rs))
    truth = [r for r in truth if not task.is_uncodable_row(r)]
    tgt = TARGETS[task_name]
    res = dict(task=task_name, holdout=holdout, items=len(design), status_note="AUTOMATED_CANDIDATE_NOT_VERIFIED "
               "outputs scored against AI-coded reference annotations unless the store manifest says otherwise",
               targets=tgt, protocol_version="1.1",
               uncodable=dict(items=len(uncodable), share=S.rnd(len(uncodable) / len(design)) if design else None,
                              codes=dict(Counter(uncodable_code(r) for i in uncodable for r in G[i])),
                              predictions_on_uncodable_items=sum(1 for r in pred if r["item_id"] in set(uncodable)),
                              rule="kept in the sample, outside scored denominators, reported here and as "
                                   "coverage_counting_uncodable_items_as_not_covered; never replaced"))
    if task_name == "holdings":
        rows = score_holdings(task, truth, pred, design, pages_by_sha, adjudication)

        def agg(lab, sub=lambda r: True, items=None):
            return aggregate_holdings(task, rows, design, adjudication, lab, sub, items, uncodable)

        def statuses(a, descriptive=False):
            h = a["holding"]
            prec = h.get("precision_true_adjudicated") or h["precision_reference_match_LOWER_BOUND"]
            return dict(precision=target_status(prec, tgt["precision"], descriptive),
                        recall=target_status(h["recall"], tgt["coverage"], descriptive))
        res["overall"] = agg("overall")
        h = res["overall"]["holding"]
        res["milestone"] = dict(statuses(res["overall"]),
                                precision_basis=("true (blind adjudication)" if "precision_true_adjudicated" in h
                                                 else "reference-match LOWER BOUND (no adjudication supplied)"),
                                note="Interim research milestone (P>=80%, R>=60%); not operational acceptance.")
    else:
        rows = score_keyed(task, truth, pred, design, pages_by_sha)

        def agg(lab, sub=lambda r: True, items=None):
            return aggregate(task, rows, design, lab, sub, items, uncodable)

        def statuses(a, descriptive=False):
            return {f: dict(strict_precision=target_status(v["strict_precision"], tgt["precision"], descriptive),
                            coverage=target_status(v["coverage"], tgt["coverage"], descriptive)) for f, v in a.items()}
        res["overall"] = agg("overall")
        res["targets_status"] = statuses(res["overall"])
        multi = agg("multi", lambda r: r["gold_multi_unit"])
        party = agg("party", lambda r: r["gold_party_specific"])
        res["subsets"] = dict(
            gold_multi_proceeding=dict(estimates=multi, targets_status=statuses(multi)),
            gold_party_specific=dict(estimates=party, targets_status=statuses(party, descriptive=True),
                                     note="DESCRIPTIVE ONLY (PROTOCOL v1.1 s.6.3): too few expected gold units; "
                                          "no pass or fail is claimed"))
        if task_name == "relations":
            res["by_predicted_relation_type"] = {
                t: agg(f"type={t}", lambda r, t=t: r.get("relation_type__pred") == t)
                for t in sorted({r.get("relation_type__pred") for r in rows if r.get("relation_type__pred")})}
    courts = sorted({d["court"] for d in design.values()})
    res["by_court"] = {}
    for c in courts:
        a = agg(f"court={c}", items=[i for i, d in design.items() if d["court"] == c])
        res["by_court"][c] = dict(estimates=a, targets_status=statuses(a))
    res["by_stratum"] = {}
    for st in sorted({d["stratum"] for d in design.values()}):
        a = agg(f"stratum={st}", items=[i for i, d in design.items() if d["stratum"] == st])
        res["by_stratum"][st] = dict(estimates=a, targets_status=statuses(a))
    res["breakdown_rule"] = ("The headline target status is the overall one. Per-court, per-stratum and "
                             "proceeding-specific statuses are reported for the owner; whether 'met' must also hold per "
                             "breakdown is an owner decision (PROTOCOL v1.1 s.6.4). Party-specific is descriptive.")
    if pre_exposed is not None:
        prim = {k for k, c in pre_exposed.items() if c & {"CURATED_KB_CONTENT", "NEAR_IDENTICAL_SPENT_SIBLING"}}
        cn = {k for k, c in pre_exposed.items() if "CASE_NUMBER_REVIEWED" in c}
        sens = {}
        for lab, excl in (("without_primary_pre_exposed", prim), ("without_case_number_reviewed", cn)):
            keep = [i for i, d in design.items() if d["cluster"] not in excl]
            a = agg(lab, items=keep)
            sens[lab] = dict(items_excluded=len(design) - len(keep), estimates=a, targets_status=statuses(a))
        res["sensitivity"] = sens
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
    assert res["subsets"]["gold_party_specific"]["targets_status"]["printed_disposal"]["coverage"] == "DESCRIPTIVE_ONLY"
    assert "SC" in res["by_court"] and "targets_status" in res["by_court"]["SC"]
    # an UNCODABLE item stays out of the denominators and is reported
    truth2 = truth[1:] + [dict(item_id=ids[0], notes="UNCODABLE:SHA_MISMATCH")]
    res2, _ = run("outcome", "SELFTEST", truth2, pred, design, pages)
    assert res2["uncodable"]["items"] == 1 and res2["uncodable"]["codes"] == {"SHA_MISMATCH": 1}
    c2 = res2["overall"]["substantive_result"]
    assert c2["coverage"]["n"] == 7 and c2["coverage_counting_uncodable_items_as_not_covered"]["n"] == 8
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
    ap.add_argument("--store", required=True,
                    help="annotation store root; the truth file must be listed in a verified manifest (GA0 F07)")
    ap.add_argument("--reserve-open", choices=["all"], help="H-HOLD only: score with the full reserve opened")
    a = ap.parse_args(argv)
    if a.store:  # always set: required
        probs = verify_store(a.store)
        if probs:
            print("annotation store does not verify:\n" + "\n".join(probs)); return 1
        h = sha256_file(a.truth)
        if not any(h in Path(m).read_text(encoding="utf-8") for m in Path(a.store).glob("*/v*/MANIFEST.json")):
            print("truth file is not a stored, versioned annotation set"); return 1
    adj = {r["pred_id"]: r["label"] for r in read_csv(a.pred_adjudication)} if a.pred_adjudication else None
    from c13_sensitivity import load_subset
    res, rows = run(a.task, a.holdout, read_csv(a.truth), read_csv(a.pred),
                    load_design(a.holdout, reserve_open=a.reserve_open), load_pages(a.pages), adj,
                    pre_exposed=load_subset(a.holdout))
    res["inputs"] = dict(truth_sha256=sha256_file(a.truth), pred_sha256=sha256_file(a.pred),
                         harness_sha256=sha256_file(__file__))
    od = Path(a.out_dir); od.mkdir(parents=True, exist_ok=True)
    (od / "RESULTS.json").write_text(render_json(res), encoding="utf-8")
    (od / "ROWS.csv").write_text(render_csv(rows) if rows else "", encoding="utf-8")
    print(f"scored {len(rows)} unit rows -> {od}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
