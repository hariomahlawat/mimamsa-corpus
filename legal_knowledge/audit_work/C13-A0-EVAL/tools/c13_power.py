#!/usr/bin/env python3
"""C13-A0 v1.1: honest size restatement for the WEIGHTED headline estimators (GA0 review F02, F03).

Reads the registered designs (unchanged; no redraw) and the coverage simulation, and states what each holdout can
and cannot show: Kish design effects of the design weights, effective n, expected half-widths of the validated
interval (design-effect Clopper-Pearson), and the simulated probability of each pass status.

  python -I -B c13_power.py [--check]
"""
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import OUT, read_csv, render_json, write_or_check, argv_check  # noqa: E402
import c13_stats as S  # noqa: E402

PARTY_PPV = (0.11, 0.04, 0.28)     # GA0 review: 3/27 candidates truly party-differentiated (95% CI 4-28%)


def kish(rows):
    return S.kish_deff([float(r["design_weight"]) for r in rows])


def build():
    sim = read_csv(OUT / "ci_validation/CI_COVERAGE.csv")
    out = read_csv(OUT / "holdouts/H-OUT-C13/SAMPLE.csv")
    hold = read_csv(OUT / "holdouts/H-HOLD-C13/SAMPLE.csv")
    rel = read_csv(OUT / "holdouts/H-REL-C13/SAMPLE.csv")
    hd = json.loads((OUT / "holdouts/H-HOLD-C13/DESIGN.json").read_text(encoding="utf-8"))
    res = {}
    d = kish(out)
    cov = 255.0
    res["H-OUT-C13"] = dict(
        judgments=len(out), kish_deff=S.rnd(d), expected_covered=cov, n_eff_covered=S.rnd(cov / d, 1),
        kish_wilson_halfwidth_at_p095=S.rnd(S.wilson_halfwidth(0.95, cov / d)),
        per_court={c: dict(judgments=len(rs), kish_deff=S.rnd(kish(rs)),
                           kish_wilson_halfwidth_at_p095=S.rnd(S.wilson_halfwidth(0.95, 0.85 * len(rs) / kish(rs))))
                   for c in sorted({r["court"] for r in out}) for rs in [[r for r in out if r["court"] == c]]},
        simulated_by_true_precision=[dict(scenario=r["scenario"], true=float(r["true"]),
                                          mean_lower_bound=float(r["mean_lower_bound_design_cp"]),
                                          mean_halfwidth=float(r["mean_halfwidth_design_cp"]),
                                          p_met_point_only=float(r["p_met_point_only"]),
                                          p_met_lower_bound=float(r["p_met_lower_bound"]))
                                     for r in sim if r["holdout"] == "H-OUT-C13"],
        can_show=("Point estimates of weighted strict precision and coverage per field with validated 95% intervals "
                  "of about +/-4-5pp overall; whether the point estimate reaches 95%/85%; per-court figures with "
                  "intervals of roughly +/-6-10pp."),
        cannot_show=("MET_LOWER_BOUND (validated lower bound >= 0.95) is practically reachable only if true precision "
                     "is about 0.99 or higher: simulated probability about 0.49 at a true 0.98 and about 0.83 at 0.99 "
                     "(uniform), and lower under heterogeneity. A true precision of 0.95-0.97 cannot be distinguished "
                     "from the target. Per-stratum figures for small cells are descriptive."),
        power_note=("The v1.0 figure (253 covered decisions for 80%% power, 0.98 vs 0.95) applies to the UNWEIGHTED "
                    "one-sided test only; the weighted headline has n_eff about %d." % round(cov / d)))
    hk = kish(hold)
    gold = hd["size_justification"]["gold_holdings_needed"]
    m_bar = hd["size_justification"]["mean_holdings_per_judgment"]
    cl = hd["size_justification"]["design_effect"]
    res["H-HOLD-C13"] = dict(
        judgments=len(hold), kish_deff_weights=S.rnd(hk), cluster_deff=cl, combined_deff=S.rnd(hk * cl),
        expected_gold_holdings=round(len(hold) * m_bar), recall_halfwidth_at_p060=S.rnd(
            S.wilson_halfwidth(0.6, len(hold) * m_bar / (hk * cl))),
        precision_halfwidth_at_p080_if_items_equal_gold=S.rnd(S.wilson_halfwidth(0.8, len(hold) * m_bar / (hk * cl))),
        simulated=[dict(design=r["holdout"], true=float(r["true"]), mean_halfwidth=float(r["mean_halfwidth_design_cp"]),
                        coverage=float(r["coverage_design_cp95"])) for r in sim if r["holdout"].startswith("H-HOLD")],
        restated=("v1.0 claimed +/-7pp; with the Kish design effect of the weights the weighted half-width is about "
                  "+/-8.5pp (registered 75 judgments). Opening the full registered reserve (113 judgments) before "
                  "coding reduces it to about +/-7pp; see PROTOCOL_C13 s.3.1 for the pre-registered decision rule."),
        gold_holdings_target_v10=gold)
    rk = kish(rel)
    tc = [r for r in rel if r["stratum"] == "TREATMENT_CUE"]
    res["H-REL-C13"] = dict(
        pages=len(rel), kish_deff_overall=S.rnd(rk), kish_deff_treatment_cue_pages=S.rnd(kish(tc)),
        restated=("Weighted overall recall is very imprecise (Kish deff about %.1f, driven by the 20 no-detected-"
                  "citation pages with weights in the hundreds or above); report it as descriptive. Per-type precision "
                  "on treatment-cue pages: about +/-9pp at p=0.8, not +/-7pp. Relations has no owner target."
                  % rk))
    party = [r for r in out if r["stratum"] == "PARTY_SPECIFIC"]
    res["party_specific_expected_gold_units_H-OUT"] = dict(
        party_stratum_judgments=len(party), cue_ppv=PARTY_PPV[0], cue_ppv_ci95=list(PARTY_PPV[1:]),
        expected_true_from_candidates=S.rnd(len(party) * PARTY_PPV[0], 1),
        expected_range=[S.rnd(len(party) * PARTY_PPV[1], 1), S.rnd(len(party) * PARTY_PPV[2], 1)],
        plus_unknown_from_other_strata="unknown base rate outside the cue; expected small",
        decision="The party-specific breakdown is DESCRIPTIVE ONLY: no pass/fail status is computed or claimed.")
    res["validated_interval"] = json.loads((OUT / "ci_validation/CI_COVERAGE_SUMMARY.json").read_text(encoding="utf-8"))
    return {"holdouts/SIZE_RESTATEMENT_V1_1.json": render_json(res)}


def main():
    return write_or_check(build(), OUT, argv_check(), "c13_power")


if __name__ == "__main__":
    sys.exit(main())
