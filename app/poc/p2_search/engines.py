"""P2 search engines: PostgreSQL FTS, Tantivy BM25, dense vector (FAISS exact, NOT pgvector), hybrid RRF,
and an exact-identifier layer. All engines return doc-level rankings (max over units).

Index build:  python -I engines.py build <work_dir> <lexicon.json>
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import psycopg

DSN = os.environ.get("POC_DSN", "host=127.0.0.1 port=55432 user=poc dbname=poc")
HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- abbreviations
# Legal-procedure codes absent from the Army lexicon v1.0; PoC supplement only (not lexicon data).
SUPPLEMENT = {
    "AFT": ["Armed Forces Tribunal"], "OA": ["Original Application"], "MA": ["Miscellaneous Application"],
    "SOE": ["Summary of Evidence"], "COI": ["Court of Inquiry"], "AR": ["Army Rule", "Army Rules"],
    "AA": ["Army Act"], "HC": ["High Court"], "SC": ["Supreme Court"], "WP": ["Writ Petition"],
    "ROE": ["Record of Evidence"], "PCP": ["Post Confirmation Petition"],
}


class Abbrev:
    """Expand UPPER-CASE tokens found in the lexicon (preferred meanings, max 2). Case-sensitive on purpose:
    'CO' expands, 'co' does not."""

    def __init__(self, lexicon_path: Path | None):
        self.map: dict[str, list[str]] = {}
        if lexicon_path:
            lex = json.loads(Path(lexicon_path).read_text())["abbreviations"]
            for code, v in lex.items():
                if code.isupper() and 2 <= len(code) <= 6 and v.get("preferred"):
                    self.map[code] = v["preferred"][:2]
        for k, v in SUPPLEMENT.items():
            self.map.setdefault(k, v)

    def expansions(self, q: str) -> list[tuple[str, list[str]]]:
        out = []
        for tok in re.findall(r"\b[A-Z]{2,6}\b", q):
            if tok in self.map:
                out.append((tok, self.map[tok]))
        return out


# ---------------------------------------------------------------- identifiers
def norm_id(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\bno\.?\b", " ", s)
    s = re.sub(r"\bof\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


ID_PATTERNS = [
    re.compile(r"\b\d{4}\s+INSC\s+\d+\b", re.I),
    re.compile(r"[\[(]\d{4}[\])]\s*\d+\s*S\.?\s*C\.?\s*R\.?\s*\d+", re.I),
    re.compile(r"[\[(]\d{4}[\])]\s*\d+\s*SCC\s*\d+", re.I),
    re.compile(r"\b[A-Z][A-Za-z.()]{1,12}\s*(?:No\.?\s*)?\d{1,6}\s*(?:/|of)\s*\d{4}\b"),
]


def extract_ids(q: str) -> list[str]:
    out = []
    for p in ID_PATTERNS:
        out += [norm_id(m.group(0)) for m in p.finditer(q)]
    return out


# ---------------------------------------------------------------- PostgreSQL FTS
class PgFts:
    name = "pg_fts"

    def __init__(self, abbrev: Abbrev | None = None, dsn: str = DSN):
        self.abbrev, self.dsn = abbrev, dsn
        self.conn = psycopg.connect(dsn, autocommit=True)

    def tsquery_sql(self, q: str):
        parts, params = ["replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery"], [q]
        for _code, phrases in (self.abbrev.expansions(q) if self.abbrev else []):
            for ph in phrases:
                parts.append("phraseto_tsquery('english', %s)"); params.append(ph)
        return " || ".join(f"({p})" for p in parts), params

    def search(self, q: str, k: int = 100, conn=None):
        tq, params = self.tsquery_sql(q)
        sql = f"""WITH q AS (SELECT {tq} AS q)
                  SELECT doc_id, max(ts_rank(tsv, q.q)) AS s FROM units, q
                  WHERE tsv @@ q.q GROUP BY doc_id ORDER BY s DESC LIMIT %s"""
        cur = (conn or self.conn).execute(sql, params + [k])
        return [(r[0], float(r[1])) for r in cur.fetchall()]


# ---------------------------------------------------------------- Tantivy BM25
TANTIVY_SPECIAL = re.compile(r'[+\-&|!(){}\[\]^"~*?:\\/<>=\'`]')


class TantivyBm25:
    name = "tantivy_bm25"

    def __init__(self, index_dir: Path, abbrev: Abbrev | None = None):
        import tantivy
        self.tantivy = tantivy
        self.index = tantivy.Index.open(str(index_dir))
        self.index.reload()
        self.searcher = self.index.searcher()
        self.abbrev = abbrev

    def build_query(self, q: str) -> str:
        base = TANTIVY_SPECIAL.sub(" ", q)
        parts = [base]
        for _code, phrases in (self.abbrev.expansions(q) if self.abbrev else []):
            parts += [f'"{ph}"' for ph in phrases]
        return " ".join(parts)

    def search(self, q: str, k: int = 100):
        query = self.index.parse_query(self.build_query(q), ["title", "body"], field_boosts={"title": 2.0})
        hits = self.searcher.search(query, 2000).hits  # statutes have many chunks per doc_id
        best: dict[str, float] = {}
        for score, addr in hits:
            d = self.searcher.doc(addr)["doc_id"][0]
            if d not in best:
                best[d] = score
        return sorted(best.items(), key=lambda x: -x[1])[:k]


def build_tantivy(index_dir: Path, units):
    import tantivy
    sb = tantivy.SchemaBuilder()
    sb.add_text_field("doc_id", stored=True, tokenizer_name="raw")
    sb.add_text_field("title", stored=False, tokenizer_name="en_stem")
    sb.add_text_field("body", stored=False, tokenizer_name="en_stem")
    schema = sb.build()
    index_dir.mkdir(parents=True, exist_ok=True)
    idx = tantivy.Index(schema, path=str(index_dir))
    w = idx.writer(heap_size=500_000_000, num_threads=2)
    for u in units:
        w.add_document(tantivy.Document(doc_id=u["doc_id"], title=u["title"] or "", body=u["body"]))
    w.commit()
    w.wait_merging_threads()


# ---------------------------------------------------------------- dense vectors (FAISS exact inner product)
class Dense:
    """Labelled alternative to pgvector: FAISS IndexFlatIP (exact) over normalised chunk embeddings."""
    name = "dense_faiss"

    def __init__(self, emb_dir: Path, model: str):
        import faiss
        self.cv = np.load(emb_dir / f"{model}.chunks.npy")
        ids = json.loads((emb_dir / f"{model}.ids.json").read_text())
        self.chunk_doc = [c.rsplit("::", 1)[0] for c in ids["chunk_ids"]]
        self.qv = dict(zip(ids["qids"], np.load(emb_dir / f"{model}.queries.npy")))
        self.index = faiss.IndexFlatIP(self.cv.shape[1])
        self.index.add(self.cv)
        self.encoder = None

    def search_vec(self, v: np.ndarray, k: int = 100):
        D, I = self.index.search(v[None, :].astype(np.float32), 1500)
        best: dict[str, float] = {}
        for s, i in zip(D[0], I[0]):
            d = self.chunk_doc[i]
            if d not in best:
                best[d] = float(s)
        return sorted(best.items(), key=lambda x: -x[1])[:k]

    def search_qid(self, qid: str, k: int = 100):
        return self.search_vec(self.qv[qid], k)


# ---------------------------------------------------------------- fusion and identifier layer
def rrf(rankings: list[list[tuple[str, float]]], k: int = 60, depth: int = 100):
    sc = defaultdict(float)
    for r in rankings:
        for rank, (d, _s) in enumerate(r[:depth]):
            sc[d] += 1.0 / (k + rank + 1)
    return sorted(sc.items(), key=lambda x: -x[1])


class IdLayer:
    """Exact identifier lookup from metadata (case numbers, neutral and reported citations).
    Docs whose identifier exactly matches an identifier in the query are pinned to the top."""

    def __init__(self, corpus_path: Path):
        self.table = defaultdict(set)
        for line in open(corpus_path):
            d = json.loads(line)
            for s in (d.get("case_numbers") or []) + (d.get("reported_citations") or []) + [d.get("neutral_citation") or ""]:
                if s:
                    self.table[norm_id(s)].add(d["doc_id"])

    def lookup(self, q: str) -> list[str]:
        hits = []
        for i in extract_ids(q):
            hits += sorted(self.table.get(i, ()))
        return list(dict.fromkeys(hits))

    def apply(self, q: str, ranking):
        pinned = self.lookup(q)
        if not pinned:
            return ranking
        rest = [(d, s) for d, s in ranking if d not in pinned]
        return [(d, 1e9) for d in pinned] + rest


# ---------------------------------------------------------------- build
def units_from_corpus(corpus_path: Path, chunks_path: Path):
    """Lexical units: whole judgments (full text) + statute chunks (sections are not split in this snapshot)."""
    docs = {}
    for line in open(corpus_path):
        d = json.loads(line)
        docs[d["doc_id"]] = d
    for d in docs.values():
        if d["doc_type"] == "judgment":
            yield dict(unit_id=d["doc_id"], doc_id=d["doc_id"], doc_type="judgment", title=d["title"], body=d["text"])
    for line in open(chunks_path):
        c = json.loads(line)
        d = docs[c["doc_id"]]
        if d["doc_type"] != "judgment":
            yield dict(unit_id=c["chunk_id"], doc_id=d["doc_id"], doc_type=d["doc_type"], title=d["title"], body=c["text"])


def build_pg(units, dsn=DSN):
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS units")
        conn.execute("""CREATE TABLE units(unit_id text PRIMARY KEY, doc_id text NOT NULL, doc_type text,
                        title text, body text, tsv tsvector)""")
        with conn.cursor().copy("COPY units(unit_id, doc_id, doc_type, title, body) FROM STDIN") as cp:
            for u in units:
                cp.write_row((u["unit_id"], u["doc_id"], u["doc_type"], u["title"], u["body"].replace("\x00", "")))
        t = time.perf_counter()
        conn.execute("""UPDATE units SET tsv = setweight(to_tsvector('english', coalesce(title,'')), 'A')
                        || setweight(to_tsvector('english', left(body, 600000)), 'B')""")
        conn.execute("CREATE INDEX units_tsv ON units USING gin(tsv)")
        conn.execute("CREATE INDEX units_doc ON units(doc_id)")
        conn.execute("VACUUM ANALYZE units")
        return time.perf_counter() - t


if __name__ == "__main__":
    cmd, work = sys.argv[1], Path(sys.argv[2])
    if cmd == "build":
        corpus, chunks = work / "corpus/corpus.jsonl", work / "corpus/chunks.jsonl"
        stats = {}
        t = time.perf_counter(); s = build_pg(units_from_corpus(corpus, chunks))
        stats["pg_fts_build_s"] = round(time.perf_counter() - t, 1); stats["pg_fts_tsvector_gin_s"] = round(s, 1)
        t = time.perf_counter(); build_tantivy(work / "tantivy_full", units_from_corpus(corpus, chunks))
        stats["tantivy_full_build_s"] = round(time.perf_counter() - t, 1)
        # head-only variant: same units the dense index sees (2 head chunks per judgment + statute chunks)
        def vunits():
            titles = {json.loads(l)["doc_id"]: json.loads(l)["title"] for l in open(corpus)}
            for l in open(work / "corpus/vchunks.jsonl"):
                c = json.loads(l)
                yield dict(doc_id=c["doc_id"], title=titles[c["doc_id"]], body=c["text"])
        t = time.perf_counter(); build_tantivy(work / "tantivy_head", vunits())
        stats["tantivy_head_build_s"] = round(time.perf_counter() - t, 1)
        # like-for-like lexical index over exactly the dense units (read by run_eval as bm25_denseunits+abbr)
        def p3units():
            titles = {json.loads(l)["doc_id"]: json.loads(l)["title"] for l in open(corpus)}
            for l in open(work / "corpus/p3chunks.jsonl"):
                c = json.loads(l)
                yield dict(doc_id=c["doc_id"], title=titles[c["doc_id"]], body=c["text"])
        t = time.perf_counter(); build_tantivy(work / "tantivy_p3", p3units())
        stats["tantivy_p3_build_s"] = round(time.perf_counter() - t, 1)
        with psycopg.connect(DSN) as c:
            stats["pg_units_rows"] = c.execute("select count(*) from units").fetchone()[0]
            stats["pg_table_bytes"] = c.execute("select pg_total_relation_size('units')").fetchone()[0]
            stats["pg_gin_bytes"] = c.execute("select pg_relation_size('units_tsv')").fetchone()[0]
        stats["tantivy_full_bytes"] = sum(p.stat().st_size for p in (work / "tantivy_full").rglob("*") if p.is_file())
        stats["tantivy_head_bytes"] = sum(p.stat().st_size for p in (work / "tantivy_head").rglob("*") if p.is_file())
        print(json.dumps(stats, indent=1))
        (work / "index_build_stats.json").write_text(json.dumps(stats, indent=1))
