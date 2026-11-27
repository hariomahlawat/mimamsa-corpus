"""Exact component digests (contract 2.1 clarification of arch §5) and the bundle-independent text-store source
digest. Each function is the byte-exact reference the .NET (B03, B04) and Python (B02) implementations must match;
golden vectors: fixtures/c16/v2_1/digests/golden.json.

All text is UTF-8. "Sorted" means ordinal / code-point order (Python default; .NET StringComparer.Ordinal for
ASCII identifiers). Every hash is lower-case hex SHA-256.
"""
from __future__ import annotations

import hashlib

TEXT_STORE_DIGEST_FORMAT = "mimamsa-text-store-source/2.1"


def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def table_rows_digest(tables: list[tuple[str, int, str]]) -> str:
    """KNOWLEDGE_ROWS (and the per-table part of GRAPH): sha256 over one line per table, tables sorted by name,
    each line `<table>|<row_count>|<rows_sha256>` terminated by LF (including the last line). B03's form."""
    return _h("".join(f"{t}|{n}|{s}\n" for t, n, s in sorted(tables)).encode("utf-8"))


def graph_digest(builder_version: str, node_ids: list[str], edge_ids: list[str]) -> str:
    """GRAPH result_digest = GraphStore.Digest exactly: sha256 of
    `<builder_version>|<node ids sorted, comma-joined>|<edge ids sorted, comma-joined>` (no trailing LF). The ids are
    the `id` columns of graph_nodes.jsonl and graph_edges.jsonl; builder_version is the manifest's
    compatibility.graph_builder_version."""
    return _h(f"{builder_version}|{','.join(sorted(node_ids))}|{','.join(sorted(edge_ids))}".encode("utf-8"))


def file_digest(data: bytes) -> str:
    """LEXICAL_INDEX (search.sqlite) and TEXT_STORE (text.sqlite) result_digest: sha256 of the store file's exact
    bytes, equal to the `sha256` its MANIFEST.json records (ADR-0007, ADR-0008)."""
    return _h(data)


def vector_pack_digest(entries: list[tuple[bytes, bytes]]) -> str:
    """VECTOR_PACK result_digest: sha256 over the concatenation, sorted by key bytes ascending, of
    key (16 bytes, little-endian UInt128 as stored in MIMVEC01) + vector (dim x float32 little-endian). Independent
    of the store file's entry order and trailer."""
    for k, v in entries:
        if len(k) != 16 or len(v) % 4:
            raise ValueError("key must be 16 bytes and vector a whole number of float32")
    return _h(b"".join(k + v for k, v in sorted(entries)))


def hashset_digest(hashes: list[str]) -> str:
    """ORIGINALS / TEXT_DERIVATIVES (arch §5, frozen; bytes fixed here): sha256 of the sorted hashes joined by LF,
    no trailing LF."""
    return _h("\n".join(sorted(hashes)).encode("ascii"))


def concat_digest(files: dict[str, bytes]) -> str:
    """RECORDS and registers (arch §5, frozen; order fixed here): sha256 of the files' bytes concatenated in path
    order (UTF-8 byte order of the paths)."""
    return _h(b"".join(files[p] for p in sorted(files, key=lambda x: x.encode("utf-8"))))


def text_store_source_digest(generation_id: str, documents: list[dict], derived: list[dict]) -> str:
    """Bundle-independent TEXT_STORE source digest (replaces, for prebuilt-store adoption, the ADR-0008 digest that
    hashes generation.json, which records the bundle's own SHA256SUMS digest and so can never match centrally).

    Inputs are the generation's servable documents (doc_id, copy sha256) and their verified derived_text records
    (v1 schema). Lines (UTF-8, each LF-terminated), in this order:
      mimamsa-text-store-source/2.1
      G\t<generation_id>
      D\t<doc_id>\t<copy_sha256>                                   per document, sorted by doc_id
      T\t<doc_id>\t<source_copy_sha256>\t<pipeline_name>/<pipeline_version>\t<text_sha256>\t<quoting 0|1>
          per derivative (its id is (source_copy_sha256, pipeline)), sorted by (doc_id, pipeline name, pipeline version)
      P\t<doc_id>\t<page>\t<method>\t<char_count>\t<low_confidence 0|1>\t<page text_sha256 or ->
          per page; derivatives in T order, then page ascending
      Q\t<doc_id>\t<passage_id>\t<page>\t<char_start>\t<char_end>\t<paragraph_label or ->\t<text_sha256>
          per passage; derivatives in T order, then (page, char_start, passage_id)
    All P lines precede all Q lines. Integers are decimal without padding.
    It decides only whether a shipped store may be adopted or must be rebuilt: DiskTextStore.Bind re-derives every
    document from the records and source derivatives on every open whatever this digest says, so it does not weaken
    integrity."""
    lines = [TEXT_STORE_DIGEST_FORMAT, f"G\t{generation_id}"]
    for d in sorted(documents, key=lambda x: x["doc_id"]):
        lines.append(f"D\t{d['doc_id']}\t{d['copy_sha256']}")
    ders = sorted(derived, key=lambda t: (t["doc_id"], t["pipeline"]["name"], t["pipeline"]["version"]))
    for t in ders:
        lines.append(f"T\t{t['doc_id']}\t{t['source_copy_sha256']}\t{t['pipeline']['name']}/{t['pipeline']['version']}\t{t['text_sha256']}\t{1 if t['quoting_permitted'] else 0}")
    for t in ders:
        for p in sorted(t["pages"], key=lambda p: p["page"]):
            lines.append(f"P\t{t['doc_id']}\t{p['page']}\t{p['method']}\t{p['char_count']}\t{1 if p.get('low_confidence') else 0}\t{p.get('text_sha256') or '-'}")
    for t in ders:
        for q in sorted(t["passages"], key=lambda q: (q["page"], q["char_start"], q["passage_id"])):
            lines.append(f"Q\t{t['doc_id']}\t{q['passage_id']}\t{q['page']}\t{q['char_start']}\t{q['char_end']}\t{q.get('paragraph_label') or '-'}\t{q['text_sha256']}")
    return _h("".join(line + "\n" for line in lines).encode("utf-8"))
