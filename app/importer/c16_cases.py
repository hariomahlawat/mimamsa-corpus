"""Synthetic C16 producer exchange with REAL bytes, for the B01 site-importer tests and the end-to-end fixture site.

The contract fixtures (app/contract/fixtures/c16) carry hashes of bytes that do not exist, so the site cannot recompute
anything from them. This module builds a small, deterministic, strictly valid contract 2.1 exchange whose originals,
derivatives, DOCX images and receipt artefacts are real, and wraps it in a development-signed v1 bundle:

  A  eligible   native PDF judgment, v1 record + C16 identity ADMITTED_AS_PRIMARY (SEARCHABLE), nine typed receipts
  B  held       native PDF, v1 record + C16 identity HELD_RELEVANCE_UNRESOLVED
  E  docx       Word file with one screenshot (OCR DONE), C16 only (no v1 record), eligible, local path 'AR 22 - ...'
  C  legacy     v1 only, PUBLISHED, pinned HF revision: independently established, served
  D  legacy     v1 only, no pinned HF revision or acquisition record: not established
  F  v7         v1 record whose bytes are a declared v7 candidate: never served

Everything is synthetic; no document text is real. Keys are disposable development keys (fixed seed only for the
committed end-to-end site, so it can be rebuilt byte for byte).
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE.parent / "contract"
sys.path[:0] = [str(HERE), str(CONTRACT), str(CONTRACT / "fixtures" / "c16")]

import build_fixtures as bf  # noqa: E402
from da_cases import NOW, REGISTER, A5, document  # noqa: E402
from mimamsa_contract.c16 import adapters, canonical, receipts  # noqa: E402
from mimamsa_contract.devbundle import write_bundle  # noqa: E402

C21 = "mimamsa-corpus-contract/2.1"
CG = "CG-20261128-b01site-0a1b2c3d"
COLL = "local:b01-owner-collection"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
GATE_KIND = {g: k for g, k in zip(bf.GATE_IDS, ("HASH_REDOWNLOAD", "FORMAT_DETECTION", "REGISTER_CHECK", "MARKING_SCREEN",
                                                              "IDENTITY_VALIDATION", "DERIVATIVE_VERIFICATION", "IMAGE_ACCOUNTING",
                                                              "RELEVANCE_DECISION", "DUPLICATE_RESOLUTION", "SCHEMA_VALIDATION"))}
ASSERTED = {"MARKING_SCREEN", "RELEVANCE_DECISION", "DUPLICATE_RESOLUTION"}
GATE_PRODUCER = {"name": "b01-synthetic-gates", "version": "1.0.0", "commit": "c8fa5290", "config_sha256": None}
GATE_CONFIG = hashlib.sha256(b"b01-gate-config").hexdigest()
HF_REV = "b" * 40
INV_E = "L-" + hashlib.sha256(b"b01-inventory-e").hexdigest()[:20]


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pdf(pages: int, label: str) -> bytes:
    """A minimal, deterministic PDF with `pages` blank pages (pypdfium2 opens it; the label makes the bytes unique)."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [" + b" ".join(f"{3 + i} 0 R".encode() for i in range(pages)) + f"] /Count {pages} >>".encode()]
    objs += [b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>" for _ in range(pages)]
    out = b"%PDF-1.4\n%" + label.encode("ascii") + b"\n"
    offs = []
    for n, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{n} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    return out


def docx(images: dict[str, bytes], body: str) -> bytes:
    """A minimal, deterministic DOCX container (fixed timestamps) holding a document part and image parts."""
    buf = io.BytesIO()
    # Platform-independent bytes: STORED (no dependence on the zlib build) and a fixed 'made by' system and
    # attributes (zipfile defaults create_system to 0 on Windows and 3 elsewhere).
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        parts = {"[Content_Types].xml": b"<?xml version='1.0'?><Types/>",
                 "word/document.xml": f"<?xml version='1.0'?><document><body>{body}</body></document>".encode()}
        parts.update(images)
        for name in sorted(parts):
            zi = zipfile.ZipInfo(name, date_time=(2026, 11, 28, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_STORED
            zi.create_system = 3
            zi.external_attr = 0o644 << 16
            z.writestr(zi, parts[name])
    return buf.getvalue()


def derivative_text(pages: list[str]) -> bytes:
    return "".join(f"[[page {n}]]\n{t}\n" for n, t in enumerate(pages, 1)).encode("utf-8")


class Corpus:
    """The synthetic bytes. Everything is a pure function of the labels, so two builds are byte-identical."""

    def __init__(self):
        self.a_pages = ["In the synthetic matter the appellant relied on section 69 of the Army Act.",
                        "The synthetic appeal is disposed of; this is fixture text only."]
        self.a = pdf(2, "b01-eligible")
        self.a_text = derivative_text(self.a_pages)
        self.b = pdf(1, "b01-held")
        self.b_text = derivative_text(["Synthetic held writ petition text."])
        self.img = b"\x89PNG\r\n\x1a\n" + b"b01-synthetic-screenshot"
        self.e = docx({"word/media/image1.png": self.img}, "Synthetic Word judgment text.")
        self.e_text = derivative_text(["Synthetic Word judgment text."])
        self.e_ocr = b"Synthetic OCR of the embedded screenshot."
        self.c = b"Synthetic legacy order. Established through a pinned canonical revision."
        self.d = b"Synthetic legacy order without any recorded provenance."
        self.f = b"Synthetic v7 candidate original, never admitted."
        self.g = pdf(1, "b01-later-held")


# ----------------------------------------------------------------------------------------------- exchange records

def _research(state, quoting, page_cite, whole, graph, basis):
    return bf.research(state, quoting, page_cite, whole, graph, basis)


def identity(doc_id, data, *, mime, fmt, pages, pagination, rep, derivs, images, research, observations=(), integrity="BYTE_VERIFIED",
             graph_node=None, history_outputs=()):
    sha = h(data)
    return {"contract": bf.CONTRACT_ID, "record_kind": "document_identity", "doc_id": doc_id,
            "source_copy": {"sha256": sha, "bytes": len(data), "mime_type": mime, "detected_format": fmt, "page_count": pages,
                            "physical_pagination": pagination, "vault_path": f"vault/sha256/{sha[:2]}/{sha}"},
            "representation": rep,
            "work_identity": {"work_kind": "JUDGMENT", "judgment_id": bf.U(), "graph_node_ref": graph_node or f"JUD:{doc_id}",
                              "proceeding_numbers_as_printed": [], "identity_basis": "COVER_PAGE_EXTRACTED",
                              "identity_verification": "CANDIDATE", "rendition": {"rendition_kind": "UNDETERMINED", "language": "en"}},
            "embedded_images": images, "text_derivatives": derivs,
            "provenance": {"acquisition": {"acquisition_channel": "CRAWLER", "source_url": f"https://judgments.example.invalid/{doc_id}",
                                           "retrieved_at": "2026-11-20T10:00:00Z", "original_filename": None, "hf": None},
                           "carrier_provenance": "GOVERNMENT_HOSTED_COPY", "observations": list(observations),
                           "processing_history": [bf.step(1, "ACQUIRE", "b01-crawler", [], [sha]),
                                                  *([bf.step(2, "EXTRACT_TEXT", "mimamsa-corpus-text", [sha], list(history_outputs))]
                                                    if history_outputs else [])]},
            "restriction": bf.restriction(),
            "integrity": {"source_integrity": integrity, "basis": "re-downloaded at a pinned revision and re-hashed (synthetic)"},
            "research_eligibility": research, "corpus_generation_id": CG}


def deriv(doc_id, text: bytes, units, *, basis="SOURCE_PHYSICAL", methods=("NATIVE_TEXT_LAYER",), name="mimamsa-corpus-text",
          images_total=0, images_done=0, quoting=True):
    return {"derivative_id": f"{doc_id}@{name}/1.0.0", "pipeline_name": name, "pipeline_version": "1.0.0",
            "derivative_text_sha256": h(text), "pagination_basis": basis, "methods": list(methods),
            "ocr_config": bf.OCR if any(m.startswith("OCR") for m in methods) else None,
            "text_reliability": "reliable" if quoting else "partly_unreliable", "quoting_permitted": quoting,
            "coverage": {"units_total": units, "units_with_text": units, "images_total": images_total, "images_text_extracted": images_done}}


def native_rep():
    return {"representation_kind": "NATIVE_DIGITAL_PDF", "origin_status": "CARRIER_ISSUED_COPY_CLAIMED", "content_scope": "WHOLE_WORK",
            "completeness": "NOT_CHECKED"}


DOC_A, DOC_B = "sc-2020-b01-eligible-ca0101", "hc-2020-b01-held-wp0102"


def population(cp: Corpus, *, e_path="Army Rules/AR 22 - Lt Col B01 Example v Union of India.docx"):
    ids = {}
    ids["A"] = identity(DOC_A, cp.a, mime="application/pdf", fmt="PDF", pages=2, pagination="PHYSICAL_PAGES", rep=native_rep(),
                        derivs=[deriv(DOC_A, cp.a_text, 2)], images=[],
                        research=_research("ELIGIBLE_FULL", True, True, False, True, ["TEXT_RELIABLE_NATIVE"]),
                        history_outputs=[h(cp.a_text)])
    ids["B"] = identity(DOC_B, cp.b, mime="application/pdf", fmt="PDF", pages=1, pagination="PHYSICAL_PAGES", rep=native_rep(),
                        derivs=[deriv(DOC_B, cp.b_text, 1)], images=[],
                        research=_research("ELIGIBLE_FULL", True, True, False, True, ["TEXT_RELIABLE_NATIVE"]),
                        history_outputs=[h(cp.b_text)])
    esha = h(cp.e)
    doc_e = adapters.local_doc_id(esha)
    img = {"image_sequence_id": f"IMG:{esha}:1", "sequence": 1, "image_sha256": h(cp.img),
           "location": {"kind": "DOCX_PART", "container_part": "word/media/image1.png", "pdf_page": None, "body_order": 1},
           "mime_type": "image/png", "pixel_width": 1240, "pixel_height": 1754, "ocr_state": "DONE", "ocr_derivative_sha256": h(cp.e_ocr)}
    ids["E"] = identity(doc_e, cp.e, mime=DOCX_MIME, fmt="DOCX", pages=None, pagination="NONE_FLOW_DOCUMENT",
                        rep={"representation_kind": "WORD_WITH_EMBEDDED_IMAGES", "origin_status": "THIRD_PARTY_REPRODUCTION",
                             "content_scope": "UNDETERMINED", "completeness": "NOT_CHECKED"},
                        derivs=[deriv(doc_e, cp.e_text, 1, basis="GENERATED_SEGMENT", methods=("DOCX_XML", "OCR_EMBEDDED_IMAGE"),
                                      name="c16-docx", images_total=1, images_done=1, quoting=False)],
                        images=[img],
                        research=_research("SEARCH_ONLY", False, False, False, True, ["OCR_TEXT_SEARCH_ONLY", "COMPLETENESS_NOT_CHECKED"]),
                        observations=[{"collection": COLL, "relative_path": e_path, "inventory_id": INV_E, "observed_at": None}],
                        history_outputs=[h(cp.e_text)])
    ids["E"]["provenance"]["acquisition"] = {"acquisition_channel": "MANUAL_OWNER", "source_url": None, "retrieved_at": None,
                                             "original_filename": None, "hf": None}
    ids["E"]["provenance"]["carrier_provenance"] = "USER_SUPPLIED"
    anchor = bf.anchor(doc_id=DOC_A, original_sha256=h(cp.a), representation_sha256=h(cp.a), derivative_text_sha256=h(cp.a_text),
                       locator={"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": 1, "citable_as_source_page": True},
                       text_span={"passage_id": None, "char_start": 0, "char_end": 31,
                                  "text_sha256": h(cp.a_pages[0][0:31].encode())},
                       extraction={"method": "NATIVE_TEXT_LAYER", "pipeline_name": "mimamsa-corpus-text", "pipeline_version": "1.0.0", "ocr_config": None},
                       quality={"text_reliability": "reliable", "ocr_mean_confidence": None, "low_confidence": False}, quoting_permitted=True)
    rels = [cites(DOC_A, h(cp.a), "PROV:AA-1950:s.69", anchor["anchor_id"])]
    rels += adapters.classify_path(e_path, doc_id=doc_e, sha=esha, subject_node=f"JUD:{doc_e}", collection=COLL,
                                   inventory_id=INV_E)
    tax = [t for t in bf.build_taxonomy() if t["node_id"] in ("SUBJ:court_martial", "INSTCODE:AA-1950", "PROV:AA-1950:s.69",
                                                                "INSTCODE:AR-1954", "CHAP:AR-1954:V", "PROV:AR-1954:r.22")]
    for t in tax:
        if t["node_id"] == "INSTCODE:AR-1954":
            t["parent_ids"] = ["SUBJ:court_martial"]
    tax += adapters.local_subject_nodes([e_path], COLL)
    return ids, {"anchors": [anchor], "relationships": rels, "taxonomy": tax}


def cites(doc, sha, target, anchor_id):
    r = {"contract": bf.CONTRACT_ID, "record_kind": "corpus_relationship", "relationship_id": "", "category": "cites_provision",
         "subject": {"doc_id": doc, "source_copy_sha256": sha, "graph_node_ref": f"JUD:{doc}"},
         "target": {"resolved": True, "node_id": target}, "evidentiary_basis": "DOCUMENT_TEXT_EXTRACTED",
         "source": {"producer": bf.TOOLS, "rule_id": "B01-SYNTHETIC-RULE", "rule_version": "1.0", "author_id": "b01-synthetic-extractor"},
         "classification_provenance": None, "anchors": [anchor_id], "verification": "CANDIDATE", "review_ref": None,
         "review_binding": None, "approval_ref": None, "validates_relationship_id": None, "proposition_ref": None,
         "temporal_scope": {"from": "2020-01-01", "from_status": "AS_OF_SOURCE_DATE", "to": None, "to_status": "NOT_APPLICABLE"},
         "has_legal_effect": False, "is_finding": False,
         "uncertainty": "Extracted citation candidate; a citation does not establish how the source treated the target."}
    r["relationship_id"] = canonical.relationship_id(r)
    p = adapters.graph_projection(r)["edge"]
    r["graph_projection"] = {"edge_type": p["type"], "origin": p["origin"]}
    return r


# ----------------------------------------------------------------------------------------------- admissions and receipts

def artefact(gate, ident, payload, *, derivative=None, register=None, outcome="PASS"):
    kind = GATE_KIND[gate]
    return {"contract": C21, "record_kind": "gate_receipt_artefact", "gate_id": gate, "receipt_kind": kind,
            "verification_class": "ASSERTED_BOUND" if kind in ASSERTED else "SITE_RECOMPUTABLE",
            "subject": {"doc_id": ident["doc_id"], "source_copy_sha256": ident["source_copy"]["sha256"]}, "corpus_generation_id": CG,
            "derivative_sha256": derivative, "rule": {"id": "c16-gate-" + gate[:3].lower(), "version": "1.0"},
            "config_sha256": GATE_CONFIG, "register_sha256": register, "outcome": outcome, "revision": 1,
            "supersedes_receipt_sha256": None, "producer": GATE_PRODUCER, "payload": payload}


def eligible_artefacts(ident, data: bytes, text: bytes, pop, *, magic: str, fmt: str, occurrences=None):
    sha = ident["source_copy"]["sha256"]
    from mimamsa_contract.c16.evidence import split_pages
    pages = split_pages(text.decode("utf-8"))
    units = [h(pages[n].encode("utf-8")) for n in sorted(pages)]
    der = ident["text_derivatives"][0]["derivative_text_sha256"]
    arts = {
        "G01_HASH_VERIFIED": artefact("G01_HASH_VERIFIED", ident, {"source": {"hf_repo": "owner/b01-synthetic", "hf_revision": HF_REV,
                                                                              "path": f"data/raw/b01/{sha}"},
                                                                   "measured_sha256": sha, "measured_bytes": len(data)}),
        "G02_FORMAT_DETECTED": artefact("G02_FORMAT_DETECTED", ident, {"magic_hex": magic, "detected_format": fmt,
                                                                       "mime_type": ident["source_copy"]["mime_type"]}),
        "G03_RESTRICTED_REGISTER": artefact("G03_RESTRICTED_REGISTER", ident, {"fields_checked": ["doc_id", "paths", "record_strings", "sha256"],
                                                                               "matches": 0}, register=REGISTER.config_sha256),
        "G04_ACCESS_MARKING_REVIEWED": artefact("G04_ACCESS_MARKING_REVIEWED", ident, {"pages_screened": len(pages), "images_screened": 0,
                                                                                       "markings_found": [], "method": "synthetic screen",
                                                                                       "ocr_config_sha256": None}),
        "G05_IDENTITY_RECORD_VALID": artefact("G05_IDENTITY_RECORD_VALID", ident, {"identity_record_sha256": canonical.record_sha256(ident), "issues": 0}),
        "G06_TEXT_DERIVATIVE_VERIFIED": artefact("G06_TEXT_DERIVATIVE_VERIFIED", ident, {"units_total": len(units), "units_with_text": len(units),
                                                                                         "unit_text_sha256": units}, derivative=der),
        "G08_RELEVANCE_ASSESSED": artefact("G08_RELEVANCE_ASSESSED", ident, {"decided_by_kind": "OWNER", "decided_by": "owner-synthetic",
                                                                             "basis": "military-law judgment (synthetic)"}),
        "G09_DUPLICATE_RESOLVED": artefact("G09_DUPLICATE_RESOLVED", ident, {"compared_scope": "synthetic canonical index",
                                                                             "method": "BYTE_HASH_AND_TEXT_REVIEW", "result": "UNIQUE"}),
        "G10_SCHEMA_VALID": artefact("G10_SCHEMA_VALID", ident, {"copy_records_sha256": receipts.copy_records_digest(ident, pop["anchors"], pop["relationships"]),
                                                                 "issues": 0}),
    }
    if occurrences is not None:
        arts["G07_EMBEDDED_IMAGES_ACCOUNTED"] = artefact("G07_EMBEDDED_IMAGES_ACCOUNTED", ident, {"occurrences": occurrences})
    return arts


def eligible_admission(ident, arts):
    over = {} if "G07_EMBEDDED_IMAGES_ACCOUNTED" in arts else {"G07_EMBEDDED_IMAGES_ACCOUNTED": "NOT_APPLICABLE"}
    g = bf.gates(G01_HASH_VERIFIED="PASS", **over)
    for x in g:
        a = arts.get(x["gate_id"])
        if a is not None:
            x["receipt"] = {"receipt_kind": a["receipt_kind"], "subject_sha256": a["subject"]["source_copy_sha256"],
                            "derivative_sha256": a["derivative_sha256"], "rule_id": a["rule"]["id"], "rule_version": a["rule"]["version"],
                            "config_sha256": a["config_sha256"], "register_sha256": a["register_sha256"], "outcome": a["outcome"],
                            "receipt_sha256": receipts.artefact_sha256(a)}
    return bf.admission(None, "ADMITTED_AS_PRIMARY", g, eligible=True, doc=ident["doc_id"], sha=ident["source_copy"]["sha256"], gen=CG,
                        reasons=["all gates passed with evidence (synthetic)"])


def held_admission(ident):
    return bf.admission(None, "HELD_RELEVANCE_UNRESOLVED",
                        bf.gates(G08_RELEVANCE_ASSESSED="NOT_RUN", G07_EMBEDDED_IMAGES_ACCOUNTED="NOT_APPLICABLE"),
                        doc=ident["doc_id"], sha=ident["source_copy"]["sha256"], gen=CG, reasons=["relevance not assessed"])


def exchange(cp: Corpus, *, contract=C21, held=("B",), mutate=None, e_path=None, mutate_arts=None, keys=None):
    """{name: bytes} of the exchange, the receipt artefacts {path: bytes}, the identities and the admissions."""
    ids, pop = population(cp, **({"e_path": e_path} if e_path else {}))
    if mutate:
        mutate(ids, pop)
    if keys is not None:
        ids = {k: v for k, v in ids.items() if k in keys}
    adms, arts = [], {}
    for key, ident in sorted(ids.items()):
        if key in held:
            adms.append(held_admission(ident))
            continue
        if key == "A":
            a = eligible_artefacts(ident, cp.a, cp.a_text, pop, magic="255044462d", fmt="PDF")
        else:
            occ = [{"image_sequence_id": i["image_sequence_id"], "image_sha256": i["image_sha256"], "ocr_state": i["ocr_state"],
                    "ocr_derivative_sha256": i.get("ocr_derivative_sha256")} for i in ident["embedded_images"]]
            a = eligible_artefacts(ident, cp.e, cp.e_text, pop, magic="504b030414", fmt="DOCX", occurrences=occ)
        if mutate_arts:
            mutate_arts(key, a)
        adms.append(eligible_admission(ident, a))
        arts.update({receipts.artefact_path(x): receipts.artefact_bytes(x) for x in a.values()})
    full = {"identities": list(ids.values()), "admissions": adms, "reviewed_records": [], **pop}
    full = {k: v for k, v in full.items() if v or k != "reviewed_records"}

    def edit(m):
        m["contract"] = contract
        m["pinned_inputs"]["restricted_register_sha256"] = REGISTER.config_sha256
        m["registries"]["external_judgments"] = []
    files = bf.exchange_files(full, manifest_edit=edit, gen=CG, external=[])
    return files, arts, ids, adms


# ----------------------------------------------------------------------------------------------- v1 bundle

def v1_doc(data: bytes, doc_id: str, *, mime="application/pdf", pages=1, hf=True):
    d = document(data, doc_id, mime=mime, page_count=pages)
    d["status_axes"]["publication"]["value"] = "PUBLISHED"
    d["judicial"] = {"judgment_identity_id": f"JUD:{doc_id}", "case_numbers": [doc_id]}
    if hf:
        d["provenance"]["hf"] = {"repo": "owner/b01-synthetic", "revision": HF_REV, "path": f"data/raw/{doc_id}"}
    else:
        d["provenance"]["hf"] = None
    return d


def v1_derived(doc_id, sha, text: bytes, path, pages_text: list[str]):
    return {"contract_version": "1.0.0", "record_kind": "derived_text", "doc_id": doc_id, "source_copy_sha256": sha,
            "pipeline": {"name": "mimamsa-corpus-text", "version": "1.0.0"}, "text_path": path, "text_sha256": h(text),
            "page_marker": "[[page N]]", "quoting_permitted": False, "evidence_fidelity": "AUTOMATED_CANDIDATE_NOT_VERIFIED",
            "pages": [{"page": n, "method": "pdf_text", "char_count": len(t), "low_confidence": False} for n, t in enumerate(pages_text, 1)],
            "passages": [{"passage_id": f"p{n}-1", "page": n, "char_start": 0, "char_end": len(t), "text_sha256": h(t.encode())}
                         for n, t in enumerate(pages_text, 1) if t]}


DOC_C, DOC_D, DOC_F, DOC_G = "aft-2020-b01-legacy-oa0103", "aft-2020-b01-noprov-oa0104", "aft-2020-b01-v7relabel-oa0105", "aft-2020-b01-later-held-oa0106"


V7_SOURCE = "v7:cycle15"
GEN_PIN_PLACEHOLDER = "0" * 64     # a well-formed pin for registers whose refusal must come from elsewhere


def _prov(gen=None, repo=None, rev=None, cset=None):
    return {"generation_manifest_sha256": gen, "hf_repo": repo, "hf_revision": rev, "candidate_set_sha256": cset}


def accounting(release_id, copies: dict | None, v1: dict, v7: list[str] | None = None, *, generation_sha256=GEN_PIN_PLACEHOLDER):
    """The contract 2.1 declared register (`SOURCE_ADMISSION_ACCOUNTING_SCHEMA`, scope DECLARED_BY_BUILD) as a
    producer writes it: `accounting.register_bytes`. copies / v1 values come from `counts()`."""
    from mimamsa_contract.c16 import accounting as acct
    srcs = []
    if copies:
        c = dict(copies)
        if not c["by_decision"] and c["input"]:
            c["by_decision"], c["effective_admissions"] = {"ADMITTED_AS_PRIMARY": c["input"]}, c["input"]
        srcs.append({"source": f"c16:{CG}", "path": "C16", "provenance": _prov(generation_sha256, "owner/b01-synthetic", HF_REV), **c})
    for src, cnt in v1.items():
        pinned = src.startswith("v1:hf:")
        srcs.append({"source": src, "path": "V1", "provenance": _prov(None, "owner/b01-synthetic" if pinned else None,
                                                                         HF_REV if pinned else None), **cnt})
    if v7 is not None:
        cset = hashlib.sha256(candidate_set_bytes(v7)).hexdigest()
        srcs.append({"source": V7_SOURCE, "path": "V7_REFERENCE", "provenance": _prov(cset=cset),
                     **counts(input=len(set(v7)), held=len(set(v7)), reasons={"V7_REFERENCE_ONLY": len(set(v7))})})
    return acct.register_bytes({"contract": C21, "record_kind": "source_admission_accounting", "release_id": release_id,
                                "scope": "DECLARED_BY_BUILD", "sources": sorted(srcs, key=lambda s: s["source"])})


def candidate_set_bytes(hashes) -> bytes:
    from mimamsa_contract.c16.accounting import candidate_set_bytes as csb   # the 2.1 reference (CS3 canonical bytes)
    return csb(hashes)


def counts(input=0, held=0, rejected=0, quarantined=0, eligible=0, served=0, *, by_decision=None, reasons=None):
    if reasons is None:
        reasons = {"NOT_SERVED": input - served} if input - served > 0 else {}
    return {"input": input, "identities": input, "held": held, "rejected": rejected, "quarantined": quarantined,
            "eligible": eligible, "served": served, "effective_admissions": sum((by_decision or {}).values()),
            "by_decision": dict(sorted((by_decision or {}).items())), "not_served_reasons": dict(sorted(reasons.items()))}


def declared_c16_counts(exchange_files: dict, v1_keys: set) -> dict | None:
    """The producer's honest C16 declaration for an exchange, counted per identity with its effective admission
    exactly as the site buckets it (HELD*, REJECTED*, eligible, otherwise quarantined); served = eligible with a v1
    record. The site may only narrow it."""
    idents, adms = [], []
    for name, b in (exchange_files or {}).items():
        recs = [json.loads(x) for x in b.decode("utf-8").split("\n") if x] if name.endswith(".jsonl") else []
        idents += [r for r in recs if r.get("record_kind") == "document_identity"]
        adms += [r for r in recs if r.get("record_kind") == "corpus_admission"]
    if not idents:
        return None
    superseded = {a.get("supersedes_admission_id") for a in adms}
    eff = {(a["subject"]["doc_id"], a["subject"]["source_copy_sha256"]): a for a in adms if a["admission_id"] not in superseded}
    c = counts(by_decision={})
    c["effective_admissions"] = len(eff)
    c["by_decision"] = dict(sorted(Counter(a["decision"] for a in eff.values()).items()))
    reasons = Counter()
    for d in idents:
        key = (d["doc_id"], d["source_copy"]["sha256"])
        a = eff.get(key)
        c["input"] += 1
        c["identities"] += 1
        if a is None:
            c["quarantined"] += 1
            reasons["NO_EFFECTIVE_ADMISSION"] += 1
        elif a["decision"].startswith("HELD"):
            c["held"] += 1
            reasons["HELD"] += 1
        elif a["decision"].startswith("REJECTED"):
            c["rejected"] += 1
            reasons["REJECTED"] += 1
        elif a["application_eligible"]:
            c["eligible"] += 1
            if key in v1_keys:
                c["served"] += 1
            else:
                reasons["C16_ONLY_NOT_SERVABLE"] += 1
        else:
            c["quarantined"] += 1
            reasons["NOT_ELIGIBLE"] += 1
    c["not_served_reasons"] = dict(sorted(reasons.items()))
    return c


def declared_accounting(release_id, exchange_files: dict | None, docs: list[dict], v7: list[str] | None = None) -> bytes:
    """Declared register for a bundle carrying `exchange_files` and v1 `docs` (documents without a C16 identity are
    counted on their v1 source, declared eligible and served; the site may lower both)."""
    v1_keys = {(d["doc_id"], d["source_copy"]["sha256"]) for d in docs}
    copies = declared_c16_counts(exchange_files or {}, v1_keys)
    keys = set()
    for name, b in (exchange_files or {}).items():
        if name.endswith(".jsonl"):
            keys |= {(r["doc_id"], r["source_copy"]["sha256"]) for r in (json.loads(x) for x in b.decode("utf-8").split("\n") if x)
                     if r.get("record_kind") == "document_identity"}
    v1 = {}
    for d in docs:
        if (d["doc_id"], d["source_copy"]["sha256"]) in keys:
            continue
        src = V1_SRC if (d["provenance"].get("hf") or {}).get("revision") else f"v1:{d['provenance']['acquisition_channel']}"
        c = v1.setdefault(src, counts())
        for f in ("input", "identities", "eligible", "served"):
            c[f] += 1
    gen = (exchange_files or {}).get("GENERATION.json")
    return accounting(release_id, copies, v1, v7, generation_sha256=h(gen) if gen is not None else GEN_PIN_PLACEHOLDER)


V1_SRC = f"v1:hf:owner/b01-synthetic@{HF_REV}"


class C16Harness:
    """Builds signed development bundles carrying the synthetic exchange (or variants) and imports them."""

    def __init__(self, root: Path, seed: bytes | None = None):
        from mimamsa_contract.devbundle import new_dev_keypair
        self.root = Path(root)
        if seed is None:
            self.key, self.pub = new_dev_keypair()
        else:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
            self.key = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(seed).digest())
            self.pub = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        man = json.loads((CONTRACT / "examples" / "release_manifest.example.json").read_text())
        man["restricted_material"].update(config_sha256=REGISTER.config_sha256, restriction_ids_applied=["RM-999"])
        self.manifest = man
        self.cp = Corpus()
        self.n = 0

    def default_docs(self):
        cp = self.cp
        return [v1_doc(cp.a, DOC_A, pages=2), v1_doc(cp.b, DOC_B), v1_doc(cp.c, DOC_C, mime="text/plain"),
                v1_doc(cp.d, DOC_D, mime="text/plain", hf=False), v1_doc(cp.f, DOC_F, mime="text/plain")]

    def bundle(self, *, exchange_files=None, artefacts=None, docs=None, extra=None, accounting_bytes=None, drop=(), release=None,
               v7=True, c16=True, unlisted=None, kinds=None):
        cp = self.cp
        self.n += 1
        m = copy.deepcopy(self.manifest)
        m["release_id"] = release or f"R16-b01-synthetic-20261128-{self.n:08x}"
        m["release_sequence"] = self.n
        docs = self.default_docs() if docs is None else docs
        doc_ids = {d["doc_id"] for d in docs}
        copies = {d["source_copy"]["sha256"]: None for d in docs}
        data_by_sha = {h(x): x for x in (cp.a, cp.b, cp.c, cp.d, cp.e, cp.f, cp.g)}
        files = {f"originals/{s}.bin": (data_by_sha[s], "original") for s in copies}
        derived = []
        if DOC_A in doc_ids:
            files["text/a.txt"] = (cp.a_text, "text")
            derived.append(v1_derived(DOC_A, h(cp.a), cp.a_text, "text/a.txt", cp.a_pages))
        if DOC_C in doc_ids:
            ct = b"[[page 1]]\n" + cp.c + b"\n"
            files["text/c.txt"] = (ct, "text")
            derived.append(v1_derived(DOC_C, h(cp.c), ct, "text/c.txt", [cp.c.decode()]))
        if c16:
            if exchange_files is None:
                exchange_files, artefacts, _, _ = exchange(cp)
            files[f"originals/{h(cp.e)}.bin"] = (cp.e, "original")
            files["text/b.txt"] = (cp.b_text, "text")
            files["text/e.txt"] = (cp.e_text, "text")
            files["text/e-image-1.txt"] = (cp.e_ocr, "text")
            for name, b in exchange_files.items():
                files[f"corpus-v2/{name}"] = (b, "other")
            for p, b in (artefacts or {}).items():
                files[p] = (b, "other")
        if accounting_bytes is None:
            accounting_bytes = self.default_accounting(m["release_id"], docs, exchange_files if c16 else None, v7=v7)
        if accounting_bytes is not False:
            files["registers/source_accounting.json"] = (accounting_bytes, "other")
            if v7:   # the v7 candidate hash set the declared V7_REFERENCE source digests (proposed 2.1 addition)
                files["registers/candidate_sets/cycle15.txt"] = (candidate_set_bytes([h(cp.f)]), "other")
        files.update(extra or {})
        for p in drop:
            files.pop(p, None)
        for p, k in (kinds or {}).items():
            files[p] = (files[p][0], k)
        path = self.root / f"b{self.n}"
        if unlisted:
            for p, b in unlisted.items():
                (path / p).parent.mkdir(parents=True, exist_ok=True)
                (path / p).write_bytes(b)
        write_bundle(path, m, documents=docs, derived=derived, extra_files=files, signing_key=self.key, public_key_raw=self.pub)
        # devbundle orders SHA256SUMS by sorted Path objects, which compare case-insensitively on Windows and
        # case-sensitively elsewhere ('CHANGES.json' vs 'corpus-v2/...'). Re-list in code-point order of the POSIX
        # path and re-sign, so the bundle (and the generation's sums_sha256) is identical on every platform.
        from mimamsa_contract.bundle import SIG, SUMS
        lines = sorted(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(path).as_posix()}\n"
                       for p in path.rglob("*") if p.is_file() and p.name not in (SUMS, SIG))
        sums = "".join(sorted(lines, key=lambda x: x[66:])).encode()
        (path / SUMS).write_bytes(sums)
        (path / SIG).write_bytes(self.key.sign(sums))
        return path

    def default_accounting(self, release_id, docs, exchange_files=None, *, v7=True):
        """The producer's honest declaration for this bundle (contract 2.1 register, DECLARED_BY_BUILD)."""
        return declared_accounting(release_id, exchange_files, docs, [h(self.cp.f)] if v7 else None)

    def run(self, bundle_path, site, *, exclusions=None, channel="none"):
        from mimamsa_importer import configure_site, import_release
        if channel and not (Path(site) / "SITE_CONFIG.json").exists():
            configure_site(site, exclusion_channel=channel)
        return import_release(bundle_path, site, trusted_public_key=self.pub, mode="development", register=REGISTER,
                              exclusions=exclusions)


def g_identity(cp: Corpus):
    """G: a copy first served as an established legacy v1 document, later held by the producer (SG-1 scenario)."""
    text = derivative_text(["Synthetic later-held text."])
    return identity(DOC_G, cp.g, mime="application/pdf", fmt="PDF", pages=1, pagination="PHYSICAL_PAGES", rep=native_rep(),
                    derivs=[deriv(DOC_G, text, 1)], images=[],
                    research=_research("ELIGIBLE_FULL", True, True, False, True, ["TEXT_RELIABLE_NATIVE"]), history_outputs=[h(text)])


E2E_SEED = b"b01-e2e-fixture-site-development-key"


def build_e2e_site(site: Path, work: Path) -> dict:
    """The committed end-to-end fixture site, built by the real importer with a fixed development key:
    generation 1 serves A (eligible C16 admission) and C, G (established legacy copies);
    generation 2 (ACTIVE) carries a producer hold on G, so G is served by neither generation any more."""
    hn = C16Harness(work, seed=E2E_SEED)
    docs = hn.default_docs() + [v1_doc(hn.cp.g, DOC_G)]
    r1 = hn.run(hn.bundle(docs=docs, release="R16-b01-e2e-20261128-00000001"), site)
    files, arts, _, _ = exchange(hn.cp, held=("B", "G"), mutate=lambda ids, pop: ids.update(G=g_identity(hn.cp)))
    r2 = hn.run(hn.bundle(docs=docs, exchange_files=files, artefacts=arts, release="R16-b01-e2e-20261128-00000002"), site)
    return {"generation_1": {"release_id": r1.release_id, "activated": r1.activated, "served": sorted(r1.verified["documents"])},
            "active": {"release_id": r2.release_id, "activated": r2.activated, "served": sorted(r2.verified["documents"])},
            "expected_documents": sorted([DOC_A, DOC_C]),
            "expected_held_copies": sorted([f"{h(hn.cp.a)}|{DOC_A}", f"{h(hn.cp.c)}|{DOC_C}"]),
            "never_visible": sorted([DOC_B, DOC_D, DOC_F, DOC_G, adapters.local_doc_id(h(hn.cp.e))])}


def _tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


if __name__ == "__main__":  # python -I c16_cases.py <fixture_dir> [--check]
    import argparse
    import shutil
    import tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", type=Path, help="e.g. app/b1/tests/Mimamsa.Tests/fixtures/c16_b01")
    ap.add_argument("--check", action="store_true", help="rebuild in a scratch directory and compare byte for byte")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "out"
        exp = build_e2e_site(out / "site", Path(t) / "work")
        (out / "expected.json").write_text(json.dumps(exp, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        (out / ".gitattributes").write_bytes(b"* -text\n")
        if a.check:
            got, want = _tree(out), _tree(a.fixture)
            same = got == want
            print("fixture site is byte-identical to the importer's output" if same else "fixture site DIFFERS from the importer's output")
            for p in sorted(set(got) | set(want)):
                if got.get(p) != want.get(p):
                    if p not in got or p not in want:
                        print(f"  {p}: only in {'committed fixture' if p in want else 'importer output'}")
                    else:
                        g, w = got[p], want[p]
                        i = next((k for k in range(min(len(g), len(w))) if g[k] != w[k]), min(len(g), len(w)))
                        print(f"  {p}: first difference at byte {i} (sizes {len(g)} vs {len(w)}): "
                              f"output {g[max(0, i - 20):i + 20]!r} committed {w[max(0, i - 20):i + 20]!r}")
                    break
            sys.exit(0 if same else 1)
        if a.fixture.exists():
            for p in sorted(a.fixture.rglob("*"), reverse=True):
                if p.is_file():
                    p.chmod(0o644)
            shutil.rmtree(a.fixture)
        shutil.copytree(out, a.fixture)
        print(json.dumps(exp, indent=1, sort_keys=True))