"""P2 latency: p50/p95 per system at 1 and 10 concurrent clients (in-process threads; PG uses one connection
per thread). Dense latency INCLUDES query embedding on CPU.

python -I latency.py <work_dir> <lexicon.json> <emb_dir> <models_dir> <out.json> [--passes 3]
"""
import argparse, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "p3_embeddings"))
from engines import Abbrev, TantivyBm25, Dense, IdLayer, rrf, PgFts  # noqa: E402
from run_eval import PgTiered  # noqa: E402
from embed import Encoder  # noqa: E402

ap = argparse.ArgumentParser()
for a in ("work", "lexicon", "emb_dir", "models_dir", "out"):
    ap.add_argument(a, type=Path)
ap.add_argument("--passes", type=int, default=3)
ap.add_argument("--model", default="bge-small-en-v1.5")
a = ap.parse_args()
queries = [q["query"] for q in json.load(open(Path(__file__).resolve().parent / "queries.json"))]
ab = Abbrev(a.lexicon)
idl = IdLayer(a.work / "corpus/corpus.jsonl")
bm25 = TantivyBm25(a.work / "tantivy_full", ab)
dense = Dense(a.emb_dir, a.model)
enc = Encoder(a.model, a.models_dir, threads=int(os.environ.get("ORT_THREADS", "4")))
tl = threading.local()


def pg():
    if not hasattr(tl, "pg"):
        tl.pg = PgTiered(ab)
    return tl.pg


def dense_search(q):
    return dense.search_vec(enc.encode([q], 1, enc.qp)[0], 100)


SYSTEMS = {
    "pg_fts_tiered+abbr": lambda q: pg().search(q, 100),
    "bm25+abbr": lambda q: bm25.search(q, 100),
    f"dense:{a.model}(incl. query embedding)": dense_search,
    "rrf(bm25+abbr,dense)+id": lambda q: idl.apply(q, rrf([bm25.search(q, 100), dense_search(q)])),
    "rrf(pg_fts_tiered+abbr,dense)+id": lambda q: idl.apply(q, rrf([pg().search(q, 100), dense_search(q)])),
}

res = {"loadavg_start": os.getloadavg(), "n_queries": len(queries), "passes": a.passes, "systems": {}}
for name, f in SYSTEMS.items():
    for q in queries[:5]:
        f(q)  # warm-up
    for conc in (1, 10):
        lat = []
        def one(q):
            t = time.perf_counter(); f(q); return (time.perf_counter() - t) * 1000
        work = queries * a.passes
        t0 = time.perf_counter()
        if conc == 1:
            lat = [one(q) for q in work]
        else:
            with ThreadPoolExecutor(conc) as ex:
                lat = list(ex.map(one, work))
        wall = time.perf_counter() - t0
        res["systems"].setdefault(name, {})[f"c{conc}"] = dict(
            p50_ms=round(float(np.percentile(lat, 50)), 2), p95_ms=round(float(np.percentile(lat, 95)), 2),
            max_ms=round(max(lat), 1), qps=round(len(work) / wall, 1), loadavg=os.getloadavg()[0])
        print(name, conc, res["systems"][name][f"c{conc}"], flush=True)
a.out.write_text(json.dumps(res, indent=1))
