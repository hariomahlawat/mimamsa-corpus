"""Generate identifier queries (case names, case numbers, citations, AFT OA numbers) from metadata.

Targets are drawn with a fixed seed BEFORE any system is run; nothing is tuned to results.
Query surface forms are deliberately varied the way a user would type them (not copied from the index).
"""
import json, random, re, sys
from pathlib import Path

corpus, out = Path(sys.argv[1]), Path(sys.argv[2])
docs = [json.loads(l) for l in open(corpus)]
J = [d for d in docs if d["doc_type"] == "judgment"]
r = random.Random(2026)
queries = []

def short_party(s):
    s = re.sub(r"\b(THR\.?|THROUGH)\b.*", "", s or "", flags=re.I)
    s = re.sub(r"\b(AND ORS\.?|& ORS\.?|AND OTHERS|AND ANR\.?|& ANR\.?|AND ANOTHER|ORS\.?)\b", "", s, flags=re.I)
    s = re.sub(r"[\s,.&]+$", "", s.strip())
    return s.title()

# A. case names: 12 judgments with a parsable "X versus/Vs Y" title, excluding generic UoI-vs-UoI
pool = [d for d in J if d["title"] and re.search(r"\b(versus|Vs\.?)\b", d["title"])]
r.shuffle(pool)
n = 0
for d in pool:
    t = re.sub(r"^.*? of ", "", d["title"]) if " of " in d["title"][:40] and "/" in d["title"][:30] else d["title"]
    p, _, q = re.split(r"\b(versus|Vs\.?)\b", t, maxsplit=1)
    p, q = short_party(p), short_party(q)
    if not p or not q or len(p) > 60 or len(q) > 60: continue
    if p.lower().startswith("union of india") and q.lower().startswith("union of india"): continue
    queries.append(dict(qid=f"CN{n+1:02d}", category="case_name", query=f"{p} v. {q}", target=d["doc_id"]))
    n += 1
    if n == 12: break

# B1. case numbers (HC writ numbers), varied surface form
pool = [d for d in J if d["case_numbers"]]
r.shuffle(pool)
n = 0
for d in pool:
    cn = d["case_numbers"][0]
    m = re.match(r"([A-Z.()]+)/(\d+)/(\d{4})$", cn)
    if not m: continue
    kind, num, yr = m.groups()
    form = [f"{kind} {num}/{yr}", f"{kind} No. {num} of {yr}", f"{kind.replace('.', '')} {num} of {yr}"][n % 3]
    queries.append(dict(qid=f"NO{n+1:02d}", category="case_number", query=form, target=d["doc_id"],
                        identifier={"kind": kind, "num": num, "year": yr}))
    n += 1
    if n == 8: break

# B2. citations: neutral and SCR
pool = [d for d in J if d["neutral_citation"]]
r.shuffle(pool)
for i, d in enumerate(pool[:3]):
    queries.append(dict(qid=f"CI{i+1:02d}", category="citation", query=d["neutral_citation"], target=d["doc_id"],
                        identifier={"exact": d["neutral_citation"]}))
pool = [d for d in J if d["reported_citations"]]
r.shuffle(pool)
for i, d in enumerate(pool[:3]):
    c = d["reported_citations"][0]
    queries.append(dict(qid=f"CI{i+4:02d}", category="citation", query=c.replace(".", "").replace("[", "(").replace("]", ")"),
                        target=d["doc_id"], identifier={"exact": c}))

# B3. AFT OA numbers quoted inside HC judgments (user knows the tribunal case number only)
oa_re = re.compile(r"\bO\.?A\.?\s*No\.?\s*(\d{1,5})\s*(?:/|of)\s*(\d{4})", re.I)
pool = [d for d in J if d["doc_id"].startswith("hc-")]
r.shuffle(pool)
n = 0
for d in pool:
    m = oa_re.search(d["text"][:6000])
    if not m: continue
    num, yr = m.groups()
    queries.append(dict(qid=f"OA{n+1:02d}", category="case_number", query=f"OA {num}/{yr} Armed Forces Tribunal",
                        target=d["doc_id"], identifier={"kind": "OA", "num": num, "year": yr}))
    n += 1
    if n == 3: break

out.write_text(json.dumps(queries, indent=1))
print(len(queries))
for q in queries: print(q["qid"], q["query"], "->", q["target"])
