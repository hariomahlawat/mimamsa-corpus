"""CP-1 fixture sources as an offline mirror of the pinned Hugging Face revision (no network, no HF).

The mirror stands in for the canonical dataset at one pinned revision, laid out as
    <mirror>/<owner>/<repo>/<revision>/
        v1/data/documents.jsonl | derived_text.jsonl | candidates.jsonl     v1-path canonical records (B02 Stage 2 form)
        v1/originals/<sha256>.pdf                                           original bytes
        v1/text/<doc_id>.txt                                                [[page N]] derivatives
        v1/research/a4_provision_versions.jsonl                             research aid
        exchanges/fixture/GENERATION.json, *.jsonl                          the strict positive producer exchange (contract fixture)
        exchanges/fixture/registers/receipts/<sha256>.json                  typed receipt artefacts (2.1 variant only)
Sources: the SYN retrieval fixture (docs/architecture/reviews/c13-assurance/retrieval-dev-fixture.json, read-only),
rendered by the same code as app/b1/build/build_fixture_site.py, and app/contract/fixtures/c16/positive/ (or v2_1/).
Everything is synthetic and fictional. The output is a pure function of those committed files (deterministic).

Stage 2 deviation (recorded): the real canonical dataset stores data/meta/<doc_id>.json and raw files; converting that
layout into v1 records (app/b1/build/build_sample.py) is Stage 3 work. Here the v1 records are prepared directly.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import REPO
from .fsutil import rmtree, write_bytes

CP1_REPO = "owner/fixture-corpus"
CP1_REVISION = "008d447011808d3d3f9095b0dbf14125002d1642"
EXCHANGE_PATH = "exchanges/fixture"
V2_1 = REPO / "app" / "contract" / "fixtures" / "c16" / "v2_1"
POSITIVE = REPO / "app" / "contract" / "fixtures" / "c16" / "positive"


def _jsonl(records) -> bytes:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records).encode("utf-8")


def revision_root(mirror: Path, repo: str, revision: str) -> Path:
    owner, name = repo.split("/", 1)
    return Path(mirror) / owner / name / revision


def prepare(mirror: Path, *, repo: str = CP1_REPO, revision: str = CP1_REVISION, exchange: str = "positive") -> Path:
    """exchange: "positive" (the strict contract 2.0 positive exchange; the CP-1 spec pins it) or "v2_1" (the 2.1
    exchange with typed receipts, whose G03 receipt is bound to a fixture register revision, so it does not resolve
    against the real register: the item stays unserved)."""
    import sys
    sys.path.insert(0, str(REPO / "app" / "b1" / "build"))
    import build_fixture_site as syn  # noqa: E402  (reuse the SYN renderer, unchanged)

    root = revision_root(mirror, repo, revision)
    rmtree(root)
    fixture = json.loads(syn.FIXTURE.read_text(encoding="utf-8"))
    recs, ders, maps = {}, [], {}
    for doc in fixture["documents"]:
        rec, der, orig, tb, mp = syn.build_doc(doc)
        h = rec["source_copy"]["sha256"]
        rec["provenance"]["hf"] = {"repo": repo, "revision": revision, "path": f"v1/originals/{h}.pdf"}
        recs[doc["id"]] = rec
        ders.append(der)
        maps.update(mp)
        write_bytes(root / "v1" / "originals" / f"{h}.pdf", orig)
        write_bytes(root / "v1" / der["text_path"], tb)
    cands = syn.candidates({d["id"]: d for d in fixture["documents"]}, recs, maps)
    a4 = {"version_id": "SYN/s.17/v01", "family": "SYN", "provision": "s.17", "version_kind": "as_enacted",
          "change_summary": "Synthetic version record (not a real provision)", "determination_state": "AUTOMATED_CANDIDATE_NOT_VERIFIED",
          "effective_from": {"status": "NOT_STATED_PENDING_ADVICE", "date": None, "reported_date": None},
          "effective_to": {"status": "OPEN_ON_LOCATED_INSTRUMENTS"}, "currency": {"status": "NOT_ESTABLISHED"},
          "text_evidence": [{"role": "synthetic_primary", "sha256": recs["S-ACT"]["source_copy"]["sha256"], "pdf_page": "2", "edition": "synthetic act"},
                            {"role": "synthetic_secondary", "sha256": recs["V-OTHER"]["source_copy"]["sha256"], "pdf_page": "1", "edition": "unrelated synthetic book"}]}
    docs = sorted(recs.values(), key=lambda r: r["doc_id"])
    write_bytes(root / "v1" / "data" / "documents.jsonl", _jsonl(docs))
    write_bytes(root / "v1" / "data" / "derived_text.jsonl", _jsonl(sorted(ders, key=lambda r: r["doc_id"])))
    write_bytes(root / "v1" / "data" / "candidates.jsonl", _jsonl(cands))
    write_bytes(root / "v1" / "research" / "a4_provision_versions.jsonl", _jsonl([a4]))
    if exchange == "positive":
        for p in sorted((POSITIVE / "exchange").iterdir()):
            write_bytes(root / EXCHANGE_PATH / p.name, p.read_bytes())
    elif exchange == "v2_1":
        for p in sorted((V2_1 / "exchange").iterdir()):
            write_bytes(root / EXCHANGE_PATH / p.name, p.read_bytes())
        for p in sorted((V2_1 / "registers" / "receipts").iterdir()):
            write_bytes(root / EXCHANGE_PATH / "registers" / "receipts" / p.name, p.read_bytes())
    else:
        raise ValueError("exchange must be 'positive' or 'v2_1'")
    return root


GENERATION_SHA256 = {"positive": "3a24aacf1e99bbbcb0fcf314c5375e9ff50a75f0e0775c0c3b345dcabd2c7834",
                     "v2_1": "8ce553cc69bdbebe7b8fea594318830bc104b4d095dbeed34d54cf408cbe79a3"}
