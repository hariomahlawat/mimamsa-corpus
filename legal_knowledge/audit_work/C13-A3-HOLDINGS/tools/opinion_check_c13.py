#!/usr/bin/env python3
"""C13-A3 opinion-attribution check on multi-opinion judgments (Bommai-type benches).

  python -I -B opinion_check_c13.py --pred DIR --out ../opinion_check/OPINION_ATTRIBUTION_C13.md

Gold: ../gold/OPINION_GOLD_C13.csv, built by the C13-A3 developer from author lines, running headers and the
reported bench composition (evidence column). It is NOT independent and not legally reviewed.
DIR holds `holdings_c13.py ids` output for the gold judgments (HOLDINGS_C13.jsonl, HOLDINGS_C13_JUDGMENTS.csv).
C12 comparison: the frozen C12 scope output (HOLDINGS_C12.jsonl).

Metrics
  Opinion level: gold opinions located (detected opinion whose author matches, start within 2 pages);
                 binding class correct (COURT_SIDE: sole/majority/concurring/order; NOT_COURT: dissent, partly
                 dissenting, minority, split verdict) for located opinions.
  Item level:    every holding-class item (holding, dissent_holding_candidate, split_opinion_holding_candidate) is
                 assigned to the gold opinion covering its page. An item on the first page of an opinion is treated as
                 ambiguous and scored leniently (either neighbour accepted).
                 - author correct: the item's opinion author matches the gold author;
                 - court-holding misattribution: item_type `holding` (presented as a holding, not flagged as dissent or
                   split) while the gold opinion is NOT_COURT.
"""
import argparse
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c13_segment as sg  # noqa: E402

ROOT = os.path.dirname(HERE)
GOLD = os.path.join(ROOT, "gold", "OPINION_GOLD_C13.csv")
C12_OUT = os.path.join(ROOT, "..", "C12-CONSOLIDATION", "holdings", "outputs", "HOLDINGS_C12.jsonl")
COURT_SIDE_ROLES = {"sole", "lead_majority", "lead", "concurring", "separate", "court_order"}


def load_gold():
    g = collections.defaultdict(list)
    with open(GOLD, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["start"] = int(r["start_page"]) if r["start_page"].isdigit() else None
            g[r["judgment_id"]].append(r)
    for j in g:
        g[j].sort(key=lambda r: (r["start"] is None, r["start"] or 0))
    return g


def gold_at(gl, page):
    """Return (opinion, ambiguous_neighbour) for a page."""
    located = [r for r in gl if r["start"] is not None]
    cur, prev = None, None
    for r in located:
        if r["start"] <= page:
            prev, cur = cur, r
    if cur is None:
        return located[0] if located else None, None
    return cur, (prev if page == cur["start"] else None)


def author_ok(item_author, gold_author):
    if gold_author == "ORDER":
        return not item_author
    return bool(item_author) and sg.same_judge(item_author, gold_author)


def score_items(items, gold, type_key, holding_test, author_key, extra_flag=None):
    tot = auth = mis = amb = 0
    per = collections.Counter()
    for it in items:
        jl = gold.get(it["judgment_id"])
        if not jl:
            continue
        g, alt = gold_at(jl, it["page"])
        if g is None:
            continue
        tot += 1
        cands = [g] + ([alt] if alt else [])
        if alt:
            amb += 1
        if any(author_ok(it.get(author_key), c["author"]) for c in cands):
            auth += 1
        if holding_test(it) and all(c["binding_class"] == "NOT_COURT" for c in cands) and not (extra_flag and extra_flag(it)):
            mis += 1
            per[it["judgment_id"]] += 1
    return tot, auth, mis, amb, per


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    gold = load_gold()
    jrows = {r["judgment_id"]: r for r in csv.DictReader(open(os.path.join(a.pred, "HOLDINGS_C13_JUDGMENTS.csv"), encoding="utf-8"))}
    items = [json.loads(l) for l in open(os.path.join(a.pred, "HOLDINGS_C13.jsonl"), encoding="utf-8")]
    L = ["# C13-A3 opinion-attribution check (multi-opinion judgments)\n",
         "Gold built by the developer from author lines, running headers and bench composition (`gold/OPINION_GOLD_C13.csv`, "
         "evidence per row). **Not independent, not legally reviewed**; the coordinator should arrange an independent check. "
         "Developer-built gold also overlaps the judgments used while writing the opinion rules (in-sample).\n"]
    # opinion level
    loc = cls_ok = n = 0
    rows = []
    for j, gl in sorted(gold.items()):
        det = []
        for part in (jrows.get(j, {}).get("opinions") or "").split(";"):
            if not part:
                continue
            oid, role, rest = part.split(":", 2)
            auth, pages = rest.rsplit("@p", 1)
            p0 = int(pages.split("-")[0]) if pages.split("-")[0].isdigit() else None
            det.append((oid, role, auth, p0))
        for g in gl:
            if g["start"] is None:
                rows.append((j, g["case"], g["author"], "NOT_LOCATED_IN_TEXT", g["gold_role"], "-", "-", "excluded"))
                continue
            n += 1
            m = None
            for d in det:
                if d[3] is None or abs(d[3] - g["start"]) > 2:
                    continue
                if g["author"] == "ORDER" and d[1] == "court_order":
                    m = d
                elif g["author"] != "ORDER" and d[2] != "?" and sg.same_judge(d[2], g["author"]):
                    m = d
                elif g["author"] != "ORDER" and len(gl) == 1 and len(det) == 1:
                    m = d
                if m:
                    break
            if m:
                loc += 1
                pc = "NOT_COURT" if m[1] in ("dissent", "split_opinion") else "COURT_SIDE"
                ok = pc == g["binding_class"]
                cls_ok += ok
                rows.append((j, g["case"], g["author"], "p%s" % g["start"], g["gold_role"], "%s:%s@p%s" % (m[0], m[1], m[3]), pc, "OK" if ok else "WRONG_CLASS"))
            else:
                rows.append((j, g["case"], g["author"], "p%s" % g["start"], g["gold_role"], "not detected", "-", "MISSED"))
    L.append("## Opinion level\n")
    L.append("| Measure | Result |\n| --- | --- |")
    L.append("| Gold opinions located (author match, start within 2 pages) | %d/%d |" % (loc, n))
    L.append("| Binding class correct among located (COURT_SIDE vs NOT_COURT) | %d/%d |" % (cls_ok, loc))
    L.append("")
    L.append("| judgment | case | gold author | gold start | gold role | detected | detected class | result |\n| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        L.append("| %s |" % " | ".join(str(x) for x in r))
    L.append("")
    # item level
    hold_types = {"holding", "dissent_holding_candidate", "split_opinion_holding_candidate"}
    its13 = [x for x in items if x["item_type"] in hold_types and x["judgment_id"] in gold]
    t13 = score_items(its13, gold, "item_type", lambda it: it["item_type"] == "holding", "opinion_author")
    its12 = []
    if os.path.exists(C12_OUT):
        with open(C12_OUT, encoding="utf-8") as f:
            for ln in f:
                x = json.loads(ln)
                if x["judgment_id"] in gold and x["item_type"] == "holding":
                    its12.append(x)
    t12 = score_items(its12, gold, "item_type", lambda it: True, "opinion_author",
                      extra_flag=lambda it: it.get("opinion") == "dissent")
    L.append("## Item level (holding-class items in the gold judgments)\n")
    L.append("| Measure | c12-holdings (frozen scope output) | c13 |\n| --- | --- | --- |")
    L.append("| Holding-class items scored | %d | %d |" % (t12[0], t13[0]))
    L.append("| Author attribution correct | %d/%d (%.1f%%) | %d/%d (%.1f%%) |" % (t12[1], t12[0], 100.0 * t12[1] / max(1, t12[0]), t13[1], t13[0], 100.0 * t13[1] / max(1, t13[0])))
    L.append("| Presented as the court's holding but gold opinion is dissent / minority / split | %d/%d (%.1f%%) | %d/%d (%.1f%%) |" % (
        t12[2], t12[0], 100.0 * t12[2] / max(1, t12[0]), t13[2], t13[0], 100.0 * t13[2] / max(1, t13[0])))
    L.append("| Items on an opinion's first page (scored leniently) | %d | %d |" % (t12[3], t13[3]))
    L.append("")
    L.append("Misattributed items per judgment (c13): " + (", ".join("%s: %d" % kv for kv in sorted(t13[4].items())) or "none"))
    L.append("\nMisattributed items per judgment (c12): " + (", ".join("%s: %d" % kv for kv in sorted(t12[4].items())) or "none"))
    L.append("\nC12 items flagged `opinion = dissent` are not counted as misattributed for C12 (it carried a dissent note).\n")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L[3:8]))
    print("\n".join(L[-8:]))


if __name__ == "__main__":
    main()
