#!/usr/bin/env python3
"""In-sample dev evaluation of holdings_c12 against reviewer-identified holdings.

Dev ground truth (ALL RESULTS ARE IN-SAMPLE: these rows were read while the rules were written and tuned):
  C11 holdout ground_truth_A.csv / ground_truth_B.csv  holding_N_pinpoint / holding_N_excerpt
  C10 review_A.csv / review_B.csv                       principal_issue_and_answer + pinpoint (page level only)
Baseline: C11 PROPOSITIONS_V2.jsonl scored with the same matcher.

Matcher (same rule as the C11 extraction review): a predicted item matches a ground-truth holding when the item's
page range is within one page of the ground-truth page and the two texts share at least 40 characters of common
text after lower-casing and removing everything except letters and digits.

Usage: eval_dev_holdings.py PRED_DIR OUT_MD [--rows OUT_CSV]
  PRED_DIR holds HOLDINGS_C12.jsonl and HOLDINGS_C12_JUDGMENTS.csv produced by `holdings_c12.py ids` on dev ids.
  `eval_dev_holdings.py --write-ids FILE` writes the dev judgment ids.
"""
import argparse
import csv
import difflib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIT = os.path.dirname(os.path.dirname(ROOT))
C11 = os.path.join(AUDIT, "C11-JUDICIAL-QUALITY")
GT_FILES = [os.path.join(C11, "holdout", "ground_truth_A.csv"), os.path.join(C11, "holdout", "ground_truth_B.csv")]
REV_FILES = [os.path.join(AUDIT, "C10-HF-JUDGMENTS", "review", "review_A.csv"),
             os.path.join(AUDIT, "C10-HF-JUDGMENTS", "review", "review_B.csv")]
C11_PROPS = os.path.join(C11, "extraction", "outputs", "PROPOSITIONS_V2.jsonl")
SCOPE = os.path.join(ROOT, "outputs", "SCOPE_C12.csv")

COURT_SET = {"question_of_law", "holding", "reasoning", "obiter_candidate", "operative_direction"}


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def lcs_len(a, b):
    if not a or not b:
        return 0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / float(n)
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def pct(k, n):
    lo, hi = wilson(k, n)
    return "%d/%d = %.1f%% (%.1f-%.1f)" % (k, n, 100.0 * k / n if n else 0.0, 100 * lo, 100 * hi)


def parse_page(pin):
    m = re.search(r"(?:pdf\s*)?\bp(?:age)?\.?\s*(\d{1,4})", pin or "", re.I)
    return int(m.group(1)) if m else None


def load_gt():
    rows = []
    seen = set()
    for f in GT_FILES:
        with open(f, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                for n in (1, 2, 3):
                    ex = (r.get("holding_%d_excerpt" % n) or "").strip()
                    if not ex or ex.upper() in ("NONE", "N/A", "NA", "-"):
                        continue
                    key = (r["judgment_id"], norm(ex))
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append({"src": os.path.basename(f), "holdout_id": r["holdout_id"], "judgment_id": r["judgment_id"],
                                 "pinpoint": r.get("holding_%d_pinpoint" % n, ""), "page": parse_page(r.get("holding_%d_pinpoint" % n, "")),
                                 "excerpt": ex, "issue": r.get("holding_%d_issue" % n, "")})
    return rows


def parse_pages(pin):
    pages = set()
    for m in re.finditer(r"pp?\.?\s*(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?", pin or ""):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        if b < a or b - a > 30:
            b = a
        pages.update(range(a, b + 1))
    return pages


def load_reviews():
    out = []
    for f in REV_FILES:
        with open(f, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                pages = parse_pages(r.get("pinpoint", ""))
                out.append({"src": os.path.basename(f), "judgment_id": r["judgment_id"], "pages": pages,
                            "issue_answer": r.get("principal_issue_and_answer", ""), "pinpoint": r.get("pinpoint", "")})
    return out


def dev_ids():
    ids = []
    for r in load_gt():
        if r["judgment_id"] not in ids:
            ids.append(r["judgment_id"])
    for r in load_reviews():
        if r["judgment_id"] not in ids:
            ids.append(r["judgment_id"])
    return ids


def item_pages(it):
    p0 = it.get("page")
    p1 = it.get("page_end", p0)
    if p0 is None:
        return set()
    return set(range(p0, (p1 if p1 is not None else p0) + 1))


def matches(gt, it, use_page=True, need=40):
    if use_page and gt["page"] is not None:
        if not any(abs(p - gt["page"]) <= 1 for p in item_pages(it)):
            return False
    a = norm(gt["excerpt"])
    b = norm(it.get("excerpt_clean") or it.get("excerpt"))
    need = min(need, len(a))
    return lcs_len(a, b) >= need


def load_pred(d):
    items = {}
    with open(os.path.join(d, "HOLDINGS_C12.jsonl"), encoding="utf-8") as f:
        for ln in f:
            r = json.loads(ln)
            items.setdefault(r["judgment_id"], []).append(r)
    jud = {}
    with open(os.path.join(d, "HOLDINGS_C12_JUDGMENTS.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            jud[r["judgment_id"]] = r
    return items, jud


def load_c11(ids):
    out = {}
    with open(C11_PROPS, encoding="utf-8") as f:
        for ln in f:
            if '"judgment_id": "' not in ln:
                continue
            r = json.loads(ln)
            if r["judgment_id"] in ids:
                out.setdefault(r["judgment_id"], []).append({"page": r["page"], "page_end": r["page"], "excerpt": r["excerpt"],
                                                             "origin": r["origin"]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pred_dir", nargs="?")
    ap.add_argument("out_md", nargs="?")
    ap.add_argument("--rows")
    ap.add_argument("--write-ids")
    a = ap.parse_args(argv)
    if a.write_ids:
        with open(a.write_ids, "w", encoding="utf-8") as f:
            f.write("# dev judgment ids (IN-SAMPLE): C11 holdout ground truth A/B + C10 review A/B\n")
            for j in dev_ids():
                f.write(j + "\n")
        print("wrote", a.write_ids)
        return 0
    items, jud = load_pred(a.pred_dir)
    gt = load_gt()
    revs = load_reviews()
    scope = set()
    if os.path.exists(SCOPE):
        with open(SCOPE, encoding="utf-8", newline="") as f:
            scope = set(r["judgment_id"] for r in csv.DictReader(f))
    ids = set(r["judgment_id"] for r in gt) | set(r["judgment_id"] for r in revs)
    c11 = load_c11(ids)

    def court_of(j):
        return (jud.get(j, {}).get("court") or "")

    def subset(g, name):
        if name == "all":
            return True
        if name == "sc_scope":
            return g["judgment_id"] in scope
        if name == "sc_all":
            return "Supreme" in court_of(g["judgment_id"])
        if name == "hc":
            return "Supreme" not in court_of(g["judgment_id"])
        return True

    sets = [("holding", {"holding"}), ("holding+question_of_law", {"holding", "question_of_law"}),
            ("court-voice set (question, holding, reasoning, obiter, operative)", COURT_SET),
            ("any emitted item", None)]
    rows_out = []
    loc = []
    for g in gt:
        its = items.get(g["judgment_id"], [])
        rec = dict(g)
        prio = ["holding", "question_of_law", "reasoning", "operative_direction", "obiter_candidate",
                "quoted_precedent", "lower_court_finding", "submission"]
        hits = sorted([it for it in its if matches(g, it)], key=lambda it: (prio.index(it["item_type"]), it["char_start"]))
        best = hits[0] if hits else None
        rec["matched_type"] = best["item_type"] if best else ""
        rec["matched_item_id"] = best["item_id"] if best else ""
        rec["matched_score"] = best["holding_score"] if best else ""
        rec["matched_opinion"] = best["opinion"] if best else ""
        rec["matched_any_page_ignored"] = "Y" if any(matches(g, it, use_page=False) for it in its) else "N"
        types = set(it["item_type"] for it in hits)
        rec["matched_types_all"] = ";".join(sorted(types))
        c = c11.get(g["judgment_id"], [])
        rec["c11_court_match"] = "Y" if any(matches(g, x) for x in c if x["origin"] in ("COURT_HOLDING_CANDIDATE", "COURT_REASONING_CANDIDATE")) else "N"
        rec["c11_any_match"] = "Y" if any(matches(g, x) for x in c) else "N"
        # top-k by holding_score among court-voice items
        cv = sorted([it for it in its if it["item_type"] in ("holding", "reasoning")], key=lambda x: (-x["holding_score"], x["char_start"]))
        rank = next((k + 1 for k, it in enumerate(cv) if matches(g, it)), "")
        rec["rank_among_holding_reasoning"] = rank
        rec["in_sc_scope"] = "Y" if g["judgment_id"] in scope else "N"
        rec["court"] = court_of(g["judgment_id"])
        rows_out.append(rec)

    L = []
    L.append("# DEV_EVALUATION_HOLDINGS (C12 Workstream E, part 1)\n")
    L.append("**ALL FIGURES ARE IN-SAMPLE.** The dev rows below were read while the rules and thresholds of `holdings_core.py` were written and tuned. "
             "They are not an estimate of performance on unseen judgments; the blind reference set is the only valid test.\n")
    L.append("Matcher: same page within one, and at least 40 common characters after normalising to lower-case letters and digits "
             "(the rule used in the C11 extraction review). Baseline: C11 `PROPOSITIONS_V2.jsonl` scored with the same matcher on the same rows.\n")
    L.append("Ground truth: %d distinct reviewer holdings in %d judgments from C11 `ground_truth_A.csv`/`ground_truth_B.csv` (single-coded; see C11 review F02)." % (
        len(gt), len(set(g["judgment_id"] for g in gt))))
    L.append("")
    for name, title in [("all", "All dev judgments (SC + HC)"), ("sc_all", "Supreme Court judgments"), ("sc_scope", "Judgments in the C12 scope set"),
                        ("hc", "High Court judgments (outside the C12 scope; tool still run on them)")]:
        G = [r for r in rows_out if subset(r, name)]
        if not G:
            continue
        L.append("## Recall: %s (%d holdings, %d judgments)\n" % (title, len(G), len(set(g["judgment_id"] for g in G))))
        L.append("| Matched to | C12 recall (Wilson 95%) |")
        L.append("| --- | --- |")
        for sname, sset in sets:
            k = sum(1 for r in G if r["matched_types_all"] and (sset is None or set(r["matched_types_all"].split(";")) & sset))
            L.append("| %s | %s |" % (sname, pct(k, len(G))))
        k1 = sum(1 for r in G if r["c11_court_match"] == "Y")
        k2 = sum(1 for r in G if r["c11_any_match"] == "Y")
        L.append("| C11 baseline: COURT_HOLDING or COURT_REASONING candidate | %s |" % pct(k1, len(G)))
        L.append("| C11 baseline: candidate of any origin | %s |" % pct(k2, len(G)))
        for kk in (3, 5, 10):
            k = sum(1 for r in G if r["rank_among_holding_reasoning"] != "" and int(r["rank_among_holding_reasoning"]) <= kk)
            L.append("| top-%d holding/reasoning items per judgment by holding_score | %s |" % (kk, pct(k, len(G))))
        L.append("")

    # precision lower bound
    L.append("## GT-matched precision (lower bound)\n")
    L.append("Reviewers recorded at most three holdings per judgment, so an emitted holding that matches none of them is not necessarily wrong. "
             "These figures are lower bounds on precision, not precision.\n")
    L.append("| Item type | Items in dev judgments with GT holdings | Matching a GT holding |")
    L.append("| --- | --- | --- |")
    gt_j = set(g["judgment_id"] for g in gt)
    for t in ["question_of_law", "holding", "reasoning", "obiter_candidate", "operative_direction", "quoted_precedent", "submission", "lower_court_finding"]:
        P = [it for j in gt_j for it in items.get(j, []) if it["item_type"] == t]
        k = sum(1 for it in P if any(matches(g, it) for g in gt if g["judgment_id"] == it["judgment_id"]))
        L.append("| %s | %d | %s |" % (t, len(P), pct(k, len(P)) if P else "-"))
    L.append("")

    # hand-check precision (AI reviewer, same developer; see caveats)
    hc_path = os.path.join(ROOT, "outputs", "PRECISION_HANDCHECK_C12.csv")
    if os.path.exists(hc_path):
        with open(hc_path, encoding="utf-8", newline="") as f:
            HC = list(csv.DictReader(f))
        L.append("## Hand-checked precision (sampled items)\n")
        L.append("Each sampled item was read with about 300 characters of preceding context by the developing agent (an AI, not a lawyer). "
                 "CORRECT for `holding` means the bench's own voice stating a legal conclusion or a decisive ruling on an issue "
                 "(including a separate opinion's own conclusion); for `question_of_law` a question the court itself frames for decision; "
                 "for `obiter_candidate` an observation not needed for the decision. Samples are the lowest sha256 of a salt plus item_id. "
                 "The developer is not independent of the rules, so these are optimistic. Labels were made on pre-freeze builds; "
                 "`type_in_frozen_output` shows what the frozen build emits for the same item. The question-of-law exclusion rules were "
                 "written after this sample was read, so the frozen-output column for questions is in-sample and biased upward; "
                 "the first column is the honest pre-fix figure.\n")
        L.append("| Sample | Type | Labelled CORRECT | Own-voice errors | Same type in frozen output: CORRECT / all |")
        L.append("| --- | --- | --- | --- | --- |")
        groups = []
        for r in HC:
            k = (r["sample"], r["sampled_type"])
            if k not in groups:
                groups.append(k)
        for k in groups:
            G = [r for r in HC if (r["sample"], r["sampled_type"]) == k]
            ok = sum(1 for r in G if r["reviewer_label"] == "CORRECT")
            ve = sum(1 for r in G if r["own_voice_error"] == "Y")
            F = [r for r in G if r["type_in_frozen_output"] == r["sampled_type"]]
            okf = sum(1 for r in F if r["reviewer_label"] == "CORRECT")
            L.append("| %s | %s | %s | %s | %s |" % (k[0], k[1], pct(ok, len(G)), ("%d/%d" % (ve, len(G))) if k[1] == "holding" else "-",
                                                  pct(okf, len(F)) if F else "-"))
        L.append("")

    # review page-level check
    L.append("## C10 review_A/B: principal issue and answer (page level)\n")
    L.append("For each reviewed judgment with a page pinpoint, does the tool emit a holding (or question of law) on one of the pinpointed pages? "
             "Page-level only; the reviewers paraphrased rather than excerpted.\n")
    L.append("| Subset | Judgments with page pinpoints | Holding on a pinpointed page | Holding or question on a pinpointed page |")
    L.append("| --- | --- | --- | --- |")
    for name in ("all", "sc_all", "hc"):
        R = [r for r in revs if r["pages"] and subset(r, name)]
        if not R:
            continue
        k1 = sum(1 for r in R if any(it["item_type"] == "holding" and item_pages(it) & r["pages"] for it in items.get(r["judgment_id"], [])))
        k2 = sum(1 for r in R if any(it["item_type"] in ("holding", "question_of_law") and item_pages(it) & r["pages"] for it in items.get(r["judgment_id"], [])))
        L.append("| %s | %d | %s | %s |" % (name, len(R), pct(k1, len(R)), pct(k2, len(R))))
    L.append("")

    # volume
    L.append("## Volume on dev judgments\n")
    L.append("| Item type | Items | Per judgment |")
    L.append("| --- | --- | --- |")
    nj = len([j for j in ids if items.get(j)])
    for t in ["question_of_law", "holding", "reasoning", "obiter_candidate", "operative_direction", "quoted_precedent", "submission", "lower_court_finding"]:
        n = sum(1 for j in ids for it in items.get(j, []) if it["item_type"] == t)
        L.append("| %s | %d | %.1f |" % (t, n, n / float(nj or 1)))
    L.append("")
    misses = [r for r in rows_out if not (r["matched_types_all"] and set(r["matched_types_all"].split(";")) & COURT_SET)]
    L.append("## Misses from the court-voice set (%d)\n" % len(misses))
    L.append("| GT | Page | Matched as (non-court types) | Page-ignored match | Excerpt (first 140 chars) |")
    L.append("| --- | --- | --- | --- | --- |")
    for r in misses:
        L.append("| %s %s | %s | %s | %s | %s |" % (r["holdout_id"], r["judgment_id"], r["page"], r["matched_types_all"] or "-",
                                                   r["matched_any_page_ignored"], r["excerpt"][:140].replace("|", "/")))
    L.append("")
    with open(a.out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    if a.rows:
        cols = ["src", "holdout_id", "judgment_id", "court", "in_sc_scope", "pinpoint", "page", "excerpt", "issue", "matched_type",
                "matched_types_all", "matched_item_id", "matched_score", "matched_opinion", "rank_among_holding_reasoning",
                "matched_any_page_ignored", "c11_court_match", "c11_any_match"]
        with open(a.rows, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
            w.writeheader()
            for r in rows_out:
                w.writerow(r)
    print("wrote", a.out_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
