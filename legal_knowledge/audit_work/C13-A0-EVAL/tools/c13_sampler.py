#!/usr/bin/env python3
"""C13-A0 sampling frame tool (sampler v2): stratified sampling with recorded inclusion probabilities.

Generic part (`stratified_sample`): units carry a stratum key; within each stratum the n_h units with the lowest
SHA-256(seed|unit_key) are taken (simple random sampling without replacement, deterministic). Inclusion probability
pi = n_h / N_h and design weight w = N_h / n_h are written on every sampled row. Refusals (C12 coordinator-tools
F05/F06): a unit whose text quality is not USABLE, whose raw path is not valid in a pinned store, which is spent, or
which carries an access marking can never be drawn (`assert_drawable`); shortfalls and reallocations are recorded in
the design file (F07), never silent.

Specific part (`build`): draws the three C13 fresh holdouts, each an independent probability sample of the same
eligible frame (separate seeds; overlap between holdouts is allowed, counted and reported, so every inclusion
probability is unconditional): H-OUT-C13 (outcomes), H-HOLD-C13 (holdings, plus a ranked reserve tranche),
H-REL-C13 (citing pages).
The sample files carry strata and weights and are for the evaluator only; coders receive blinded packets
(c13_coding.py). Nobody reads holdout texts for development.

  python -I -B c13_sampler.py [--check]
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import (C11, C12, OUT, read_csv, render_csv, render_json, seeded_hash, sha256_file,  # noqa: E402
                        write_or_check, argv_check)
import c13_stats as S  # noqa: E402

COURTS = ["SC", "DEL", "PH", "JK", "ALL"]
OUT_STRATA = ["BATCH_OR_MULTI", "PARTY_SPECIFIC", "PENSION_OR_DISCIPLINARY", "OTHER"]

# ------------------------------------------------------------------ pre-registered design constants (PROTOCOL_C13 s.4)
SEED_OUT, SEED_HOLD, SEED_REL = "mimamsa-c13-h-out", "mimamsa-c13-h-hold", "mimamsa-c13-h-rel"
OUT_COURT_N = {"SC": 70, "DEL": 70, "PH": 70, "JK": 45, "ALL": 45}          # 300 judgments
OUT_STRATUM_SHARE = {"BATCH_OR_MULTI": 0.30, "PARTY_SPECIFIC": 0.15}         # remainder: proportional, min 5 each
OUT_TARGET_P, OUT_TARGET_COV = 0.95, 0.85
HOLD_TARGET_P, HOLD_TARGET_R, HOLD_HALFWIDTH = 0.80, 0.60, 0.07
HOLD_HC_MEAN_HOLDINGS_ASSUMED = 2.5      # no HC holdings reference exists: assumption, re-checked at GA2 (reserve rule)
HOLD_SC_SHARE = 0.40
HOLD_HC_MIN_PAGES = 5
REL_PAGE_N = {"TREATMENT_CUE": 50, "RESOLVED_CITATION": 50, "UNRESOLVED_CITATION_ONLY": 40, "NO_DETECTED_CITATION": 20}


class NotDrawable(ValueError):
    pass


def assert_drawable(u):
    """Refuse any unit that must never enter a fresh holdout (F05 text layer, F06 raw path, spent, markings)."""
    if u.get("text_quality") != "USABLE":
        raise NotDrawable(f"{u.get('judgment_key')}: text quality {u.get('text_quality')} is not USABLE")
    if str(u.get("rep_raw_store", "")).startswith("NOT_FOUND") or not u.get("rep_raw_path"):
        raise NotDrawable(f"{u.get('judgment_key')}: raw path not valid in a pinned store")
    if u.get("spent_sets"):
        raise NotDrawable(f"{u.get('judgment_key')}: spent ({u['spent_sets']})")
    if u.get("eligible_fresh_holdout") not in ("true", True):
        raise NotDrawable(f"{u.get('judgment_key')}: not eligible ({u.get('ineligibility_reasons')})")


def stratified_sample(units, stratum_of, key_of, alloc, seed, check=assert_drawable):
    """units: list of dicts; alloc: {stratum: n_h}. Returns (sample rows, per-stratum design rows)."""
    by = defaultdict(list)
    for u in units:
        by[stratum_of(u)].append(u)
    sample, design = [], []
    for h in sorted(alloc):
        pool = sorted(by.get(h, []), key=lambda u: seeded_hash(seed, key_of(u)))
        N, n = len(pool), alloc[h]
        if n > N:
            raise ValueError(f"stratum {h}: allocation {n} exceeds population {N}")
        take = pool[:n]
        for u in take:
            check(u)
        pi = n / N if N else 0.0
        for rank, u in enumerate(take, 1):
            sample.append(dict(u, _stratum=h, _rank=rank, _N_h=N, _n_h=n, _pi=round(pi, 6),
                               _weight=round(N / n, 6) if n else 0.0))
        design.append(dict(stratum=h, N_h=N, n_h=n, inclusion_probability=round(pi, 6),
                           design_weight=round(N / n, 6) if n else "", seed=seed))
    return sample, design


# ------------------------------------------------------------------ H-OUT-C13 allocation
def allocate_out(pop_counts):
    """pop_counts: {(court, stratum): N}. Returns (alloc {(court,stratum): n}, notes)."""
    alloc, notes = {}, []
    for c in COURTS:
        nc = OUT_COURT_N[c]
        N = {s: pop_counts.get((c, s), 0) for s in OUT_STRATA}
        if sum(N.values()) < nc:
            raise ValueError(f"court {c}: population {sum(N.values())} below allocation {nc}")
        a = {}
        for s, share in OUT_STRATUM_SHARE.items():
            want = round(nc * share)
            a[s] = min(N[s], want)
            if a[s] < want:
                notes.append(f"{c}/{s}: wanted {want}, population {N[s]}: took all {a[s]}; "
                             f"{want - a[s]} slot(s) reallocated to PENSION_OR_DISCIPLINARY/OTHER proportionally")
        rest = nc - sum(a.values())
        rem = ["PENSION_OR_DISCIPLINARY", "OTHER"]
        tot = sum(N[s] for s in rem)
        a1 = max(min(5, N[rem[0]]), min(N[rem[0]], round(rest * N[rem[0]] / tot)))
        a1 = min(a1, rest - min(5, N[rem[1]]))
        a[rem[0]], a[rem[1]] = a1, rest - a1
        for s in rem:
            if a[s] > N[s]:
                raise ValueError(f"{c}/{s}: allocation exceeds population")
        for s in OUT_STRATA:
            alloc[(c, s)] = a[s]
    return alloc, notes


def out_size_justification(sample):
    """CI-width / power calculation for H-OUT-C13 at the 95% precision target (recorded in DESIGN.json)."""
    n = len(sample)
    covered = n * OUT_TARGET_COV
    deff = S.kish_deff([r["_weight"] for r in sample])
    per_court = {}
    for c in COURTS:
        rs = [r for r in sample if r["court"] == c]
        nc = len(rs) * OUT_TARGET_COV
        dc = S.kish_deff([r["_weight"] for r in rs])
        per_court[c] = dict(judgments=len(rs), expected_covered=round(nc, 1), kish_deff_within_court=S.rnd(dc),
                            wilson_halfwidth_at_p95_unweighted=S.rnd(S.wilson_halfwidth(OUT_TARGET_P, nc)),
                            wilson_halfwidth_at_p95_weighted_neff=S.rnd(S.wilson_halfwidth(OUT_TARGET_P, nc / dc)))
    return dict(
        judgments=n, assumed_coverage=OUT_TARGET_COV, expected_covered_judgments=round(covered, 1),
        note=("Judgment-level calculation (conservative: multi-proceeding judgments add proceedings but are "
              "clustered, handled by the judgment-cluster bootstrap)."),
        power_one_sided=dict(
            question="covered decisions needed so that, with 80% power, the one-sided 95% test rejects "
                     "H0: precision <= 0.95 when true precision is 0.98",
            n_required=S.n_one_sided_power(0.95, 0.98)),
        overall_wilson_halfwidth_at_p95_unweighted=S.rnd(S.wilson_halfwidth(OUT_TARGET_P, covered)),
        kish_deff_overall=S.rnd(deff),
        overall_wilson_halfwidth_at_p95_weighted_neff=S.rnd(S.wilson_halfwidth(OUT_TARGET_P, covered / deff)),
        coverage_wilson_halfwidth_at_c85_unweighted=S.rnd(S.wilson_halfwidth(OUT_TARGET_COV, n)),
        per_court=per_court,
        limitation=("If true precision is close to 0.95, no feasible holdout can show it is >= 0.95; the protocol "
                    "reports the point estimate and interval and states 'met' only on the point estimate rule "
                    "defined in PROTOCOL_C13.md s.6, with the lower bound shown beside it."))


# ------------------------------------------------------------------ H-HOLD-C13 size
def hold_size():
    """Size from the ±7pp target, a design effect estimated on the C12 holdings reference (dev data)."""
    rows = read_csv(C12 / "holdings_eval" / "EVALUATION_ROWS.csv")
    groups = defaultdict(list)
    for r in rows:
        if r["row_kind"] == "reference" and r["item_type"] == "holding":
            groups[r["judgment_id"]].append(1 if r["matched_holding_items_primary"] else 0)
    m_sc = sum(len(g) for g in groups.values()) / len(groups)
    icc = S.icc_anova(list(groups.values()))
    m_bar = HOLD_SC_SHARE * m_sc + (1 - HOLD_SC_SHARE) * HOLD_HC_MEAN_HOLDINGS_ASSUMED
    deff = 1 + (m_bar - 1) * icc
    n_rec = S.n_for_halfwidth(HOLD_TARGET_R, HOLD_HALFWIDTH)
    n_prec = S.n_for_halfwidth(HOLD_TARGET_P, HOLD_HALFWIDTH)
    gold_needed = math.ceil(n_rec * deff)
    judgments = math.ceil(gold_needed / m_bar)
    return dict(c12_reference_judgments=len(groups), c12_mean_holdings_per_sc_judgment=S.rnd(m_sc),
                c12_icc_recall_hits=S.rnd(icc), hc_mean_holdings_assumed=HOLD_HC_MEAN_HOLDINGS_ASSUMED,
                sc_share=HOLD_SC_SHARE, mean_holdings_per_judgment=S.rnd(m_bar), design_effect=S.rnd(deff),
                recall_neff_for_halfwidth=n_rec, precision_neff_for_halfwidth=n_prec,
                precision_items_needed_with_deff=math.ceil(n_prec * deff),
                gold_holdings_needed=gold_needed, judgments=judgments,
                sc_judgments=math.ceil(judgments * HOLD_SC_SHARE),
                hc_judgments=judgments - math.ceil(judgments * HOLD_SC_SHARE),
                reserve_rule=("A reserve tranche of 50% more judgments, ranked by the same seed, is drawn now. At GA2 "
                              "(after both annotators finish and before any extractor output is scored) the reserve is "
                              "opened in rank order, stratum by stratum, only if adjudicated gold holdings fall below "
                              "gold_holdings_needed; inclusion probabilities are then recomputed from the opened n_h."))


def hold_stratum(u):
    pages = int(u["rep_text_pages"] or 0)
    if u["court"] == "SC":
        return "SC|MULTI_OPINION_CUE" if int(u["multi_opinion_cues"] or 0) > 0 else \
            ("SC|LONG_15P_PLUS" if pages >= 15 else "SC|SHORT_UNDER_15P")
    return f"HC_{u['court']}|" + ("LONG_15P_PLUS" if pages >= 15 else "MEDIUM_5_14P")


TAKE_ALL = {"SC|MULTI_OPINION_CUE"}      # over-sampled: every eligible multi-opinion SC judgment is taken


def allocate_proportional(pop, total, minimum=2):
    """Proportional allocation with a per-stratum minimum (largest-remainder rounding, capped at N_h); strata in
    TAKE_ALL are taken whole first."""
    keys = sorted(pop)
    a = {k: (pop[k] if k in TAKE_ALL else min(pop[k], minimum)) for k in keys}
    left = total - sum(a.values())
    tot = sum(pop.values())
    raw = {k: total * pop[k] / tot for k in keys}
    while left > 0:
        k = max((k for k in keys if a[k] < pop[k] and k not in TAKE_ALL), key=lambda k: (raw[k] - a[k], k))
        a[k] += 1
        left -= 1
    return a


# ------------------------------------------------------------------ H-REL-C13 population of citing pages
def rel_pages(eligible_by_jid, rep_sha):
    rel = C11 / "relations" / "outputs"
    cls = defaultdict(set)
    for r in read_csv(rel / "CASE_CITATION_GRAPH.csv"):
        j = r["source_judgment_id"]
        if j in eligible_by_jid and r["zone"] == "BODY" and r["page"].isdigit():
            cls[(j, int(r["page"]))].add("RESOLVED" if r["target_state"] == "RESOLVED" else "UNRESOLVED")
    for r in read_csv(rel / "TREATMENT_CANDIDATES.csv"):
        j = r["source_judgment_id"]
        if j in eligible_by_jid and r["cue_page"].isdigit():
            cls[(j, int(r["cue_page"]))].add("TREATMENT")
    pages = []
    for (j, p), c in cls.items():
        k = "TREATMENT_CUE" if "TREATMENT" in c else "RESOLVED_CITATION" if "RESOLVED" in c else \
            "UNRESOLVED_CITATION_ONLY"
        pages.append(dict(eligible_by_jid[j], page=p, page_class=k))
    seen = set(cls)
    for j, u in eligible_by_jid.items():   # pages with no detected citation (miss / recall check)
        for p in range(1, int(u["rep_text_pages"] or 0) + 1):
            if (j, p) not in seen:
                pages.append(dict(u, page=p, page_class="NO_DETECTED_CITATION"))
    return pages


SAMPLE_COLS = ["holdout", "stratum", "rank_in_stratum", "N_h", "n_h", "inclusion_probability", "design_weight",
               "judgment_key", "court", "year_band", "rep_sha256", "rep_doc_id", "rep_raw_path", "rep_raw_store",
               "rep_text_pages", "page"]


def rows_out(holdout, sample, page=False):
    return [dict(holdout=holdout, stratum=r["_stratum"], rank_in_stratum=r["_rank"], N_h=r["_N_h"], n_h=r["_n_h"],
                 inclusion_probability=r["_pi"], design_weight=r["_weight"], judgment_key=r["judgment_key"],
                 court=r["court"], year_band=r["year_band"], rep_sha256=r["rep_sha256"], rep_doc_id=r["rep_doc_id"],
                 rep_raw_path=r["rep_raw_path"], rep_raw_store=r["rep_raw_store"], rep_text_pages=r["rep_text_pages"],
                 page=r.get("page", "") if page else "")
            for r in sorted(sample, key=lambda r: (r["_stratum"], r["_rank"]))]


def build():
    frame_path = OUT / "frame" / "FRAME_JUDGMENTS.csv"
    excl_path = OUT / "exclusions" / "EXCLUDED_JUDGMENTS.csv"
    frame = read_csv(frame_path)
    elig = [u for u in frame if u["eligible_fresh_holdout"] == "true"]
    outputs = {}
    provenance = dict(frame_sha256=sha256_file(frame_path), exclusions_sha256=sha256_file(excl_path),
                      eligible_judgments=len(elig))

    # ---- H-OUT-C13
    pop = Counter((u["court"], u["stratum"]) for u in elig)
    alloc, notes = allocate_out(pop)
    so, design_o = stratified_sample(elig, lambda u: (u["court"], u["stratum"]), lambda u: u["judgment_key"],
                                     alloc, SEED_OUT)
    for r in design_o:
        r["court"], r["stratum"] = r.pop("stratum")
    outputs["holdouts/H-OUT-C13/SAMPLE.csv"] = render_csv(rows_out("H-OUT-C13", so), SAMPLE_COLS)
    outputs["holdouts/H-OUT-C13/DESIGN.json"] = render_json(dict(
        holdout="H-OUT-C13", unit="judgment (representative copy; all copies of a judgment are one cluster)",
        seed=SEED_OUT, selection="lowest SHA-256(seed|judgment_key) within each court x stratum",
        strata=design_o, reallocation_notes=notes, size_justification=out_size_justification(so), **provenance))

    # ---- H-HOLD-C13 (+ reserve)
    hs = hold_size()
    hpop_units = [u for u in elig if (u["court"] == "SC" or int(u["rep_text_pages"] or 0) >= HOLD_HC_MIN_PAGES)]
    hpop = Counter(hold_stratum(u) for u in hpop_units)
    sc_pop = {k: v for k, v in hpop.items() if k.startswith("SC|")}
    hc_pop = {k: v for k, v in hpop.items() if not k.startswith("SC|")}
    main_alloc = dict(allocate_proportional(sc_pop, hs["sc_judgments"]), **allocate_proportional(hc_pop,
                                                                                                hs["hc_judgments"]))
    res_total = math.ceil(hs["judgments"] * 0.5)
    tot_alloc = dict(allocate_proportional(sc_pop, min(sum(sc_pop.values()), hs["sc_judgments"]
                                                      + math.ceil(res_total * HOLD_SC_SHARE))),
                     **allocate_proportional(hc_pop, hs["hc_judgments"] + res_total
                                             - math.ceil(res_total * HOLD_SC_SHARE)))
    tot_alloc = {k: max(v, main_alloc[k]) for k, v in tot_alloc.items()}
    sh_all, _ = stratified_sample(hpop_units, hold_stratum, lambda u: u["judgment_key"], tot_alloc, SEED_HOLD)
    sh = [r for r in sh_all if r["_rank"] <= main_alloc[r["_stratum"]]]
    reserve = [r for r in sh_all if r["_rank"] > main_alloc[r["_stratum"]]]
    for r in sh:
        r["_n_h"] = main_alloc[r["_stratum"]]
        r["_pi"] = round(r["_n_h"] / r["_N_h"], 6)
        r["_weight"] = round(r["_N_h"] / r["_n_h"], 6)
    design_h = [dict(stratum=k, N_h=hpop[k], n_h=main_alloc[k], reserve_n=tot_alloc[k] - main_alloc[k],
                     inclusion_probability=round(main_alloc[k] / hpop[k], 6),
                     design_weight=round(hpop[k] / main_alloc[k], 6)) for k in sorted(main_alloc)]
    outputs["holdouts/H-HOLD-C13/SAMPLE.csv"] = render_csv(rows_out("H-HOLD-C13", sh), SAMPLE_COLS)
    reserve_rows = rows_out("H-HOLD-C13-RESERVE", reserve)
    for r in reserve_rows:
        r["inclusion_probability"] = r["design_weight"] = "RECOMPUTED_ONLY_IF_OPENED"
    outputs["holdouts/H-HOLD-C13/RESERVE.csv"] = render_csv(reserve_rows, SAMPLE_COLS)
    outputs["holdouts/H-HOLD-C13/DESIGN.json"] = render_json(dict(
        holdout="H-HOLD-C13", unit="judgment", seed=SEED_HOLD,
        population=("eligible judgments (overlap with H-OUT-C13 allowed); all SC, and HC judgments with >= %d text pages"
                    % HOLD_HC_MIN_PAGES),
        selection="lowest SHA-256(seed|judgment_key) within each stratum; reserve = next ranks in the same order",
        strata=design_h, size_justification=hs, **provenance))

    # ---- H-REL-C13 (citing pages)
    by_jid = {}
    for u in elig:
        by_jid["J-" + u["rep_sha256"][:16]] = u
    pages = rel_pages(by_jid, None)
    for p in pages:
        p["_unit"] = f"{p['judgment_key']}#p{p['page']}"
        p["_grp"] = ("SC" if p["court"] == "SC" else "HC") + "|" + p["page_class"]
    rpop = Counter(p["_grp"] for p in pages)
    ralloc = {}
    for cls, n in REL_PAGE_N.items():
        sc, hc = rpop.get("SC|" + cls, 0), rpop.get("HC|" + cls, 0)
        nsc = min(sc, n // 2)
        ralloc["SC|" + cls], ralloc["HC|" + cls] = nsc, min(hc, n - nsc)
    ralloc = {k: v for k, v in ralloc.items() if rpop.get(k)}
    sr, design_r = stratified_sample(pages, lambda p: p["_grp"], lambda p: p["_unit"], ralloc, SEED_REL)
    outputs["holdouts/H-REL-C13/SAMPLE.csv"] = render_csv(rows_out("H-REL-C13", sr, page=True), SAMPLE_COLS)
    n_rel = sum(ralloc.values())
    outputs["holdouts/H-REL-C13/DESIGN.json"] = render_json(dict(
        holdout="H-REL-C13", unit="citing page (representative copy x page); clustered by judgment",
        seed=SEED_REL, population=("pages of eligible judgments (overlap with H-OUT/H-HOLD allowed), classed from the C11 citation "
                                   "graph and treatment candidates (BODY zone, first-occurrence page), plus pages with "
                                   "no detected citation (to measure misses)"),
        page_class_rule="TREATMENT_CUE > RESOLVED_CITATION > UNRESOLVED_CITATION_ONLY; else NO_DETECTED_CITATION",
        selection="lowest SHA-256(seed|judgment_key#pN) within each court-group x page class",
        strata=design_r, pages=n_rel, judgments=len({r["judgment_key"] for r in sr}),
        size_justification=dict(
            note=("Coders record every case citation and treatment on each sampled page, so precision and recall are "
                  "measured on the same units. With about 3 citations per citing page, 140 citing pages give about "
                  "400 citation instances; the 50 treatment-cue pages give a per-type precision interval of about "
                  "+/-%.0fpp at p=0.8 for the common types (APPLIES, CITES); rare types (OVERRULES, DISTINGUISHES) "
                  "get descriptive counts only." % (100 * S.wilson_halfwidth(0.8, 120)))),
        **provenance))
    reg = {"H-OUT-C13": {}, "H-HOLD-C13": {}, "H-REL-C13": {}}
    import hashlib
    for k, v in outputs.items():
        for h in reg:
            if k.startswith(f"holdouts/{h}/"):
                reg[h][k] = hashlib.sha256(v.encode()).hexdigest()
    outputs["holdouts/HOLDOUT_REGISTRATION.json"] = render_json(dict(
        purpose="Proves later extractor freezes post-date the fresh holdouts: the sha256 below are committed with "
                "the samples; a freeze commit must be a descendant of the commit that adds this file.",
        holdouts={h: dict(files=reg[h]) for h in reg},
        overlaps={"H-OUT_and_H-HOLD": len({r["judgment_key"] for r in so} & {r["judgment_key"] for r in sh}),
                  "H-OUT_and_H-REL": len({r["judgment_key"] for r in so} & {r["judgment_key"] for r in sr}),
                  "H-HOLD_and_H-REL": len({r["judgment_key"] for r in sh} & {r["judgment_key"] for r in sr})},
        sizes={"H-OUT-C13": len(so), "H-HOLD-C13": len(sh), "H-HOLD-C13-RESERVE": len(reserve),
               "H-REL-C13_pages": len(sr)},
        rule="Holdout texts are not read for development. Spent sets are excluded (outputs/exclusions).",
        status="DRAWN_NOT_CODED"))
    return outputs


def main():
    return write_or_check(build(), OUT, argv_check(), "c13_sampler")


if __name__ == "__main__":
    sys.exit(main())
