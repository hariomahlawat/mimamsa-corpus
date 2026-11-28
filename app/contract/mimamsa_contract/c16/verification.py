"""B04 kind-specific verifier reference (contract 2.1 additive item 11; C16 Stage 3 S3-B).

Language-neutral parts of the accelerator checks that every implementation (the .NET site `Mimamsa.Core.Verification`,
the central build) must reproduce byte for byte. Golden vectors: fixtures/c16/v2_1/component_verification/golden.json
(`make_verification_golden.py`), reproduced by the .NET tests.

1. Deterministic seeded samples (B04 section 1 "Samples": "every sample is deterministic and seeded by the release id").
   A member is a string identity (doc_id, passage_id, term, key hex). Its score is
       sha256("mimamsa-b04-sample/2.1|<release_id>|<check_id>|<member>")   (UTF-8)
   `seeded_sample` keeps the `size` members with the smallest (score bytes, member); `stratified_sample` takes members
   round-robin over the strata in ordinal name order, each stratum in ascending (score, member) order. Both return the
   selection in ordinal order. Sizes are inputs: this module never chooses one (FG-CALIBRATED-SAMPLES).
2. Vector packs (MIMVEC01, VectorStore): the trailer check, the key rule, the 2.1 bundle-independent source digest
   (`vector_pack_source_digest`), the params sidecar and the spot comparison metric.
3. GRAPH structural recheck over the shipped rows (endpoints exist, evidence resolves to a verified page of a served
   document, builder-only verification values, known vocabularies, unique ids) and the GRAPH_DIGEST recomputation.
4. Effective sample selection: a contract check with an UNCALIBRATED size or tolerance is never run in production (the
   activation outcome refuses first: OD-C16-UNCALIBRATED-PRODUCTION); in development it runs with a declared development
   default that is recorded as such in the evidence, never written into a contract.
"""
from __future__ import annotations

import hashlib
import math
import struct

from . import digests

SAMPLE_FORMAT = "mimamsa-b04-sample/2.1"
VECTOR_SOURCE_FORMAT = "mimamsa-vector-pack-source/2.1"
VECTOR_PARAMS_FORMAT = "mimamsa-vector-pack-params/2.1"
MIMVEC_MAGIC = b"MIMVEC01"

# The development defaults are NOT calibrated values. They are what development mode runs while the contract says
# UNCALIBRATED, are recorded as `size_source: UNCALIBRATED_DEVELOPMENT_DEFAULT` in every evidence record, and are
# never written into a contract. The calibration study (app/b1/evidence/c16_s3b/CALIBRATION_STUDY.md) proposes values
# for the owner; until OD-12 / FG-CALIBRATED-SAMPLES accepts them, production refuses.
DEVELOPMENT_DEFAULTS = {
    "SAMPLED_REBUILD_PARITY": {"size": 64, "tolerance": "EXACT"},
    "SAMPLED_POSTINGS_REDERIVE": {"size": 64, "tolerance": "EXACT"},
    "SAMPLED_QUERY_PARITY": {"size": 32, "tolerance": "EXACT"},
    "VECTOR_SPOT_REEMBED": {"size": 32, "tolerance": 1e-4},
}

GRAPH_NODE_KINDS = ("instrument", "provision", "provision_version", "judgment", "unresolved_reference",
                    "procedural_requirement", "form", "competent_authority")
GRAPH_EDGE_TYPES = ("CONTAINS_PROVISION", "VERSION_OF", "AMENDS_PROVISION_VERSION", "OMITS_PROVISION",
                    "SUBSTITUTES_PROVISION_TEXT", "INSERTS_PROVISION", "REPEALS_PROVISION", "COMMENCES",
                    "REPEALS_INSTRUMENT", "SAVES_OR_TRANSITIONS", "RE_ENACTED_AS", "CITES_PROVISION",
                    "QUOTES_PROVISION", "CITES_JUDGMENT", "FOLLOWS_PROPOSITION", "OVERRULES_OR_LIMITS_PROPOSITION",
                    "PROCEDURE_REFERENCES_PROVISION", "COMPETENT_AUTHORITY_FOR", "PRESCRIBES_OR_EXEMPLIFIES_FORM")
GRAPH_BUILDER_VERIFICATION = ("CANDIDATE", "EXTRACTED_STRUCTURE", "CURATED_NAVIGATION")
GRAPH_REVIEW_STATE = "UNREVIEWED"


# ----------------------------------------------------------------------------------------------- 1. samples

def sample_score(release_id: str, check_id: str, member: str) -> bytes:
    return hashlib.sha256(f"{SAMPLE_FORMAT}|{release_id}|{check_id}|{member}".encode("utf-8")).digest()


def _ordered(release_id: str, check_id: str, members) -> list[str]:
    return sorted(set(members), key=lambda m: (sample_score(release_id, check_id, m), m))


def seeded_sample(release_id: str, check_id: str, members, size: int) -> list[str]:
    if not isinstance(size, int) or size < 1:
        raise ValueError("sample size must be a positive integer")
    return sorted(_ordered(release_id, check_id, members)[:size])


def stratified_sample(release_id: str, check_id: str, strata: dict, size: int) -> list[str]:
    if not isinstance(size, int) or size < 1:
        raise ValueError("sample size must be a positive integer")
    seen: set[str] = set()
    for name in strata:
        overlap = seen & set(strata[name])
        if overlap:
            raise ValueError(f"strata overlap: {sorted(overlap)[0]}")
        seen |= set(strata[name])
    queues = [_ordered(release_id, check_id, strata[n]) for n in sorted(strata)]
    out: list[str] = []
    depth = 0
    while len(out) < size and any(depth < len(q) for q in queues):
        for q in queues:
            if depth < len(q) and len(out) < size:
                out.append(q[depth])
        depth += 1
    return sorted(out)


def effective_sample(check: dict, mode: str) -> dict:
    """What a sampled check runs with: {size, tolerance, size_source}. A calibrated contract value wins; UNCALIBRATED
    runs only in development, with the declared development default (recorded); production refuses (raises)."""
    s = check["sample"]
    if s["selection"] == "FULL":
        return {"size": "ALL", "tolerance": s["tolerance"], "size_source": "FULL"}
    if s["size"] != "UNCALIBRATED" and s["tolerance"] != "UNCALIBRATED":
        tol = s["tolerance"] if s["tolerance"] == "EXACT" else s["tolerance"]["value"]
        return {"size": s["size"]["value"], "tolerance": tol, "size_source": "CONTRACT_CALIBRATED"}
    if mode != "development":
        raise PermissionError("UNCALIBRATED_IN_PRODUCTION: an uncalibrated sampled check is never run in production "
                              "(OD-C16-UNCALIBRATED-PRODUCTION open)")
    d = DEVELOPMENT_DEFAULTS[check["check_id"]]
    size = d["size"] if s["size"] == "UNCALIBRATED" else s["size"]["value"]
    tol = s["tolerance"] if s["tolerance"] != "UNCALIBRATED" else d["tolerance"]
    if isinstance(tol, dict):
        tol = tol["value"]
    return {"size": size, "tolerance": tol, "size_source": "UNCALIBRATED_DEVELOPMENT_DEFAULT"}


def detection_probability(population: int, corrupted: int, sample: int) -> float:
    """Probability that a uniform sample of `sample` members out of `population` contains at least one of `corrupted`
    members (hypergeometric; the exact, EXACT-tolerance checks detect any sampled corruption)."""
    if corrupted <= 0:
        return 0.0
    sample = min(sample, population)
    if population - corrupted < sample:
        return 1.0
    return 1.0 - math.comb(population - corrupted, sample) / math.comb(population, sample)


# ----------------------------------------------------------------------------------------------- 2. vector packs

def vector_key(model_sha256: str, max_tokens: int, embedding_input: str) -> bytes:
    """VectorStore.Key: the first 16 bytes of sha256("<model sha>|<max tokens>|<input>"); stored as-is in MIMVEC01
    (little-endian UInt128 of those bytes). `embedding_input` includes the passage prefix ("passage: ...")."""
    return hashlib.sha256(f"{model_sha256}|{max_tokens}|{embedding_input}".encode("utf-8")).digest()[:16]


def write_mimvec(dim: int, entries: list[tuple[bytes, bytes]]) -> bytes:
    """MIMVEC01 bytes with entries in ascending key-byte order (the central build's canonical file order)."""
    body = MIMVEC_MAGIC + struct.pack("<iq", dim, len(entries)) + b"".join(k + v for k, v in sorted(entries))
    return body + hashlib.sha256(body).digest()


def read_mimvec(data: bytes) -> tuple[int | None, list[tuple[bytes, bytes]], list[str]]:
    """(dim, entries, issues). Any issue means VECTOR_TRAILER fails; entries are only returned for a valid file."""
    head = 8 + 4 + 8
    if len(data) < head + 32 or data[:8] != MIMVEC_MAGIC:
        return None, [], ["not a MIMVEC01 vector store"]
    body = data[:-32]
    if hashlib.sha256(body).digest() != data[-32:]:
        return None, [], ["SHA-256 trailer does not verify"]
    dim, n = struct.unpack_from("<iq", data, 8)
    rec = 16 + 4 * dim
    if dim <= 0 or n < 0 or head + n * rec != len(body):
        return None, [], [f"shape mismatch (dim {dim}, count {n})"]
    entries = [(body[head + i * rec: head + i * rec + 16], body[head + i * rec + 16: head + (i + 1) * rec]) for i in range(n)]
    if len({k for k, _ in entries}) != n:
        return None, [], ["duplicate key in the vector store"]
    return dim, entries, []


def vector_pack_source_digest(model_sha256: str, max_tokens: int, keys) -> str:
    """2.1 SOURCE_DIGEST_EQUALS_SITE for VECTOR_PACK ("recompute the sorted key set"): sha256 of LF-terminated lines
         mimamsa-vector-pack-source/2.1
         M\t<model sha256>
         T\t<max tokens>
         K\t<key hex>          per distinct key, ascending key bytes
    over the keys recomputed from the generation's indexed passages. Bundle-independent (no file bytes)."""
    lines = [VECTOR_SOURCE_FORMAT, f"M\t{model_sha256}", f"T\t{max_tokens}"]
    lines += [f"K\t{k.hex()}" for k in sorted(set(keys))]
    return hashlib.sha256("".join(x + "\n" for x in lines).encode("ascii")).hexdigest()


def vector_params(model_sha256: str, dim: int, max_tokens: int, passage_prefix: str = "passage: ",
                  query_prefix: str = "query: ") -> dict:
    """The params sidecar shipped with a pack (accelerators/vectors/<model sha>.params.json): everything the key rule and
    a spot re-embed need, bound by the signed inventory."""
    return {"format": VECTOR_PARAMS_FORMAT, "model_sha256": model_sha256, "dim": dim, "max_tokens": max_tokens,
            "passage_prefix": passage_prefix, "query_prefix": query_prefix, "pooling": "mean", "normalised": True}


def vector_difference(a: bytes, b: bytes) -> tuple[float, float]:
    """(max absolute component difference, cosine) of two float32 LE vectors. VECTOR_SPOT_REEMBED passes when the max
    absolute difference is within the tolerance."""
    n = len(a) // 4
    if len(a) != len(b) or n == 0:
        return math.inf, 0.0
    x, y = struct.unpack(f"<{n}f", a), struct.unpack(f"<{n}f", b)
    dot = sum(p * q for p, q in zip(x, y))
    na, nb = math.sqrt(sum(p * p for p in x)), math.sqrt(sum(q * q for q in y))
    return max(abs(p - q) for p, q in zip(x, y)), (dot / (na * nb) if na and nb else 0.0)


def check_vector_pack(data: bytes, params: dict, passage_ids_and_inputs: list[tuple[str, str]], *, release_id: str,
                      declared_result_digest: str, declared_source_digest: str, model_sha256: str,
                      sample_size: int, tolerance: float, embed=None) -> dict:
    """Reference VECTOR_PACK verification. `passage_ids_and_inputs`: (passage_id, embedding input incl. prefix) for every
    indexed passage of the generation. `embed(input) -> float32 LE bytes` re-embeds ONE sampled input per call (never the
    corpus); None marks VECTOR_SPOT_REEMBED NOT_RUN (and the pack is then not VERIFIED)."""
    checks, issues = {}, []
    dim, entries, why = read_mimvec(data)
    checks["VECTOR_TRAILER"] = "FAIL" if why else "PASS"
    issues += why
    if params.get("format") != VECTOR_PARAMS_FORMAT or params.get("model_sha256") != model_sha256 or (dim is not None and params.get("dim") != dim):
        issues.append("vector params do not match the pinned model or the pack")
        checks["VECTOR_KEYS_RECOMPUTED"] = "FAIL"
    keys = {}
    for pid, inp in passage_ids_and_inputs:
        keys.setdefault(vector_key(model_sha256, params["max_tokens"], inp), (pid, inp))
    if not why and "VECTOR_KEYS_RECOMPUTED" not in checks:
        stored = {k for k, _ in entries}
        foreign, missing = stored - set(keys), set(keys) - stored
        checks["VECTOR_KEYS_RECOMPUTED"] = "PASS" if not foreign and not missing else "FAIL"
        if foreign:
            issues.append(f"{len(foreign)} vector keys belong to no verified passage of this generation and model")
        if missing:
            issues.append(f"{len(missing)} indexed passages have no vector")
    elif "VECTOR_KEYS_RECOMPUTED" not in checks:
        checks["VECTOR_KEYS_RECOMPUTED"] = "FAIL"
    src = vector_pack_source_digest(model_sha256, params["max_tokens"], keys)
    checks["SOURCE_DIGEST_EQUALS_SITE"] = "PASS" if src == declared_source_digest else "FAIL"
    checks["RESULT_DIGEST"] = "PASS" if not why and digests.vector_pack_digest(entries) == declared_result_digest else "FAIL"
    worst = None
    if embed is None or why:
        checks["VECTOR_SPOT_REEMBED"] = "NOT_RUN"
    else:
        by_key = dict(entries)
        strata: dict[str, list[str]] = {}
        for k in keys:
            if k in by_key:
                strata.setdefault(f"len{min(len(keys[k][1].encode('utf-8')) // 512, 7)}", []).append(k.hex())
        chosen = stratified_sample(release_id, "VECTOR_SPOT_REEMBED", strata, sample_size) if strata else []
        ok = bool(chosen)
        for kh in chosen:
            d, _ = vector_difference(by_key[bytes.fromhex(kh)], embed(keys[bytes.fromhex(kh)][1]))
            worst = d if worst is None else max(worst, d)
            ok = ok and d <= tolerance
        checks["VECTOR_SPOT_REEMBED"] = "PASS" if ok else "FAIL"
        if not ok:
            issues.append("a sampled vector differs from a fresh embedding beyond the tolerance")
    status = "VERIFIED" if all(v == "PASS" for v in checks.values()) else "FAILED"
    return {"kind": "VECTOR_PACK", "status": status, "checks": checks, "issues": issues, "max_abs_difference": worst,
            "keys": len(keys), "source_digest": src}


# ----------------------------------------------------------------------------------------------- 3. graph

def graph_structural_issues(nodes: list[dict], edges: list[dict], documents: dict) -> list[str]:
    """GRAPH_STRUCTURAL_RECHECK over the shipped rows (KNOWLEDGE_ROWS_SCHEMA graph_nodes_row / graph_edges_row).
    `documents`: doc_id -> set of verified page numbers of the generation's served documents.
    The issue strings are part of the reference (the .NET mirror emits the same codes before the colon)."""
    out = []
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        out.append("GRAPH_DUPLICATE_NODE: node ids are not unique")
    node_ids = set(ids)
    eids = [e["id"] for e in edges]
    if len(set(eids)) != len(eids):
        out.append("GRAPH_DUPLICATE_EDGE: edge ids are not unique")
    for n in nodes:
        if n["kind"] not in GRAPH_NODE_KINDS:
            out.append(f"GRAPH_UNKNOWN_KIND: {n['id']}")
        if n["doc_id"] is not None:
            if n["doc_id"] not in documents:
                out.append(f"GRAPH_NODE_DOC_UNRESOLVED: {n['id']}")
            elif n["page"] is not None and n["page"] not in documents[n["doc_id"]]:
                out.append(f"GRAPH_NODE_PAGE_UNRESOLVED: {n['id']}")
        elif n["held"] and n["kind"] not in ("procedural_requirement",):
            out.append(f"GRAPH_HELD_NODE_WITHOUT_DOCUMENT: {n['id']}")
    for e in edges:
        if e["type"] not in GRAPH_EDGE_TYPES:
            out.append(f"GRAPH_UNKNOWN_TYPE: {e['id']}")
        if e["from_id"] not in node_ids or e["to_id"] not in node_ids:
            out.append(f"GRAPH_DANGLING_EDGE: {e['id']}")
        if e["verification"] not in GRAPH_BUILDER_VERIFICATION or e["review_state"] != GRAPH_REVIEW_STATE:
            out.append(f"GRAPH_NOT_BUILDER_VALUE: {e['id']}")
        if e["source_doc_id"] is not None:
            if e["source_doc_id"] not in documents:
                out.append(f"GRAPH_EVIDENCE_DOC_UNRESOLVED: {e['id']}")
            elif e["page"] is not None and e["page"] not in documents[e["source_doc_id"]]:
                out.append(f"GRAPH_EVIDENCE_PAGE_UNRESOLVED: {e['id']}")
    return out


def graph_digest_of_rows(builder_version: str, nodes: list[dict], edges: list[dict]) -> str:
    return digests.graph_digest(builder_version, [n["id"] for n in nodes], [e["id"] for e in edges])
