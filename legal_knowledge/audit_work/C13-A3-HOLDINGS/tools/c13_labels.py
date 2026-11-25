"""Spent label sources for C13-A3 training and in-sample development evaluation.

Only already-spent sets are read (all were seen in earlier cycles):
  - C12 holdings reference (30 judgments): REFERENCE_HOLDINGS.csv (question_of_law / holding / reasoning rows);
  - C12 blind-evaluation adjudication sample (86 labelled C12 predictions on those 30 judgments);
  - C12 dev hand-check (PRECISION_HANDCHECK_C12.csv, 115 labelled C12 predictions);
  - C11 holdout ground truth A/B (up to 3 holdings + the operative excerpt per judgment).
C10 review_A/B principal issue and answer are paraphrases without verbatim excerpts; they are used only for the
pinpoint-page check in the dev evaluation, not for training.
The fresh C13 reference (A0, H-HOLD-C13) is never read; its id list is only ever used to exclude judgments.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.normpath(os.path.join(HERE, "..", ".."))
C12 = os.path.join(AUDIT, "C12-CONSOLIDATION")
C11 = os.path.join(AUDIT, "C11-JUDICIAL-QUALITY")
C10 = os.path.join(AUDIT, "C10-HF-JUDGMENTS")
EVAL_TOOLS = os.path.join(C12, "holdings_eval", "tools")
if EVAL_TOOLS not in sys.path:
    sys.path.insert(0, EVAL_TOOLS)
import eval_holdings_c12 as ev  # noqa: E402  (pre-registered C12 matcher, reused read-only)

FILES = {
    "c12_reference": os.path.join(C12, "holdings_reference", "REFERENCE_HOLDINGS.csv"),
    "c12_selection": os.path.join(C12, "holdings_reference", "SELECTION.csv"),
    "c12_adjudication": os.path.join(C12, "holdings_eval", "ADJUDICATION_SAMPLE.csv"),
    "c12_handcheck": os.path.join(C12, "holdings", "outputs", "PRECISION_HANDCHECK_C12.csv"),
    "c11_gt_a": os.path.join(C11, "holdout", "ground_truth_A.csv"),
    "c11_gt_b": os.path.join(C11, "holdout", "ground_truth_B.csv"),
    "c10_review_a": os.path.join(C10, "review", "review_A.csv"),
    "c10_review_b": os.path.join(C10, "review", "review_B.csv"),
}

content = ev.content


def _csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _page(s):
    s = (s or "").strip()
    if s.isdigit():
        return int(s)
    m = re.search(r"(?:pdf\s*)?\bp(?:age)?\.?\s*(\d{1,4})", s, re.I) or re.match(r"(\d{1,4})", s)
    return int(m.group(1)) if m else None


def load_labels():
    """Return a list of label rows: {src, judgment_id, page, excerpt, kind, polarity, weight}.
    kind in {holding, question_of_law, reasoning, operative}; polarity +1 (is that kind) or -1 (is not)."""
    rows = []
    for r in _csv(FILES["c12_reference"]):
        rows.append({"src": "c12_reference", "judgment_id": r["judgment_id"], "page": _page(r["page"]), "excerpt": r["excerpt"],
                     "kind": r["item_type"], "polarity": 1, "opinion": r.get("opinion", "")})
    for r in _csv(FILES["c12_adjudication"]):
        lab = r["label"]
        if r["item_type"] == "holding":
            rows.append({"src": "c12_adjudication", "judgment_id": r["judgment_id"], "page": _page(r["page"]), "excerpt": r["excerpt_clean"],
                         "kind": "holding", "polarity": 1 if lab == "CORRECT_HOLDING" else -1, "detail": lab + ":" + r.get("subtype", "")})
        elif r["item_type"] == "question_of_law":
            rows.append({"src": "c12_adjudication", "judgment_id": r["judgment_id"], "page": _page(r["page"]), "excerpt": r["excerpt_clean"],
                         "kind": "question_of_law", "polarity": 1 if lab == "CORRECT_QOL" else -1, "detail": lab})
    for r in _csv(FILES["c12_handcheck"]):
        if r["sampled_type"] not in ("holding", "question_of_law"):
            continue
        rows.append({"src": "c12_handcheck", "judgment_id": r["judgment_id"], "page": _page(r["page"]), "excerpt": r["excerpt"],
                     "kind": r["sampled_type"], "polarity": 1 if r["reviewer_label"] == "CORRECT" else -1, "detail": r["reviewer_label"]})
    seen = set()
    for key in ("c11_gt_a", "c11_gt_b"):
        for r in _csv(FILES[key]):
            for n in (1, 2, 3):
                ex = (r.get("holding_%d_excerpt" % n) or "").strip()
                if not ex or ex.upper() in ("NONE", "N/A", "NA", "-"):
                    continue
                k = (r["judgment_id"], " ".join(sorted(content(ex))))
                if k in seen:
                    continue
                seen.add(k)
                rows.append({"src": "c11_gt", "judgment_id": r["judgment_id"], "page": _page(r.get("holding_%d_pinpoint" % n, "")),
                             "excerpt": ex, "kind": "holding", "polarity": 1})
            ex = (r.get("outcome_excerpt") or "").strip()
            if ex and ex.upper() not in ("NONE", "N/A"):
                k = (r["judgment_id"], "OUT", " ".join(sorted(content(ex))))
                if k not in seen:
                    seen.add(k)
                    rows.append({"src": "c11_gt", "judgment_id": r["judgment_id"], "page": _page(r.get("outcome_page", "")),
                                 "excerpt": ex, "kind": "operative", "polarity": 1})
    for r in rows:
        r["_c"] = content(r["excerpt"])
    return rows


def judgment_ids(rows):
    out = []
    for r in rows:
        if r["judgment_id"] not in out:
            out.append(r["judgment_id"])
    return out


def c12_reference_ids():
    return [r["judgment_id"] for r in _csv(FILES["c12_selection"])]


def c11_gt_ids():
    ids = []
    for key in ("c11_gt_a", "c11_gt_b"):
        for r in _csv(FILES[key]):
            if r["judgment_id"] not in ids:
                ids.append(r["judgment_id"])
    return ids


def sentence_matches(c_sent, page_lo, page_hi, lab, thr=0.60, pd=1):
    """C12 pre-registered primary matcher applied to a sentence span and a label row."""
    if lab["page"] is not None and page_lo is not None:
        if not (page_lo - pd <= lab["page"] <= page_hi + pd):
            return False
    a, b = c_sent, lab["_c"]
    if not a or not b:
        return False
    inter = len(a & b)
    return inter >= 3 and inter / min(len(a), len(b)) >= thr
