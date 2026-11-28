"""More than one producer generation in one build (B02 Stage 3; SG-1 "in this or any retained generation").

A release carries ONE strict exchange under `corpus-v2/` (what B01 imports), and contract 2.0/2.1 binds every
identity, admission and receipt to its own GENERATION.json `corpus_generation_id` (rules.py: identity and admission
generation must equal the manifest's). A build-side merge of two producer exchanges would therefore NOT be
contract-valid; a composite generation (decision Q8) is the PRODUCER's to publish. The spec may pin any number of
producer generations, read as a succession:
- 0: a v1-only release (plus V7_REFERENCE candidate sets); nothing under `corpus-v2/`.
- 1: that generation ships byte for byte (Stage 2 behaviour, unchanged).
- 2 or more, in spec order (oldest first): every one is fetched at its pin and validated strictly (S2); the LAST is
  the current generation and ships; the earlier ones are retained governance inputs:
    * SG-1 across generations: the v1 relabel check sees the identities and admissions of EVERY pinned generation,
      so a copy any of them governs without an eligible effective admission is never served on the v1 path;
    * holds are never lifted by omission: a (doc_id, sha256) that an earlier generation governs with a held, rejected
      or otherwise not-eligible effective admission must still be governed (have an identity) in the current
      generation, or the build refuses (BUILD_GENERATION_HOLD_DROPPED). A newer decision is the producer's to make,
      through its own admissions; the build never decides it;
    * the per-source accounting declares the current generation (exactly what the site recomputes from corpus-v2/);
      every pinned generation is listed in the release manifest's `corpus_generations`.
"""
from __future__ import annotations

import json

from .errors import BuildRefused


def _jsonl(data: bytes) -> list[dict]:
    return [json.loads(x) for x in data.decode("utf-8").split("\n") if x.strip()]


def population(exchange: dict[str, bytes]) -> dict[str, list[dict]]:
    pop: dict[str, list[dict]] = {}
    for name, data in exchange.items():
        if name.endswith(".jsonl"):
            pop.setdefault(name.split(".", 1)[0], []).extend(_jsonl(data))
    return pop


def effective(adms: list[dict]) -> dict[tuple[str, str], dict]:
    superseded = {a.get("supersedes_admission_id") for a in adms}
    return {(a["subject"]["doc_id"], a["subject"]["source_copy_sha256"]): a for a in adms if a["admission_id"] not in superseded}


def succession_issues(members: list[dict]) -> list[dict]:
    """members: [{"pin": spec entry, "exchange": {name: bytes}}] in spec order (oldest first). Checks the pins name the
    manifests' own generation ids and that no earlier non-eligible decision is dropped by the current generation."""
    out = []
    for m in members:
        gid = json.loads(m["exchange"]["GENERATION.json"])["corpus_generation_id"]
        if gid != m["pin"]["corpus_generation_id"]:
            out.append({"code": "BUILD_PIN_MISMATCH", "message": "a pinned corpus_generation_id is not its GENERATION.json's",
                        "generation": m["pin"]["corpus_generation_id"]})
    if len(members) < 2 or out:
        return out
    current = population(members[-1]["exchange"])
    governed_now = {(i["doc_id"], i["source_copy"]["sha256"]) for i in current.get("identities", [])}
    for m in members[:-1]:
        pop = population(m["exchange"])
        for key, a in sorted(effective(pop.get("admissions", [])).items()):
            if a.get("application_eligible") is True:
                continue
            if key not in governed_now:
                out.append({"code": "BUILD_GENERATION_HOLD_DROPPED",
                            "message": "an earlier generation's held/rejected/not-eligible copy is not governed by the current generation "
                                       "(a hold is never lifted by omission)", "generation": m["pin"]["corpus_generation_id"],
                            "doc_id": key[0]})
    return out


def governance(members: list[dict]) -> tuple[list[dict], list[dict]]:
    """(identities, admissions) of EVERY pinned generation, for the SG-1 relabel check."""
    idents, adms = [], []
    for m in members:
        pop = population(m["exchange"])
        idents += pop.get("identities", [])
        adms += pop.get("admissions", [])
    return idents, adms


def require_succession(members: list[dict]) -> None:
    issues = succession_issues(members)
    if issues:
        raise BuildRefused(issues[0]["code"], issues[0]["message"], "S2", issues)
