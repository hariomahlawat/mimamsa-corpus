#!/usr/bin/env python3
"""C13-A0 v1.1: coverage simulation for the validated weighted interval (GA0 review F01, F02).

Synthetic finite populations with the exact registered designs (N_h, n_h from DESIGN.json; no holdout content):
  * H-OUT-C13 precision: true precision p in 0.90..0.99, uniform and heterogeneous by court/stratum; multi-unit
    clusters in BATCH_OR_MULTI; 85% answer rate; 30% "hard" judgments (all-or-nothing errors), as in the reviewer's
    simulation (reviews/scripts/sim_ci.py).
  * H-HOLD-C13 recall: p in 0.5..0.8, 4.1 holdings per SC judgment and 2.5 per HC judgment; registered 75 and the
    full-reserve option (113).
For each scenario: coverage of the 95% design-effect Clopper-Pearson interval (`c13_stats.design_cp`, the v1.1
pass-rule interval) and of the Kish-Wilson interval, bias of the HT ratio, mean lower bound, and the probability
of MET_POINT_ONLY / MET_LOWER_BOUND at the target. Deterministic (seeded).

  python -I -B c13_ci_sim.py [--check] [--quick]
"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import OUT, render_csv, render_json, write_or_check, argv_check  # noqa: E402
import c13_stats as S  # noqa: E402

NSIM = 1000
P_OUT = [0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]
P_HOLD = [0.5, 0.6, 0.7, 0.8]
COURT_OFFSET = {"SC": 0.005, "DEL": -0.005, "PH": -0.02, "JK": -0.035, "ALL": -0.015}


def out_design():
    d = json.loads((OUT / "holdouts/H-OUT-C13/DESIGN.json").read_text(encoding="utf-8"))
    return [(f"{s['court']}|{s['stratum']}", s["court"], s["stratum"], s["N_h"], s["n_h"]) for s in d["strata"]]


def hold_design(full_reserve):
    d = json.loads((OUT / "holdouts/H-HOLD-C13/DESIGN.json").read_text(encoding="utf-8"))
    return [(s["stratum"], s["stratum"].split("|")[0], s["stratum"], s["N_h"],
             s["n_h"] + (s["reserve_n"] if full_reserve else 0)) for s in d["strata"]]


def population_out(design, p, hetero, rng):
    pop = defaultdict(list)
    for cell, court, stratum, N, _ in design:
        for _ in range(N):
            m = 1 + (rng.choice([1, 1, 2, 3, 5]) if stratum == "BATCH_OR_MULTI" else 0)
            ans = sum(rng.random() < 0.85 for _ in range(m))
            q = p
            if hetero:
                q = p + COURT_OFFSET[court] - (0.02 if stratum == "BATCH_OR_MULTI" else 0)
            q = min(max(q, 0.0), 0.999)
            if rng.random() < 0.3:
                cor = ans if rng.random() < q else 0
            else:
                cor = sum(rng.random() < q for _ in range(ans))
            pop[cell].append((cor, ans))
    return pop


def population_hold(design, p, rng):
    pop = defaultdict(list)
    for cell, court, _, N, _ in design:
        mean = 4.1 if court == "SC" else 2.5
        for _ in range(N):
            m = max(1, int(round(rng.gauss(mean, 1.8))))
            q = min(max(p + rng.gauss(0, 0.12), 0.0), 1.0)      # judgment-level heterogeneity (ICC ~ 0.1)
            pop[cell].append((sum(rng.random() < q for _ in range(m)), m))
    return pop


def simulate(design, pop, target, nsim, rng):
    true = sum(c for v in pop.values() for c, _ in v) / sum(a for v in pop.values() for _, a in v)
    cov_cp = cov_kw = met_point = met_lb = 0
    hts, lbs, hws = [], [], []
    for k in range(nsim):
        units = []
        for cell, _, _, N, n in design:
            if not n:
                continue
            for j, (y, x) in enumerate(rng.sample(pop[cell], n)):
                units.append((f"{cell}#{j}", cell, N / n, y, x))
        ci = S.design_cp(units)
        _, klo, khi = S.weighted_wilson(units)
        pos = [u for u in units if u[4] > 0]
        uw = sum(u[3] for u in pos) / sum(u[4] for u in pos)
        cov_cp += ci["lo"] <= true <= ci["hi"]
        cov_kw += klo <= true <= khi
        hts.append(ci["p"]); lbs.append(ci["lo"]); hws.append((ci["hi"] - ci["lo"]) / 2)
        if target is not None and ci["p"] >= target and uw >= target:
            met_point += 1
            met_lb += ci["lo"] >= target
    m = sum(hts) / nsim
    return dict(true=round(true, 4), nsim=nsim, ht_mean=round(m, 4),
                ht_sd=round(math.sqrt(sum((h - m) ** 2 for h in hts) / (nsim - 1)), 4),
                coverage_design_cp95=round(cov_cp / nsim, 4), coverage_kish_wilson95=round(cov_kw / nsim, 4),
                mean_lower_bound_design_cp=round(sum(lbs) / nsim, 4),
                mean_halfwidth_design_cp=round(sum(hws) / nsim, 4),
                p_met_point_only=None if target is None else round(met_point / nsim, 4),
                p_met_lower_bound=None if target is None else round(met_lb / nsim, 4))


def build(nsim=NSIM, p_out=P_OUT, p_hold=P_HOLD):
    rows = []
    od = out_design()
    for hetero in (False, True):
        for p in p_out:
            rng = random.Random(f"c13-ci-sim|out|{hetero}|{p}")
            r = simulate(od, population_out(od, p, hetero, rng), 0.95, nsim, rng)
            rows.append(dict(holdout="H-OUT-C13", estimand="precision", scenario="heterogeneous" if hetero else "uniform",
                             nominal_p=p, target=0.95, **r))
    for full in (False, True):
        hd = hold_design(full)
        for p in p_hold:
            rng = random.Random(f"c13-ci-sim|hold|{full}|{p}")
            r = simulate(hd, population_hold(hd, p, rng), 0.60 if p <= 0.65 else 0.80, nsim, rng)
            rows.append(dict(holdout="H-HOLD-C13" + ("+RESERVE" if full else ""), estimand="recall_or_precision",
                             scenario="judgment_heterogeneity", nominal_p=p, target=0.60 if p <= 0.65 else 0.80, **r))
    worst = min(r["coverage_design_cp95"] for r in rows)
    summ = dict(nsim_per_scenario=nsim, monte_carlo_se_at_095=round(math.sqrt(0.95 * 0.05 / nsim), 4),
                min_coverage_design_cp95=worst,
                min_coverage_design_cp95_outcome_p090_099=min(r["coverage_design_cp95"] for r in rows
                                                              if r["holdout"] == "H-OUT-C13"),
                min_coverage_kish_wilson95=min(r["coverage_kish_wilson95"] for r in rows),
                criterion="validated if every scenario's design-CP coverage >= 0.95",
                validated=worst >= 0.95,
                note=("Bootstrap coverage is not re-simulated here; the GA0 reviewer measured 0.830 (p=0.983) and "
                      "0.923 (heterogeneous) for the v1.0 weighted percentile bootstrap (reviewer scratchpad sim_*.json; review report in reviews/), which is "
                      "why v1.1 no longer uses it for the pass rule."))
    return {"ci_validation/CI_COVERAGE.csv": render_csv(rows), "ci_validation/CI_COVERAGE_SUMMARY.json": render_json(summ)}


def main():
    if "--quick" in sys.argv[1:]:
        out = build(nsim=150, p_out=[0.95, 0.98], p_hold=[0.6])
        print(out["ci_validation/CI_COVERAGE_SUMMARY.json"])
        return 0
    return write_or_check(build(), OUT, argv_check(), "c13_ci_sim")


if __name__ == "__main__":
    sys.exit(main())
