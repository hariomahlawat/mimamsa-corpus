"""Run every P2 system over the query set; write runs/<system>.json = {qid: [[doc_id, score], ...]} (top 100).

python -I run_eval.py <work_dir> <lexicon.json> <runs_out_dir> [--emb-dir DIR --model KEY]
"""
import argparse, glob, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engines import Abbrev, PgFts, TantivyBm25, Dense, IdLayer, rrf  # noqa: E402


class PgTiered(PgFts):
    """AND-match docs first (websearch semantics), then OR-match docs. Common production pattern."""
    name = "pg_fts_tiered"

    def search(self, q, k=100, conn=None):
        tq_or, p_or = self.tsquery_sql(q)
        tq_and = "(plainto_tsquery('english', %s))" + "".join(
            " || phraseto_tsquery('english', %s)" for _c, phs in (self.abbrev.expansions(q) if self.abbrev else []) for _ in phs)
        p_and = [q] + [ph for _c, phs in (self.abbrev.expansions(q) if self.abbrev else []) for ph in phs]
        sql = f"""WITH qa AS (SELECT {tq_and} AS q), qo AS (SELECT {tq_or} AS q)
                  SELECT doc_id, max((tsv @@ qa.q)::int + ts_rank(tsv, qo.q)) AS s FROM units, qa, qo
                  WHERE tsv @@ qo.q GROUP BY doc_id ORDER BY s DESC LIMIT %s"""
        cur = (conn or self.conn).execute(sql, p_and + p_or + [k])
        return [(r[0], float(r[1])) for r in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work", type=Path); ap.add_argument("lexicon", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--emb-dir", type=Path); ap.add_argument("--model", default="bge-small-en-v1.5")
    ap.add_argument("--queries", type=Path, default=Path(__file__).resolve().parent / "queries.json")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    queries = json.load(open(a.queries))
    ab = Abbrev(a.lexicon)
    idl = IdLayer(a.work / "corpus/corpus.jsonl")
    systems = {
        "pg_fts": PgFts(None).search,
        "pg_fts+abbr": PgFts(ab).search,
        "pg_fts_tiered+abbr": PgTiered(ab).search,
        "bm25": TantivyBm25(a.work / "tantivy_full", None).search,
        "bm25+abbr": TantivyBm25(a.work / "tantivy_full", ab).search,
        "bm25_head+abbr": TantivyBm25(a.work / "tantivy_head", ab).search,
    }
    runs = {s: {} for s in systems}
    for q in queries:
        for s, f in systems.items():
            runs[s][q["qid"]] = f(q["query"], 100)
    if a.emb_dir:
        dense = Dense(a.emb_dir, a.model)
        dn = f"dense:{a.model}"
        runs[dn] = {q["qid"]: dense.search_qid(q["qid"], 100) for q in queries}
        for lex in ("bm25+abbr", "pg_fts_tiered+abbr"):
            h = f"rrf({lex},{dn})"
            runs[h] = {q["qid"]: rrf([runs[lex][q["qid"]], runs[dn][q["qid"]]])[:100] for q in queries}
            runs[h + "+id"] = {q["qid"]: idl.apply(q["query"], runs[h][q["qid"]])[:100] for q in queries}
    for lex in ("bm25+abbr", "pg_fts_tiered+abbr"):
        runs[lex + "+id"] = {q["qid"]: idl.apply(q["query"], runs[lex][q["qid"]])[:100] for q in queries}
    for s, r in runs.items():
        (a.out / f"{s.replace(':', '__').replace('/', '_')}.json").write_text(json.dumps({"system": s, "run": r}))
    print("systems:", list(runs))


if __name__ == "__main__":
    main()
