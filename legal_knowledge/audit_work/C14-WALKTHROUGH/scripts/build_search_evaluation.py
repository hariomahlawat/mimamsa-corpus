"""Merge the auditor's per-query assessments into the observed search results -> SEARCH_EVALUATION.json.

Assessments are human judgement (the auditor's), kept separate from what the API returned. Verdicts:
pass | partial | fail | not_determinable. Classes: ok | retrieval_failure | corpus_deficiency | incomplete_feature |
usability. Nothing here is a legal conclusion; it only says whether the library surfaced what a researcher would
look for first.  Usage: python build_search_evaluation.py evidence/search_raw.json SEARCH_EVALUATION.json
"""
import collections
import json
import sys

A = {
 "Q01": ("partial", "incomplete_feature", ["F09"], "Army Act and Army Rules surface, but no procedural provision is targeted; a how-to question needs passage-level semantic ranking."),
 "Q02": ("pass", "ok", [], "Army Rules first, then judgments discussing the summary of evidence."),
 "Q03": ("partial", "retrieval_failure", ["F09"], "AWL expanded correctly (chip). Army Act s.39 is not pinned; a judgment ranks first and the Army Act is 4th."),
 "Q04": ("partial", "retrieval_failure", ["F09"], "Air Force Act and Navy Regulations rank above the Army Act; no service-context preference."),
 "Q05": ("fail", "retrieval_failure", ["F09"], "Navy Regulations Part II rank first; Army Act s.80 is not the lead result for an Army commander."),
 "Q06": ("partial", "usability", ["F09"], "Results list Air Force Act first. The Statutes view of Army Act s.75 correctly prints 'Omitted by Act 37 of 1992' (J06)."),
 "Q07": ("fail", "retrieval_failure", ["F09"], "BNS, IPC and CrPC rank first; Army Act ss.101-102 (custody) absent from the top four."),
 "Q08": ("pass", "ok", [], "SCM expanded; Army Rules first."),
 "Q09": ("pass", "ok", ["F11"], "Provision text pinned first. The Hindi copy (garbled text) takes rank 2."),
 "Q10": ("pass", "ok", [], "Provision text first."),
 "Q11": ("pass", "ok", [], "Instrument scoped to Army Rules, 1954; provision first."),
 "Q12": ("pass", "ok", [], "Army Rules r.180 first, then a 2019 SC judgment."),
 "Q13": ("fail", "retrieval_failure", ["F09"], "Navy Act and Navy Regulations outrank the Army Act; s.39 not in the top four."),
 "Q14": ("pass", "ok", [], "Air Force Act s.82 first."),
 "Q15": ("pass", "ok", [], "Army Act s.80 first."),
 "Q16": ("pass", "ok", [], "s.127 found; the statute view prints it as omitted (1992)."),
 "Q17": ("pass", "ok", [], "Neutral citation resolves to the single judgment."),
 "Q18": ("fail", "retrieval_failure", ["F02"], "The named judgment ranks 9th behind judgments that cite it; party names are not an identifier tier or boosted field."),
 "Q19": ("fail", "corpus_deficiency", ["F06"], "Metadata holds only [2013] 8 S.C.R. 1119 for Dharamvir Singh; the SCC citation is not captured, so the identifier layer cannot match it."),
 "Q20": ("pass", "ok", [], "Case number from the page-1 cover resolves to the judgment (labelled candidate)."),
 "Q21": ("pass", "ok", [], "SC and HC disability-pension judgments; Dharamvir Singh at rank 4."),
 "Q22": ("not_determinable", "corpus_deficiency", ["F04", "F09"], "HC writs from service matters surface. Whether the controlling 2023 SC ruling on HC writs against AFT orders is held in the sample was not established; no result identified it."),
 "Q23": ("partial", "incomplete_feature", ["F09"], "Relevant SC court-martial judgments appear; no ranking by legal issue."),
 "Q24": ("partial", "incomplete_feature", ["F09"], "Delhi HC disability judgments that apply the presumption appear; the source authority (Dharamvir Singh) is not in the top four."),
 "Q25": ("fail", "incomplete_feature", ["F08"], "Spelling variant: the judgment falls to rank 35; no suggestion is offered."),
 "Q26": ("fail", "incomplete_feature", ["F08"], "'court marshal' matches 'provost marshal' in Navy Regulations; no 'did you mean court martial'."),
 "Q27": ("partial", "incomplete_feature", ["F08"], "Matches on 'pension' only; the typo is silently dropped."),
 "Q28": ("fail", "retrieval_failure", ["F01"], "'No instrument titled “IPC” in this library' although the IPC is held; the full title works."),
 "Q29": ("fail", "retrieval_failure", ["F01"], "'No instrument titled “BNS”' although BNS is held (three copies)."),
 "Q30": ("pass", "ok", [], "BPRD comparison tables first."),
 "Q31": ("pass", "ok", [], "Evidence Act s.65B pinned (full short title used)."),
 "Q32": ("pass", "ok", [], "Army Act first; 1992 amendment footnotes found."),
 "Q33": ("pass", "ok", [], "Both Tribunals Reforms Acts and the AFT Act first."),
 "Q34": ("pass", "ok", [], "AFT Act s.30 pinned."),
 "Q35": ("partial", "retrieval_failure", ["F09"], "AFT expanded, but bench notifications and recruitment rules outrank the AFT Act jurisdiction provisions (ss.14-15)."),
 "Q36": ("pass", "usability", [], "No document contains both words; 20 documents match 'quantum' (of punishment/pension). Per-hit 'Matched:' lines show this, but the head does not say 'not all words matched'."),
 "Q37": ("pass", "ok", [], "Parser error with position; nothing searched; explicit 'words only' action."),
 "Q38": ("pass", "ok", [], "Which-instrument chip lists 11 candidates; nothing pinned."),
 "Q39": ("pass", "ok", [], "Exact phrase only; expansion disabled and stated."),
 "Q40": ("pass", "ok", [], "Boolean exclusion chip shown."),
 "Q41": ("pass", "ok", [], "Field filter to Delhi HC."),
 "Q42": ("pass", "ok", [], "Type and year filters applied; counts reduce accordingly."),
 "Q43": ("fail", "corpus_deficiency", ["F07"], "Hindi query ranks BNSS/BNS/BSA alternate copies first; the Hindi Army Act text is garbled (legacy font mapping), so Hindi search is unreliable."),
}

raw = json.load(open(sys.argv[1], encoding="utf-8"))
out = []
for r in raw:
    v, c, f, note = A[r["id"]]
    out.append({**r, "assessment": {"verdict": v, "class": c, "findings": f, "note": note}})
summary = {
    "queries": len(out),
    "by_verdict": dict(collections.Counter(o["assessment"]["verdict"] for o in out)),
    "by_class": dict(collections.Counter(o["assessment"]["class"] for o in out)),
    "by_persona": {p: dict(collections.Counter(o["assessment"]["verdict"] for o in out if o["persona"] == p))
                   for p in sorted({o["persona"] for o in out})},
    "method": "Each query run once through /api/search as a User on the commissioned instance (290-document sample, "
              "release R13-b1-sample-20261126-4b31855f). The top five documents and top three passages were recorded "
              "(evidence/search_raw.json) and judged by the auditor against what a researcher would look for first. "
              "Judgements are not legal conclusions and not a retrieval-quality metric: there are no human relevance "
              "labels and the blind holdout was not used.",
}
json.dump({"summary": summary, "queries": out}, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(summary, indent=1))
