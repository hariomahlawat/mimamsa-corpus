"""C13-A0 statistics: Wilson intervals, Horvitz-Thompson ratio estimators, stratified judgment-cluster bootstrap,
Kish effective sample size, sample-size calculations, Cohen's kappa and Krippendorff's alpha (nominal).

Standard library only. Deterministic: the bootstrap uses random.Random(seed) with a string seed.
"""
import math
import random
from collections import Counter, defaultdict

Z95 = 1.959964


def wilson(k, n, z=Z95):
    """Wilson score interval. Returns (p, lo, hi) or (None, None, None) when n == 0. Accepts non-integer k, n
    (used with Kish effective n for the weighted interval)."""
    if n <= 0:
        return (None, None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0.0)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def wilson_halfwidth(p, n, z=Z95):
    _, lo, hi = wilson(p * n, n, z)
    return (hi - lo) / 2


def n_for_halfwidth(p, h, z=Z95, deff=1.0, nmax=100000):
    """Smallest n whose Wilson half-width at proportion p is <= h, inflated by a design effect."""
    for n in range(2, nmax):
        if wilson_halfwidth(p, n / deff, z) <= h:
            return n
    raise ValueError("no n found")


def n_one_sided_power(p0, p1, alpha=0.05, power=0.80):
    """Normal-approximation n for a one-sided test H0: p <= p0 against p = p1 > p0."""
    za = _zinv(1 - alpha)
    zb = _zinv(power)
    num = za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))
    return math.ceil((num / (p1 - p0)) ** 2)


def _zinv(q):
    """Inverse standard normal CDF (Acklam's rational approximation; |error| < 1.2e-9)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if q < 0.02425:
        t = math.sqrt(-2 * math.log(q))
        return (((((c[0] * t + c[1]) * t + c[2]) * t + c[3]) * t + c[4]) * t + c[5]) / \
            ((((d[0] * t + d[1]) * t + d[2]) * t + d[3]) * t + 1)
    if q > 1 - 0.02425:
        return -_zinv(1 - q)
    t = q - 0.5
    r = t * t
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * t / \
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def kish_deff(weights):
    """Kish design effect from unequal weights: n * sum(w^2) / sum(w)^2."""
    w = [x for x in weights if x > 0]
    if not w:
        return None
    return len(w) * sum(x * x for x in w) / (sum(w) ** 2)


def kish_neff(weights):
    w = [x for x in weights if x > 0]
    return (sum(w) ** 2) / sum(x * x for x in w) if w else 0.0


def icc_anova(groups):
    """One-way ANOVA ICC for binary outcomes grouped by cluster. groups: list of lists of 0/1."""
    groups = [g for g in groups if g]
    k = len(groups)
    N = sum(len(g) for g in groups)
    if k < 2 or N <= k:
        return 0.0
    grand = sum(sum(g) for g in groups) / N
    ssb = sum(len(g) * (sum(g) / len(g) - grand) ** 2 for g in groups)
    ssw = sum(sum((x - sum(g) / len(g)) ** 2 for x in g) for g in groups)
    msb = ssb / (k - 1)
    msw = ssw / (N - k)
    n0 = (N - sum(len(g) ** 2 for g in groups) / N) / (k - 1)
    denom = msb + (n0 - 1) * msw
    return max(0.0, (msb - msw) / denom) if denom > 0 else 0.0


# ------------------------------------------------------------------------------------------- ratio estimators
def ht_ratio(units):
    """Horvitz-Thompson ratio estimate sum(w*y)/sum(w*x). units: iterable of (cluster_id, stratum, weight, y, x),
    where y and x are already summed within the cluster (e.g. correct and answered proceedings of one judgment)."""
    num = den = 0.0
    for _, _, w, y, x in units:
        num += w * y
        den += w * x
    return num / den if den else None


def stratified_cluster_bootstrap(units, reps=2000, seed="c13-bootstrap", alpha=0.05, weighted=True):
    """Percentile interval for the (weighted) ratio sum(w*y)/sum(w*x). Clusters (judgments) are resampled with
    replacement within each stratum, so the design's stratification is preserved. Returns (lo, hi) or (None, None)."""
    units = list(units)
    by_s = defaultdict(list)
    for u in units:
        by_s[u[1]].append(u)
    rng = random.Random(seed)
    strata = sorted(by_s)
    est = []
    for _ in range(reps):
        num = den = 0.0
        for s in strata:
            us = by_s[s]
            for _ in range(len(us)):
                _, _, w, y, x = us[rng.randrange(len(us))]
                ww = w if weighted else 1.0
                num += ww * y
                den += ww * x
        if den:
            est.append(num / den)
    if not est:
        return (None, None)
    est.sort()
    lo = est[int(math.floor((alpha / 2) * (len(est) - 1)))]
    hi = est[int(math.ceil((1 - alpha / 2) * (len(est) - 1)))]
    return (lo, hi)


def weighted_wilson(units, z=Z95):
    """Wilson interval for the weighted ratio using Kish effective n of the denominator units (x > 0)."""
    units = [u for u in units if u[4] > 0]
    if not units:
        return (None, None, None)
    p = ht_ratio(units)
    # unit-level weights replicated by x so that proceeding-level denominators count
    ws = []
    for _, _, w, _, x in units:
        ws.extend([w] * int(round(x)) if x >= 1 else [w * x])
    neff = kish_neff(ws)
    _, lo, hi = wilson(p * neff, neff, z)
    return (p, lo, hi)


# ------------------------------------------------------------------------------------------- agreement
def cohen_kappa(pairs):
    """Cohen's kappa for two coders. pairs: list of (label_a, label_b). Returns None if undefined."""
    pairs = list(pairs)
    n = len(pairs)
    if n == 0:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else None
    return (po - pe) / (1 - pe)


def krippendorff_alpha_nominal(units):
    """Krippendorff's alpha, nominal metric. units: list of lists of labels (one list per unit; None = missing).
    Units with fewer than two non-missing values are not pairable and are skipped."""
    coincid = Counter()
    for vals in units:
        v = [x for x in vals if x is not None]
        m = len(v)
        if m < 2:
            continue
        for i in range(m):
            for j in range(m):
                if i != j:
                    coincid[(v[i], v[j])] += 1.0 / (m - 1)
    n = sum(coincid.values())
    if n <= 1:
        return None
    nc = Counter()
    for (c, _), w in coincid.items():
        nc[c] += w
    do = sum(w for (c, k), w in coincid.items() if c != k)
    de = sum(nc[c] * nc[k] for c in nc for k in nc if c != k) / (n - 1)
    if de == 0:
        return 1.0 if do == 0 else None
    return 1 - do / de


def rnd(x, nd=4):
    return None if x is None else round(x, nd)


# ------------------------------------------------------------------------------------------- validated interval (v1.1)
def _betacf(a, b, x):
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c; c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c; c = c if abs(c) > tiny else tiny
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-12:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b) for real a, b > 0."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def beta_ppf(q, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if betainc(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k, n, alpha=0.05):
    """Exact (Clopper-Pearson) interval; k and n may be non-integer (effective counts)."""
    if n <= 0:
        return (None, None, None)
    p = k / n
    lo = 0.0 if k <= 0 else beta_ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k >= n else beta_ppf(1 - alpha / 2, k + 1, n - k)
    return (p, lo, hi)


def linearized_ratio_variance(units):
    """Taylor-linearised variance of the HT ratio sum(w*y)/sum(w*x) under stratified SRS of clusters with FPC.
    units: (cluster, stratum, weight, y, x) for EVERY sampled cluster (including x == 0). Clusters sharing a
    (stratum, cluster id) are summed into one PSU. N_h = weight * n_h."""
    psu = defaultdict(lambda: [0.0, 0.0, 0.0])
    for c, h, w, y, x in units:
        a = psu[(h, c)]
        a[0] = w; a[1] += y; a[2] += x
    X = sum(w * x for (_, _), (w, _, x) in psu.items())
    Y = sum(w * y for (_, _), (w, y, _) in psu.items())
    if not X:
        return None, None
    R = Y / X
    by_h = defaultdict(list)
    for (h, _), (w, y, x) in psu.items():
        by_h[h].append((w, y - R * x))
    V = 0.0
    for h, zs in by_h.items():
        n = len(zs)
        if n < 2:
            continue
        w = zs[0][0]
        N = w * n
        mz = sum(z for _, z in zs) / n
        s2 = sum((z - mz) ** 2 for _, z in zs) / (n - 1)
        V += N * N * (1 - n / N) * s2 / n
    return R, V / (X * X)


def design_cp(units, alpha=0.05):
    """C13 v1.1 validated interval for a weighted ratio: Clopper-Pearson on an effective sample size
    n_eff = min(Kish n_eff of the denominator, Korn-Graubard n_eff = p(1-p)/V_lin, n), with k_eff = p * n_eff.
    Taking the smallest effective n is conservative: it guards against the zero-variance cells that made the
    percentile bootstrap under-cover (GA0 review F01). Coverage is demonstrated by c13_ci_sim.py."""
    units = list(units)
    pos = [u for u in units if u[4] > 0]
    if not pos:
        return dict(p=None, lo=None, hi=None, n_eff=0)
    R, V = linearized_ratio_variance(units)
    n = sum(u[4] for u in pos)
    ws = []
    for _, _, w, _, x in pos:
        ws.extend([w] * int(round(x)) if x >= 1 else [w * x])
    n_kish = kish_neff(ws)
    n_kg = (R * (1 - R) / V) if V and 0 < R < 1 else float("inf")
    n_eff = max(1.0, min(n_kish, n_kg, n))
    _, lo, hi = clopper_pearson(R * n_eff, n_eff, alpha)
    return dict(p=R, lo=lo, hi=hi, n_eff=n_eff, n_kish=n_kish, n_korn_graubard=None if n_kg == float("inf") else n_kg)
