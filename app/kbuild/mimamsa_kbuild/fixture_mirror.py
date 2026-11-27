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


def cp1_exchange(repo: str, revision: str):
    """The CP-1 vertical-slice exchange (contract 2.1, real bytes): the B01 synthetic producer exchange
    (app/importer/c16_cases.py), with its receipts bound to the committed restricted-material register and its G01
    source pointing at this mirror. A (eligible, nine typed receipts) also gets a v1 record pinned to the mirror, so an
    admitted copy is served end to end; B (held) and E (eligible, DOCX, C16 only) have no v1 record and are never served.
    Returns (exchange files, receipt artefacts, extra v1 documents, extra v1 derivatives, {sha: original}, {text path: bytes})."""
    import sys
    for p in (REPO / "app" / "importer", REPO / "app" / "contract"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import c16_cases as cc  # noqa: E402  (the B01 synthetic producer, unchanged)
    from mimamsa_contract.restricted import register_from_bytes
    reg_path = REPO / "config" / "restricted_material.json"
    cc.REGISTER = register_from_bytes(reg_path.read_bytes(), "config/restricted_material.json")
    cp = cc.Corpus()

    def point_g01_at_mirror(key, arts):
        a = arts["G01_HASH_VERIFIED"]
        a["payload"]["source"] = {"hf_repo": repo, "hf_revision": revision,
                                  "path": f"v1/originals/{a['subject']['source_copy_sha256']}.pdf"}
    files, arts, _ids, _adms = cc.exchange(cp, mutate_arts=point_g01_at_mirror)
    doc = cc.v1_doc(cp.a, cc.DOC_A, pages=2)
    sha = cc.h(cp.a)
    doc["provenance"]["hf"] = {"repo": repo, "revision": revision, "path": f"v1/originals/{sha}.pdf"}
    text_path = f"text/{cc.DOC_A}.txt"
    der = cc.v1_derived(cc.DOC_A, sha, cp.a_text, text_path, cp.a_pages)
    return files, arts, [doc], [der], {sha: cp.a}, {text_path: cp.a_text}


def prepare(mirror: Path, *, repo: str = CP1_REPO, revision: str = CP1_REVISION, exchange: str = "positive") -> Path:
    """exchange: "positive" (the strict contract 2.0 positive exchange; the CP-1 fixture spec pins it), "v2_1" (the 2.1
    exchange with typed receipts, whose G03 receipt is bound to a fixture register revision, so it does not resolve
    against the real register: the item stays unserved) or "cp1" (the CP-1 vertical-slice exchange: `cp1_exchange`)."""
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
    if exchange == "cp1":
        cp1_files, cp1_arts, extra_docs, extra_ders, extra_orig, extra_text = cp1_exchange(repo, revision)
        for d in extra_docs:
            recs[d["doc_id"]] = d
        ders += extra_ders
        for h, b in extra_orig.items():
            write_bytes(root / "v1" / "originals" / f"{h}.pdf", b)
        for p, b in extra_text.items():
            write_bytes(root / "v1" / p, b)
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
    elif exchange == "cp1":
        for name, b in sorted(cp1_files.items()):
            write_bytes(root / EXCHANGE_PATH / name, b)
        for p, b in sorted(cp1_arts.items()):
            write_bytes(root / EXCHANGE_PATH / p, b)
    else:
        raise ValueError("exchange must be 'positive', 'v2_1' or 'cp1'")
    return root


GENERATION_SHA256 = {"positive": "3a24aacf1e99bbbcb0fcf314c5375e9ff50a75f0e0775c0c3b345dcabd2c7834",
                     "v2_1": "8ce553cc69bdbebe7b8fea594318830bc104b4d095dbeed34d54cf408cbe79a3",
                     "cp1": "70ea18de2a2f209f59124aaf084512e1db18b2e498bd06c7f1b8cc83841332c5"}
