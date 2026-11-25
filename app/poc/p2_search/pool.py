"""Pool top-k from all runs, auto-label objective categories, and emit blind sheets for the rest.

python -I pool.py <work_dir> <runs_dir> <qrels.json> <sheet_dir> [--depth 10] [--extra-runs DIR --extra-depth 5]

- The sheet order is sha1(qid|doc_id): the labeller never sees which system retrieved a doc or its rank.
- Existing labels in qrels.json are kept; only new (qid, doc_id) pairs are added (incremental pooling).
"""
import argparse, hashlib, json, re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("work", type=Path); ap.add_argument("runs", type=Path); ap.add_argument("qrels", type=Path)
ap.add_argument("sheets", type=Path); ap.add_argument("--depth", type=int, default=10)
ap.add_argument("--extra-runs", type=Path); ap.add_argument("--extra-depth", type=int, default=5)
ap.add_argument("--queries", type=Path, default=Path(__file__).resolve().parent / "queries.json")
a = ap.parse_args()

queries = {q["qid"]: q for q in json.load(open(a.queries))}
docs = {}
for line in open(a.work / "corpus/corpus.jsonl"):
    d = json.loads(line); docs[d["doc_id"]] = d

pool = {qid: set() for qid in queries}
def add_runs(folder, depth):
    for f in sorted(folder.glob("*.json")):
        run = json.loads(f.read_text())["run"]
        for qid, lst in run.items():
            pool[qid].update(d for d, _s in lst[:depth])
add_runs(a.runs, a.depth)
if a.extra_runs:
    add_runs(a.extra_runs, a.extra_depth)
for q in queries.values():
    if q.get("target"):
        pool[q["qid"]].add(q["target"])

qrels = json.loads(a.qrels.read_text()) if a.qrels.exists() else {}

def flat(s): return re.sub(r"\s+", " ", s)

def id_regex(ident):
    if "exact" in ident:
        e = re.escape(ident["exact"]).replace(r"\ ", r"\s*").replace(r"\.", r"\.?")
        return re.compile(e, re.I)
    kind = r"\W*".join(re.escape(ch) for ch in re.sub(r"[^A-Za-z]", "", ident["kind"]))
    return re.compile(rf"\b{kind}\W*(?:no\.?\s*)?{ident['num']}\s*(?:/|of)\s*{ident['year']}\b", re.I)

def statute_regex(st):
    sec, act = st["sec"], st["act_re"]
    kw = r"(?:section|sec\.?|s\.|rule|r\.|regulation|reg\.?|para)"
    pats = [rf"{kw}\s*{sec}\b(?:\s*\([^)]{{1,6}}\))*[^.;\n]{{0,80}}?{act}",
            rf"{act}[^.;\n]{{0,40}}?{kw}\s*{sec}\b"]
    if st["kind"] == "rule":
        pats.append(rf"army\s+rules?\s*{sec}\b")
    if st["kind"] == "regulation":
        pats.append(rf"regulation\s*{sec}\b")
    return re.compile("|".join(pats), re.I)

to_sheet = {}
for qid, q in queries.items():
    ql = qrels.setdefault(qid, {})
    for d in pool[qid]:
        if d in ql:
            continue
        text = flat(docs[d]["text"]) if d in docs else ""
        cat = q["category"]
        if cat in ("case_name", "case_number", "citation"):
            if d == q["target"]:
                ql[d] = {"grade": 2, "by": "auto_rule:known_item_target"}
            elif cat != "case_name" and id_regex(q["identifier"]).search(text):
                ql[d] = {"grade": 1, "by": "auto_rule:identifier_string_in_text"}
            else:
                ql[d] = {"grade": 0, "by": "auto_rule:known_item_other"}
        elif cat == "statute_ref":
            st = q["statute"]
            if st["act_doc"] and d == st["act_doc"]:
                ql[d] = {"grade": 2, "by": "auto_rule:statute_document"}
            elif statute_regex(st).search(text):
                ql[d] = {"grade": 1, "by": "auto_rule:section_reference_in_text"}
            else:
                ql[d] = {"grade": 0, "by": "auto_rule:no_section_reference"}
        else:
            to_sheet.setdefault(qid, []).append(d)

# full-collection recall base for objective categories (relevant docs that NO system retrieved)
for qid, q in queries.items():
    if q["category"] in ("case_number", "citation"):
        rx = id_regex(q["identifier"])
        for d, doc in docs.items():
            if d not in qrels[qid] and rx.search(flat(doc["text"])):
                qrels[qid][d] = {"grade": 1, "by": "auto_rule:identifier_string_in_text_unpooled"}
    if q["category"] == "statute_ref":
        rx = statute_regex(q["statute"])
        for d, doc in docs.items():
            if d not in qrels[qid] and rx.search(flat(doc["text"])):
                qrels[qid][d] = {"grade": 1, "by": "auto_rule:section_reference_in_text_unpooled"}

a.qrels.parent.mkdir(parents=True, exist_ok=True)
a.qrels.write_text(json.dumps(qrels, indent=0, sort_keys=True))

# blind sheets
STOP = set("a an the of to in for by on at is be can and or with from what when which does do has have his her their under after before not".split())
a.sheets.mkdir(parents=True, exist_ok=True)
n = 0
for qid, lst in to_sheet.items():
    q = queries[qid]["query"]
    terms = [t for t in re.findall(r"[a-z0-9]+", q.lower()) if t not in STOP and len(t) > 1]
    lines = [f"### {qid}: {q}"]
    for d in sorted(lst, key=lambda d: hashlib.sha1(f"{qid}|{d}".encode()).hexdigest()):
        doc = docs[d]; t = flat(doc["text"])
        words = t.split(); best, bi = -1, 0
        for i in range(0, max(1, len(words) - 60), 30):
            win = " ".join(words[i:i + 60]).lower()
            s = sum(win.count(x) for x in terms)
            if s > best: best, bi = s, i
        snippet = " ".join(words[bi:bi + 60])[:420]
        lines.append(f"- {d} | {(doc['title'] or '')[:90]} | {snippet}")
        n += 1
    (a.sheets / f"{qid}.txt").write_text("\n".join(lines) + "\n")
print("auto-labelled + pooled; manual items to judge:", n, "queries:", len(to_sheet))
