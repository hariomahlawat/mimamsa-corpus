"""Reviewer simulation: HT ratio bias and CI coverage under the H-OUT design (author's c13_stats functions)."""
import sys, json, random, math, time
sys.path.insert(0, sys.argv[1]); import c13_stats as S
design = json.load(open(sys.argv[2]))["strata"]
NSIM, REPS, SCEN = int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
rng = random.Random(20261125)
base = {"SC": 0.985, "DEL": 0.97, "PH": 0.95, "JK": 0.93, "ALL": 0.96}
if SCEN == "p98": base = {k: 0.98 for k in base}
pop = []  # (cell, m_answered, correct)
for s in design:
    cell = (s["court"], s["stratum"])
    for i in range(s["N_h"]):
        m = 1 + (rng.choice([1, 1, 2, 3, 5]) if s["stratum"] == "BATCH_OR_MULTI" else 0)
        ans = sum(rng.random() < 0.85 for _ in range(m))
        p = base[s["court"]] - (0.03 if s["stratum"] == "BATCH_OR_MULTI" else 0) + (-0.02 if s["stratum"] == "PARTY_SPECIFIC" else 0)
        if SCEN == "p98": p = 0.98
        # cluster effect: with prob 0.3 the judgment is 'hard' (all-or-nothing), else independent
        if rng.random() < 0.3:
            ok = rng.random() < p; cor = ans if ok else 0
        else:
            cor = sum(rng.random() < p for _ in range(ans))
        pop.append((cell, ans, cor))
true = sum(c for _, _, c in pop) / sum(a for _, a, _ in pop)
by = {}
for u in pop: by.setdefault(u[0], []).append(u)
alloc = {(s["court"], s["stratum"]): s["n_h"] for s in design}
res = dict(ht=[], uw=[], cov_boot=0, cov_kw=0, cov_uw=0, cov_uboot=0, met_lb=0, met_point=0, lbs=[])
t0 = time.time()
for k in range(NSIM):
    units = []
    for cell, n in alloc.items():
        if not n: continue
        N = len(by[cell]); smp = rng.sample(by[cell], n)
        for j, (c, a, cor) in enumerate(smp):
            units.append((f"{cell}{j}", "|".join(cell), N / n, cor, a))
    units = [u for u in units if u[4] > 0]
    ht = S.ht_ratio(units); res["ht"].append(ht)
    k_ = sum(u[3] for u in units); n_ = sum(u[4] for u in units); uw = k_ / n_; res["uw"].append(uw)
    lo, hi = S.stratified_cluster_bootstrap(units, REPS, f"s{k}", weighted=True)
    ulo, uhi = S.stratified_cluster_bootstrap(units, REPS, f"u{k}", weighted=False)
    _, klo, khi = S.weighted_wilson(units)
    _, wlo, whi = S.wilson(k_, n_)
    res["cov_boot"] += lo <= true <= hi; res["cov_kw"] += klo <= true <= khi
    res["cov_uw"] += wlo <= true <= whi; res["cov_uboot"] += ulo <= true <= uhi
    res["lbs"].append(lo)
    if ht >= 0.95 and uw >= 0.95:
        res["met_point"] += 1
        if lo >= 0.95: res["met_lb"] += 1
m = lambda x: sum(x) / len(x)
sd = lambda x: math.sqrt(sum((v - m(x)) ** 2 for v in x) / (len(x) - 1))
print(json.dumps(dict(scenario=SCEN, nsim=NSIM, reps=REPS, true=round(true, 4), ht_mean=round(m(res["ht"]), 4), ht_sd=round(sd(res["ht"]), 4),
    unweighted_mean=round(m(res["uw"]), 4), cov_weighted_boot=res["cov_boot"] / NSIM, cov_weighted_kish_wilson=res["cov_kw"] / NSIM,
    cov_unweighted_wilson_vs_pop=res["cov_uw"] / NSIM, cov_unweighted_boot_vs_pop=res["cov_uboot"] / NSIM,
    p_met_point=res["met_point"] / NSIM, p_met_lower_bound=res["met_lb"] / NSIM, secs=round(time.time() - t0))))
