"""P3: dense-only and hybrid runs for every model embedded on the P3 subset.
python -I p3_runs.py <work_dir> <lexicon.json> <emb_dir> <runs_out>"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "p2_search"))
from engines import Abbrev, TantivyBm25, Dense, IdLayer, rrf

work, lex, emb, out = map(Path, sys.argv[1:5]); out.mkdir(parents=True, exist_ok=True)
queries = json.load(open(Path(__file__).resolve().parents[1] / "p2_search/queries.json"))
bm25 = TantivyBm25(work / "tantivy_full", Abbrev(lex)); idl = IdLayer(work / "corpus/corpus.jsonl")
lexrun = {q["qid"]: bm25.search(q["query"], 100) for q in queries}
for f in sorted(emb.glob("*.chunks.npy")):
    model = f.name[:-len(".chunks.npy")]
    d = Dense(emb, model)
    dn = {q["qid"]: d.search_qid(q["qid"], 100) for q in queries}
    hy = {q["qid"]: idl.apply(q["query"], rrf([lexrun[q["qid"]], dn[q["qid"]]]))[:100] for q in queries}
    for name, run in ((f"p3dense:{model}", dn), (f"p3hybrid:rrf(bm25+abbr;{model})+id", hy)):
        (out / (name.replace(":", "__").replace(";", "_") + ".json")).write_text(json.dumps({"system": name, "run": run}))
    print(model)
