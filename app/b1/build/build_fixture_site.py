"""Synthetic SYN site for the PR #54 retrieval oracle and the B1 UX journeys (retrieval-ux.md, environment SYN).

Renders docs/architecture/reviews/c13-assurance/retrieval-dev-fixture.json (read-only; never modified) as synthetic
original PDFs plus matching derived text, builds two development-signed contract-v1 releases and imports both through
app/importer into a disposable site:
  R1  every fixture document; V-STAGED carries publication STAGED; V-WITHDRAWN is published (the journeys withdraw it
      through the Admin API, exercising the real fence);
  R2  the same, except J-ALLOW is replaced by a repaginated copy (one cover page inserted), so a citation made in R1
      must still open the R1 copy at the cited page (UX-12, ASR-E06).
A mapping fixture passage id -> (doc_id, passage_id) of the ACTIVE generation is frozen to <out>/fixture_map.json
before any query runs.

Deviation recorded (not hidden): the build host has no Devanagari font and no imaging library (no apt), so the Hindi
original page L-HI is rendered as a Latin placeholder page instead of an image of Devanagari text; its derived text is
the fixture's noisy OCR string. RET-09 retrieval is testable; UX-19 original-pixel checks are not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import textwrap
from copy import deepcopy
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / "app" / "contract"), str(REPO / "app" / "importer")]
from mimamsa_contract.devbundle import new_dev_keypair, write_bundle  # noqa: E402
from mimamsa_contract.restricted import load_register  # noqa: E402
from mimamsa_importer import configure_site, import_release  # noqa: E402

FIXTURE = REPO / "docs/architecture/reviews/c13-assurance/retrieval-dev-fixture.json"
TYPES = {"act": "act", "rules": "rules", "notification": "notification", "judgment": "judgment", "manual": "manual",
         "historical_manual": "book_historical"}
PIPE = {"name": "syn-fixture-text", "version": "1.0.0"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pdf(pages: list[str]) -> bytes:
    """Minimal valid PDF (Helvetica, WinAnsi), one text block per page; text is extractable by PDF.js."""
    objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>",
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"}
    n = len(pages)
    kids = []
    for i, text in enumerate(pages):
        pid, cid = 4 + i, 4 + n + i
        kids.append(b"%d 0 R" % pid)
        lines = []
        for para in text.split("\n"):
            lines += textwrap.wrap(para, 78) or [""]
        ops = [b"BT /F1 12 Tf 15 TL 64 770 Td"]
        for ln in lines[:48]:
            esc = ln.encode("cp1252", "replace").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
            ops.append(b"(" + esc + b") Tj T*")
        ops.append(b"ET")
        ops.append(b"BT /F1 9 Tf 64 40 Td (Synthetic fixture page %d - fictional content, not a real source) Tj ET" % (i + 1))
        stream = b"\n".join(ops)
        objs[pid] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents %d 0 R /Resources << /Font << /F1 3 0 R >> >> >>" % cid
        objs[cid] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
    objs[2] = b"<< /Type /Pages /Kids [" + b" ".join(kids) + b"] /Count %d >>" % n
    out, offs = bytearray(b"%PDF-1.4\n"), {}
    for i in sorted(objs):
        offs[i] = len(out)
        out += b"%d 0 obj\n" % i + objs[i] + b"\nendobj\n"
    x = len(out)
    size = max(objs) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size + b"".join(b"%010d 00000 n \n" % offs[i] for i in range(1, size))
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, x)
    return bytes(out)


def axes(publication: str, truncated: bool):
    return {
        "source_integrity": {"value": "BYTE_VERIFIED", "basis": "synthetic fixture bytes hashed at build", "recorded_at": "2026-11-25T00:00:00Z",
                             "evidence_ref": "app/b1/build/build_fixture_site.py"},
        "source_authenticity": {"value": "UNKNOWN", "basis": "synthetic fixture: fictional",
                                "policy_v1": {"document_authority": "UNKNOWN", "carrier_provenance": "UNKNOWN", "copy_fidelity": "HASH_ONLY",
                                              "amendment_chain_status": "NOT_CHECKED", "instrument_identity": None, "authority_rationale": None}},
        "evidence_fidelity": {"value": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "basis": "synthetic derived text"},
        "legal_applicability": {"value": "NOT_ESTABLISHED", "basis": "fictional"},
        "legal_approval": {"value": "T0_RESEARCH_ONLY", "basis": "AUTH-LEDGER version 0"},
        "publication": {"value": publication, "basis": "synthetic fixture publication state"},
        "dependency_freshness": {"value": "NOT_EVALUATED", "basis": "synthetic"},
    }


def build_doc(doc: dict, *, cover: bool = False):
    """Returns (document record, derived record, original bytes, text bytes, {fixture passage id: passage id})."""
    did = "syn-" + doc["id"].lower()
    shift = 1 if cover else 0
    maxp = max(p["page"] for p in doc["pages"]) + shift
    by_page = {p["page"] + shift: p for p in doc["pages"]}
    pdf_pages = []
    for n in range(1, maxp + 1):
        p = by_page.get(n)
        if p is None:
            pdf_pages.append("Replacement edition cover page (synthetic)." if cover and n == 1 else f"[Synthetic page {n}: no fixture text]")
        elif p.get("language") == "hi":
            pdf_pages.append("[Image-only Hindi page placeholder: no Devanagari font on the build host. "
                             "The original would show Devanagari text here.]")
        else:
            pdf_pages.append(p["text"])
    orig = pdf(pdf_pages)
    h = sha(orig)
    text = "".join(f"[[page {n}]]\n{by_page[n]['text']}\n" for n in sorted(by_page))
    tb = text.encode("utf-8")
    pages, passages, mapping = [], [], {}
    for n in sorted(by_page):
        p = by_page[n]
        body = p["text"]
        ocr = p.get("extraction") == "OCR"
        pages.append({"page": n, "method": "ocr" if ocr else "pdf_text", "char_count": len(body), "ocr_engine": "fixture" if ocr else None,
                      "ocr_mean_confidence": 40.0 if ocr else None, "low_confidence": p.get("confidence") == "low",
                      "has_word_boxes": False, "text_sha256": sha(body.encode())})
        pid = f"p{n}-1"
        passages.append({"passage_id": pid, "page": n, "char_start": 0, "char_end": len(body),
                         "paragraph_label": str(p["para"]) if p.get("para") is not None else None, "kind": "body",
                         "text_sha256": sha(body.encode())})
        mapping[p["id"]] = [did, pid]
    pub = {"published": "PUBLISHED", "staged": "STAGED", "withdrawn": "PUBLISHED"}[doc["publication"]]
    has_ocr = any(p.get("extraction") == "OCR" for p in doc["pages"])
    rec = {
        "contract_version": "1.0.0", "record_kind": "document", "doc_id": did, "doc_type": TYPES[doc["type"]],
        "source_copy": {"sha256": h, "bytes": len(orig), "mime_type": "application/pdf", "vault_path": f"vault/sha256/{h[:2]}/{h}",
                        "page_count": maxp, "completeness": "TRUNCATED_AT_SOURCE" if doc.get("completeness") == "truncated_at_source" else "COMPLETE"},
        "alternate_copy_sha256": [], "parent_doc_id": None, "title": doc["title"], "number": None,
        "issuing_authority": doc.get("court") or "Fictional issuer (synthetic)", "issue_date": doc["date"], "effective_date": None,
        "language": "en", "corpus_status": "unknown", "corpus_status_note": None, "corpus_status_as_of": None,
        "text_method": "mixed" if has_ocr else "pdf_text", "ocr_confidence": 40.0 if has_ocr else None,
        "provenance": {"acquisition_channel": "MANUAL_OWNER", "source_url": None, "retrieved_at": "2026-11-25T00:00:00Z",
                       "source_system": "synthetic-fixture", "source_record_id": doc["id"], "original_filename": None, "aliases": [],
                       "hf": None, "git": None, "acquisition_record_ref": None, "admin_submission_id": None},
        "status_axes": axes(pub, doc.get("completeness") == "truncated_at_source"),
        "restriction": {"access_marking": None, "marking_page": None, "eligibility": "ELIGIBLE_ALL_USERS" if pub == "PUBLISHED" else "NOT_ASSESSED",
                        "restriction_id": None, "decided_by": None, "basis": None},
        "field_origin": {"title": "human"},
    }
    if doc["type"] == "judgment":
        a, _, b = doc["title"].partition(" v. ")
        rec["judicial"] = {"court": doc.get("court"), "bench": doc.get("bench"), "case_numbers": doc.get("case_numbers", []),
                           "neutral_citation": doc.get("neutral_citation"), "reported_citations": [],
                           "parties": {"petitioner": a or None, "respondent": b or None}, "judges": [], "judgment_identity_id": doc.get("judgment_identity")}
        rec["field_origin"].update(court="human", case_numbers="human", neutral_citation="human", parties="human", issue_date="human")
    der = {"contract_version": "1.0.0", "record_kind": "derived_text", "source_copy_sha256": h, "doc_id": did,
           "pipeline": {"name": PIPE["name"], "version": PIPE["version"], "tools": {}}, "text_path": f"text/{did}.txt",
           "text_sha256": sha(tb), "page_marker": "[[page N]]", "quoting_permitted": not has_ocr,
           "evidence_fidelity": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "pages": pages, "passages": passages}
    return rec, der, orig, tb, mapping


def candidates(docs: dict, recs: dict, maps: dict):
    out = []
    ja = docs.get("J-ALLOW")
    if ja:
        did = recs["J-ALLOW"]["doc_id"]; h = recs["J-ALLOW"]["source_copy"]["sha256"]
        page_of = {fid: int(pid.split("-")[0][1:]) for fid, (_, pid) in maps.items() if fid.startswith("J2-")}
        for i, (proc, v) in enumerate(sorted(ja["candidate_outcomes"].items())):
            label = "dismissed" if v["label"].startswith("dismissed") else v["label"]
            out.append({"contract_version": "1.0.0", "record_kind": "candidate", "candidate_id": f"syn.outcome.{i}", "candidate_type": "outcome",
                        "source_doc_id": did, "anchors": [{"source_copy_sha256": h, "page": page_of["J2-MAJ"], "passage_id": None, "char_start": None,
                                                           "char_end": None, "paragraph_label": "12", "text_sha256": None, "pipeline_version": None,
                                                           "quote": None, "pipeline_name": None, "derivative_text_sha256": None}],
                        "extractor": {"name": "syn-fixture", "version": "1", "artefact_commit": "0000000", "artefact_path": None, "artefact_sha256": None},
                        "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None, "capability_restriction": "NON_OPERATIONAL_RESEARCH_ONLY",
                        "deferred_findings": [], "evaluation_ref": None,
                        "payload": {"field": "printed_disposal", "label": label, "proceeding_ref": proc, "party_scope": None,
                                    "abstain_reason": None}})
        tgt = recs.get("J-REJECT")
        if tgt:
            out.append({"contract_version": "1.0.0", "record_kind": "candidate", "candidate_id": "syn.edge.cites.0", "candidate_type": "graph_edge",
                        "source_doc_id": did, "anchors": [{"source_copy_sha256": h, "page": page_of["J2-QUOTE"], "passage_id": None, "char_start": None,
                                                           "char_end": None, "paragraph_label": "9", "text_sha256": None, "pipeline_version": None,
                                                           "quote": None, "pipeline_name": None, "derivative_text_sha256": None}],
                        "extractor": {"name": "syn-fixture", "version": "1", "artefact_commit": "0000000", "artefact_path": None, "artefact_sha256": None},
                        "status": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None, "capability_restriction": "NONE_RECORDED",
                        "deferred_findings": [], "evaluation_ref": None,
                        "payload": {"relation": "CITES_JUDGMENT", "source_node": f"JUD:JG-{h[:12]}", "confidence": "extracted",
                                    "has_legal_effect": False, "effective_date": None, "evidence_text": None,
                                    "target": {"node_id": f"JUD:JG-{tgt['source_copy']['sha256'][:12]}", "raw_reference": "2021 BRSYN 12", "resolved": True}}})
    return out


# Eligibility controls for review F01 (not part of the PR #54 fixture; unique words so no RET query matches them):
#   X-DROPPED      published in R1, absent from R2 (a later release dropped it, e.g. for a restriction)
#   X-STAGEDEARLY  STAGED (never published) copy in R1; a different, PUBLISHED copy in R2
def extras(n: int):
    mk = lambda i, text, pub: {"id": i, "title": f"Eligibility control {i} (synthetic)", "type": "manual", "date": "2022-01-01",
                               "pages": [{"page": 1, "id": f"{i}-P1", "text": text}], "publication": pub, "copy": f"C-{i}-{n}",
                               "completeness": "complete"}
    out = [mk("X-STAGEDEARLY", f"zinnia quartz control edition {n}", "staged" if n == 1 else "published")]
    if n == 1:
        out.append(mk("X-DROPPED", "zinnia quartz dropped control", "published"))
    return out


def release(hn_key, pub, register, fixture, n: int, cover_ids=(), out: Path = None):
    recs, ders, files, maps = {}, [], {}, {}
    for doc in fixture["documents"] + extras(n):
        rec, der, orig, tb, mp = build_doc(doc, cover=doc["id"] in cover_ids)
        recs[doc["id"]] = rec
        ders.append(der)
        files[f"originals/{rec['source_copy']['sha256']}.pdf"] = (orig, "original")
        files[der["text_path"]] = (tb, "text")
        maps.update(mp)
    cands = candidates({d["id"]: d for d in fixture["documents"]}, recs, maps)
    # one synthetic A4-shaped research record whose evidence names two copies (review F02 redaction test)
    a4 = {"version_id": "SYN/s.17/v01", "family": "SYN", "provision": "s.17", "version_kind": "as_enacted",
          "change_summary": "Synthetic version record (not a real provision)", "determination_state": "AUTOMATED_CANDIDATE_NOT_VERIFIED",
          "effective_from": {"status": "NOT_STATED_PENDING_ADVICE", "date": None, "reported_date": None},
          "effective_to": {"status": "OPEN_ON_LOCATED_INSTRUMENTS"}, "currency": {"status": "NOT_ESTABLISHED"},
          "text_evidence": [{"role": "synthetic_primary", "sha256": recs["S-ACT"]["source_copy"]["sha256"], "pdf_page": "2", "edition": "synthetic act"},
                            {"role": "synthetic_secondary", "sha256": recs["V-OTHER"]["source_copy"]["sha256"], "pdf_page": "1", "edition": "unrelated synthetic book"}]}
    files["research/a4_provision_versions.jsonl"] = ((json.dumps(a4, sort_keys=True) + "\n").encode(), "report")
    man = json.loads((REPO / "app/contract/examples/release_manifest.example.json").read_text(encoding="utf-8"))
    man.update(release_id=f"R13-syn-fixture-20261125-{n:08x}", release_sequence=n, created_at="2026-11-25T00:00:00Z")
    man["restricted_material"].update(config_sha256=register.config_sha256, restriction_ids_applied=["RM-001"])
    path = out / f"bundle-r{n}"
    if path.exists():
        shutil.rmtree(path)
    write_bundle(path, man, documents=list(recs.values()), derived=ders, candidates=cands, extra_files=files,
                 signing_key=hn_key, public_key_raw=pub)
    return path, maps, recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fixture", type=Path, default=FIXTURE, help="default: the committed dev fixture; an independent evaluator may pass a holdout file")
    a = ap.parse_args()
    out = a.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    fixture = json.loads(a.fixture.read_text(encoding="utf-8"))
    register = load_register(REPO / "config" / "restricted_material.json")
    key, pub = new_dev_keypair()
    site = out / "site"
    configure_site(site, exclusion_channel="none")
    b1, maps1, recs1 = release(key, pub, register, fixture, 1, out=out)
    r1 = import_release(b1, site, trusted_public_key=pub, mode="development", register=register)
    b2, maps2, recs2 = release(key, pub, register, fixture, 2, cover_ids={"J-ALLOW"}, out=out)
    r2 = import_release(b2, site, trusted_public_key=pub, mode="development", register=register)
    del key
    res = {"fixture_sha256": sha(a.fixture.read_bytes()), "r1": {"activated": r1.activated, "refused": r1.refused_reasons, "unresolved": r1.unresolved},
           "r2": {"activated": r2.activated, "refused": r2.refused_reasons, "unresolved": r2.unresolved},
           "active_release": f"R13-syn-fixture-20261125-{2:08x}", "map": maps2,
           "doc_ids": {k: v["doc_id"] for k, v in recs2.items()},
           "j_allow_r1_copy": recs1["J-ALLOW"]["source_copy"]["sha256"], "j_allow_r2_copy": recs2["J-ALLOW"]["source_copy"]["sha256"],
           "x_dropped_r1_copy": recs1["X-DROPPED"]["source_copy"]["sha256"],
           "x_stagedearly_r1_copy": recs1["X-STAGEDEARLY"]["source_copy"]["sha256"],
           "x_stagedearly_r2_copy": recs2["X-STAGEDEARLY"]["source_copy"]["sha256"],
           "j_allow_r1_pages": {fid: int(pid.split("-")[0][1:]) for fid, (_, pid) in maps1.items() if fid.startswith("J2-")},
           "deviations": ["L-HI original rendered as a Latin placeholder page (no Devanagari font; apt not allowed)"]}
    res["map"] = {k: v for k, v in res["map"].items() if not k.startswith("X-")}   # oracle mapping: fixture passages only
    (out / "fixture_map.json").write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("r1", "r2")}, indent=1)[:2000])
    return 0 if r1.activated and r2.activated else 1


if __name__ == "__main__":
    sys.exit(main())
