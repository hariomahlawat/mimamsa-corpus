#!/usr/bin/env python3
"""Score extractor V4 against the SPENT development sets, with the frozen V3 and V2 outputs as comparators.

IN-SAMPLE. Every judgment scored here was available to the V4 developer while the rules were written. These figures
are NOT an estimate of blind performance; the formal evaluation on the fresh holdout H-OUT-C13 is run independently.

Sets (read-only):
  C12H  C12-CONSOLIDATION/holdout_v3/GROUND_TRUTH_V3.csv (150 judgments, 215 proceeding rows; spent by the V3
        evaluation). Scored with the C12 pre-registered protocol (holdout_v3_eval/PROTOCOL.md): same key(), same
        matcher, same unscorable labels. Split by sha256(holdout_id) into TUNE (2/3) and LATE (1/3); LATE was set aside
        by the V4 developer and scored only at the end (still in-sample in the wider sense: the V3 review discussed
        some of its rows).
  DEVG  C12-CONSOLIDATION/extractor_v3/tools/dev_gold_v3.json (C10 50, C11H 56 = the spent C11 holdout, C11R 30).
        Row-level: each gold proceeding with an accepted-label list is matched to a predicted row (same key() on the
        number; a gold 'ALL' matches a single predicted row); accepted lists may hold several defensible labels.

Systems: V4 (run live), V3 (frozen OUTCOMES_V3.csv), V2 (frozen OUTCOMES_V2.csv; one outcome per judgment; its
substantive value is the default mapping, scored only for completeness).

Usage: python -I -B tools/eval_dev_v4.py [--write] [--errors tune|late|all] [--exclude-ids FILE]
"""
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract_v4  # noqa: E402
import v4core  # noqa: E402

AW = extract_v4.AUDIT
C12 = os.path.join(AW, "C12-CONSOLIDATION")
GT = os.path.join(C12, "holdout_v3", "GROUND_TRUTH_V3.csv")
SAMPLE = os.path.join(C12, "holdout_v3", "HOLDOUT_V3_SAMPLE.csv")
DEVG = os.path.join(C12, "extractor_v3", "tools", "dev_gold_v3.json")
V3 = os.path.join(C12, "extractor_v3", "outputs", "OUTCOMES_V3.csv")
V2 = os.path.join(AW, "C11-JUDICIAL-QUALITY", "extraction", "outputs", "OUTCOMES_V2.csv")
EVAL_DIR = os.path.join(extract_v4.ROOT, "dev_eval")
FIELDS = ("printed_disposal", "substantive_result")
UNSCORABLE = {"unclear", "other"}
ABSTAIN = {"", "OUTCOME_UNVERIFIED"}
FAMILY = {"allowed": "ALLOWED", "partly_allowed": "PARTLY", "dismissed": "DISMISSED", "dismissed_as_withdrawn": "DISMISSED",
          "dismissed_as_infructuous": "DISMISSED", "dismissed_in_default": "DISMISSED", "disposed_of": "DISPOSED",
          "disposed_of_with_directions": "DISPOSED", "disposed": "DISPOSED", "remanded": "REMANDED",
          "set_aside_and_remanded": "REMANDED", "transferred": "TRANSFERRED"}
DEFAULT_SUBST = v4core.DEFAULT_SUBST


def key(s):  # identical to C12 tools/holdout_v3_agreement_c12.py and eval_v3_holdout_c12.py
    m = re.findall(r"(\d{1,6})\s*(?:/|-|\s+of\s+|\s+OF\s+)\s*((?:19|20)\d\d)", s or "")
    return ";".join(sorted({f"{int(a)}-{b}" for a, b in m})) or (s or "").strip().upper()


def split_of(holdout_id):
    return "LATE" if int(hashlib.sha256(holdout_id.encode()).hexdigest(), 16) % 3 == 0 else "TUNE"


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def match(gts, preds, gkey=lambda g: key(g["proceeding"])):
    """C12 protocol matcher. Returns [(gt, pred|None)], [extra preds]."""
    if len(gts) == 1 and len(preds) == 1:
        return [(gts[0], preds[0])], []
    used, pairs = set(), []
    for g in gts:
        gk = gkey(g)
        hit = None
        if gk == "ALL" and len(preds) == 1:
            hit = 0
        else:
            for i, p in enumerate(preds):
                if i not in used and key(p["proceeding"]) == gk:
                    hit = i
                    break
        if hit is not None:
            used.add(hit)
        pairs.append((g, preds[hit] if hit is not None else None))
    return pairs, [p for i, p in enumerate(preds) if i not in used]


# ------------------------------------------------------------------ data
def load_gold(excl):
    gt = list(csv.DictReader(open(GT, encoding="utf-8")))
    sample = {r["judgment_id"]: r for r in csv.DictReader(open(SAMPLE, encoding="utf-8"))}
    items = []   # unified gold proceeding rows
    for r in gt:
        acc = {}
        for f in FIELDS:
            v = r[f]
            acc[f] = None if v in UNSCORABLE or not v else [v]
        items.append({"set": "C12H", "split": split_of(r["holdout_id"]), "ref": r["holdout_id"], "judgment_id": r["judgment_id"],
                      "court": sample[r["judgment_id"]]["court"], "stratum": sample[r["judgment_id"]]["stratum"],
                      "proceeding": r["proceeding"], "gkey": key(r["proceeding"]), "accepted": acc, "gt_raw": r})
    dg = json.load(open(DEVG, encoding="utf-8"))
    for jid, g in sorted(dg.items()):
        if jid.startswith("_"):
            continue
        for p in g.get("procs", []):
            nums = p["nums"]
            gk = "ALL" if nums == ["ALL"] else ";".join(sorted("%d-%s" % (int(n.split("/")[0]), n.split("/")[1])
                                                              for n in nums if "/" in n)) or "ALL"
            items.append({"set": "DEVG_" + g["set"], "split": "DEVG", "ref": g.get("holdout_id") or g.get("item_id") or "",
                          "judgment_id": jid, "court": "", "stratum": "", "proceeding": ",".join(nums), "gkey": gk,
                          "accepted": {"printed_disposal": p.get("printed"), "substantive_result": p.get("subst")},
                          "gt_raw": p})
    dropped = sorted({i["judgment_id"] for i in items if i["judgment_id"] in excl})
    items = [i for i in items if i["judgment_id"] not in excl]
    return items, dropped


def load_frozen(path, ids, v2=False):
    out = defaultdict(list)
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["judgment_id"] not in ids:
            continue
        if v2:
            o = r["outcome"]
            keyed = "per_proceeding_mapping" in (r.get("method") or "")
            r = {"proceeding": r["proceeding"] if keyed else "ALL", "printed_disposal": o,
                 "substantive_result": DEFAULT_SUBST.get(o, "OUTCOME_UNVERIFIED") if o in DEFAULT_SUBST else "OUTCOME_UNVERIFIED",
                 "abstain_reason": r.get("abstain_reason", ""), "excerpt": r.get("excerpt", ""), "page": r.get("page", ""),
                 "char_start": r.get("char_start", ""), "char_end": r.get("char_end", ""), "text_source": r.get("text_source", ""),
                 "judgment_id": r["judgment_id"]}
        out[r["judgment_id"]].append(r)
    return out


def run_v4(ids):
    J, _ = extract_v4.load_inputs()
    store = extract_v4.TextStore()
    out = {}
    for j in sorted(ids):
        out[j] = extract_v4.process_one(J[j], store) if j in J else [extract_v4._blank(j, "UNKNOWN_JUDGMENT_ID")]
    store.close()
    return out


# ------------------------------------------------------------------ scoring
def score_items(items, preds):
    """Per gold row and field: (category, predicted label). Returns list of result dicts and extras."""
    byj = defaultdict(list)
    for it in items:
        byj[it["judgment_id"]].append(it)
    res, extras = [], []
    for j, its in byj.items():
        pairs, ex = match(its, preds.get(j, []), gkey=lambda g: g["gkey"])
        extras += [(j, p) for p in ex]
        for it, p in pairs:
            r = {"it": it, "pred": p}
            for f in FIELDS:
                acc = it["accepted"][f]
                v = p[f] if p else ""
                if not acc:
                    cat = None
                elif p is None:
                    cat = "PROCEEDING_UNMATCHED"
                elif v in ABSTAIN:
                    cat = "ABSTAINED"
                elif v in acc:
                    cat = "CORRECT"
                else:
                    cat = "WRONG_LABEL_SAME_FAMILY" if any(FAMILY.get(v, v) == FAMILY.get(a, a) for a in acc) else "WRONG_FAMILY"
                r[f] = (cat, v)
            res.append(r)
    return res, extras


def summarize(res, field, pred_filter=lambda r: True):
    rr = [r for r in res if r[field][0] is not None and pred_filter(r)]
    ans = [r for r in rr if r[field][0] in ("CORRECT", "WRONG_LABEL_SAME_FAMILY", "WRONG_FAMILY")]
    ok = [r for r in ans if r[field][0] == "CORRECT"]
    fam_ok = [r for r in ans if r[field][0] in ("CORRECT", "WRONG_LABEL_SAME_FAMILY")]
    return {"scorable": len(rr), "answered": len(ans), "correct": len(ok), "family_correct": len(fam_ok),
            "precision": round(len(ok) / len(ans), 4) if ans else None, "precision_wilson95": wilson(len(ok), len(ans)),
            "coverage": round(len(ans) / len(rr), 4) if rr else None, "coverage_wilson95": wilson(len(ans), len(rr)),
            "categories": dict(Counter(r[field][0] for r in rr if r[field][0] != "CORRECT"))}


GROUPS = [("C12H all", lambda it: it["set"] == "C12H"), ("C12H TUNE", lambda it: it["split"] == "TUNE"),
          ("C12H LATE", lambda it: it["split"] == "LATE"), ("DEVG all", lambda it: it["set"].startswith("DEVG")),
          ("DEVG C10", lambda it: it["set"] == "DEVG_C10"), ("DEVG C11H", lambda it: it["set"] == "DEVG_C11H"),
          ("DEVG C11R", lambda it: it["set"] == "DEVG_C11R"), ("ALL spent sets", lambda it: True)]


def anchor_ok(p):
    """Excerpt found at the cited offsets of the cited blob, and page equal to the preceding page marker."""
    t = v3_blob(p.get("text_source"))
    ex = " ".join((p.get("excerpt") or "").split()).rstrip(".").rstrip()
    if t is None or not ex:
        return False, False
    try:
        a, b = int(p["char_start"]), int(p["char_end"])
    except (ValueError, KeyError, TypeError):
        return False, False
    span = " ".join(t[max(0, a - 10):b + 10].split())
    at = ex.replace("...", "") in span or ex[:200] in span
    pages = re.findall(r"\[\[page (\d+)\]\]", t[:a + 1])
    return at, bool(pages) and pages[-1] == str(p.get("page") or "").strip()


_blobs = {}


def v3_blob(ts):
    m = re.search(r"@blob:([0-9a-f]{40})", ts or "")
    if not m:
        return None
    b = m.group(1)
    if b not in _blobs:
        import subprocess
        r = subprocess.run(["git", "-C", extract_v4.DEF_REPO, "cat-file", "-p", b], capture_output=True)
        _blobs[b] = r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None
    return _blobs[b]


def main(argv):
    excl = set(extract_v4.read_ids(argv[argv.index("--exclude-ids") + 1])) if "--exclude-ids" in argv else set()
    items, dropped = load_gold(excl)
    ids = {i["judgment_id"] for i in items}
    systems = {"V4": run_v4(ids), "V3": load_frozen(V3, ids), "V2": load_frozen(V2, ids, v2=True)}
    show = argv[argv.index("--errors") + 1] if "--errors" in argv else ""
    summary = {"IN_SAMPLE": True, "extractor": v4core.VERSION, "tool_sha256": extract_v4.tool_hashes(),
               "n_gold_rows": len(items), "n_judgments": len(ids), "excluded_dev_judgments": dropped, "systems": {}}
    allres = {}
    for name, preds in systems.items():
        res, extras = score_items(items, preds)
        allres[name] = res
        s = {"extra_predicted_rows": len(extras)}
        for g, fn in GROUPS:
            s[g] = {f: summarize(res, f, lambda r, fn=fn: fn(r["it"])) for f in FIELDS}
        summary["systems"][name] = s
    # anchors (V4 answered rows on the gold judgments)
    n = at = pg = 0
    for j, rows in systems["V4"].items():
        for p in rows:
            if p["printed_disposal"] in ABSTAIN and p["substantive_result"] in ABSTAIN:
                continue
            n += 1
            a, b = anchor_ok(p)
            at += a
            pg += b
    summary["V4_anchors"] = {"answered_rows": n, "excerpt_at_offset": at, "page_consistent": pg}
    # C12 protocol self-check: the frozen V3 numbers must reproduce
    c3 = summary["systems"]["V3"]["C12H all"]
    summary["protocol_reproduces_V3_C12_result"] = (c3["printed_disposal"]["correct"], c3["printed_disposal"]["answered"],
                                                     c3["printed_disposal"]["scorable"]) == (126, 138, 213) and \
        (c3["substantive_result"]["correct"], c3["substantive_result"]["answered"], c3["substantive_result"]["scorable"]) == (108, 113, 207)
    print(table(summary))
    if show:
        for r4, r3 in zip(allres["V4"], allres["V3"]):
            it = r4["it"]
            if show != "all" and it["split"] != show.upper():
                continue
            c = [r4[f][0] for f in FIELDS]
            if all(x in (None, "CORRECT") for x in c):
                continue
            p = r4["pred"] or {}
            print("%-5s %-6s %s %s | gold %s/%s | v4 %s/%s | v3 %s/%s | %s | %s" % (
                it["split"], it["ref"], it["judgment_id"], it["proceeding"][:40],
                (it["accepted"]["printed_disposal"] or ["-"])[0], (it["accepted"]["substantive_result"] or ["-"])[0],
                r4["printed_disposal"][1], r4["substantive_result"][1], r3["printed_disposal"][1], r3["substantive_result"][1],
                (p.get("abstain_reason") or "")[:70], (p.get("excerpt") or "")[:160]))
    if "--write" in argv:
        os.makedirs(EVAL_DIR, exist_ok=True)
        extract_v4.write_atomic(os.path.join(EVAL_DIR, "DEV_EVALUATION_V4_SUMMARY.json"),
                                (json.dumps(summary, indent=1, sort_keys=True) + "\n").encode())
        cols = ["set", "split", "ref", "judgment_id", "court", "stratum", "gold_proceeding", "gold_printed", "gold_substantive"]
        for nme in systems:
            cols += [nme + "_proceeding", nme + "_printed", nme + "_substantive", nme + "_cat_printed", nme + "_cat_substantive"]
        cols += ["V4_abstain_reason", "V4_confidence", "V4_page", "V4_char_start", "V4_char_end", "V4_excerpt"]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for k in range(len(items)):
            it = allres["V4"][k]["it"]
            row = {"set": it["set"], "split": it["split"], "ref": it["ref"], "judgment_id": it["judgment_id"], "court": it["court"],
                   "stratum": it["stratum"], "gold_proceeding": it["proceeding"],
                   "gold_printed": "|".join(it["accepted"]["printed_disposal"] or []),
                   "gold_substantive": "|".join(it["accepted"]["substantive_result"] or [])}
            for nme in systems:
                r = allres[nme][k]
                assert r["it"] is it
                p = r["pred"] or {}
                row.update({nme + "_proceeding": p.get("proceeding", ""), nme + "_printed": r["printed_disposal"][1],
                            nme + "_substantive": r["substantive_result"][1], nme + "_cat_printed": r["printed_disposal"][0] or "",
                            nme + "_cat_substantive": r["substantive_result"][0] or ""})
            p = allres["V4"][k]["pred"] or {}
            row.update({"V4_abstain_reason": p.get("abstain_reason", ""), "V4_confidence": p.get("confidence", ""),
                        "V4_page": p.get("page", ""), "V4_char_start": p.get("char_start", ""),
                        "V4_char_end": p.get("char_end", ""), "V4_excerpt": (p.get("excerpt") or "")[:300]})
            w.writerow(row)
        extract_v4.write_atomic(os.path.join(EVAL_DIR, "DEV_EVALUATION_V4_ROWS.csv"), buf.getvalue().encode())
        extract_v4.write_atomic(os.path.join(EVAL_DIR, "DEV_EVALUATION_V4_TABLE.md"), table(summary).encode())


def table(s):
    out = ["IN-SAMPLE development evaluation (spent sets only). Not a blind estimate.", "",
           "| Set | Field | V4 precision | V4 coverage | V3 precision | V3 coverage | V2 precision | V2 coverage |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for g, _ in GROUPS:
        for f in FIELDS:
            cells = []
            for nme in ("V4", "V3", "V2"):
                x = s["systems"][nme][g][f]
                cells += ["%d/%d = %s" % (x["correct"], x["answered"], "%.1f%%" % (100 * x["precision"]) if x["precision"] is not None else "n/a"),
                          "%d/%d = %s" % (x["answered"], x["scorable"], "%.1f%%" % (100 * x["coverage"]) if x["coverage"] is not None else "n/a")]
            out.append("| %s | %s | %s |" % (g, f, " | ".join(cells)))
    out.append("")
    out.append("Protocol reproduces frozen V3 C12 holdout result (126/138, 108/113): %s" % s["protocol_reproduces_V3_C12_result"])
    out.append("V4 anchors: %s" % json.dumps(s["V4_anchors"]))
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main(sys.argv[1:])
