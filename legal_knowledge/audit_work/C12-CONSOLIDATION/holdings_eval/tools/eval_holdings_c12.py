#!/usr/bin/env python3
"""Blind evaluation of the frozen holdings extractor c12-holdings/1.0.0.

Subcommands (run from holdings_eval/):
  render   (needs PyMuPDF; run with the scratchpad venv) renders every page of the 30 reference
           judgment PDFs from the c7 git object store into predictions/PAGE_TEXT_PYMUPDF.jsonl.
  sample   writes the blind adjudication sheet ADJUDICATION_SAMPLE.csv (labels blank) and
           predictions/ADJUDICATION_CONTEXT.txt (page text for the adjudicator). Refuses to
           overwrite a sheet that already carries labels unless the sampled ids are identical.
  run      computes all metrics -> EVALUATION_ROWS.csv, predictions/METRICS.json,
           EVALUATION_HOLDINGS_C12.md (tables between AUTO markers), SHA256SUMS.
  run --check  recomputes everything in memory and compares with the files on disk.

Standard library only for `sample`/`run`. Deterministic. The matcher is the one pre-registered in README.md.
"""
import csv, hashlib, io, json, math, os, random, re, subprocess, sys, unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.dirname(HERE)
PRED = os.path.join(HERE, "predictions")
REF = os.path.join(C, "holdings_reference", "REFERENCE_HOLDINGS.csv")
SEL = os.path.join(C, "holdings_reference", "SELECTION.csv")
PAGES = os.path.join(PRED, "PAGE_TEXT_PYMUPDF.jsonl")
SHEET = os.path.join(HERE, "ADJUDICATION_SAMPLE.csv")
REPORT = os.path.join(HERE, "EVALUATION_HOLDINGS_C12.md")
ROWS = os.path.join(HERE, "EVALUATION_ROWS.csv")
METRICS = os.path.join(PRED, "METRICS.json")
SEED = "C12-HOLD-EVAL-2026"
COURT_VOICE = {"question_of_law", "holding", "reasoning", "obiter_candidate", "operative_direction"}
FROZEN = {"holdings_core.py": "6d5b05e447e082cb8d9be4a1784148a18221091bd836b5fceb4cecbf6178fe8e",
          "holdings_c12.py": "a1b0163824e4062b38efe1423985559935130f7e581f3c3ba61e29a50fc7bb89"}
VARIANTS = {"primary": (0.60, 1), "strict": (0.80, 0), "loose": (0.40, 1)}
LABELS = ["CORRECT_HOLDING", "CORRECT_QOL", "REASONING_NOT_HOLDING", "NOT_COURT_VOICE", "OBITER",
          "WRONG_SPAN", "UNCLEAR"]
SHEET_COLS = ["sample_no", "stratum", "item_id", "judgment_id", "item_type", "opinion", "page", "page_end",
              "paragraph", "holding_score", "rank_in_opinion", "excerpt_clean", "label", "subtype", "reason"]

STOP = set("""a an the and or but if then else of to in on at by for with from into onto upon as is are was were be
been being am do does did done have has had having it its this that these those there here which who whom whose what
when where why how not no nor so than too very can could may might must shall should will would such any all each
every some other another same own only also both either neither he she they we you i him her them us me his hers their
our your my mr ms dr said per vs v viz ie eg etc further thus hence therefore however whereas whether about above below
under over after before between through during without within against again once out up down off more most much many
few one two three""".split())


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def norm_tokens(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = s.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                                   "—": "-"}))
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return s.split()


def content(s):
    return {t for t in norm_tokens(s) if len(t) >= 2 and t not in STOP and not (t.isdigit() and len(t) <= 3)}


def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def fmt(k, n):
    p, lo, hi = wilson(k, n)
    if p is None:
        return "n/a (0/0)"
    return "%.1f%% (%d/%d; 95%% CI %.1f-%.1f)" % (100 * p, k, n, 100 * lo, 100 * hi)


# ------------------------------------------------------------------ loading
def load():
    sel = list(csv.DictReader(open(SEL, encoding="utf-8")))
    ref = list(csv.DictReader(open(REF, encoding="utf-8")))
    for i, r in enumerate(ref):
        r["ref_id"] = "R%03d" % (i + 1)
        r["_c"] = content(r["excerpt"])
        r["_page"] = int(r["page"]) if r["page"].strip().isdigit() else None
    preds = [json.loads(l) for l in open(os.path.join(PRED, "HOLDINGS_C12.jsonl"), encoding="utf-8")]
    for p in preds:
        p["_c"] = content(p.get("excerpt_clean") or p.get("excerpt") or "")
    return sel, ref, preds


def page_dist(p, r):
    if p.get("page") is None or r["_page"] is None:
        return 0
    a, b = p["page"], p.get("page_end") or p["page"]
    rp = r["_page"]
    if a <= rp <= b:
        return 0
    return min(abs(rp - a), abs(rp - b))


def match(p, r, thr, pd, use_page=True, same_judgment=True):
    if same_judgment and p["judgment_id"] != r["judgment_id"]:
        return False
    if use_page and page_dist(p, r) > pd:
        return False
    a, b = p["_c"], r["_c"]
    if not a or not b:
        return False
    inter = len(a & b)
    return inter >= 3 and inter / min(len(a), len(b)) >= thr


# ------------------------------------------------------------------ render (PyMuPDF)
def cmd_render():
    import pymupdf  # noqa
    sel = list(csv.DictReader(open(SEL, encoding="utf-8")))
    out = []
    for s in sorted(sel, key=lambda x: x["judgment_id"]):
        blob = subprocess.run(["git", "-C", "/home/user/c7", "show", "ad77758d:" + s["raw_path"]],
                              capture_output=True, check=True).stdout
        assert hashlib.sha256(blob).hexdigest() == s["sha256"], s["judgment_id"]
        doc = pymupdf.open(stream=blob, filetype="pdf")
        for i, pg in enumerate(doc):
            out.append({"judgment_id": s["judgment_id"], "page": i + 1, "text": pg.get_text()})
    with open(PAGES, "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n")
    print("rendered", len(out), "pages")


def load_pages():
    P = {}
    for l in open(PAGES, encoding="utf-8"):
        o = json.loads(l)
        P[(o["judgment_id"], o["page"])] = o["text"]
    return P


# ------------------------------------------------------------------ sample
def draw_sample(preds):
    rng = random.Random(SEED)
    out = []
    for stratum, n in (("holding", 60), ("question_of_law", 30)):
        pool = sorted([p for p in preds if p["item_type"] == stratum], key=lambda x: x["item_id"])
        pick = pool if len(pool) <= n else rng.sample(pool, n)
        out += [(stratum, p) for p in sorted(pick, key=lambda x: (x["judgment_id"], x["page"] or 0, x["char_start"]))]
    return out


def cmd_sample():
    _, _, preds = load()
    smp = draw_sample(preds)
    ids = [p["item_id"] for _, p in smp]
    if os.path.exists(SHEET):
        old = list(csv.DictReader(open(SHEET, encoding="utf-8")))
        if any(r["label"] for r in old):
            if [r["item_id"] for r in old] != ids:
                sys.exit("sheet has labels and sample differs; refusing")
            print("sheet already labelled and identical; untouched")
            return
    P = load_pages()
    with open(SHEET, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, SHEET_COLS)
        w.writeheader()
        for i, (st, p) in enumerate(smp, 1):
            w.writerow({"sample_no": i, "stratum": st, "item_id": p["item_id"], "judgment_id": p["judgment_id"],
                        "item_type": p["item_type"], "opinion": p["opinion"], "page": p["page"],
                        "page_end": p.get("page_end"), "paragraph": p.get("paragraph"),
                        "holding_score": p.get("holding_score"), "rank_in_opinion": p.get("rank_in_opinion"),
                        "excerpt_clean": p.get("excerpt_clean"), "label": "", "subtype": "", "reason": ""})
    with open(os.path.join(PRED, "ADJUDICATION_CONTEXT.txt"), "w", encoding="utf-8") as f:
        for i, (st, p) in enumerate(smp, 1):
            f.write("=" * 100 + "\n#%d %s %s %s p%s-%s para=%s opinion=%s\nITEM: %s\n" % (
                i, st, p["item_id"], p["judgment_id"], p["page"], p.get("page_end"), p.get("paragraph"),
                p["opinion"], p.get("excerpt_clean")))
            a, b = (p["page"] or 1), (p.get("page_end") or p["page"] or 1)
            for pg in range(a - 1, b + 1):
                t = P.get((p["judgment_id"], pg))
                if t is not None:
                    f.write("--- page %d ---\n%s\n" % (pg, t))
    print("sample", len(smp))


# ------------------------------------------------------------------ anchoring
PARA_RE = re.compile(r"(?m)^\s*\(?(\d{1,3})\s*[\.\)]")


def anchor(p, P):
    a = p.get("page")
    if a is None:
        return None, None, None
    b = p.get("page_end") or a
    txt = " ".join(P.get((p["judgment_id"], g), "") for g in range(a, b + 1))
    pc = content(txt)
    c = p["_c"]
    page_ok = bool(c) and len(c & pc) / len(c) >= 0.90
    para_strict = para_len = None
    if p.get("paragraph") is not None:
        N = int(p["paragraph"])
        win = "\n".join(P.get((p["judgment_id"], g), "") for g in range(max(1, a - 3), a + 1))
        nums = [int(m.group(1)) for m in PARA_RE.finditer(win)]
        para_len = N in nums
        # locate the excerpt start: first 6 content-ish tokens of the excerpt, searched in lowered window
        toks = [t for t in norm_tokens(p.get("excerpt_clean") or "") if len(t) >= 3][:5]
        wl = re.sub(r"[^0-9a-z]+", " ", win.lower())
        pos = -1
        if toks:
            pos = wl.find(" ".join(toks))
        if pos < 0:
            para_strict = False
        else:
            # map: count markers whose position (in normalised coordinates) precedes pos
            last = None
            for m in PARA_RE.finditer(win):
                prefix = re.sub(r"[^0-9a-z]+", " ", win[:m.start()].lower())
                if len(prefix) <= pos:
                    last = int(m.group(1))
            para_strict = (last == N)
    return page_ok, para_strict, para_len


def para_posthoc(p, P):
    """POST-HOC diagnostic (not pre-registered): locate the excerpt in the raw window by the first run of
    3 consecutive alphabetic tokens (>=4 letters) allowing <=25 chars of noise between them (margin letters,
    hyphenation), then take the last line-start paragraph marker before it. Returns None if not located."""
    if p.get("paragraph") is None or p.get("page") is None:
        return None
    a = p["page"]
    win = "\n".join(P.get((p["judgment_id"], g), "") for g in range(max(1, a - 3), (p.get("page_end") or a) + 1))
    allt = re.findall(r"[A-Za-z]{4,}", p.get("excerpt_clean") or "")
    pos = -1
    for st in range(0, max(0, len(allt) - 2)):
        m = re.search(r".{0,25}?".join(map(re.escape, allt[st:st + 3])), win, re.I | re.S)
        if m:
            pos = m.start()
            break
    if pos < 0:
        return None
    last = None
    for m in PARA_RE.finditer(win[:pos]):
        last = int(m.group(1))
    return last == int(p["paragraph"])


# ------------------------------------------------------------------ compute
def compute():
    sel, ref, preds = load()
    jids = sorted(s["judgment_id"] for s in sel)
    P = load_pages()
    sheet = list(csv.DictReader(open(SHEET, encoding="utf-8")))
    smp_ids = [p["item_id"] for _, p in draw_sample(preds)]
    assert [r["item_id"] for r in sheet] == smp_ids, "sheet does not match seeded sample"
    bad = [r["item_id"] for r in sheet if r["label"] not in LABELS]
    assert not bad, "unlabelled/invalid rows: %s" % bad[:5]
    M = {"run_meta": json.load(open(os.path.join(PRED, "RUN_META.json"))),
         "inputs": {"reference_sha256": sha(REF), "selection_sha256": sha(SEL),
                    "predictions_sha256": sha(os.path.join(PRED, "HOLDINGS_C12.jsonl")),
                    "page_text_sha256": sha(PAGES), "adjudication_sha256": sha(SHEET)}}
    assert M["run_meta"]["tool_sha256"] == FROZEN, "extractor hashes differ from frozen"
    rows = []
    ref_h = [r for r in ref if r["item_type"] == "holding"]
    ref_q = [r for r in ref if r["item_type"] == "question_of_law"]
    p_h = [p for p in preds if p["item_type"] == "holding"]
    p_q = [p for p in preds if p["item_type"] == "question_of_law"]
    p_cv = [p for p in preds if p["item_type"] in COURT_VOICE]
    byj = lambda L: {j: [x for x in L if x["judgment_id"] == j] for j in jids}
    PJ = {"holding": byj(p_h), "qol": byj(p_q), "cv": byj(p_cv), "all": byj(preds)}
    RJ = {"holding": byj(ref_h), "qol": byj(ref_q), "all": byj(ref)}

    def recall(refs, pj, thr, pd):
        hits = {}
        for r in refs:
            m = [p["item_id"] for p in pj[r["judgment_id"]] if match(p, r, thr, pd)]
            hits[r["ref_id"]] = m
        return hits

    def macro(refs, hits):
        rates = []
        for j in jids:
            rr = [r for r in refs if r["judgment_id"] == j]
            if rr:
                rates.append(sum(1 for r in rr if hits[r["ref_id"]]) / len(rr))
        return (math.fsum(rates) / len(rates)) if rates else None, len(rates)

    def prec(pl, rj, thr, pd):
        return {p["item_id"]: [r["ref_id"] for r in rj[p["judgment_id"]] if match(p, r, thr, pd)] for p in pl}

    res = {}
    for v, (thr, pd) in VARIANTS.items():
        R = {}
        R["holding_recall_by_holding"] = recall(ref_h, PJ["holding"], thr, pd)
        R["holding_recall_by_cv"] = recall(ref_h, PJ["cv"], thr, pd)
        R["all_ref_recall_by_cv"] = recall(ref, PJ["cv"], thr, pd)
        R["all_ref_recall_by_any"] = recall(ref, PJ["all"], thr, pd)
        R["qol_recall_by_qol"] = recall(ref_q, PJ["qol"], thr, pd)
        R["qol_recall_by_cv"] = recall(ref_q, PJ["cv"], thr, pd)
        R["holding_prec_vs_refholding"] = prec(p_h, RJ["holding"], thr, pd)
        R["holding_prec_vs_anyref"] = prec(p_h, RJ["all"], thr, pd)
        R["qol_prec_vs_refqol"] = prec(p_q, RJ["qol"], thr, pd)
        R["qol_prec_vs_anyref"] = prec(p_q, RJ["all"], thr, pd)
        res[v] = R
    S = {}
    for v, R in res.items():
        d = {}
        for k, hits in R.items():
            n = len(hits)
            kk = sum(1 for x in hits.values() if x)
            p, lo, hi = wilson(kk, n)
            d[k] = {"k": kk, "n": n, "rate": p, "ci": [lo, hi]}
        for k, refs in (("holding_recall_by_holding", ref_h), ("holding_recall_by_cv", ref_h),
                        ("qol_recall_by_qol", ref_q), ("all_ref_recall_by_cv", ref)):
            d[k]["macro"], d[k]["macro_n_judgments"] = macro(refs, R[k])
        for k, pl in (("holding_prec_vs_refholding", p_h), ("qol_prec_vs_refqol", p_q)):
            rates = []
            for j in jids:
                pp = [p for p in pl if p["judgment_id"] == j]
                if pp:
                    rates.append(sum(1 for p in pp if R[k][p["item_id"]]) / len(pp))
            d[k]["macro"] = math.fsum(rates) / len(rates) if rates else None
            d[k]["macro_n_judgments"] = len(rates)
        S[v] = d
    M["metrics"] = S

    # rank/score trade-off for holding recall (primary)
    thr, pd = VARIANTS["primary"]
    tr = []
    for cut in (1, 2, 3, 5, 10, 25):
        sub = {j: [p for p in PJ["holding"][j] if (p.get("rank_in_opinion") or 99) <= cut] for j in jids}
        h = recall(ref_h, sub, thr, pd)
        npred = sum(len(x) for x in sub.values())
        pm = prec([p for x in sub.values() for p in x], RJ["holding"], thr, pd)
        tr.append({"rank_le": cut, "n_pred": npred, "recall_k": sum(1 for x in h.values() if x),
                   "recall_n": len(h), "prec_lb_k": sum(1 for x in pm.values() if x), "prec_lb_n": len(pm)})
    M["rank_tradeoff"] = tr

    # reference holdings by opinion type
    op = defaultdict(lambda: [0, 0])
    for r in ref_h:
        op[r["opinion"]][1] += 1
        if res["primary"]["holding_recall_by_holding"][r["ref_id"]]:
            op[r["opinion"]][0] += 1
    M["recall_by_ref_opinion"] = {k: v for k, v in sorted(op.items())}
    # where are missed reference holdings? classify by best-matching prediction type (primary, any type)
    miss = defaultdict(int)
    for r in ref_h:
        if res["primary"]["holding_recall_by_holding"][r["ref_id"]]:
            continue
        types = sorted({p["item_type"] for p in PJ["all"][r["judgment_id"]] if match(p, r, thr, pd)})
        if not types:
            miss["NO_ITEM_OF_ANY_TYPE"] += 1
        else:
            pri = [t for t in ("reasoning", "operative_direction", "question_of_law", "obiter_candidate",
                               "lower_court_finding", "submission", "quoted_precedent") if t in types]
            miss["CAPTURED_AS_" + pri[0]] += 1
    M["missed_holdings_by_type"] = dict(sorted(miss.items()))

    # adjudication
    ad = defaultdict(lambda: defaultdict(int))
    for r in sheet:
        ad[r["stratum"]][r["label"]] += 1
        if r["label"] == "NOT_COURT_VOICE":
            ad[r["stratum"]]["NCV:" + (r["subtype"] or "unspecified")] += 1
    A = {}
    for st, corr in (("holding", "CORRECT_HOLDING"), ("question_of_law", "CORRECT_QOL")):
        n = sum(1 for r in sheet if r["stratum"] == st)
        k = ad[st][corr]
        nu = n - ad[st]["UNCLEAR"]
        A[st] = {"n": n, "correct": k, "rate": wilson(k, n)[0], "ci": list(wilson(k, n)[1:]),
                 "excl_unclear_n": nu, "excl_unclear_rate": wilson(k, nu)[0], "excl_unclear_ci": list(wilson(k, nu)[1:]),
                 "labels": dict(sorted(ad[st].items()))}
        for sub in ("quoted_precedent", "submission", "lower_forum"):
            ks = ad[st]["NCV:" + sub]
            A[st]["origin_" + sub] = {"k": ks, "n": n, "rate": wilson(ks, n)[0], "ci": list(wilson(ks, n)[1:])}
        # per-judgment macro for sample
        rates = []
        for j in jids:
            rr = [r for r in sheet if r["stratum"] == st and r["judgment_id"] == j]
            if rr:
                rates.append(sum(1 for r in rr if r["label"] == corr) / len(rr))
        A[st]["macro"] = math.fsum(rates) / len(rates) if rates else None
        A[st]["macro_n_judgments"] = len(rates)
        # agreement between manual label and reference-match (primary), for transparency
        mk = "holding_prec_vs_refholding" if st == "holding" else "qol_prec_vs_refqol"
        both = defaultdict(int)
        for r in sheet:
            if r["stratum"] == st:
                both["%s|refmatch=%s" % (r["label"] == corr, bool(res["primary"][mk][r["item_id"]]))] += 1
        A[st]["label_vs_refmatch"] = dict(sorted(both.items()))
    M["adjudication"] = A

    # anchoring
    an = {"n": 0, "page_ok": 0, "para_n": 0, "para_strict": 0, "para_lenient": 0, "posthoc_located": 0, "posthoc_ok": 0}
    anrows = {}
    for p in p_cv:
        po, ps, pl = anchor(p, P)
        anrows[p["item_id"]] = (po, ps, pl)
        if po is None:
            continue
        an["n"] += 1
        an["page_ok"] += po
        if ps is not None:
            an["para_n"] += 1
            an["para_strict"] += ps
            an["para_lenient"] += pl
            ph = para_posthoc(p, P)
            if ph is not None:
                an["posthoc_located"] += 1
                an["posthoc_ok"] += ph
    M["anchoring"] = an
    an_by = defaultdict(lambda: [0, 0])
    for p in p_cv:
        po = anrows[p["item_id"]][0]
        if po is not None:
            an_by[p["item_type"]][1] += 1
            an_by[p["item_type"]][0] += po
    M["anchoring_by_type"] = dict(sorted(an_by.items()))
    # reference anchoring sanity (same page rule applied to reference excerpts)
    rk = sum(1 for r in ref if r["_c"] and len(r["_c"] & content(P.get((r["judgment_id"], r["_page"]), ""))) / len(r["_c"]) >= 0.9)
    M["reference_anchoring"] = {"k": rk, "n": len(ref)}

    # negative control
    nc = {}
    for use_page in (True, False):
        tot = hit = 0
        for k in range(1, 6):
            for i, j in enumerate(jids):
                y = jids[(i + k) % len(jids)]
                for r in RJ["holding"][y]:
                    tot += 1
                    if any(match(p, r, thr, pd, use_page=use_page, same_judgment=False) for p in PJ["holding"][j]):
                        hit += 1
        nc["page_rule" if use_page else "no_page_rule"] = {"k": hit, "n": tot, "rate": wilson(hit, tot)[0],
                                                           "ci": list(wilson(hit, tot)[1:])}
    # same-judgment, page rule disabled, for comparison
    hk = sum(1 for r in ref_h if any(match(p, r, thr, pd, use_page=False) for p in PJ["holding"][r["judgment_id"]]))
    nc["same_judgment_no_page_rule"] = {"k": hk, "n": len(ref_h)}
    M["negative_control"] = nc

    # per judgment
    pj_rows = []
    sel_t = {s["judgment_id"]: s["title"] for s in sel}
    jmeta = {r["judgment_id"]: r for r in csv.DictReader(open(os.path.join(PRED, "HOLDINGS_C12_JUDGMENTS.csv"), encoding="utf-8"))}
    for j in jids:
        R = res["primary"]
        rh = RJ["holding"][j]
        rq = RJ["qol"][j]
        ph = PJ["holding"][j]
        pq = PJ["qol"][j]
        smp = [r for r in sheet if r["judgment_id"] == j and r["stratum"] == "holding"]
        pj_rows.append({"judgment_id": j, "title": sel_t[j][:60], "opinions": jmeta[j]["opinions"],
                        "ref_holdings": len(rh), "rec_by_holding": sum(1 for r in rh if R["holding_recall_by_holding"][r["ref_id"]]),
                        "rec_by_cv": sum(1 for r in rh if R["holding_recall_by_cv"][r["ref_id"]]),
                        "ref_qol": len(rq), "qol_rec": sum(1 for r in rq if R["qol_recall_by_qol"][r["ref_id"]]),
                        "pred_holding": len(ph), "pred_holding_refmatch": sum(1 for p in ph if R["holding_prec_vs_refholding"][p["item_id"]]),
                        "pred_qol": len(pq), "sample_holding": len(smp),
                        "sample_holding_correct": sum(1 for r in smp if r["label"] == "CORRECT_HOLDING"),
                        "pred_cv": len(PJ["cv"][j])})
    M["per_judgment"] = pj_rows

    # EVALUATION_ROWS.csv: one row per reference item and per predicted holding/qol item
    out = []
    for r in ref:
        R = res["primary"]
        out.append({"row_kind": "reference", "id": r["ref_id"], "judgment_id": r["judgment_id"],
                    "item_type": r["item_type"], "opinion": r["opinion"], "page": r["page"], "paragraph": r["para"],
                    "matched_holding_items_primary": ";".join(R["holding_recall_by_holding"].get(r["ref_id"], [])) if r["item_type"] == "holding" else "",
                    "matched_cv_items_primary": ";".join(R["all_ref_recall_by_cv"][r["ref_id"]]),
                    "matched_qol_items_primary": ";".join(R["qol_recall_by_qol"].get(r["ref_id"], [])) if r["item_type"] == "question_of_law" else "",
                    "hit_strict": int(bool(res["strict"]["all_ref_recall_by_cv"][r["ref_id"]])),
                    "hit_loose": int(bool(res["loose"]["all_ref_recall_by_cv"][r["ref_id"]])),
                    "anchor_page_ok": "", "anchor_para_strict": "", "adjudication_label": "",
                    "excerpt": r["excerpt"][:300]})
    lab = {r["item_id"]: r["label"] for r in sheet}
    for p in sorted(p_cv, key=lambda x: (x["judgment_id"], x["char_start"], x["item_id"])):
        R = res["primary"]
        po, ps, _ = anrows[p["item_id"]]
        refm = R["holding_prec_vs_anyref"].get(p["item_id"]) if p["item_type"] == "holding" else (
            R["qol_prec_vs_anyref"].get(p["item_id"]) if p["item_type"] == "question_of_law" else
            [r["ref_id"] for r in RJ["all"][p["judgment_id"]] if match(p, r, *VARIANTS["primary"])])
        out.append({"row_kind": "prediction", "id": p["item_id"], "judgment_id": p["judgment_id"],
                    "item_type": p["item_type"], "opinion": p["opinion"], "page": p["page"], "paragraph": p.get("paragraph"),
                    "matched_holding_items_primary": "", "matched_cv_items_primary": ";".join(refm or []),
                    "matched_qol_items_primary": "", "hit_strict": "", "hit_loose": "",
                    "anchor_page_ok": "" if po is None else int(po), "anchor_para_strict": "" if ps is None else int(ps),
                    "adjudication_label": lab.get(p["item_id"], ""), "excerpt": (p.get("excerpt_clean") or "")[:300]})
    buf = io.StringIO()
    w = csv.DictWriter(buf, list(out[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(out)
    rows_text = buf.getvalue()

    # coverage of non-evaluated fields (count only)
    M["not_credited_counts"] = {"items_with_statute_links": sum(1 for p in preds if p.get("statute_links")),
                                "items_with_statutes": sum(1 for p in preds if p.get("statutes")),
                                "items_with_treatment": sum(1 for p in preds if p.get("treatment")),
                                "item_type_counts": dict(sorted(defaultdict(int, {t: sum(1 for p in preds if p["item_type"] == t) for t in {p["item_type"] for p in preds}}).items()))}
    metrics_text = json.dumps(M, indent=1, sort_keys=True, default=str) + "\n"
    return M, rows_text, metrics_text


def pct(x):
    return "n/a" if x is None else "%.1f%%" % (100 * x)


def tables(M):
    S = M["metrics"]
    L = []
    a = M["adjudication"]
    L.append("| Metric | Result |\n| --- | --- |")
    L.append("| **Holding precision, TRUE (manual, n=%d)** | %s |" % (a["holding"]["n"], fmt(a["holding"]["correct"], a["holding"]["n"])))
    L.append("| Holding precision, true, excluding UNCLEAR | %s |" % fmt(a["holding"]["correct"], a["holding"]["excl_unclear_n"]))
    L.append("| Holding precision, reference-match lower bound | %s |" % fmt(S["primary"]["holding_prec_vs_refholding"]["k"], S["primary"]["holding_prec_vs_refholding"]["n"]))
    L.append("| **Holding recall (`holding` items)** | %s; macro %s over %d judgments |" % (
        fmt(S["primary"]["holding_recall_by_holding"]["k"], S["primary"]["holding_recall_by_holding"]["n"]),
        pct(S["primary"]["holding_recall_by_holding"]["macro"]), S["primary"]["holding_recall_by_holding"]["macro_n_judgments"]))
    L.append("| **Holding recall, court-voice set** | %s; macro %s |" % (
        fmt(S["primary"]["holding_recall_by_cv"]["k"], S["primary"]["holding_recall_by_cv"]["n"]),
        pct(S["primary"]["holding_recall_by_cv"]["macro"])))
    L.append("| All 245 reference items, court-voice set | %s |" % fmt(S["primary"]["all_ref_recall_by_cv"]["k"], S["primary"]["all_ref_recall_by_cv"]["n"]))
    L.append("| **QoL precision, TRUE (manual, all %d)** | %s |" % (a["question_of_law"]["n"], fmt(a["question_of_law"]["correct"], a["question_of_law"]["n"])))
    L.append("| QoL precision, reference-match lower bound | %s |" % fmt(S["primary"]["qol_prec_vs_refqol"]["k"], S["primary"]["qol_prec_vs_refqol"]["n"]))
    L.append("| **QoL recall (`question_of_law` items)** | %s; macro %s over %d judgments |" % (
        fmt(S["primary"]["qol_recall_by_qol"]["k"], S["primary"]["qol_recall_by_qol"]["n"]),
        pct(S["primary"]["qol_recall_by_qol"]["macro"]), S["primary"]["qol_recall_by_qol"]["macro_n_judgments"]))
    L.append("| QoL recall, court-voice set | %s |" % fmt(S["primary"]["qol_recall_by_cv"]["k"], S["primary"]["qol_recall_by_cv"]["n"]))
    head = "\n".join(L)

    L = ["| Metric | Strict (>=0.80, same page) | Primary (>=0.60, +-1) | Loose (>=0.40, +-1) |", "| --- | --- | --- | --- |"]
    for k, nm in (("holding_recall_by_holding", "Holding recall (`holding`)"), ("holding_recall_by_cv", "Holding recall (court-voice)"),
                  ("qol_recall_by_qol", "QoL recall"), ("all_ref_recall_by_cv", "All ref items (court-voice)"),
                  ("all_ref_recall_by_any", "All ref items (any item type)"),
                  ("holding_prec_vs_refholding", "Holding precision LB vs ref holdings"),
                  ("holding_prec_vs_anyref", "Holding precision LB vs any ref item"),
                  ("qol_prec_vs_refqol", "QoL precision LB vs ref QoL")):
        L.append("| %s | %s |" % (nm, " | ".join(fmt(S[v][k]["k"], S[v][k]["n"]) for v in ("strict", "primary", "loose"))))
    sens = "\n".join(L)

    L = ["| holding items with rank_in_opinion <= | n predicted | recall of ref holdings | precision LB |", "| --- | --- | --- | --- |"]
    for t in M["rank_tradeoff"]:
        L.append("| %d | %d | %s | %s |" % (t["rank_le"], t["n_pred"], fmt(t["recall_k"], t["recall_n"]), fmt(t["prec_lb_k"], t["prec_lb_n"])))
    rank = "\n".join(L)

    L = ["| Label | holding sample | question_of_law sample |", "| --- | --- | --- |"]
    keys = sorted(set(a["holding"]["labels"]) | set(a["question_of_law"]["labels"]))
    for k in keys:
        L.append("| %s | %d | %d |" % (k, a["holding"]["labels"].get(k, 0), a["question_of_law"]["labels"].get(k, 0)))
    adj = "\n".join(L)
    L = ["| Origin error (holding sample) | Rate |", "| --- | --- |"]
    for sub in ("quoted_precedent", "submission", "lower_forum"):
        o = a["holding"]["origin_" + sub]
        L.append("| %s | %s |" % (sub, fmt(o["k"], o["n"])))
    o = sum(a["holding"]["origin_" + s]["k"] for s in ("quoted_precedent", "submission", "lower_forum"))
    L.append("| any non-court origin | %s |" % fmt(o, a["holding"]["n"]))
    origin = "\n".join(L)

    an = M["anchoring"]
    L = ["| Anchoring check | Result |", "| --- | --- |",
         "| Page verified (court-voice items, >=90%% content tokens on claimed page span, PyMuPDF text) | %s |" % fmt(an["page_ok"], an["n"]),
         "| Paragraph verified, strict (last marker before excerpt = N) | %s |" % fmt(an["para_strict"], an["para_n"]),
         "| Paragraph verified, lenient (N is a line-start marker within claimed page and 3 before) | %s |" % fmt(an["para_lenient"], an["para_n"]),
         "| POST-HOC (not pre-registered): paragraph verified among items located by a noise-tolerant locator | %s |" % fmt(an["posthoc_ok"], an["posthoc_located"]),
         "| Reference excerpts passing the same page check (sanity) | %s |" % fmt(M["reference_anchoring"]["k"], M["reference_anchoring"]["n"])]
    for t, (k, n) in M["anchoring_by_type"].items():
        L.append("| page verified: %s | %s |" % (t, fmt(k, n)))
    anc = "\n".join(L)

    nc = M["negative_control"]
    neg = "\n".join(["| Shuffle control (holding items of X vs reference holdings of Y, 5 cyclic shifts) | Spurious match rate |", "| --- | --- |",
                     "| Primary matcher, page rule applied | %s |" % fmt(nc["page_rule"]["k"], nc["page_rule"]["n"]),
                     "| Primary matcher, page rule disabled | %s |" % fmt(nc["no_page_rule"]["k"], nc["no_page_rule"]["n"]),
                     "| (Comparison: same judgment, page rule disabled) | %s |" % fmt(nc["same_judgment_no_page_rule"]["k"], nc["same_judgment_no_page_rule"]["n"])])

    L = ["| judgment_id | title | opinions | ref H | H rec (`holding`) | H rec (cv) | ref QoL | QoL rec | pred H | pred H ref-match | pred QoL | sample H correct |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in M["per_judgment"]:
        L.append("| %s | %s | %s | %d | %d | %d | %d | %d | %d | %d | %d | %d/%d |" % (
            r["judgment_id"], r["title"].replace("|", "/"), r["opinions"].replace("|", "/"), r["ref_holdings"], r["rec_by_holding"], r["rec_by_cv"],
            r["ref_qol"], r["qol_rec"], r["pred_holding"], r["pred_holding_refmatch"], r["pred_qol"],
            r["sample_holding_correct"], r["sample_holding"]))
    pj = "\n".join(L)
    L = ["| Reference opinion | holdings recovered by `holding` |", "| --- | --- |"]
    for k, (h, n) in M["recall_by_ref_opinion"].items():
        L.append("| %s | %s |" % (k, fmt(h, n)))
    L.append("")
    L.append("| Missed reference holdings: best-matching item type (primary matcher) | count |")
    L.append("| --- | --- |")
    for k, v in M["missed_holdings_by_type"].items():
        L.append("| %s | %d |" % (k, v))
    opn = "\n".join(L)
    return {"HEADLINE": head, "SENSITIVITY": sens, "RANK": rank, "ADJUDICATION": adj, "ORIGIN": origin,
            "ANCHORING": anc, "NEGATIVE": neg, "PER_JUDGMENT": pj, "OPINION": opn}


def render_report(M, existing):
    T = tables(M)
    txt = existing
    for k, v in T.items():
        a, b = "<!-- AUTO:%s -->" % k, "<!-- /AUTO:%s -->" % k
        if a in txt:
            pre, rest = txt.split(a, 1)
            _, post = rest.split(b, 1)
            txt = pre + a + "\n" + v + "\n" + b + post
    return txt


def sums_text():
    files = ["README.md", "ADJUDICATION_SAMPLE.csv", "EVALUATION_ROWS.csv", "EVALUATION_HOLDINGS_C12.md",
             "tools/eval_holdings_c12.py", "predictions/ids.txt", "predictions/HOLDINGS_C12.jsonl",
             "predictions/HOLDINGS_C12_JUDGMENTS.csv", "predictions/RUN_META.json", "predictions/METRICS.json",
             "predictions/PAGE_TEXT_PYMUPDF.jsonl", "predictions/ADJUDICATION_CONTEXT.txt"]
    return "".join("%s  %s\n" % (sha(os.path.join(HERE, f)), f) for f in files if os.path.exists(os.path.join(HERE, f)))


def cmd_run(check):
    for f, h in FROZEN.items():
        assert sha(os.path.join(C, "holdings", "tools", f)) == h, f
    M, rows_text, metrics_text = compute()
    rep = render_report(M, open(REPORT, encoding="utf-8").read()) if os.path.exists(REPORT) else None
    if check:
        ok = True
        for path, t in ((ROWS, rows_text), (METRICS, metrics_text)) + (((REPORT, rep),) if rep else ()):
            same = open(path, encoding="utf-8").read() == t
            print(("OK   " if same else "DIFF ") + os.path.relpath(path, HERE))
            ok &= same
        cur = open(os.path.join(HERE, "SHA256SUMS")).read() if os.path.exists(os.path.join(HERE, "SHA256SUMS")) else ""
        s = cur == sums_text()
        print(("OK   " if s else "DIFF ") + "SHA256SUMS")
        sys.exit(0 if ok and s else 1)
    open(ROWS, "w", encoding="utf-8").write(rows_text)
    open(METRICS, "w", encoding="utf-8").write(metrics_text)
    if rep is not None:
        open(REPORT, "w", encoding="utf-8").write(rep)
    open(os.path.join(HERE, "SHA256SUMS"), "w").write(sums_text())
    print(json.dumps({k: M["metrics"]["primary"][k] for k in M["metrics"]["primary"]}, default=str)[:3000])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "render":
        cmd_render()
    elif a and a[0] == "sample":
        cmd_sample()
    elif a and a[0] == "run":
        cmd_run("--check" in a)
    elif a == ["--check"]:
        cmd_run(True)
    else:
        sys.exit(__doc__)
