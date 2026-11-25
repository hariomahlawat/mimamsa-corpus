"""PR #54 data-assurance cases (DA-01, DA-03, DA-04, DA-35) run through the real importer.

Fixture conditions mirror `docs/architecture/reviews/c13-assurance/data_oracle.py` and `data-fixtures.json` at
PR #54 (`pr54` = 703d98cb), which are NOT modified: the three fixture texts below are copied verbatim, and the
record shapes follow the oracle's document()/derived()/candidate() builders. Differences from the oracle are
deliberate and listed in RESULTS_DA.md (a real derived-text file is bundled, because the importer verifies it).

`python da_cases.py --observations out.json` writes adapter observations in the shape the PR #54 comparator
(`data_oracle.py --adapter-observations`) reads; only fields this importer can actually observe are emitted.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "contract")]

from mimamsa_contract.devbundle import new_dev_keypair, write_bundle  # noqa: E402
from mimamsa_contract.restricted import register_from_bytes  # noqa: E402
from mimamsa_importer import active_generation, configure_site, import_release, servable  # noqa: E402

# Verbatim from data-fixtures.json at pr54 703d98cb.
SOURCE = b"Fictional blue form. Two independent toy proceedings."
ALT = b"Fictional blue form. An alternate typesetting."
RAW_REFERENCE = "Unknown fictional authority ZZ-9"
A5 = "f915ac11494208a8ebad09f7910ea6cab6f21266"
NOW = "2090-01-01T00:00:00Z"
DOC_ID = "toy-blue-form-review"
REGISTER_TEXT = json.dumps({"items": [{
    "restriction_id": "RM-999", "source_sha256": sha256(b"fictional restricted marker only").hexdigest(),
    "doc_id": "toy-excluded-id", "hosted_paths": ["toy/excluded.txt"]}]})
REGISTER = register_from_bytes(REGISTER_TEXT.encode())
REPLACEMENT = b"Fictional green form. Supersession is only a claim."  # verbatim from data-fixtures.json


def h(b: bytes) -> str:
    return sha256(b).hexdigest()


def text_file(body: bytes) -> bytes:
    return b"[[page 1]]\n" + body + b"\n"


def document(data=SOURCE, doc_id=DOC_ID, mime="text/plain", page_count=1):
    axes = {a: {"value": v, "basis": "Synthetic fixture"} for a, v in {
        "source_integrity": "DECLARED_HASH_ONLY", "source_authenticity": "UNKNOWN",
        "evidence_fidelity": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "legal_applicability": "NOT_ESTABLISHED",
        "legal_approval": "T0_RESEARCH_ONLY", "publication": "STAGED", "dependency_freshness": "NOT_EVALUATED"}.items()}
    axes["source_authenticity"]["policy_v1"] = {"document_authority": "UNKNOWN", "carrier_provenance": "USER_SUPPLIED",
                                                "copy_fidelity": "HASH_ONLY", "amendment_chain_status": "NOT_CHECKED"}
    return {"contract_version": "1.0.0", "record_kind": "document", "doc_id": doc_id, "doc_type": "judgment",
            "title": "Fictional blue form", "number": None, "issuing_authority": None, "issue_date": None,
            "effective_date": None, "corpus_status": "unknown", "corpus_status_note": None, "text_method": "ocr",
            "ocr_confidence": 40.0,
            "source_copy": {"sha256": h(data), "bytes": len(data), "mime_type": mime,
                            "vault_path": f"vault/sha256/{h(data)[:2]}/{h(data)}", "page_count": page_count},
            "judicial": {"judgment_identity_id": "JUD:fictional-blue-form", "case_numbers": ["A", "B"]},
            "provenance": {"acquisition_channel": "RELEASE_IMPORT", "source_url": "https://fictional.invalid/blue.txt",
                           "retrieved_at": NOW, "hf": {"repo": "fictional/toy", "revision": "a" * 40, "path": "toy/blue.txt"},
                           "git": {"commit": A5, "path": "toy/producer.py"}},
            "status_axes": axes,
            "restriction": {"access_marking": None, "marking_page": None, "eligibility": "ELIGIBLE_ALL_USERS",
                            "restriction_id": None, "decided_by": None, "basis": None},
            "field_origin": {"title": "rule"}}


def derived(body=SOURCE, text_path="text/toy.txt"):
    return {"contract_version": "1.0.0", "record_kind": "derived_text", "doc_id": DOC_ID,
            "source_copy_sha256": h(SOURCE), "pipeline": {"name": "synthetic-extract", "version": "0.0.1"},
            "text_path": text_path, "text_sha256": h(text_file(body)), "page_marker": "[[page N]]",
            "quoting_permitted": False, "evidence_fidelity": "AUTOMATED_CANDIDATE_NOT_VERIFIED",
            "pages": [{"page": 1, "method": "ocr", "char_count": len(body), "low_confidence": True}],
            "passages": [{"passage_id": "p1-1", "page": 1, "char_start": 0, "char_end": len(body), "text_sha256": h(body)}]}


def candidate(bound=True):
    a = {"source_copy_sha256": h(SOURCE), "page": 1, "passage_id": "p1-1", "char_start": 0,
         "char_end": len(SOURCE), "text_sha256": h(SOURCE), "pipeline_version": "0.0.1"}
    if bound:
        a.update(pipeline_name="synthetic-extract", derivative_text_sha256=h(text_file(SOURCE)))
    return {"contract_version": "1.0.0", "record_kind": "candidate", "candidate_id": "toy:edge:001",
            "candidate_type": "graph_edge", "source_doc_id": DOC_ID, "anchors": [a],
            "extractor": {"name": "synthetic-extract", "version": "0.0.1", "artefact_commit": A5, "author_id": "toy-author"},
            "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "capability_restriction": "NON_OPERATIONAL_RESEARCH_ONLY",
            "evaluation_ref": None,
            "payload": {"relation": "CITES_JUDGMENT", "source_node": "JUD:fictional-blue-form",
                        "target": {"resolved": False, "node_id": None, "raw_reference": RAW_REFERENCE},
                        "confidence": "extracted", "has_legal_effect": False, "evidence_text": SOURCE.decode()}}


class Harness:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.key, self.pub = new_dev_keypair()  # disposable development key
        self.n = 0
        man = json.loads((HERE.parent / "contract" / "examples" / "release_manifest.example.json").read_text())
        man["restricted_material"].update(config_sha256=REGISTER.config_sha256, restriction_ids_applied=["RM-999"])
        self.manifest = man

    def bundle(self, *, docs=None, copies=None, derived_recs=None, texts=None, cands=(), flip=False, release=None,
               register_items=None):
        self.n += 1
        m = deepcopy(self.manifest)
        m["release_id"] = release or f"R13-asr-toy-20900101-{self.n:08x}"
        m["release_sequence"] = self.n
        docs = [document()] if docs is None else docs
        copies = [SOURCE] if copies is None else copies
        files = {f"originals/{h(c)}.bin": (c, "original") for c in copies}
        for path, body in (texts if texts is not None else {"text/toy.txt": text_file(SOURCE)}).items():
            files[path] = (body, "text")
        path = self.root / f"b{self.n}"
        write_bundle(path, m, documents=docs, derived=derived_recs if derived_recs is not None else [derived()],
                     candidates=list(cands), extra_files=files, signing_key=self.key, public_key_raw=self.pub)
        if flip:
            p = path / f"originals/{h(SOURCE)}.bin"
            p.write_bytes(SOURCE + b".")
        return path

    def run(self, bundle_path, site, register=REGISTER, rollback=False, channel="none"):
        # Synthetic sites are installed with an explicit exclusion-channel mode (fail-closed default is "signed").
        if channel and not (Path(site) / "SITE_CONFIG.json").exists():
            configure_site(site, exclusion_channel=channel)
        return import_release(bundle_path, site, trusted_public_key=self.pub, mode="development", register=register,
                              rollback=rollback)


def observations(root: Path) -> dict:
    hn = Harness(root)
    site = root / "site"
    obs = {}
    good = hn.run(hn.bundle(cands=[candidate()]), site)
    stored = (site / "vault" / "sha256" / h(SOURCE)[:2] / h(SOURCE))
    obs["DA-01"] = {"original_bytes_equal": stored.read_bytes() == SOURCE,
                    "sha256_equal": h(stored.read_bytes()) == document()["source_copy"]["sha256"],
                    "vault_key_matches": stored.relative_to(site).as_posix() == document()["source_copy"]["vault_path"]}
    before = (site / "ACTIVE").read_text()
    corrupt = hn.run(hn.bundle(flip=True), site)
    pdf_bad = hn.run(hn.bundle(docs=[document(b"%PDF-1.7 not really", mime="application/pdf")],
                               copies=[b"%PDF-1.7 not really"], derived_recs=[], texts={}), site)
    obs["DA-03"] = {"corrupt_rejected": not corrupt.activated and "CHECKSUM_MISMATCH" in corrupt.contract_errors,
                    "active_generation_unchanged": (site / "ACTIVE").read_text() == before,
                    "prior_original_unchanged": stored.read_bytes() == SOURCE,
                    "unopenable_source_rejected": not pdf_bad.activated}
    far = derived()
    far["passages"][0]["char_end"] = len(SOURCE) + 1
    r = hn.run(hn.bundle(derived_recs=[far]), root / "site-da04")
    # ocr_quote_enabled is not observed: no quotation surface exists yet (Not implemented).
    obs["DA-04"] = {"out_of_range_anchor_rejected": any(u["kind"] == "derived_text" for u in r.unresolved)
                    and not servable(root / "site-da04", "derived_text", f"{DOC_ID}@synthetic-extract/0.0.1",
                                     exclusions=None)}
    alt_doc = document(ALT, "toy-blue-form-alternate")
    cross = candidate(bound=False)
    cross["anchors"][0].update(page=99, source_copy_sha256=h(ALT))
    r35 = hn.run(hn.bundle(docs=[document(), alt_doc], copies=[SOURCE, ALT], cands=[cross]), root / "site-da35")
    ev = active_generation(site)["candidate_evidence"].get("toy:edge:001", {})
    obs["DA-35"] = {"source_copy_hash_verified": good.activated and "toy:edge:001" in good.verified["candidates"],
                    "page_anchor_verified": bool(ev) and ev["anchors"][0]["page"] == 1,
                    "producing_commit_retained": ev.get("artefact_commit") == A5,
                    # recomputed by the importer from the verified derivative page text (not copied from input)
                    "passage_hash_retained": bool(ev) and ev["anchors"][0]["text_sha256"] == h(SOURCE)
                    and ev["anchors"][0]["page_only"] is False,
                    "broken_binding_rejected": r35.activated and "toy:edge:001" not in r35.verified["candidates"]}
    return obs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--observations", type=Path, required=True)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as t:
        out = observations(Path(t))
    a.observations.write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps(out, indent=1, sort_keys=True))
