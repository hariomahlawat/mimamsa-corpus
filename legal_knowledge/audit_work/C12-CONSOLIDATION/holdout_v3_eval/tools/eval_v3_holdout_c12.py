#!/usr/bin/env python3
"""C12 WS-D: score the frozen V3 outcome extractor against the double-coded V3 holdout (see ../PROTOCOL.md).

  python -I -B eval_v3_holdout_c12.py [--check]

Reads holdout_v3/GROUND_TRUTH_V3.csv, holdout_v3/HOLDOUT_V3_SAMPLE.csv, extractor_v3/outputs/OUTCOMES_V3.csv and the C11
V2 outputs; text blobs for traceability come from the git object store /home/user/c7 (read-only).
Writes RESULTS.json, RESULTS.md, ROWS.csv, ERRORS.csv, JUDGMENT_COMPARISON.csv next to this tool's parent directory."""
import csv, hashlib, io, json, math, random, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
PKG = OUT.parent
AW = PKG.parent
C7 = "/home/user/c7"
GT = PKG / "holdout_v3" / "GROUND_TRUTH_V3.csv"
SAMPLE = PKG / "holdout_v3" / "HOLDOUT_V3_SAMPLE.csv"
V3 = PKG / "extractor_v3" / "outputs" / "OUTCOMES_V3.csv"
V2 = AW / "C11-JUDICIAL-QUALITY" / "extraction" / "outputs" / "OUTCOMES_V2.csv"
FIELDS = ("printed_disposal", "substantive_result")
UNSCORABLE = {"unclear", "other"}
ABSTAIN = {"", "OUTCOME_UNVERIFIED"}
FAMILY = {"allowed": "ALLOWED", "partly_allowed": "PARTLY", "dismissed": "DISMISSED", "dismissed_as_withdrawn": "DISMISSED",
          "dismissed_as_infructuous": "DISMISSED", "dismissed_in_default": "DISMISSED", "disposed_of": "DISPOSED",
          "disposed_of_with_directions": "DISPOSED", "disposed": "DISPOSED", "remanded": "REMANDED",
          "set_aside_and_remanded": "REMANDED", "transferred": "TRANSFERRED"}
TARGET_P, TARGET_C = 0.95, 0.85
SEED = "c12-v3-eval"


def key(s):  # identical to tools/holdout_v3_agreement_c12.py
    m = re.findall(r"(\d{1,6})\s*(?:/|-|\s+of\s+|\s+OF\s+)\s*((?:19|20)\d\d)", s or "")
    return ";".join(sorted({f"{int(a)}-{b}" for a, b in m})) or (s or "").strip().upper()


def fam(x):
    return FAMILY.get(x, x)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def rd(x):
    return None if x is None else round(x, 4)


def load():
    gt = list(csv.DictReader(open(GT, encoding="utf-8")))
    sample = {r["judgment_id"]: r for r in csv.DictReader(open(SAMPLE, encoding="utf-8"))}
    ids = {r["judgment_id"] for r in gt}
    v3 = defaultdict(list)
    for r in csv.DictReader(open(V3, encoding="utf-8")):
        if r["judgment_id"] in ids:
            v3[r["judgment_id"]].append(r)
    v2 = {}
    for r in csv.DictReader(open(V2, encoding="utf-8")):
        if r["judgment_id"] in ids:
            v2[r["judgment_id"]] = r
    return gt, sample, v3, v2


def match(gts, preds):
    """Return list of (gt_row, pred_row|None) and list of extra pred rows."""
    if len(gts) == 1 and len(preds) == 1:
        return [(gts[0], preds[0])], []
    used, pairs = set(), []
    for g in gts:
        gk = key(g["proceeding"])
        hit = None
        if gk == "ALL" and len(preds) == 1:
            hit = 0
        else:
            for i, p in enumerate(preds):
                if i not in used and key(p["proceeding"]) == gk:
                    hit = i; break
        if hit is not None:
            used.add(hit)
        pairs.append((g, preds[hit] if hit is not None else None))
    return pairs, [p for i, p in enumerate(preds) if i not in used]


_blob_cache = {}


def blob_text(text_source):
    m = re.search(r"@blob:([0-9a-f]{40})", text_source or "")
    if not m:
        return None
    b = m.group(1)
    if b not in _blob_cache:
        r = subprocess.run(["git", "-C", C7, "cat-file", "-p", b], capture_output=True)
        _blob_cache[b] = r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None
    return _blob_cache[b]


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def trace(p):
    """(excerpt_at_offset, excerpt_anywhere, page_consistent) for an answered V3 row."""
    t = blob_text(p.get("text_source"))
    ex = norm(p.get("excerpt"))
    if t is None or not ex:
        return (False, False, False)
    try:
        a, b = int(p["char_start"]), int(p["char_end"])
    except (ValueError, KeyError):
        a = b = None
    at = a is not None and ex in norm(t[max(0, a - 10):b + 10])
    anywhere = ex in norm(t)
    page_ok = False
    if a is not None:
        pages = re.findall(r"\[\[page (\d+)\]\]", t[:a + 1])
        page_ok = bool(pages) and pages[-1] == (p.get("page") or "").strip()
    return (at, anywhere, page_ok)


def score(rows, field, label_fn=lambda x: x):
    scor = [r for r in rows if r[f"gt_{field}"] not in UNSCORABLE]
    ans = [r for r in scor if r[f"v3_{field}"] not in ABSTAIN]
    ok = [r for r in ans if label_fn(r[f"v3_{field}"]) == label_fn(r[f"gt_{field}"])]
    return dict(scorable=len(scor), answered=len(ans), correct=len(ok),
                precision=rd(len(ok) / len(ans)) if ans else None, precision_wilson95=wilson(len(ok), len(ans)),
                coverage=rd(len(ans) / len(scor)) if scor else None, coverage_wilson95=wilson(len(ans), len(scor)))


def bootstrap(rows, field):
    byj = defaultdict(list)
    for r in rows:
        byj[r["judgment_id"]].append(r)
    js = sorted(byj)
    rng = random.Random(SEED + field)
    ps, cs = [], []
    for _ in range(2000):
        pick = [rng.choice(js) for _ in js]
        rr = [r for j in pick for r in byj[j]]
        s = score(rr, field)
        if s["precision"] is not None:
            ps.append(s["precision"])
        if s["coverage"] is not None:
            cs.append(s["coverage"])
    q = lambda v: [round(sorted(v)[int(0.025 * len(v))], 4), round(sorted(v)[int(0.975 * len(v)) - 1], 4)]
    return dict(precision_cluster95=q(ps), coverage_cluster95=q(cs))


def category(r, field):
    g, v = r[f"gt_{field}"], r[f"v3_{field}"]
    if g in UNSCORABLE:
        return None
    if r["match"] == "UNMATCHED":
        return "PROCEEDING_UNMATCHED"
    if v in ABSTAIN:
        return "ABSTAINED"
    if v == g:
        return None
    return "WRONG_LABEL_SAME_FAMILY" if fam(v) == fam(g) else "WRONG_FAMILY"


def build():
    gt, sample, v3, v2 = load()
    byj = defaultdict(list)
    for r in gt:
        byj[r["judgment_id"]].append(r)
    rows, extras, traces = [], [], Counter()
    for j in sorted(byj, key=lambda x: byj[x][0]["holdout_id"]):
        pairs, ex = match(byj[j], v3.get(j, []))
        s = sample[j]
        for p in ex:
            extras.append(dict(holdout_id=byj[j][0]["holdout_id"], judgment_id=j, v3_proceeding=p["proceeding"],
                               v3_printed=p["printed_disposal"], v3_substantive=p["substantive_result"]))
        for g, p in pairs:
            row = dict(holdout_id=g["holdout_id"], judgment_id=j, court=s["court"], stratum=s["stratum"], gt_source=g["source"],
                       gt_proceeding=g["proceeding"], v3_proceeding=p["proceeding"] if p else "",
                       match="MATCHED" if p else "UNMATCHED",
                       gt_printed_disposal=g["printed_disposal"], v3_printed_disposal=p["printed_disposal"] if p else "",
                       gt_substantive_result=g["substantive_result"], v3_substantive_result=p["substantive_result"] if p else "",
                       v3_abstain_reason=p["abstain_reason"] if p else "", v3_page=p["page"] if p else "",
                       v3_paragraph=p["paragraph"] if p else "", v3_excerpt=(p["excerpt"] if p else "")[:300])
            answered = p is not None and any(p[f] not in ABSTAIN for f in FIELDS)
            if answered:
                at, anywhere, page_ok = trace(p)
                traces["answered"] += 1; traces["excerpt_at_offset"] += at; traces["excerpt_in_text"] += anywhere
                traces["page_consistent"] += page_ok; traces["paragraph_given"] += bool((p.get("paragraph") or "").strip())
                row.update(trace_excerpt_at_offset=at, trace_excerpt_in_text=anywhere, trace_page_consistent=page_ok)
            else:
                row.update(trace_excerpt_at_offset="", trace_excerpt_in_text="", trace_page_consistent="")
            for f in FIELDS:
                row[f"category_{f}"] = category(row, f) or ""
            rows.append(row)

    res = {"protocol": "PROTOCOL.md", "inputs": {"ground_truth_sha256": sha(GT), "sample_sha256": sha(SAMPLE),
                                                 "v3_outputs_sha256": sha(V3), "v2_outputs_sha256": sha(V2)},
           "n_judgments": len(byj), "n_gt_rows": len(rows),
           "unmatched_gt_rows": sum(r["match"] == "UNMATCHED" for r in rows), "extra_v3_rows": len(extras),
           "targets": {"strict_precision": TARGET_P, "coverage": TARGET_C}, "fields": {}}
    for f in FIELDS:
        st = score(rows, f); fa = score(rows, f, fam)
        st.update(bootstrap(rows, f))
        st["meets_targets"] = bool(st["precision"] is not None and st["precision"] >= TARGET_P and st["coverage"] >= TARGET_C)
        res["fields"][f] = {"strict": st, "family": {k: fa[k] for k in ("correct", "answered", "precision", "precision_wilson95")},
                            "by_court": {c: score([r for r in rows if r["court"] == c], f) for c in sorted({r["court"] for r in rows})},
                            "by_stratum": {c: score([r for r in rows if r["stratum"] == c], f) for c in sorted({r["stratum"] for r in rows})},
                            "by_gt_source": {c: score([r for r in rows if r["gt_source"] == c], f) for c in sorted({r["gt_source"] for r in rows})},
                            "categories": dict(sorted(Counter(r[f"category_{f}"] for r in rows if r[f"category_{f}"]).items()))}
    both = [r for r in rows if r["gt_printed_disposal"] not in UNSCORABLE and r["gt_substantive_result"] not in UNSCORABLE]
    both_ans = [r for r in both if r["v3_printed_disposal"] not in ABSTAIN and r["v3_substantive_result"] not in ABSTAIN]
    both_ok = [r for r in both_ans if r["v3_printed_disposal"] == r["gt_printed_disposal"] and r["v3_substantive_result"] == r["gt_substantive_result"]]
    res["both_fields_strict"] = dict(scorable=len(both), answered=len(both_ans), correct=len(both_ok),
                                     precision=rd(len(both_ok) / len(both_ans)) if both_ans else None,
                                     precision_wilson95=wilson(len(both_ok), len(both_ans)),
                                     coverage=rd(len(both_ans) / len(both)) if both else None)
    res["traceability"] = {k: traces[k] for k in ("answered", "excerpt_at_offset", "excerpt_in_text", "page_consistent", "paragraph_given")}

    # judgment-level comparison, printed field
    comp, jstats = [], defaultdict(Counter)
    for j in sorted(byj, key=lambda x: byj[x][0]["holdout_id"]):
        glabs = {r["printed_disposal"] for r in byj[j]}
        g = glabs.pop() if len(glabs) == 1 else "MIXED"
        v3l = {r["printed_disposal"] for r in v3.get(j, [])}
        v3j = "OUTCOME_UNVERIFIED" if not v3l else (v3l.pop() if len(v3l) == 1 else "MIXED")
        v2j = v2.get(j, {}).get("outcome", "")
        cr = v2.get(j, {}).get("crawler_outcome", "")
        comp.append(dict(holdout_id=byj[j][0]["holdout_id"], judgment_id=j, court=sample[j]["court"], gt=g, v3=v3j, v2=v2j, crawler=cr))
        if g in UNSCORABLE or g == "MIXED":
            continue
        for name, val, strict_ok in (("v3", v3j, True), ("v2", v2j, True), ("crawler", cr, False)):
            st = jstats[name]; st["scorable"] += 1
            if val in ABSTAIN or val == "MIXED":
                continue
            st["answered"] += 1
            st["family_correct"] += fam(val) == fam(g)
            if strict_ok:
                st["strict_correct"] += val == g
    res["judgment_level_printed"] = {}
    for name, st in jstats.items():
        d = dict(scorable=st["scorable"], answered=st["answered"], coverage=rd(st["answered"] / st["scorable"]) if st["scorable"] else None,
                 family_precision=rd(st["family_correct"] / st["answered"]) if st["answered"] else None,
                 family_precision_wilson95=wilson(st["family_correct"], st["answered"]))
        if name != "crawler":
            d.update(strict_precision=rd(st["strict_correct"] / st["answered"]) if st["answered"] else None,
                     strict_precision_wilson95=wilson(st["strict_correct"], st["answered"]))
        res["judgment_level_printed"][name] = d

    # ---- added after independent review (review_v3_holdout_eval F01/F02); post hoc, headline unchanged ----
    V2_VOCAB = {r.get("outcome", "") for r in csv.DictReader(open(V2, encoding="utf-8"))} - ABSTAIN
    common = defaultdict(Counter)
    for c in comp:
        g = c["gt"]
        if g in UNSCORABLE or g == "MIXED" or g not in V2_VOCAB:
            continue
        for name in ("v3", "v2"):
            v = c[name]; st = common[name]; st["scorable"] += 1
            if v in ABSTAIN or v == "MIXED":
                continue
            st["answered"] += 1; st["correct"] += v == g
    res["posthoc_judgment_level_common_vocabulary"] = {
        "note": "Judgment-level printed field restricted to ground-truth labels V2 can output (review F01). Post hoc.",
        "v2_vocabulary": sorted(V2_VOCAB),
        **{n: dict(scorable=s["scorable"], answered=s["answered"], correct=s["correct"],
                   strict_precision=rd(s["correct"] / s["answered"]) if s["answered"] else None,
                   strict_precision_wilson95=wilson(s["correct"], s["answered"])) for n, s in common.items()}}
    corpus = Counter()
    seen = set()
    for r in csv.DictReader(open(V3, encoding="utf-8")):
        if r["judgment_id"] not in seen:
            seen.add(r["judgment_id"]); corpus[r["court"]] += 1
    tot = sum(corpus.values())
    wres = {"note": "Precision weighted by each court's share of the V3 corpus (judgments), using per-court holdout precision; "
                    "coverage weighted likewise (review F02 / C11 F03 carry-over). Post hoc; small cells, indicative only.",
            "corpus_judgments_by_court": dict(sorted(corpus.items()))}
    for f in FIELDS:
        bc = res["fields"][f]["by_court"]
        ws = {c: corpus[c] / tot for c in bc if corpus.get(c)}
        pw = [(ws[c], bc[c]["precision"]) for c in ws if bc[c]["precision"] is not None]
        cw = [(ws[c], bc[c]["coverage"]) for c in ws if bc[c]["coverage"] is not None]
        wres[f] = dict(weighted_precision=rd(sum(w * x for w, x in pw) / sum(w for w, _ in pw)) if pw else None,
                       weighted_coverage=rd(sum(w * x for w, x in cw) / sum(w for w, _ in cw)) if cw else None,
                       courts_in_holdout_weight=rd(sum(ws.values())))
    res["posthoc_population_weighted"] = wres

    def tocsv(rs):
        if not rs:
            return ""
        s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(rs[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rs)
        return s.getvalue()
    errors = [r for r in rows if r["category_printed_disposal"] or r["category_substantive_result"]]
    out = {"RESULTS.json": json.dumps(res, indent=1, sort_keys=True) + "\n", "ROWS.csv": tocsv(rows), "ERRORS.csv": tocsv(errors),
           "EXTRA_V3_ROWS.csv": tocsv(extras) or "holdout_id,judgment_id,v3_proceeding,v3_printed,v3_substantive\n",
           "JUDGMENT_COMPARISON.csv": tocsv(comp)}
    out["RESULTS.md"] = render_md(res)
    return out


def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def ci(v):
    return "n/a" if not v or v[0] is None else f"{100 * v[0]:.1f}–{100 * v[1]:.1f}%"


def render_md(res):
    L = ["# V3 outcome extractor: holdout results (generated by tools/eval_v3_holdout_c12.py; see PROTOCOL.md)", "",
         f"V3 outputs sha256 `{res['inputs']['v3_outputs_sha256']}`; ground truth sha256 `{res['inputs']['ground_truth_sha256']}`.", "",
         f"{res['n_judgments']} judgments, {res['n_gt_rows']} ground-truth proceeding rows; unmatched ground-truth rows "
         f"{res['unmatched_gt_rows']}; extra V3 rows {res['extra_v3_rows']}.", "",
         "| Field | Strict precision | Wilson 95% | Cluster bootstrap 95% | Coverage | Wilson 95% | Meets ≥95% / ≥85% |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for f, d in res["fields"].items():
        s = d["strict"]
        L.append(f"| {f} | {s['correct']}/{s['answered']} = {pct(s['precision'])} | {ci(s['precision_wilson95'])} | "
                 f"{ci(s['precision_cluster95'])} | {s['answered']}/{s['scorable']} = {pct(s['coverage'])} | "
                 f"{ci(s['coverage_wilson95'])} | {'yes' if s['meets_targets'] else 'no'} |")
    b = res["both_fields_strict"]
    L += ["", f"Both fields exactly right: {b['correct']}/{b['answered']} = {pct(b['precision'])} ({ci(b['precision_wilson95'])}); coverage {pct(b['coverage'])}.", ""]
    for f, d in res["fields"].items():
        L += [f"## {f}", "", f"Family precision {d['family']['correct']}/{d['family']['answered']} = {pct(d['family']['precision'])} ({ci(d['family']['precision_wilson95'])}).", "",
              "| Group | Precision | Coverage |", "| --- | --- | --- |"]
        for grp in ("by_court", "by_stratum", "by_gt_source"):
            for k, s in d[grp].items():
                L.append(f"| {grp[3:]}: {k} | {s['correct']}/{s['answered']} = {pct(s['precision'])} | {s['answered']}/{s['scorable']} = {pct(s['coverage'])} |")
        L += ["", "Failure categories: " + ", ".join(f"{k} {v}" for k, v in d["categories"].items()), ""]
    t = res["traceability"]
    L += ["## Traceability", "", f"Of {t['answered']} answered rows: excerpt found at the cited offset {t['excerpt_at_offset']}, "
          f"anywhere in the cited text {t['excerpt_in_text']}, page consistent with the preceding page marker {t['page_consistent']}, "
          f"paragraph given {t['paragraph_given']}.", "", "## Judgment-level comparison (printed field only)", "",
          "| Method | Coverage | Strict precision | Family precision |", "| --- | --- | --- | --- |"]
    for n, d in res["judgment_level_printed"].items():
        L.append(f"| {n} | {d['answered']}/{d['scorable']} = {pct(d['coverage'])} | "
                 f"{pct(d.get('strict_precision')) + ' (' + ci(d.get('strict_precision_wilson95')) + ')' if 'strict_precision' in d else 'n/a (vocabulary)'} | "
                 f"{pct(d['family_precision'])} ({ci(d['family_precision_wilson95'])}) |")
    cv = res["posthoc_judgment_level_common_vocabulary"]; pw = res["posthoc_population_weighted"]
    L += ["", "## Added after independent review (post hoc; the pre-registered figures above are unchanged)", "",
          "**Common vocabulary (review F01).** On judgments whose ground-truth printed label V2 can output: "
          + "; ".join(f"{n} {cv[n]['correct']}/{cv[n]['answered']} = {pct(cv[n]['strict_precision'])} ({ci(cv[n]['strict_precision_wilson95'])})"
                      for n in ("v3", "v2") if n in cv)
          + ". V3's strict lead over V2 in the table above comes from labels V2 cannot express.", "",
          "**Population-weighted (review F02).** Weighted by court share of the V3 corpus: "
          + "; ".join(f"{f}: precision {pct(pw[f]['weighted_precision'])}, coverage {pct(pw[f]['weighted_coverage'])}" for f in FIELDS)
          + ". Small per-court cells; indicative only.", "",
          "**Matcher sensitivity (review).** Re-matching the two pairs the reviewer classed as matcher artefacts (V3H005, V3H036) gives "
          "printed 127/139 = 91.4% (coverage 65.3%) and substantive 109/115 = 94.8% (coverage 55.6%) (reviewer's computation, "
          "`reviews/review_v3_holdout_eval.md`). Not applied to the headline."]
    L += ["", "All V3 outputs remain AUTOMATED_CANDIDATE_NOT_VERIFIED; these are technical measurements, not legal validation.", ""]
    return "\n".join(L)


def main():
    out = build()
    if "--check" in sys.argv[1:]:
        bad = [k for k, v in out.items() if not (OUT / k).exists() or (OUT / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED: " + ", ".join(bad) if bad else "evaluation reproduces"); return 1 if bad else 0
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(out["RESULTS.md"]); return 0


if __name__ == "__main__":
    sys.exit(main())
