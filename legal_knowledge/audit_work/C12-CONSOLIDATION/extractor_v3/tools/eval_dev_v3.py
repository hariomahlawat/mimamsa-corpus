#!/usr/bin/env python3
"""Score extractor v3 and the frozen v2 comparator on the DEVELOPMENT gold (tools/dev_gold_v3.json).

IN-SAMPLE: every judgment here was available to the v3 developer while the rules were written.

Unit: the judgment, per field (printed_disposal, substantive_result).
  - ABSTAIN: every row has the field OUTCOME_UNVERIFIED.
  - CORRECT: every non-abstained row maps to gold proceeding(s) and carries an accepted label for each of them.
  - WRONG: any non-abstained row carries a label not accepted for a proceeding it maps to, or (strict) names a
    proceeding that is not in the gold.
  - NOT_SCORABLE: the gold has no value for the field.
Precision = CORRECT / (CORRECT + WRONG); coverage = (CORRECT + WRONG) / scorable judgments.
Proceeding completeness = gold proceedings covered by a non-abstained row / gold proceedings (over predicted judgments).
v2 has a single outcome label: it is scored as printed_disposal as-is, and as substantive_result through the default
mapping (allowed -> relief_granted, ...; disposed_of_with_directions -> no substantive value, i.e. abstain).

Usage: python -I -B tools/eval_dev_v3.py [--write] [-v]
"""
import csv
import importlib.util
import io
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract_v3  # noqa: E402
import v3core  # noqa: E402

V2DIR = os.path.join(extract_v3.AUDIT, "C11-JUDICIAL-QUALITY", "extraction", "tools")
U = v3core.UNVERIFIED


def load_v2():
    """Import the frozen v2 comparator read-only (no bytecode written into its folder)."""
    if not os.path.exists(os.path.join(V2DIR, "v2core.py")):
        return None
    sys.path.insert(0, V2DIR)
    spec = importlib.util.spec_from_file_location("extract_v2_frozen", os.path.join(V2DIR, "extract_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.path.remove(V2DIR)
    return mod


def v2_rows(v2, info, store):
    rows, _ = v2.process_one(info, store)
    out = []
    for r in rows:
        o = r["outcome"]
        keyed = "per_proceeding_mapping" in (r.get("method") or "")
        out.append({"proceeding": r["proceeding"] if keyed else "ALL", "printed_disposal": o,
                    "substantive_result": v3core.DEFAULT_SUBST.get(o, U), "excerpt": r.get("excerpt", ""),
                    "party_specific": "", "page": r.get("page", ""), "abstain_reason": r.get("abstain_reason", ""),
                    "method": r.get("method", "")})
    return out


def row_nums(label):
    if label in ("ALL", "UNIDENTIFIED", ""):
        return None
    out = set()
    for c in v3core.find_case_numbers(label):
        for n in c["nums"]:
            out.add((n, c["year"]))
    return out or None


def matches(row, procs):
    if len(procs) == 1 and procs[0]["nums"] == ["ALL"]:
        return [0], False
    R = row_nums(row["proceeding"])
    if R is None:
        return list(range(len(procs))), False
    hit = []
    hay = (row["proceeding"] + " " + row.get("party_specific", "") + " " + row.get("excerpt", "")).lower()
    for i, p in enumerate(procs):
        ok = False
        for k in p["nums"]:
            if k == "ALL":
                ok = True
            elif k.startswith("#"):
                ok = ok or any(n == int(k[1:]) for n, _ in R)
            else:
                n, y = k.split("/")
                ok = ok or (int(n), int(y)) in R
        if not ok and p.get("party_rx"):
            ok = bool(re.search(p["party_rx"], hay))
        if ok:
            hit.append(i)
    if not hit and len(procs) == 1:
        return [0], True
    return hit, False


GF = {"printed_disposal": "printed", "substantive_result": "subst"}


def score_field(g, rows, field):
    procs = g.get("procs", [])
    gf = GF[field]
    nonab = [r for r in rows if r[field] != U]
    if g.get("expect_abstain"):
        return ("CORRECT_ABSTAIN" if not nonab else "WRONG"), 0, 0, []
    scorable = [i for i, p in enumerate(procs) if p.get(gf)]
    if not scorable:
        return "NOT_SCORABLE", 0, 0, []
    if not nonab:
        return "ABSTAIN", 0, len(scorable), []
    wrong, covered, used, notes = False, set(), False, []
    for r in nonab:
        hit, label_guess = matches(r, procs)
        if not hit:
            wrong = True
            notes.append("EXTRA_PROCEEDING:%s=%s" % (r["proceeding"], r[field]))
            continue
        for i in hit:
            if not procs[i].get(gf):
                continue
            used = True
            if r[field] in procs[i][gf]:
                covered.add(i)
            else:
                wrong = True
                notes.append("%s=%s (gold %s)" % (r["proceeding"][:40], r[field], "|".join(procs[i][gf])))
        if label_guess:
            notes.append("LABEL_NOT_VERIFIABLE")
    if not used and not wrong:
        return "NOT_SCORABLE", 0, 0, notes
    return ("WRONG" if wrong else "CORRECT"), len(covered & set(scorable)), len(scorable), notes


def summarize(res, key, subset=None):
    rr = [r for r in res if subset is None or r["set"] in subset]
    out = {}
    for field in ("printed", "subst", "pair"):
        v = [r[key + "_" + field] for r in rr]
        c = v.count("CORRECT") + v.count("CORRECT_ABSTAIN")
        w = v.count("WRONG")
        a = v.count("ABSTAIN")
        ns = v.count("NOT_SCORABLE")
        cov_num = sum(r[key + "_" + field + "_cov"][0] for r in rr if r[key + "_" + field] in ("CORRECT", "WRONG"))
        cov_den = sum(r[key + "_" + field + "_cov"][1] for r in rr if r[key + "_" + field] in ("CORRECT", "WRONG"))
        out[field] = {"n_scorable": c + w + a, "correct": c, "wrong": w, "abstain": a, "not_scorable": ns,
                      "precision": round(c / (c + w), 4) if c + w else None,
                      "coverage": round((c + w) / (c + w + a), 4) if c + w + a else None,
                      "proceeding_completeness": round(cov_num / cov_den, 4) if cov_den else None}
    return out


def pair(pv, sv):
    if "WRONG" in (pv[0], sv[0]):
        return ("WRONG", 0, 0)
    if pv[0] == "CORRECT_ABSTAIN":
        return ("CORRECT_ABSTAIN", 0, 0)
    if "CORRECT" in (pv[0], sv[0]):
        best = pv if pv[0] == "CORRECT" else sv
        return ("CORRECT", best[1], best[2])
    if "ABSTAIN" in (pv[0], sv[0]):
        return ("ABSTAIN", 0, 0)
    return ("NOT_SCORABLE", 0, 0)


def batch_copy_check(J, store, gold):
    """Every stored copy of a batch judgment in the gold: is the copy's OWN_CASE row right for its own petition?"""
    reg = os.path.join(extract_v3.AUDIT, "C11-JUDICIAL-QUALITY", "identity", "outputs", "JUDGMENT_IDENTITY_REGISTER.csv")
    with open(reg, encoding="utf-8") as f:
        R = list(csv.DictReader(f))
    by_text = {}
    for r in R:
        by_text.setdefault(r["text_sha256"], []).append(r["judgment_id_c10"])
    jid_text = {r["judgment_id_c10"]: r["text_sha256"] for r in R}
    out = []
    for jid, g in gold.items():
        if jid.startswith("_") or len(g.get("procs", [])) < 2 or jid not in jid_text:
            continue
        copies = [c for c in by_text.get(jid_text[jid], []) if c in J]
        if len(copies) < 2:
            continue
        procs = g["procs"]
        for c in sorted(copies):
            rows = extract_v3.process_one(J[c], store)
            own = [r for r in rows if r["file_case_role"] == "OWN_CASE"]
            for r in own:
                hit, _ = matches(r, procs)
                p = procs[hit[0]] if len(hit) == 1 else None
                gp = p.get("printed") if p else None
                verdict = ("ABSTAIN" if r["printed_disposal"] == U else "NOT_SCORABLE" if not gp else
                           "CORRECT" if r["printed_disposal"] in gp else "WRONG")
                out.append({"gold_judgment": jid, "copy": c, "own_case": r["proceeding"], "printed": r["printed_disposal"],
                            "subst": r["substantive_result"], "gold_printed": "|".join(gp or []), "verdict": verdict})
    return out


def main():
    gold = json.load(open(os.path.join(HERE, "dev_gold_v3.json"), encoding="utf-8"))
    J, order = extract_v3.load_inputs()
    store = extract_v3.TextStore()
    v2 = load_v2()
    res = []
    for jid in sorted(k for k in gold if not k.startswith("_")):
        g = gold[jid]
        if jid not in J:
            continue
        rows3 = extract_v3.process_one(J[jid], store)
        rows2 = v2_rows(v2, J[jid], store) if v2 else []
        rec = {"judgment_id": jid, "set": g["set"], "ref": g.get("holdout_id") or g.get("item_id") or "",
               "court": J[jid]["court"], "gold": json.dumps([[p["nums"], p.get("printed"), p.get("subst")] for p in g.get("procs", [])])[:600]}
        for key, rows in (("v3", rows3), ("v2", rows2)):
            pv = score_field(g, rows, "printed_disposal")
            sv = score_field(g, rows, "substantive_result")
            rec[key + "_printed"], rec[key + "_printed_cov"] = pv[0], (pv[1], pv[2])
            rec[key + "_subst"], rec[key + "_subst_cov"] = sv[0], (sv[1], sv[2])
            pp = pair(pv, sv)
            rec[key + "_pair"], rec[key + "_pair_cov"] = pp[0], (pp[1], pp[2])
            rec[key + "_notes"] = "; ".join(pv[3] + ["S:" + x for x in sv[3]])[:400]
            rec[key + "_rows"] = " || ".join("%s=%s/%s%s" % (r["proceeding"][:40], r["printed_disposal"], r["substantive_result"],
                                                           (" [" + r["abstain_reason"][:60] + "]") if r["abstain_reason"] else "")
                                             for r in rows)[:900]
        rec["v3_excerpt"] = (rows3[-1]["excerpt"] if rows3 else "")[:300]
        rec["v3_page"] = rows3[-1]["page"] if rows3 else ""
        res.append(rec)
    copies = batch_copy_check(J, store, gold)
    store.close()
    summ = {"extractor": v3core.VERSION, "IN_SAMPLE": True, "n": len(res)}
    for key in ("v3", "v2"):
        summ[key] = {"all": summarize(res, key)}
        for s in ("C10", "C11H", "C11R"):
            summ[key][s] = summarize(res, key, {s})
    cv = [c["verdict"] for c in copies]
    summ["batch_copies_own_case"] = {"rows": len(copies), "correct": cv.count("CORRECT"), "wrong": cv.count("WRONG"),
                                     "abstain": cv.count("ABSTAIN"), "not_scorable": cv.count("NOT_SCORABLE")}
    print(json.dumps(summ, indent=1))
    if "-v" in sys.argv:
        for r in res:
            print(r["v3_printed"], r["v3_subst"], "| v2", r["v2_printed"], r["judgment_id"], r["set"], r["ref"], r["court"][:14])
            print("    V3:", r["v3_rows"][:400])
            print("    V2:", r["v2_rows"][:200])
            if r["v3_notes"]:
                print("    NOTES:", r["v3_notes"][:300])
    if "--write" in sys.argv:
        cols = [k for k in res[0].keys() if not k.endswith("_cov")] + [k for k in res[0].keys() if k.endswith("_cov")]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in res:
            w.writerow({k: (json.dumps(v) if isinstance(v, tuple) else v) for k, v in r.items()})
        extract_v3.write_atomic(os.path.join(extract_v3.OUT, "DEV_EVALUATION_V3_ROWS.csv"), buf.getvalue().encode("utf-8"))
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(copies[0].keys()) if copies else ["none"], lineterminator="\n")
        w.writeheader()
        w.writerows(copies)
        extract_v3.write_atomic(os.path.join(extract_v3.OUT, "DEV_BATCH_COPIES_V3.csv"), buf.getvalue().encode("utf-8"))
        extract_v3.write_atomic(os.path.join(extract_v3.OUT, "DEV_EVALUATION_V3_SUMMARY.json"),
                                (json.dumps(summ, indent=1, sort_keys=True) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
