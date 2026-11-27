"""Canonical serialisation and deterministic identifiers for mimamsa-corpus-contract/2.0 (contract section 9).

Canonical JSON:
- UTF-8, no BOM; object keys sorted by Unicode code point (all keys are ASCII, so this equals RFC 8785 order);
- separators "," and ":" with no whitespace; non-ASCII characters written as themselves (ensure_ascii=False);
- every string already in Unicode NFC (records with non-NFC strings are rejected, never silently normalised);
- numbers: integers in the IEEE-754 safe range; a float only where the schema allows a number, finite, not -0.0,
  at most 4 decimal places, and written as an integer when it is integral (12.0 -> 12). No exponent form occurs.
JSONL: one canonical record per line, LF line ends, a final LF, one record kind per file, records sorted by the
kind's sort key (SORT_KEYS), no duplicate sort keys.
"""
from __future__ import annotations

import hashlib
import json
import math
import unicodedata

MAX_SAFE_INT = 2**53 - 1


class CanonicalError(ValueError):
    pass


def _check(value, path="$"):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise CanonicalError(f"{path}: string is not NFC")
        return value
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INT:
            raise CanonicalError(f"{path}: integer outside the safe range")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalError(f"{path}: non-finite number")
        if value == 0 and math.copysign(1.0, value) < 0:
            raise CanonicalError(f"{path}: negative zero")
        if value.is_integer():
            return _check(int(value), path)
        if round(value, 4) != value:
            raise CanonicalError(f"{path}: more than 4 decimal places")
        if abs(value) >= 1e15:
            raise CanonicalError(f"{path}: float magnitude too large")
        return value
    if isinstance(value, list):
        return [_check(v, f"{path}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalError(f"{path}: non-string key")
            _check(k, path)
            out[k] = _check(v, f"{path}.{k}")
        return out
    raise CanonicalError(f"{path}: unsupported type {type(value).__name__}")


def canonical_bytes(obj) -> bytes:
    return json.dumps(_check(obj), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def record_sha256(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def stable_id(prefix: str, identity_tuple) -> str:
    """<prefix>-<first 24 hex of sha256(canonical JSON of [prefix, *identity_tuple])>."""
    if prefix not in ("REL", "ANC", "ADM"):
        raise CanonicalError("unknown id prefix")
    return f"{prefix}-{hashlib.sha256(canonical_bytes([prefix, *identity_tuple])).hexdigest()[:24]}"


# ---- identity tuples (contract section 9.2). Only identity-bearing fields: verification, quality, notes and
# timestamps are excluded so that a re-review or a new pipeline run that yields the same item keeps the id.

def relationship_identity(rel: dict) -> list:
    subj, tgt, cp = rel["subject"], rel["target"], rel.get("classification_provenance") or {}
    target = tgt.get("node_id") if tgt.get("resolved") else ["raw", tgt.get("raw_reference")]
    if rel["category"] == "legally_validated":
        discriminator = ["validates", rel.get("validates_relationship_id"), rel.get("approval_ref")]
    elif cp:
        discriminator = ["path", cp.get("collection"), cp.get("relative_path"), cp.get("path_component"), cp.get("matched_text")]
    else:
        discriminator = ["anchors", sorted(rel.get("anchors") or [])]
    return [rel["category"], subj["doc_id"], subj["source_copy_sha256"], subj.get("compilation_member_seq"),
            target, rel["evidentiary_basis"], rel["source"]["rule_id"], discriminator]


def anchor_identity(a: dict) -> list:
    loc = a["locator"]
    return [a["doc_id"], a["original_sha256"], a["representation_sha256"], a.get("derivative_text_sha256"),
            a.get("image_sha256"),
            [loc.get("kind"), loc.get("physical_page"), loc.get("reconstructed_page"), loc.get("generated_segment"),
             loc.get("image_sequence_id"), loc.get("paragraph_index")],
            (lambda s: None if not s else [s.get("char_start"), s.get("char_end"), s.get("text_sha256")])(a.get("text_span")),
            (lambda b: None if not b else [b.get("unit"), b.get("space"), b.get("x0"), b.get("y0"), b.get("x1"), b.get("y1")])(a.get("bbox"))]


def admission_identity(adm: dict) -> list:
    """Revision identity: a changed decision or gate result is a different id and must be a new revision that
    supersedes the previous one (append-only chain per generation and copy)."""
    return [adm["corpus_generation_id"], adm["subject"]["doc_id"], adm["subject"]["source_copy_sha256"],
            adm["revision"], adm.get("supersedes_admission_id"), adm["rule_set"]["id"], adm["rule_set"]["version"],
            adm["decision"], sorted([g["gate_id"], g["result"]] for g in adm["gates"])]


def relationship_id(rel: dict) -> str:
    return stable_id("REL", relationship_identity(rel))


def anchor_id(a: dict) -> str:
    return stable_id("ANC", anchor_identity(a))


def admission_id(adm: dict) -> str:
    return stable_id("ADM", admission_identity(adm))


# ---- JSONL

_LEVEL_RANK = {"SUBJECT": 0, "STATUTE": 1, "CHAPTER": 2, "PROVISION": 3}

SORT_KEYS = {
    "document_identity": lambda r: (r["doc_id"], r["source_copy"]["sha256"]),
    "evidence_anchor": lambda r: (r["anchor_id"],),
    "corpus_relationship": lambda r: (r["relationship_id"],),
    "taxonomy_node": lambda r: (_LEVEL_RANK.get(r["level"], 9), r["node_id"]),
    "corpus_admission": lambda r: (r["admission_id"],),
    "reviewed_record": lambda r: (r["review_record_id"],),
}


def dumps_jsonl(records: list[dict]) -> bytes:
    if not records:
        return b""
    kinds = {r.get("record_kind") for r in records}
    if len(kinds) != 1:
        raise CanonicalError("one record kind per JSONL file")
    key = SORT_KEYS[kinds.pop()]
    ordered = sorted(records, key=key)
    keys = [key(r) for r in ordered]
    if len(set(keys)) != len(keys):
        raise CanonicalError("duplicate sort key")
    return b"".join(canonical_bytes(r) + b"\n" for r in ordered)


def jsonl_problems(data: bytes) -> list[str]:
    """Why bytes are not a canonical C16 JSONL file (empty list when they are)."""
    problems = []
    if data.startswith(b"\xef\xbb\xbf"):
        return ["byte order mark"]
    if b"\r" in data:
        problems.append("CR in line ends")
    if data and not data.endswith(b"\n"):
        problems.append("missing final LF")
    try:
        records = [json.loads(line) for line in data.decode("utf-8").split("\n") if line != ""]
    except (UnicodeDecodeError, ValueError):
        return problems + ["not UTF-8 JSONL"]
    if not all(isinstance(r, dict) for r in records):
        return problems + ["a line is not a JSON object"]
    try:
        if dumps_jsonl(records) != data:
            problems.append("records not canonical or not in sort order")
    except (CanonicalError, KeyError) as exc:
        problems.append(str(exc))
    return problems
