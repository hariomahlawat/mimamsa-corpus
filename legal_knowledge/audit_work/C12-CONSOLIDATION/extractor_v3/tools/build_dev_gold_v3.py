#!/usr/bin/env python3
"""Build tools/dev_gold_v3.json: the DEVELOPMENT gold for extractor v3 (two-field outcome per proceeding).

All of this data was available to (and used by) the v3 developer, so every score computed on it is IN-SAMPLE.
Sources (read-only):
  C10  C10-HF-JUDGMENTS/review/review_A.csv, review_B.csv, WS_REVIEW_SAMPLE20_3257ebb9.csv, as already mapped to
       outcome labels in C11-JUDICIAL-QUALITY/extraction/tools/dev_gold.json (50 judgments)
  C11H the spent C11 holdout: C11-JUDICIAL-QUALITY/holdout/ground_truth_A.csv, ground_truth_B.csv (56 judgments)
  C11R C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_items.csv, section 4 (30 judgments whose printed
       disposition the C11 reviewer confirmed against the text)

Each judgment maps to a list of proceedings: {"nums": ["1319/2024", ...] or ["ALL"], "printed": [accepted labels]
or null (not scored), "subst": [accepted labels] or null (not scored)}.
The C11 ground truth has ONE outcome per proceeding, coded on substance by reviewer A and on printed words by
reviewer B. The split into printed_disposal and substantive_result below is this workstream's reading of the
reviewers' excerpts and notes (documented per row in "basis"); where a reading is ambiguous every defensible label
is accepted, and where the field is undeterminable from the reviewers' material it is null (not scored).
"""
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
C10G = os.path.join(AUDIT, "C11-JUDICIAL-QUALITY", "extraction", "tools", "dev_gold.json")
C11 = os.path.join(AUDIT, "C11-JUDICIAL-QUALITY")

DEFAULT_SUBST = {"allowed": "relief_granted", "partly_allowed": "relief_partly_granted", "dismissed": "relief_refused",
                 "dismissed_as_withdrawn": "no_adjudication", "dismissed_as_infructuous": "no_adjudication",
                 "dismissed_in_default": "no_adjudication", "transferred": "no_adjudication",
                 "remanded": "remanded_for_fresh_decision", "set_aside_and_remanded": "remanded_for_fresh_decision",
                 "not_final": "interim_only"}

# ---------------------------------------------------------------- C10 (50): substantive readings where the default
# mapping does not apply. Values: accepted subst labels (None = not scored).
C10_SUBST = {
    "J-1de6c12b474985bf": None,            # disposed of with directions (PC for women officers): substance mixed
    "J-937ee98804344d1e": ["relief_granted", "relief_partly_granted"],  # 'allow the petitions in terms of directions'
    "J-dc60fe0001b07e43": ["relief_granted"],  # impugned AFT order quashed; OA infructuous; liberty
    "J-b4fd0cb4c3c6d2d5": None,
    "J-0b97fbf0f2969f37": None,
    "J-256fcb675dc11dfb": None,
    "J-76a1a41c4624e842": None,
    "J-72a623bb18bbef79": ["relief_granted", "remanded_for_fresh_decision"],  # allowed; penalty remitted
    "J-b159ba1791fd48a2": ["relief_partly_granted"],
}
C10_PRINTED_EXTRA = {
    # reviewer readings that the C11 gold collapsed; the literal printed form is accepted as well
    "J-dc60fe0001b07e43": ["allowed", "disposed_of_with_directions", "disposed_of"],
    "J-0b97fbf0f2969f37": ["disposed_of_with_directions", "disposed_of"],
    "J-256fcb675dc11dfb": ["disposed_of_with_directions", "disposed_of"],
    "J-76a1a41c4624e842": ["disposed_of_with_directions", "disposed_of"],
    "J-b4fd0cb4c3c6d2d5": ["disposed_of_with_directions", "disposed_of"],
    "J-1de6c12b474985bf": ["disposed_of_with_directions", "disposed_of"],
}

# ---------------------------------------------------------------- C11 holdout: printed/substantive split.
# key: holdout id -> {proceeding-number-or-ALL: (printed accepted | None, subst accepted | None, basis)}
# '*' applies to every proceeding of that holdout id not listed explicitly.
P = {
    "H001": {"*": (["allowed"], ["relief_granted", "relief_partly_granted"], "allow the appeal and modify the AFT order")},
    "H003": {"*": (["dismissed"], ["relief_refused", "relief_partly_granted"], "dismissed on the aforesaid terms; SJ order modified")},
    "H006": {"*": (["dismissed"], ["relief_refused"], "will stand dismissed subject to directions")},
    "H007": {"*": (["allowed"], ["relief_granted"], "no 'allowed' printed; Tribunal order set aside")},
    "H008": {"*": (["allowed"], ["relief_granted", "relief_partly_granted"], "both appeals allowed in terms; net effect mixed")},
    "H010": {"127/2003": (["set_aside_and_remanded", "partly_allowed", "allowed", "disposed_of"],
                          ["remanded_for_fresh_decision", "relief_partly_granted"], "allowed to that extent; HC to reconsider sentence"),
             "606/2003": (["allowed", "partly_allowed", "disposed_of"], ["relief_granted", "relief_partly_granted"], "allowed to that extent"),
             "128/2003": (["dismissed", "disposed_of"], ["relief_refused"], "'sans merit'; para 16 appeals disposed of")},
    "H012": {"16441/2017": (["not_final"], ["interim_only"], "List the SLP separately"),
             "*": (["partly_allowed"], ["relief_partly_granted"], "allow the present appeals to the above limited extent")},
    "H015": {"*": (["disposed_of_with_directions", "disposed_of"], None, "dispose of the appeals; directions")},
    "H018": {"*": (["partly_allowed"], ["relief_partly_granted"], "writ petitions are partly allowed")},
    "H019": {"*": (["disposed_of_with_directions", "disposed_of"], ["relief_refused"], "disposed of in terms of this judgment; challenges rejected")},
    "H021": {"*": (["disposed_of_with_directions", "disposed_of"], ["relief_granted"], "disposed of in above terms; dismissal set aside, reinstatement")},
    "H024": {"*": (None, ["relief_granted"], "no formal disposal words; AFT order set aside")},
    "H026": {"*": (["disposed_of", "disposed_of_with_directions", "dismissed_as_withdrawn"], ["no_adjudication"], "leave to withdraw granted; disposed of")},
    "H027": {"*": (["disposed_of_with_directions", "disposed_of"], ["remanded_for_fresh_decision"], "dispose of; impugned order set aside; remanded")},
    "H028": {"*": (["disposed_of_with_directions", "disposed_of"], ["relief_refused"], "disposed of with directions; relief refused in substance")},
    "H034": {"*": (["disposed_of_with_directions", "disposed_of"], ["relief_granted"], "disposed of in terms of earlier judgment; same relief")},
    "H036": {"*": (["disposed_of_with_directions", "disposed_of"], None, "disposed of in the above terms; none appeared")},
    "H048": {"*": (["allowed"], ["remanded_for_fresh_decision"], "remanded back for fresh order; writ petition allowed")},
    "H049": {"*": (["disposed_of"], ["no_adjudication"], "consigned to records; left to avail remedy")},
    "H055": {"*": (["transferred"], ["no_adjudication"], "transmitted to the AFT")},
}
H042 = {  # per-petition exceptions in the J&K batch; others: dismissed / relief_refused
    "1007/2024": (["allowed"], ["relief_granted", "remanded_for_fresh_decision"], "allow; AFT judgment set aside; review medical board"),
    "1319/2024": (["allowed"], ["relief_granted", "remanded_for_fresh_decision"], "allowed; set aside; review medical board"),
    "1708/2024": (["allowed"], ["relief_granted", "remanded_for_fresh_decision"], "allow; set aside; review medical board"),
    "1653/2024": (["partly_allowed"], ["relief_partly_granted"], "partly allowed"),
    "2301/2024": (None, ["relief_granted", "remanded_for_fresh_decision"], "no disposal word printed; AFT order set aside; RMB"),
}


def numkey(s):
    """'Civil Appeal No. 20858 of 2017' -> ['20858/2017']; ranges are not expected in GT proceeding cells."""
    s = s.replace("–", "-")
    m = re.search(r"(\d{1,6})\s*(?:of|/|-)\s*((?:19|20)\d{2})\b", s)
    if m:
        return ["%d/%s" % (int(m.group(1)), m.group(2))]
    return ["ALL"]


def build():
    gold = {"_source": __doc__.strip().splitlines()[0], "_note": "IN-SAMPLE development gold; see build_dev_gold_v3.py"}
    c10 = json.load(open(C10G, encoding="utf-8"))
    for jid, g in c10.items():
        if jid.startswith("_"):
            continue
        if g.get("expect_abstain"):
            gold[jid] = {"set": "C10", "expect_abstain": True, "procs": [], "note": g.get("note", "")}
            continue
        procs = []
        if g.get("mixed"):
            for rx, o in g["mixed"]:
                nums = []
                words = []
                for part in rx.split("|"):
                    m = re.match(r"\s*(\d+)\s+of\s+((?:19|20)\d{2})\s*$", part)
                    if m:
                        nums.append("%d/%s" % (int(m.group(1)), m.group(2)))
                    elif part.strip().isdigit():
                        nums.append("#" + part.strip())
                    else:
                        words.append(part)
                sub = [DEFAULT_SUBST[o]] if o in DEFAULT_SUBST else None
                if jid == "J-3a4ed1aba90b8e35" and o == "allowed":
                    sub = ["relief_granted", "remanded_for_fresh_decision"]   # Delhi appeals allowed and remitted
                procs.append({"nums": nums or ["ALL"], "printed": [o], "subst": sub,
                              "party_rx": "|".join(words) or None})
        else:
            acc = list(g["accept"])
            for x in C10_PRINTED_EXTRA.get(jid, []):
                if x not in acc:
                    acc.append(x)
            if jid in C10_SUBST:
                sub = C10_SUBST[jid]
            else:
                subs = sorted(set(DEFAULT_SUBST[o] for o in acc if o in DEFAULT_SUBST))
                sub = subs or None
            procs.append({"nums": ["ALL"], "printed": acc, "subst": sub})
        gold[jid] = {"set": "C10", "procs": procs, "note": g.get("note", "")}
    # C11 holdout
    rows = []
    for fn in ("ground_truth_A.csv", "ground_truth_B.csv"):
        rows += list(csv.DictReader(open(os.path.join(C11, "holdout", fn), encoding="utf-8")))
    byh = {}
    for r in rows:
        byh.setdefault((r["holdout_id"], r["judgment_id"]), []).append(r)
    for (hid, jid), rr in sorted(byh.items()):
        procs = []
        for r in rr:
            nk = numkey(r["proceeding"]) if r["proceeding"].strip() != "ALL" else ["ALL"]
            o = r["outcome"].split(" ")[0].strip()
            spec = None
            if hid == "H042":
                spec = H042.get(nk[0], (["dismissed"], ["relief_refused"], "per-petition dismissal"))
            elif hid in P:
                spec = P[hid].get(nk[0]) or P[hid].get("*")
            if spec is None:
                if o in DEFAULT_SUBST:
                    spec = ([o], [DEFAULT_SUBST[o]], "GT label; default substantive mapping")
                else:
                    spec = (None, None, "GT label '%s' not scorable" % o)
            procs.append({"nums": nk, "printed": spec[0], "subst": spec[1], "basis": spec[2], "gt_outcome": r["outcome"][:80]})
        gold[jid] = {"set": "C11H", "holdout_id": hid, "procs": procs}
    # C11 review: printed confirmed
    for r in csv.DictReader(open(os.path.join(C11, "review", "fable_review_extraction_c11_items.csv"), encoding="utf-8")):
        if not r["section"].startswith("4"):
            continue
        o = r["v2_value"].strip()
        sub = [DEFAULT_SUBST[o]] if o in DEFAULT_SUBST else None
        if r["item_id"] == "DO06":
            sub = ["relief_granted", "relief_partly_granted"]
        gold[r["judgment_id"]] = {"set": "C11R", "item_id": r["item_id"],
                                  "procs": [{"nums": ["ALL"], "printed": [o], "subst": sub}], "note": r["note"]}
    return gold


if __name__ == "__main__":
    g = build()
    out = os.path.join(HERE, "dev_gold_v3.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(g, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    n = {}
    for k, v in g.items():
        if not k.startswith("_"):
            n[v["set"]] = n.get(v["set"], 0) + 1
    print("wrote", out, n)
