"""Deterministic builder for the C16 contract fixtures (mimamsa-corpus-contract/2.0).

All identities, names, hashes and texts are synthetic. No text, file name or hash is taken from any real collection:
hashes are sha256("fixture:<label>"); parties are 'A B Example' and similar placeholders; URLs use the reserved
.invalid domain. Run:  python -I app/contract/fixtures/c16/build_fixtures.py [--check]
--check exits 1 when the committed files differ from what this script would write (the test runs the same check).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from mimamsa_contract.c16 import adapters, canonical  # noqa: E402
from mimamsa_contract.c16.schemas import CONTRACT_ID  # noqa: E402

CG = "CG-20261127-fixtures-0a1b2c3d"
COLL = "local:owner-collection-fixture"
TOOLS = {"name": "c16-fixture-producer", "version": "1.0.0", "commit": "c8fa5290", "config_sha256": None}
AUTHOR = "fixture-extractor"
REVIEWER = "fixture-independent-reviewer"


def H(label: str) -> str:
    return hashlib.sha256(f"fixture:{label}".encode()).hexdigest()


def U(reason="NOT_DETERMINED"):
    return {"unresolved": reason}


OCR = {"engine": "tesseract", "engine_version": "5.4.0", "languages": ["eng"], "dpi": 300, "page_segmentation_mode": "3",
       "preprocessing": ["deskew"], "config_sha256": H("ocr-config-eng-300")}

SHA = {k: H(k) for k in ("official-pdf", "scan-pdf", "word-screenshots", "mixed-pdf", "reconstructed-pdf", "extract-pdf",
                         "compilation-pdf", "word-native", "word-uninventoried", "restricted-copy", "duplicate-copy")}
DOC = {
    "official-pdf": "sc-2019-example-v-union-of-india-ca0001",
    "scan-pdf": "aft-2004-example-scan-oa0002",
    "word-screenshots": adapters.local_doc_id(SHA["word-screenshots"]),
    "mixed-pdf": "hc-2010-example-mixed-wp0003",
    "reconstructed-pdf": "aft-2004-example-scan-oa0002-reconstructed",
    "extract-pdf": "aft-2015-example-extract-oa0004",
    "compilation-pdf": "local-compilation-example-0005",
    "word-native": "local-word-native-example-0006",
    "word-uninventoried": adapters.local_doc_id(SHA["word-uninventoried"]),
}
WORD_PATH = "Army Rules/AR 22, 23, 30 - Lt Col A B Example v Union of India.docx"
WORD_PATH_2 = "Court Martial/AR 22 - Lt Col A B Example v Union of India.docx"


def v1_provenance(url=None, channel="MANUAL_OWNER"):
    return {"acquisition_channel": channel, "source_url": url, "retrieved_at": "2026-11-20T10:00:00Z" if url else None,
            "original_filename": None, "hf": None}


def restriction(elig="ELIGIBLE_ALL_USERS", rid=None):
    return {"access_marking": None, "eligibility": elig, "restriction_id": rid, "decided_by": "fixture", "basis": "synthetic fixture"}


def derivative(doc_id, name, version, basis, methods, units, with_text, reliability, quoting, images_total=0,
               images_done=0, ocr=False):
    return {"derivative_id": f"{doc_id}@{name}/{version}", "pipeline_name": name, "pipeline_version": version,
            "derivative_text_sha256": H(f"derivative:{doc_id}:{name}:{version}"), "pagination_basis": basis,
            "methods": methods, "ocr_config": OCR if ocr else None, "text_reliability": reliability,
            "quoting_permitted": quoting,
            "coverage": {"units_total": units, "units_with_text": with_text, "images_total": images_total,
                         "images_text_extracted": images_done}}


def identity(key, *, mime, fmt, pages, pagination, rep, work, derivs, images=None, research, prov=None,
             carrier="USER_SUPPLIED", observations=None, restr=None, alternates=None, history=None, integrity="DECLARED_HASH_ONLY"):
    rec = {"contract": CONTRACT_ID, "record_kind": "document_identity", "doc_id": DOC.get(key, key),
           "source_copy": {"sha256": SHA[key], "bytes": 100000 + len(key) * 1000, "mime_type": mime, "detected_format": fmt,
                           "page_count": pages, "physical_pagination": pagination,
                           "vault_path": f"vault/sha256/{SHA[key][:2]}/{SHA[key]}"},
           "representation": rep, "work_identity": work,
           "embedded_images": [] if images is None else images, "text_derivatives": derivs,
           "provenance": {"acquisition": prov or v1_provenance(), "carrier_provenance": carrier,
                          "observations": observations or [], "processing_history": history or []},
           "restriction": restr or restriction(),
           "integrity": {"source_integrity": integrity, "basis": "re-downloaded at a pinned revision and re-hashed (fixture)"
                         if integrity == "BYTE_VERIFIED" else "producer-computed SHA-256 (fixture)"},
           "research_eligibility": research, "corpus_generation_id": CG}
    if alternates:
        rec["alternate_copies"] = alternates
    return rec


def research(state, quoting, page_cite, whole, graph, basis):
    return {"state": state, "quoting_permitted": quoting, "source_page_citation_permitted": page_cite,
            "whole_work_claims_permitted": whole, "graph_evidence_permitted": graph, "basis": basis}


def judgment_work(doc_key, verification="CANDIDATE", basis="COVER_PAGE_EXTRACTED", numbers=()):
    return {"work_kind": "JUDGMENT", "judgment_id": U(), "graph_node_ref": f"JUD:{DOC[doc_key]}",
            "proceeding_numbers_as_printed": list(numbers), "identity_basis": basis, "identity_verification": verification,
            "rendition": {"rendition_kind": "UNDETERMINED", "language": "en"}}


def step(seq, op, tool, inputs, outputs, result="OK"):
    return {"seq": seq, "operation": op, "tool": {"name": tool, "version": "1.0.0", "commit": None, "config_sha256": None},
            "inputs": inputs, "outputs": outputs, "actor_kind": "AUTOMATED", "result": result}


def build_identities():
    ids = {}
    ids["official-pdf"] = identity(
        "official-pdf", mime="application/pdf", fmt="PDF", pages=12, pagination="PHYSICAL_PAGES",
        rep={"representation_kind": "NATIVE_DIGITAL_PDF", "origin_status": "CARRIER_ISSUED_COPY_CLAIMED",
             "content_scope": "WHOLE_WORK", "completeness": "COMPLETE",
             "completeness_basis": "printed page sequence 1-12 matches the 12 physical pages (fixture)"},
        work=judgment_work("official-pdf", numbers=["Civil Appeal No. 1 of 2019 (synthetic)"]),
        derivs=[derivative(DOC["official-pdf"], "mimamsa-corpus-text", "1.0.0", "SOURCE_PHYSICAL", ["NATIVE_TEXT_LAYER"],
                           12, 12, "reliable", True)],
        research=research("ELIGIBLE_FULL", True, True, True, True, ["TEXT_RELIABLE_NATIVE"]),
        prov=v1_provenance("https://judgments.example.invalid/ca0001.pdf", "CRAWLER"), carrier="GOVERNMENT_HOSTED_COPY",
        integrity="BYTE_VERIFIED",
        history=[step(1, "ACQUIRE", "crawler-fixture", [], [SHA["official-pdf"]]),
                 step(2, "EXTRACT_TEXT", "mimamsa-corpus-text", [SHA["official-pdf"]], [H("derivative:%s:mimamsa-corpus-text:1.0.0" % DOC["official-pdf"])])])
    ids["scan-pdf"] = identity(
        "scan-pdf", mime="application/pdf", fmt="PDF", pages=6, pagination="PHYSICAL_PAGES",
        rep={"representation_kind": "SCANNED_PDF", "origin_status": "CARRIER_ISSUED_COPY_CLAIMED", "content_scope": "WHOLE_WORK",
             "completeness": "NOT_CHECKED"},
        work=judgment_work("scan-pdf", numbers=["O.A. No. 2 of 2004 (synthetic)"]),
        derivs=[derivative(DOC["scan-pdf"], "mimamsa-ocr", "2.0.0", "SOURCE_PHYSICAL", ["OCR_PAGE_IMAGE"], 6, 6,
                           "partly_unreliable", False, ocr=True)],
        research=research("SEARCH_ONLY", False, True, False, True, ["OCR_TEXT_SEARCH_ONLY", "COMPLETENESS_NOT_CHECKED"]),
        prov=v1_provenance("https://tribunal.example.invalid/oa0002.pdf", "CRAWLER"), carrier="GOVERNMENT_HOSTED_COPY",
        alternates=[{"sha256": SHA["reconstructed-pdf"], "relation": "RECONSTRUCTION_OF_THIS", "verification": "EXTRACTED_STRUCTURE",
                     "basis": "built by the fixture OCR pipeline"}])
    wimg = SHA["word-screenshots"]
    images = [{"image_sequence_id": f"IMG:{wimg}:{n}", "sequence": n, "image_sha256": H(f"image:{n}"),
               "location": {"kind": "DOCX_PART", "container_part": f"word/media/image{n}.png", "pdf_page": None, "body_order": n},
               "mime_type": "image/png", "pixel_width": 1240, "pixel_height": 1754, "ocr_state": st,
               "ocr_derivative_sha256": H(f"image-ocr:{n}") if st == "DONE" else None}
              for n, st in ((1, "DONE"), (2, "DONE"), (3, "QUEUED"))]
    ids["word-screenshots"] = identity(
        "word-screenshots", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", fmt="DOCX",
        pages=None, pagination="NONE_FLOW_DOCUMENT",
        rep={"representation_kind": "WORD_WITH_EMBEDDED_IMAGES", "origin_status": "THIRD_PARTY_REPRODUCTION",
             "content_scope": "UNDETERMINED", "completeness": "NOT_CHECKED"},
        work={"work_kind": "JUDGMENT", "judgment_id": U(), "graph_node_ref": f"JUD:{DOC['word-screenshots']}",
              "proceeding_numbers_as_printed": [], "identity_basis": "FOLDER_OR_FILENAME_LABEL",
              "identity_verification": "CANDIDATE"},
        derivs=[derivative(DOC["word-screenshots"], "c16-docx", "1.0.0", "GENERATED_SEGMENT",
                           ["DOCX_XML", "OCR_EMBEDDED_IMAGE"], 4, 3, "partly_unreliable", False, 3, 2, ocr=True)],
        images=images,
        research=research("SEARCH_ONLY", False, False, False, True,
                          ["OCR_TEXT_SEARCH_ONLY", "GENERATED_PAGINATION", "EMBEDDED_IMAGES_NOT_EXTRACTED", "COMPLETENESS_NOT_CHECKED"]),
        observations=[{"collection": COLL, "relative_path": WORD_PATH, "inventory_id": "L-" + H("inv:1")[:20], "observed_at": None},
                      {"collection": COLL, "relative_path": WORD_PATH_2, "inventory_id": "L-" + H("inv:2")[:20], "observed_at": None}],
        history=[step(1, "HASH", "c16-local-reconcile", [], [wimg]),
                 step(2, "EXTRACT_IMAGES", "c16-docx", [wimg], [H(f"image:{n}") for n in (1, 2, 3)]),
                 step(3, "OCR", "c16-docx", [H("image:1"), H("image:2")], [H("image-ocr:1"), H("image-ocr:2")]),
                 step(4, "OCR", "c16-docx", [H("image:3")], [], "SKIPPED")])
    ids["mixed-pdf"] = identity(
        "mixed-pdf", mime="application/pdf", fmt="PDF", pages=8, pagination="PHYSICAL_PAGES",
        rep={"representation_kind": "MIXED_PDF", "origin_status": "ACQUIRED_COPY_ORIGIN_UNDETERMINED", "content_scope": "WHOLE_WORK",
             "completeness": "NOT_CHECKED"},
        work=judgment_work("mixed-pdf"),
        derivs=[derivative(DOC["mixed-pdf"], "mimamsa-ocr", "2.0.0", "SOURCE_PHYSICAL", ["NATIVE_TEXT_LAYER", "OCR_PAGE_IMAGE"],
                           8, 8, "partly_unreliable", False, ocr=True)],
        research=research("SEARCH_ONLY", False, True, False, True, ["OCR_TEXT_SEARCH_ONLY", "COMPLETENESS_NOT_CHECKED"]))
    ids["reconstructed-pdf"] = identity(
        "reconstructed-pdf", mime="application/pdf", fmt="PDF", pages=6, pagination="PHYSICAL_PAGES",
        rep={"representation_kind": "RECONSTRUCTED_SEARCHABLE_PDF", "origin_status": "LOCALLY_RECONSTRUCTED",
             "content_scope": "WHOLE_WORK", "completeness": "NOT_CHECKED", "reconstructed_from_sha256": [SHA["scan-pdf"]],
             "reconstruction_method": "OCR_TEXT_LAYER_ADDED",
             "page_mapping": {"original_sha256": SHA["scan-pdf"], "basis": "ONE_TO_ONE_PAGE_HASH_CHECKED", "offset": 0}},
        work=judgment_work("reconstructed-pdf"),
        derivs=[derivative(DOC["reconstructed-pdf"], "mimamsa-ocr", "2.0.0", "RECONSTRUCTED_PDF", ["OCR_PAGE_IMAGE"], 6, 6,
                           "partly_unreliable", False, ocr=True)],
        research=research("SEARCH_ONLY", False, True, False, True, ["OCR_TEXT_SEARCH_ONLY", "COMPLETENESS_NOT_CHECKED"]),
        alternates=[{"sha256": SHA["scan-pdf"], "relation": "THIS_RECONSTRUCTED_FROM", "verification": "EXTRACTED_STRUCTURE",
                     "basis": "page images re-hashed one to one (fixture)"}])
    ids["reconstructed-pdf"]["work_identity"]["graph_node_ref"] = f"JUD:{DOC['scan-pdf']}"
    ids["extract-pdf"] = identity(
        "extract-pdf", mime="application/pdf", fmt="PDF", pages=2, pagination="PHYSICAL_PAGES",
        rep={"representation_kind": "NATIVE_DIGITAL_PDF", "origin_status": "ACQUIRED_COPY_ORIGIN_UNDETERMINED",
             "content_scope": "EXTRACT", "completeness": "PARTIAL_EXTRACT",
             "extract_scope": {"description": "operative order only (fixture)", "work_pages": {"from_page": 14, "to_page": 15}}},
        work=judgment_work("extract-pdf"),
        derivs=[derivative(DOC["extract-pdf"], "mimamsa-corpus-text", "1.0.0", "SOURCE_PHYSICAL", ["NATIVE_TEXT_LAYER"], 2, 2,
                           "reliable", True)],
        research=research("ELIGIBLE_FULL", True, True, False, True, ["TEXT_RELIABLE_NATIVE", "PARTIAL_EXTRACT"]))
    ids["compilation-pdf"] = identity(
        "compilation-pdf", mime="application/pdf", fmt="PDF", pages=30, pagination="PHYSICAL_PAGES",
        rep={"representation_kind": "NATIVE_DIGITAL_PDF", "origin_status": "ACQUIRED_COPY_ORIGIN_UNDETERMINED",
             "content_scope": "COMPILATION", "completeness": "NOT_CHECKED",
             "members": [{"member_seq": 1, "work_kind": "JUDGMENT", "work_ref": U(), "label_as_printed": "First example judgment",
                          "pages": {"from_page": 1, "to_page": 12}, "member_completeness": "NOT_CHECKED"},
                         {"member_seq": 2, "work_kind": "JUDGMENT", "work_ref": "JUD:JG-" + H("jg:2")[:12],
                          "label_as_printed": "Second example judgment", "pages": {"from_page": 13, "to_page": 22},
                          "member_completeness": "NOT_CHECKED"},
                         {"member_seq": 3, "work_kind": "ORDER", "work_ref": U(), "label_as_printed": None,
                          "pages": U("NOT_YET_PROCESSED"), "member_completeness": "PARTIAL_EXTRACT"}]},
        work={"work_kind": "COMPILATION_CONTAINER", "graph_node_ref": U(), "proceeding_numbers_as_printed": [],
              "identity_basis": "NOT_ESTABLISHED", "identity_verification": "CANDIDATE"},
        derivs=[derivative(DOC["compilation-pdf"], "mimamsa-corpus-text", "1.0.0", "SOURCE_PHYSICAL", ["NATIVE_TEXT_LAYER"], 30, 30,
                           "reliable", True)],
        research=research("ELIGIBLE_FULL", True, True, False, True, ["TEXT_RELIABLE_NATIVE", "COMPILATION_MEMBER_BOUNDARIES"]))
    ids["word-native"] = identity(
        "word-native", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", fmt="DOCX",
        pages=None, pagination="NONE_FLOW_DOCUMENT",
        rep={"representation_kind": "WORD_NATIVE_TEXT", "origin_status": "THIRD_PARTY_REPRODUCTION", "content_scope": "WHOLE_WORK",
             "completeness": "NOT_CHECKED"},
        work={"work_kind": "COMMENTARY_OR_NOTE", "graph_node_ref": U(), "proceeding_numbers_as_printed": [],
              "identity_basis": "NOT_ESTABLISHED", "identity_verification": "CANDIDATE"},
        derivs=[derivative(DOC["word-native"], "c16-docx", "1.0.0", "GENERATED_SEGMENT", ["DOCX_XML"], 5, 5, "reliable", True)],
        research=research("ELIGIBLE_FULL", True, False, False, True, ["GENERATED_PAGINATION", "COMPLETENESS_NOT_CHECKED"]))
    ids["word-uninventoried"] = identity(
        "word-uninventoried", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", fmt="DOCX",
        pages=None, pagination="NONE_FLOW_DOCUMENT",
        rep={"representation_kind": "WORD_IMAGES_NOT_INVENTORIED", "origin_status": "ACQUIRED_COPY_ORIGIN_UNDETERMINED",
             "content_scope": "UNDETERMINED", "completeness": "NOT_CHECKED"},
        work={"work_kind": "UNKNOWN", "graph_node_ref": U(), "proceeding_numbers_as_printed": [],
              "identity_basis": "NOT_ESTABLISHED", "identity_verification": "CANDIDATE"},
        derivs=[derivative(DOC["word-uninventoried"], "c16-local-reconcile", "2", "GENERATED_SEGMENT", ["DOCX_XML"], 1, 1,
                           "not_assessed", False, U("NOT_YET_PROCESSED"), 0)],
        images=U("NOT_YET_PROCESSED"),
        research=research("NOT_ASSESSED", False, False, False, False, ["ELIGIBILITY_NOT_ASSESSED", "EMBEDDED_IMAGES_NOT_EXTRACTED"]))
    ids["duplicate-copy"] = identity(
        "duplicate-copy", mime="application/pdf", fmt="PDF", pages=3, pagination="PHYSICAL_PAGES",
        rep={"representation_kind": "NATIVE_DIGITAL_PDF", "origin_status": "ACQUIRED_COPY_ORIGIN_UNDETERMINED",
             "content_scope": "UNDETERMINED", "completeness": "NOT_CHECKED"},
        work={"work_kind": "UNKNOWN", "graph_node_ref": U(), "proceeding_numbers_as_printed": [],
              "identity_basis": "NOT_ESTABLISHED", "identity_verification": "CANDIDATE"},
        derivs=[], research=research("NOT_ASSESSED", False, False, False, False, ["ELIGIBILITY_NOT_ASSESSED"]))
    return ids


def review_record(rid, subject_id, author=AUTHOR, reviewer=REVIEWER):
    return {"contract_version": "1.0.0", "record_kind": "reviewed_record", "review_record_id": rid,
            "subject": {"kind": "candidate", "id": subject_id}, "axis": "evidence_fidelity",
            "from_value": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "to_value": "DOCUMENTARY_CHECKED",
            "reviewer": {"reviewer_id": reviewer, "name_or_role": "synthetic fixture reviewer", "kind": "HUMAN"},
            "method": "page image compared with the anchored span (synthetic fixture)", "decided_at": "2026-11-27T00:00:00Z",
            "record_location": {"path": "reviews/fixture.md", "commit": "c8fa5290"},
            "reviewed_artefact": {"author_id": author, "reviewed_commit": "c8fa5290"}}


def binding(rec):
    return {"review_record_id": rec["review_record_id"], "review_record_sha256": canonical.record_sha256(rec),
            "reviewed_commit": rec["reviewed_artefact"]["reviewed_commit"], "reviewer_id": rec["reviewer"]["reviewer_id"],
            "reviewer_kind": rec["reviewer"]["kind"], "author_id": rec["reviewed_artefact"]["author_id"]}


def anchor(**kw):
    a = {"contract": CONTRACT_ID, "record_kind": "evidence_anchor", "anchor_id": "", "image_sha256": None,
         "derivative_text_sha256": None, "text_span": None, "bbox": None, "quote": None,
         "verification": {"state": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None}}
    a.update(kw)
    a["anchor_id"] = canonical.anchor_id(a)
    return a


def build_anchors(ids):
    def der(key):
        return ids[key]["text_derivatives"][0]
    A = {}
    d = der("official-pdf")
    A["native"] = anchor(doc_id=DOC["official-pdf"], original_sha256=SHA["official-pdf"], representation_sha256=SHA["official-pdf"],
                         derivative_text_sha256=d["derivative_text_sha256"],
                         locator={"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": 3, "printed_page_label": "3",
                                  "paragraph_label": "12", "citable_as_source_page": True},
                         text_span={"passage_id": "p3-2", "char_start": 120, "char_end": 188, "text_sha256": H("span:native")},
                         bbox={"unit": "PDF_POINT", "space": "SOURCE_PAGE", "x0": 72, "y0": 200.5, "x1": 520, "y1": 236},
                         extraction={"method": "NATIVE_TEXT_LAYER", "pipeline_name": "mimamsa-corpus-text", "pipeline_version": "1.0.0", "ocr_config": None},
                         quality={"text_reliability": "reliable", "ocr_mean_confidence": None, "low_confidence": False},
                         quoting_permitted=True, quote="(synthetic quoted text for the fixture)")
    A["native_cite_judgment"] = anchor(
        doc_id=DOC["official-pdf"], original_sha256=SHA["official-pdf"], representation_sha256=SHA["official-pdf"],
        derivative_text_sha256=d["derivative_text_sha256"],
        locator={"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": 7, "citable_as_source_page": True},
        text_span={"passage_id": "p7-1", "char_start": 0, "char_end": 64, "text_sha256": H("span:cite-judgment")},
        extraction={"method": "NATIVE_TEXT_LAYER", "pipeline_name": "mimamsa-corpus-text", "pipeline_version": "1.0.0", "ocr_config": None},
        quality={"text_reliability": "reliable", "ocr_mean_confidence": None, "low_confidence": False}, quoting_permitted=True)
    A["native_follows"] = anchor(
        doc_id=DOC["official-pdf"], original_sha256=SHA["official-pdf"], representation_sha256=SHA["official-pdf"],
        derivative_text_sha256=d["derivative_text_sha256"],
        locator={"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": 8, "paragraph_label": "21", "citable_as_source_page": True},
        text_span={"passage_id": "p8-3", "char_start": 300, "char_end": 410, "text_sha256": H("span:follows")},
        extraction={"method": "NATIVE_TEXT_LAYER", "pipeline_name": "mimamsa-corpus-text", "pipeline_version": "1.0.0", "ocr_config": None},
        quality={"text_reliability": "reliable", "ocr_mean_confidence": None, "low_confidence": False}, quoting_permitted=True)
    d = der("scan-pdf")
    A["ocr_page"] = anchor(doc_id=DOC["scan-pdf"], original_sha256=SHA["scan-pdf"], representation_sha256=SHA["scan-pdf"],
                           derivative_text_sha256=d["derivative_text_sha256"], image_sha256=H("page-image:scan:2"),
                           locator={"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": 2, "printed_page_label": None,
                                    "citable_as_source_page": True},
                           text_span={"passage_id": None, "char_start": 10, "char_end": 52, "text_sha256": H("span:ocr")},
                           bbox={"unit": "IMAGE_PIXEL", "space": "SOURCE_PAGE", "x0": 210, "y0": 640, "x1": 2210, "y1": 720},
                           extraction={"method": "OCR_PAGE_IMAGE", "pipeline_name": "mimamsa-ocr", "pipeline_version": "2.0.0", "ocr_config": OCR},
                           quality={"text_reliability": "partly_unreliable", "ocr_mean_confidence": 81.5, "low_confidence": False},
                           quoting_permitted=False)
    w = SHA["word-screenshots"]
    d = der("word-screenshots")
    A["docx_image_ocr"] = anchor(doc_id=DOC["word-screenshots"], original_sha256=w, representation_sha256=w,
                                 derivative_text_sha256=H("image-ocr:2"), image_sha256=H("image:2"),
                                 locator={"kind": "IMAGE_SEQUENCE", "image_sequence_id": f"IMG:{w}:2", "physical_page": None,
                                          "citable_as_source_page": False},
                                 text_span={"passage_id": None, "char_start": 0, "char_end": 48, "text_sha256": H("span:docx-image")},
                                 bbox={"unit": "IMAGE_PIXEL", "space": "IMAGE", "x0": 40, "y0": 300, "x1": 1180, "y1": 352},
                                 extraction={"method": "OCR_EMBEDDED_IMAGE", "pipeline_name": "c16-docx", "pipeline_version": "1.0.0", "ocr_config": OCR},
                                 quality={"text_reliability": "partly_unreliable", "ocr_mean_confidence": 74.25, "low_confidence": True},
                                 quoting_permitted=False)
    A["docx_generated"] = anchor(doc_id=DOC["word-screenshots"], original_sha256=w, representation_sha256=w,
                                 derivative_text_sha256=d["derivative_text_sha256"],
                                 locator={"kind": "GENERATED_SEGMENT", "generated_segment": 1, "physical_page": None,
                                          "paragraph_index": 2, "citable_as_source_page": False},
                                 text_span={"passage_id": "p1-1", "char_start": 0, "char_end": 30, "text_sha256": H("span:docx-text")},
                                 extraction={"method": "DOCX_XML", "pipeline_name": "c16-docx", "pipeline_version": "1.0.0", "ocr_config": None},
                                 quality={"text_reliability": "reliable", "ocr_mean_confidence": None, "low_confidence": False},
                                 quoting_permitted=False)
    d = der("reconstructed-pdf")
    A["reconstructed"] = anchor(doc_id=DOC["scan-pdf"], original_sha256=SHA["scan-pdf"], representation_sha256=SHA["reconstructed-pdf"],
                                derivative_text_sha256=d["derivative_text_sha256"],
                                locator={"kind": "RECONSTRUCTED_PAGE", "reconstructed_page": 4, "physical_page": 4,
                                         "citable_as_source_page": True},
                                page_mapping_basis="ONE_TO_ONE_PAGE_HASH_CHECKED",
                                text_span={"passage_id": None, "char_start": 5, "char_end": 90, "text_sha256": H("span:recon")},
                                extraction={"method": "OCR_PAGE_IMAGE", "pipeline_name": "mimamsa-ocr", "pipeline_version": "2.0.0", "ocr_config": OCR},
                                quality={"text_reliability": "partly_unreliable", "ocr_mean_confidence": U("NOT_DETERMINED"), "low_confidence": False},
                                quoting_permitted=False)
    d = der("extract-pdf")
    A["extract"] = anchor(doc_id=DOC["extract-pdf"], original_sha256=SHA["extract-pdf"], representation_sha256=SHA["extract-pdf"],
                          derivative_text_sha256=d["derivative_text_sha256"],
                          locator={"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": 1, "printed_page_label": "14",
                                   "citable_as_source_page": True},
                          text_span={"passage_id": "p1-1", "char_start": 0, "char_end": 40, "text_sha256": H("span:extract")},
                          extraction={"method": "NATIVE_TEXT_LAYER", "pipeline_name": "mimamsa-corpus-text", "pipeline_version": "1.0.0", "ocr_config": None},
                          quality={"text_reliability": "reliable", "ocr_mean_confidence": None, "low_confidence": False},
                          quoting_permitted=True)
    return A


def rel(category, subject_key, target, basis, anchors, *, verification="CANDIDATE", legal=False, review=None,
        proposition=None, date=None, uncertainty="Synthetic fixture relationship.", rule="C16-FIXTURE-RULE", subject_doc=None,
        subject_sha=None):
    r = {"contract": CONTRACT_ID, "record_kind": "corpus_relationship", "relationship_id": "", "category": category,
         "subject": {"doc_id": subject_doc or DOC[subject_key], "source_copy_sha256": subject_sha or SHA[subject_key],
                     "graph_node_ref": f"JUD:{DOC[subject_key]}"},
         "target": target, "evidentiary_basis": basis,
         "source": {"producer": TOOLS, "rule_id": rule, "rule_version": "1.0", "author_id": "fixture-extractor"},
         "classification_provenance": None, "anchors": sorted(anchors), "verification": verification,
         "review_ref": review, "review_binding": None, "approval_ref": None, "validates_relationship_id": None,
         "proposition_ref": proposition,
         "temporal_scope": {"from": date, "from_status": "AS_OF_SOURCE_DATE", "to": None, "to_status": "NOT_APPLICABLE"},
         "has_legal_effect": legal, "is_finding": verification == "DOCUMENTARY_CHECKED", "uncertainty": uncertainty}
    r["relationship_id"] = canonical.relationship_id(r)
    r["graph_projection"] = {k: v for k, v in (("edge_type", adapters.graph_projection(r)["edge"]["type"]),
                                               ("origin", adapters.graph_projection(r)["edge"]["origin"]))}
    return r


def build_relationships(ids, A):
    R = []
    w = DOC["word-screenshots"]
    for path, inv in ((WORD_PATH, "L-" + H("inv:1")[:20]), (WORD_PATH_2, "L-" + H("inv:2")[:20])):
        R += adapters.classify_path(path, doc_id=w, sha=SHA["word-screenshots"], subject_node=f"JUD:{w}", collection=COLL,
                                    inventory_id=inv)
    R.append(rel("cites_provision", "word-screenshots", {"resolved": True, "node_id": "PROV:AR-1954:r.22"}, "DOCUMENT_TEXT_EXTRACTED",
                 [A["docx_image_ocr"]["anchor_id"]], date=None,
                 uncertainty="OCR of an embedded screenshot; the citation is a candidate and the text may be misread."))
    R[-1]["temporal_scope"] = {"from": None, "from_status": "NOT_RECORDED", "to": None, "to_status": "NOT_APPLICABLE"}
    R[-1]["relationship_id"] = canonical.relationship_id(R[-1])
    R.append(rel("cites_provision", "official-pdf", {"resolved": True, "node_id": "PROV:AA-1950:s.69"}, "DOCUMENT_TEXT_EXTRACTED",
                 [A["native"]["anchor_id"]], date="2019-03-01",
                 uncertainty="Extracted citation candidate; a citation does not establish how the source treated the target."))
    R.append(rel("cites_provision", "official-pdf", {"resolved": True, "node_id": "PROV:AR-1954:r.22"}, "DOCUMENT_TEXT_REVIEWED",
                 [A["native"]["anchor_id"]], verification="DOCUMENTARY_CHECKED", review="RV-FIXTURE-0001", date="2019-03-01",
                 uncertainty="Citation checked against the page by an independent documentary review (fixture); not a legal finding."))
    R.append(rel("refers_to_judgment", "official-pdf", {"resolved": True, "node_id": "JUD:JG-" + H("jg:cited")[:12]},
                 "DOCUMENT_TEXT_EXTRACTED", [A["native_cite_judgment"]["anchor_id"]], date="2019-03-01",
                 uncertainty="Extracted citation candidate; a citation does not establish how the source treated the target."))
    R.append(rel("follows", "official-pdf", {"resolved": False, "node_id": None, "raw_reference": "(synthetic) Example v. Union, 2001",
                                             "unresolved": U("AMBIGUOUS_REFERENCE")},
                 "DOCUMENT_TEXT_EXTRACTED", [A["native_follows"]["anchor_id"]], legal=True, proposition=U(), date="2019-03-01",
                 uncertainty="Treatment candidate; requires legal review before any reliance."))
    R.append(rel("interprets_provision", "official-pdf", {"resolved": True, "node_id": "PROV:AA-1950:s.69"}, "DOCUMENT_TEXT_EXTRACTED",
                 [A["native_follows"]["anchor_id"]], legal=True, date="2019-03-01",
                 uncertainty="Interpretation candidate; requires legal review before any reliance."))
    checked = next(r for r in R if r["verification"] == "DOCUMENTARY_CHECKED")
    rv1 = review_record("RV-FIXTURE-0001", checked["relationship_id"])
    checked["review_binding"] = binding(rv1)
    REVIEWS.append(rv1)
    return R


REVIEWS: list[dict] = []


def bind_native_anchor(A):
    rv2 = review_record("RV-FIXTURE-0002", A["native"]["anchor_id"])
    A["native"]["verification"] = {"state": "DOCUMENTARY_CHECKED", "review_ref": "RV-FIXTURE-0002", "review_binding": binding(rv2)}
    REVIEWS.append(rv2)


def tax(node_id, level, label, parents, *, code=None, prov=None, basis, verification, maps=None, aliases=(), src=None):
    t = {"contract": CONTRACT_ID, "record_kind": "taxonomy_node", "node_id": node_id, "level": level, "label": label,
         "parent_ids": sorted(parents), "instrument_code": code, "provision": prov, "maps_to_subject": maps,
         "aliases": list(aliases), "taxonomy_version": "c16-taxonomy-1.0", "source": {"basis": basis, **(src or {})},
         "verification": verification}
    return t


def build_taxonomy():
    T = [tax("SUBJ:court_martial", "SUBJECT", "Court martial", [], basis="CONTROLLED_TOPIC_LIST", verification="CURATED_NAVIGATION"),
         tax("SUBJ:local:army-rules", "SUBJECT", "Army Rules", [], basis="OWNER_FOLDER", verification="CURATED_NAVIGATION",
             src={"collection": COLL, "relative_path": "Army Rules"}),
         tax("SUBJ:local:court-martial", "SUBJECT", "Court Martial", [], basis="OWNER_FOLDER", verification="CURATED_NAVIGATION",
             maps="SUBJ:court_martial", src={"collection": COLL, "relative_path": "Court Martial"}),
         tax("INSTCODE:AR-1954", "STATUTE", "Army Rules, 1954", ["SUBJ:court_martial", "SUBJ:local:army-rules"], code="AR-1954",
             basis="GRAPH_INSTRUMENT", verification="CURATED_NAVIGATION", aliases=["AR"]),
         tax("INSTCODE:AA-1950", "STATUTE", "Army Act, 1950", ["SUBJ:court_martial"], code="AA-1950", basis="GRAPH_INSTRUMENT",
             verification="CURATED_NAVIGATION", aliases=["AA"]),
         tax("CHAP:AR-1954:V", "CHAPTER", "Chapter V (fixture label)", ["INSTCODE:AR-1954"], code="AR-1954",
             basis="TABLE_OF_CONTENTS", verification="EXTRACTED_STRUCTURE", src={"doc_id": "rules-army-rules-1954", "page": 4})]
    for n in ("22", "23", "30"):
        T.append(tax(f"PROV:AR-1954:r.{n}", "PROVISION", f"Rule {n} (fixture label)", ["CHAP:AR-1954:V"], code="AR-1954",
                     prov={"prefix": "r", "number": n, "sub_provision": None}, basis="TABLE_OF_CONTENTS",
                     verification="EXTRACTED_STRUCTURE", aliases=[f"AR {n}"], src={"doc_id": "rules-army-rules-1954", "page": 4}))
    T.append(tax("PROV:AA-1950:s.69", "PROVISION", "Section 69 (fixture label)", ["INSTCODE:AA-1950"], code="AA-1950",
                 prov={"prefix": "s", "number": "69", "sub_provision": None}, basis="GRAPH_PROVISION", verification="EXTRACTED_STRUCTURE"))
    return T


GATE_IDS = ["G01_HASH_VERIFIED", "G02_FORMAT_DETECTED", "G03_RESTRICTED_REGISTER", "G04_ACCESS_MARKING_REVIEWED",
            "G05_IDENTITY_RECORD_VALID", "G06_TEXT_DERIVATIVE_VERIFIED", "G07_EMBEDDED_IMAGES_ACCOUNTED",
            "G08_RELEVANCE_ASSESSED", "G09_DUPLICATE_RESOLVED", "G10_SCHEMA_VALID"]


def gates(**over):
    """Default: G01 NOT_RUN (declared hash only), every other gate PASS with evidence; override per case."""
    out = []
    for g in GATE_IDS:
        res = over.get(g, "NOT_RUN" if g == "G01_HASH_VERIFIED" else "PASS")
        out.append({"gate_id": g, "result": res, "evidence_ref": f"fixture evidence for {g}" if res == "PASS" else None})
    return out


def receipts(g, sha, derivative=None):
    """Typed receipts for every PASS gate (C01-R1): bound to the copy, derivative, rule, config and register revision."""
    kinds = {"G01_HASH_VERIFIED": "HASH_REDOWNLOAD", "G02_FORMAT_DETECTED": "FORMAT_DETECTION", "G03_RESTRICTED_REGISTER": "REGISTER_CHECK",
             "G04_ACCESS_MARKING_REVIEWED": "MARKING_SCREEN", "G05_IDENTITY_RECORD_VALID": "IDENTITY_VALIDATION",
             "G06_TEXT_DERIVATIVE_VERIFIED": "DERIVATIVE_VERIFICATION", "G07_EMBEDDED_IMAGES_ACCOUNTED": "IMAGE_ACCOUNTING",
             "G08_RELEVANCE_ASSESSED": "RELEVANCE_DECISION", "G09_DUPLICATE_RESOLVED": "DUPLICATE_RESOLUTION", "G10_SCHEMA_VALID": "SCHEMA_VALIDATION"}
    for x in g:
        if x["result"] == "PASS":
            x["receipt"] = {"receipt_kind": kinds[x["gate_id"]], "subject_sha256": sha,
                            "derivative_sha256": derivative if x["gate_id"] == "G06_TEXT_DERIVATIVE_VERIFIED" else None,
                            "rule_id": "c16-gate-" + x["gate_id"][:3].lower(), "rule_version": "1.0", "config_sha256": H("gate-config"),
                            "register_sha256": H("register-fixture") if x["gate_id"] == "G03_RESTRICTED_REGISTER" else None,
                            "outcome": "PASS", "receipt_sha256": H(f"receipt:{sha}:{x['gate_id']}")}
    return g


def admission(key, decision, g, *, eligible=False, scope=None, dup=None, rid=None, reasons=("fixture",), doc=None, sha=None, disp=None,
              revision=1, supersedes=None, gen=CG):
    a = {"contract": CONTRACT_ID, "record_kind": "corpus_admission", "admission_id": "", "revision": revision,
         "supersedes_admission_id": supersedes,
         "subject": {"doc_id": doc or DOC.get(key, key), "source_copy_sha256": sha or SHA[key]}, "corpus_generation_id": gen,
         "decision": decision, "source_disposition": disp, "duplicate_of": dup, "restriction_id": rid, "gates": g,
         "application_eligible": eligible, "service_scope": scope or ("SEARCHABLE" if eligible else "NONE"),
         "publication_effect": "NONE", "legal_effect": "NONE",
         "decided_by": {"kind": "AUTOMATED_RULE", "id": "c16-fixture-admission"}, "decided_at": None,
         "rule_set": {"id": "c16-admission", "version": "1.1"}, "reasons": list(reasons)}
    a["admission_id"] = canonical.admission_id(a)
    return a


def build_admissions():
    NA7 = {"G07_EMBEDDED_IMAGES_ACCOUNTED": "NOT_APPLICABLE"}
    w1 = admission("word-screenshots", "HELD_OCR_REQUIRED", gates(G07_EMBEDDED_IMAGES_ACCOUNTED="NOT_RUN"),
                   reasons=["embedded images queued for OCR"], disp={"system": "c16-local-reconcile", "value": "NEW_DOCUMENT", "secondary_flags": []})
    w2 = admission("word-screenshots", "HELD_EXTRACTION_INCOMPLETE", gates(G07_EMBEDDED_IMAGES_ACCOUNTED="FAIL"),
                   reasons=["embedded image 3 not yet read (ocr_state QUEUED)"], revision=2, supersedes=w1["admission_id"],
                   disp={"system": "c16-local-reconcile", "value": "NEW_DOCUMENT", "secondary_flags": []})
    return [
        admission("official-pdf", "ADMITTED_AS_PRIMARY",
                  receipts(gates(G01_HASH_VERIFIED="PASS", **NA7), SHA["official-pdf"],
                           H("derivative:%s:mimamsa-corpus-text:1.0.0" % DOC["official-pdf"])), eligible=True,
                  reasons=["all gates passed with evidence (fixture)"]),
        admission("scan-pdf", "HELD_INTEGRITY_UNVERIFIED", gates(**NA7), reasons=["hash declared, not re-verified"]),
        admission("mixed-pdf", "HELD_RELEVANCE_UNRESOLVED", gates(G08_RELEVANCE_ASSESSED="NOT_RUN", **NA7), reasons=["relevance not assessed"]),
        admission("reconstructed-pdf", "ADMITTED_AS_ALTERNATE_COPY", gates(**NA7),
                  dup={"sha256": SHA["scan-pdf"], "doc_id": DOC["scan-pdf"], "relation": "RECONSTRUCTION_OF", "held_at": None},
                  reasons=["searchable reconstruction kept beside its original; original remains the evidence copy"]),
        admission("extract-pdf", "HELD_IDENTITY_UNRESOLVED", gates(G09_DUPLICATE_RESOLVED="NOT_RUN", **NA7), reasons=["work identity open"]),
        admission("compilation-pdf", "HELD_IDENTITY_UNRESOLVED", gates(G09_DUPLICATE_RESOLVED="NOT_RUN", **NA7), reasons=["member identities open"]),
        admission("word-native", "HELD_INTEGRITY_UNVERIFIED", gates(**NA7), reasons=["hash declared, not re-verified"]),
        admission("word-uninventoried", "HELD_EXTRACTION_INCOMPLETE",
                  gates(G03_RESTRICTED_REGISTER="NOT_RUN", G04_ACCESS_MARKING_REVIEWED="NOT_RUN", G05_IDENTITY_RECORD_VALID="NOT_RUN",
                        G06_TEXT_DERIVATIVE_VERIFIED="NOT_RUN", G07_EMBEDDED_IMAGES_ACCOUNTED="NOT_RUN", G08_RELEVANCE_ASSESSED="NOT_RUN",
                        G09_DUPLICATE_RESOLVED="NOT_RUN"),
                  reasons=["embedded images not inventoried"]),
        admission("duplicate-copy", "REJECTED_EXACT_DUPLICATE",
                  gates(G06_TEXT_DERIVATIVE_VERIFIED="NOT_APPLICABLE", **NA7),
                  dup={"sha256": SHA["duplicate-copy"], "doc_id": None, "relation": "BYTE_IDENTICAL", "held_at": "hf:fixture-revision"},
                  reasons=["bytes already held at the canonical revision"]),
        w1, w2,
    ]


def legally_validated(base):
    r = {"contract": CONTRACT_ID, "record_kind": "corpus_relationship", "relationship_id": "", "category": "legally_validated",
         "subject": copy.deepcopy(base["subject"]), "target": copy.deepcopy(base["target"]), "evidentiary_basis": "LEGAL_REVIEW",
         "source": {"producer": TOOLS, "rule_id": "LEGAL-REVIEW", "rule_version": "1.0", "author_id": None},
         "classification_provenance": None, "anchors": [], "verification": "LEGAL_REVIEWED", "review_ref": None,
         "review_binding": None, "approval_ref": "AP-FIXTURE-0001", "validates_relationship_id": base["relationship_id"],
         "proposition_ref": None,
         "temporal_scope": {"from": None, "from_status": "NOT_DETERMINED", "to": None, "to_status": "NOT_DETERMINED"},
         "has_legal_effect": True, "is_finding": True,
         "uncertainty": "Representation test only: a legal approval overlay (impossible while AUTH-LEDGER is at version 0)."}
    r["relationship_id"] = canonical.relationship_id(r)
    return r


STEMS = {"identities": "document_identity", "anchors": "evidence_anchor", "relationships": "corpus_relationship",
         "taxonomy": "taxonomy_node", "admissions": "corpus_admission", "reviewed_records": "reviewed_record"}
GIT_PIN = "c8fa5290a7f03ed47f57ba82cc57503005e11d48"


def exchange_files(pop: dict[str, list[dict]], *, manifest_edit=None, raw: dict[str, bytes] | None = None,
                   gen=CG, external=None) -> dict[str, bytes]:
    files = {f"{stem}.jsonl": canonical.dumps_jsonl(recs) for stem, recs in pop.items()}
    files.update(raw or {})
    man = {"contract": CONTRACT_ID, "record_kind": "corpus_generation_manifest", "corpus_generation_id": gen, "built_at": None,
           "pinned_inputs": {"hf": [], "git": [{"commit": GIT_PIN, "purpose": "contract, tools and fixtures"}],
                             "restricted_register_sha256": H("register-fixture"), "tools": [TOOLS]},
           "files": [{"path": name, "record_kind": STEMS[name.split(".")[0]], "sha256": hashlib.sha256(data).hexdigest(),
                      "records": sum(1 for x in data.split(b"\n") if x)} for name, data in sorted(files.items())
                     if name.split(".")[0] in STEMS],
           "registries": {"instrument_codes": ["AA-1950", "AFA-1950", "AFT-2007", "AFT-PR-2008", "AR-1954", "BNS-2023", "BNSS-2023",
                                               "BSA-2023", "CRPC-1973", "IEA-1872", "IPC-1860", "NA-1957"],
                          "external_judgments": sorted(external if external is not None else
                                                       ["JUD:JG-" + H("jg:cited")[:12], "JUD:JG-" + H("jg:2")[:12]])}}
    if manifest_edit:
        manifest_edit(man)
    files["GENERATION.json"] = json.dumps(man, indent=1, sort_keys=True).encode() + b"\n"
    return files


def negatives(ids, A, R, T, ADM):
    N = {}

    def m(name, rec, expect_code, path_hint=None, ledger=0):
        N[name] = (rec, expect_code, path_hint, ledger)

    folder = next(r for r in R if r["evidentiary_basis"] == "FOLDER_PATH")
    x = copy.deepcopy(folder)
    x.update(verification="DOCUMENTARY_CHECKED", is_finding=True, review_ref="RV-FIXTURE-0002")
    m("N01_folder_classification_as_verified_finding", x, "SCHEMA", "verification")
    x = copy.deepcopy(ids["reconstructed-pdf"])
    x["representation"]["origin_status"] = "CARRIER_ISSUED_COPY_CLAIMED"
    m("N02_reconstructed_pdf_claims_original", x, "SCHEMA", "origin_status")
    x = copy.deepcopy(ids["extract-pdf"])
    x["representation"]["completeness"] = "COMPLETE"
    x["representation"]["completeness_basis"] = "claimed"
    m("N03_extract_claims_complete", x, "SCHEMA", "completeness")
    x = copy.deepcopy(ids["official-pdf"])
    del x["source_copy"]["sha256"]
    m("N04_missing_mandatory_sha256", x, "SCHEMA", "source_copy")
    x = copy.deepcopy(A["ocr_page"])
    x["quoting_permitted"] = True
    m("N05_ocr_anchor_quotable", x, "SCHEMA", "quoting_permitted")
    lv = legally_validated(next(r for r in R if r["category"] == "follows"))
    m("N06_legally_validated_at_ledger_v0", lv, "LEDGER_V0_NO_APPROVAL", None, 0)
    x = copy.deepcopy(lv)
    x["approval_ref"] = None
    m("N07_legally_validated_without_approval", x, "SCHEMA", "approval_ref", 1)
    x = copy.deepcopy(ADM[1])
    x.update(application_eligible=True, decision="ADMITTED_AS_PRIMARY")
    x["admission_id"] = canonical.admission_id(x)
    m("N08_admission_eligible_without_mandatory_pass", x, "SCHEMA", "gates")
    x = copy.deepcopy(next(r for r in R if r["category"] == "follows"))
    x["anchors"] = []
    x["relationship_id"] = canonical.relationship_id(x)
    m("N09_treatment_without_anchor", x, "SCHEMA", "anchors")
    x = copy.deepcopy(ids["word-screenshots"])
    x["embedded_images"] = []
    m("N10_word_screenshots_without_image_inventory", x, "SCHEMA", "embedded_images")
    x = copy.deepcopy(A["docx_generated"])
    x["locator"]["citable_as_source_page"] = True
    m("N11_generated_segment_cited_as_page", x, "SCHEMA", "citable_as_source_page")
    x = copy.deepcopy(ids["compilation-pdf"])
    x["representation"]["members"] = x["representation"]["members"][:1]
    m("N12_compilation_with_one_member", x, "SCHEMA", "members")
    x = copy.deepcopy(next(r for r in R if r["evidentiary_basis"] == "FILENAME_PATTERN"))
    x["verification"] = "CURATED_NAVIGATION"
    m("N13_abbreviation_reading_not_candidate", x, "SCHEMA", "verification")
    x = copy.deepcopy(ids["reconstructed-pdf"])
    x["representation"]["reconstructed_from_sha256"] = [SHA["reconstructed-pdf"]]
    x["representation"]["page_mapping"]["original_sha256"] = SHA["reconstructed-pdf"]
    m("N14_reconstruction_of_itself", x, "C16_RECONSTRUCTED_SELF")
    x = copy.deepcopy(R[0])
    x["relationship_id"] = "REL-" + "0" * 24
    m("N15_relationship_id_not_deterministic", x, "C16_ID_MISMATCH")
    x = copy.deepcopy(next(t for t in T if t["node_id"] == "PROV:AR-1954:r.22"))
    x["provision"]["number"] = "23"
    m("N16_provision_id_mismatch", x, "C16_TAXONOMY_ID")
    x = copy.deepcopy(ids["extract-pdf"])
    x["research_eligibility"]["whole_work_claims_permitted"] = True
    m("N18_extract_permits_whole_work_claims", x, "SCHEMA", "whole_work_claims_permitted")
    x = copy.deepcopy(ids["official-pdf"])
    x["restriction"] = restriction("RESTRICTED", "RM-999")
    m("N19_restricted_but_eligible", x, "SCHEMA", "state")
    x = copy.deepcopy(ADM[0])
    x["gates"] = [g for g in x["gates"] if g["gate_id"] != "G07_EMBEDDED_IMAGES_ACCOUNTED"]
    m("N20_admission_missing_gate", x, "SCHEMA", "gates")
    x = copy.deepcopy(ids["word-screenshots"])
    x["representation"]["origin_status"] = "CARRIER_ISSUED_COPY_CLAIMED"
    m("N21_word_screenshots_claims_issued_copy", x, "SCHEMA", "origin_status")
    x = copy.deepcopy(next(r for r in R if r["category"] == "cites_provision" and r["verification"] == "CANDIDATE"))
    x["is_finding"] = True
    m("N22_candidate_marked_as_finding", x, "SCHEMA", "verification")
    # C01 admission
    x = copy.deepcopy(ADM[0])
    x["gates"] = [dict(g, result="NOT_APPLICABLE", evidence_ref=None) for g in x["gates"]]
    m("N29_admission_eligible_all_not_applicable", x, "SCHEMA", "gates")
    x = copy.deepcopy(ADM[0])
    x["gates"][9] = dict(x["gates"][0])
    m("N30_admission_repeated_gate", x, "SCHEMA", "gates")
    x = copy.deepcopy(ADM[-1])
    x["supersedes_admission_id"] = None
    m("N31_admission_revision_without_supersession", x, "SCHEMA", "supersedes_admission_id")
    x = copy.deepcopy(ADM[1])
    x["gates"][0] = {"gate_id": "G01_HASH_VERIFIED", "result": "PASS", "evidence_ref": None}
    m("N32_gate_pass_without_evidence", x, "SCHEMA", "evidence_ref")
    # C02 classification can never be reviewed or a finding
    x = copy.deepcopy(next(r for r in R if r["evidentiary_basis"] == "FILENAME_PATTERN"))
    x.update(evidentiary_basis="DOCUMENT_TEXT_REVIEWED", is_finding=True)
    m("N33_classification_text_reviewed_finding", x, "SCHEMA", "evidentiary_basis")
    x = copy.deepcopy(next(r for r in R if r["verification"] == "DOCUMENTARY_CHECKED"))
    x["review_binding"] = dict(x["review_binding"], reviewer_id=AUTHOR)
    m("N34_review_not_independent", x, "C16_REVIEW_NOT_INDEPENDENT")
    x = copy.deepcopy(next(r for r in R if r["verification"] == "DOCUMENTARY_CHECKED"))
    x["review_binding"] = None
    m("N35_checked_without_review_binding", x, "SCHEMA", "review_binding")
    # C06 unknown format may not be claimed as PDF
    x = copy.deepcopy(ids["duplicate-copy"])
    x["source_copy"]["detected_format"] = "UNKNOWN"
    m("N36_unknown_format_claimed_pdf", x, "SCHEMA", "mime_type")
    x = copy.deepcopy(ADM[0])
    for g in x["gates"]:
        g.pop("receipt", None)
    x["admission_id"] = canonical.admission_id(x)
    m("N46_eligible_admission_with_asserted_evidence_only", x, "SCHEMA", "gates")
    x = copy.deepcopy(ADM[0])
    g6 = next(g for g in x["gates"] if g["gate_id"] == "G06_TEXT_DERIVATIVE_VERIFIED")
    g6.update(result="NOT_APPLICABLE", evidence_ref=None, receipt=None)
    x["admission_id"] = canonical.admission_id(x)
    m("N47_searchable_admission_without_derivative_gate", x, "SCHEMA", "result")
    x = copy.deepcopy(ids["word-screenshots"])
    x["embedded_images"][2]["ocr_state"] = "NOT_REQUIRED_DECORATIVE"
    m("N48_decorative_image_without_basis", x, "SCHEMA", "embedded_images")
    return N


def exchange_negatives(pop):
    X = {}

    def var(name, code, mutate=None, mode="strict", **kw):
        p = copy.deepcopy(pop)
        if mutate:
            mutate(p)
        X[name] = ({"expect_code": code, "mode": mode, "ledger": 0}, exchange_files(p, **kw))

    def readmit(a):
        a["admission_id"] = canonical.admission_id(a)
        return a

    def orphan(p):
        a = copy.deepcopy(p["admissions"][1])
        a["subject"] = {"doc_id": "orphan-fixture", "source_copy_sha256": H("orphan")}
        p["admissions"].append(readmit(a))
    var("X01_orphan_admission", "C16_ADMISSION_ORPHAN", orphan)

    def missing(p):
        p["admissions"] = [a for a in p["admissions"] if a["subject"]["doc_id"] != DOC["mixed-pdf"]]
    var("X02_identity_without_decision", "C16_ADMISSION_MISSING", missing)

    def wrong_gen(p):
        a = next(a for a in p["admissions"] if a["subject"]["doc_id"] == DOC["mixed-pdf"])
        a["corpus_generation_id"] = "CG-20261127-other-ffffffff"
        readmit(a)
    var("X03_admission_from_another_generation", "C16_GENERATION_MISMATCH", wrong_gen)

    def fork(p):
        w2 = next(a for a in p["admissions"] if a["revision"] == 2)
        f = copy.deepcopy(w2)
        f["reasons"] = ["conflicting second revision"]
        f["decision"] = "HELD_IDENTITY_UNRESOLVED"
        p["admissions"].append(readmit(f))
    var("X04_admission_fork", "C16_ADMISSION_FORK", fork)

    def g01_conflict(p):
        a = next(a for a in p["admissions"] if a["subject"]["doc_id"] == DOC["scan-pdf"])
        a["gates"][0] = {"gate_id": "G01_HASH_VERIFIED", "result": "PASS", "evidence_ref": "claimed"}
        readmit(a)
    var("X05_hash_pass_on_declared_hash", "C16_GATE_EVIDENCE", g01_conflict)

    def restricted_eligible(p):
        d = next(d for d in p["identities"] if d["doc_id"] == DOC["official-pdf"])
        d["restriction"] = restriction("RESTRICTED", "RM-999")
        d["research_eligibility"] = research("NOT_ELIGIBLE", False, False, False, False, ["RESTRICTED"])
    var("X06_restricted_identity_eligible_admission", "C16_ELIGIBLE_IDENTITY_NOT_READY", restricted_eligible)

    def incomplete_eligible(p):
        d = next(d for d in p["identities"] if d["doc_id"] == DOC["official-pdf"])
        d["integrity"] = {"source_integrity": "DECLARED_HASH_ONLY", "basis": "not re-verified"}
    var("X07_incomplete_identity_eligible_admission", "C16_ELIGIBLE_IDENTITY_NOT_READY", incomplete_eligible)

    def self_super(p):
        w2 = next(a for a in p["admissions"] if a["revision"] == 2)
        w2["supersedes_admission_id"] = "ADM-" + "1" * 24
        readmit(w2)
    var("X08_supersedes_unknown_admission", "C16_ADMISSION_SUPERSESSION", self_super)

    def page_range(p):
        a = next(a for a in p["anchors"] if a["anchor_id"] == pop_anchor(p, "native_cite_judgment"))
        a["locator"]["physical_page"] = 99
        rename_anchor(p, a)
    var("X09_anchor_page_beyond_copy", "C16_ANCHOR_PAGE_RANGE", page_range)

    def bad_image(p):
        a = next(a for a in p["anchors"] if a["locator"]["kind"] == "IMAGE_SEQUENCE")
        a["image_sha256"] = H("other-image")
        rename_anchor(p, a)
    var("X10_anchor_image_not_the_occurrence", "C16_ANCHOR_IMAGE", bad_image)

    def foreign_derivative(p):
        a = next(a for a in p["anchors"] if a["anchor_id"] == pop_anchor(p, "native_follows"))
        a["derivative_text_sha256"] = H("derivative:another-copy")
        rename_anchor(p, a)
    var("X11_anchor_derivative_of_another_copy", "C16_ANCHOR_DERIVATIVE", foreign_derivative)

    def unchecked_mapping(p):
        d = next(d for d in p["identities"] if d["doc_id"] == DOC["reconstructed-pdf"])
        d["representation"]["page_mapping"]["basis"] = "ONE_TO_ONE_DECLARED_NOT_CHECKED"
        d["research_eligibility"]["source_page_citation_permitted"] = False
    var("X12_reconstructed_page_without_checked_mapping", "C16_ANCHOR_MAPPING", unchecked_mapping)

    def node_mismatch(p):
        r = next(r for r in p["relationships"] if r["category"] == "refers_to_judgment")
        r["subject"]["graph_node_ref"] = "JUD:someone-else"
        r["relationship_id"] = canonical.relationship_id(r)
    var("X13_subject_node_differs_from_identity", "C16_SUBJECT_NODE_MISMATCH", node_mismatch)

    def compilation_no_member(p):
        comp = next(d for d in p["identities"] if d["doc_id"] == DOC["compilation-pdf"])
        anc = {"contract": CONTRACT_ID, "record_kind": "evidence_anchor", "anchor_id": "", "doc_id": comp["doc_id"],
               "original_sha256": comp["source_copy"]["sha256"], "representation_sha256": comp["source_copy"]["sha256"],
               "derivative_text_sha256": comp["text_derivatives"][0]["derivative_text_sha256"], "image_sha256": None,
               "locator": {"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": 14, "citable_as_source_page": True},
               "text_span": None, "bbox": None,
               "extraction": {"method": "NATIVE_TEXT_LAYER", "pipeline_name": "mimamsa-corpus-text", "pipeline_version": "1.0.0", "ocr_config": None},
               "quality": {"text_reliability": "reliable", "ocr_mean_confidence": None, "low_confidence": False},
               "verification": {"state": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None}, "quoting_permitted": True, "quote": None}
        anc["anchor_id"] = canonical.anchor_id(anc)
        p["anchors"].append(anc)
        r = rel("cites_provision", "compilation-pdf", {"resolved": True, "node_id": "PROV:AA-1950:s.69"}, "DOCUMENT_TEXT_EXTRACTED",
                [anc["anchor_id"]], date="2019-03-01")
        r["subject"]["graph_node_ref"] = U()
        r["relationship_id"] = canonical.relationship_id(r)
        r.pop("graph_projection")
        p["relationships"].append(r)
    var("X14_compilation_evidence_without_member", "C16_COMPILATION_MEMBER", compilation_no_member)

    def unresolved_review(p):
        p["reviewed_records"] = [r for r in p["reviewed_records"] if r["review_record_id"] != "RV-FIXTURE-0001"]
    var("X15_review_record_missing", "C16_REVIEW_UNRESOLVED", unresolved_review)

    def altered_review(p):
        rr = next(r for r in p["reviewed_records"] if r["review_record_id"] == "RV-FIXTURE-0001")
        rr["method"] = "altered after the binding was computed"
    var("X16_review_record_altered_after_binding", "C16_REVIEW_BINDING", altered_review)

    var("X17_judgment_target_not_registered", "C16_TARGET_UNREGISTERED", external=[])

    def restricted_admission(p):
        a = admission(None, "EXCLUDED_RESTRICTED", gates(G03_RESTRICTED_REGISTER="FAIL", G07_EMBEDDED_IMAGES_ACCOUNTED="NOT_APPLICABLE"),
                      rid="RM-999", doc="local-restricted-fixture", sha=H("restricted-copy"), reasons=["register match (fixture id)"])
        p["admissions"].append(a)
    var("X18_restricted_item_in_exchange", "C16_RESTRICTED_IN_EXCHANGE", restricted_admission)

    def weak_finding(p):
        a = next(a for a in p["anchors"] if a["anchor_id"] == pop_anchor(p, "native"))
        a["verification"] = {"state": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None}
        p["reviewed_records"] = [r for r in p["reviewed_records"] if r["review_record_id"] != "RV-FIXTURE-0002"]
    var("X19_checked_relationship_on_unchecked_anchor", "C16_FINDING_ON_WEAK_ANCHOR", weak_finding)

    var("X20_manifest_count_mismatch", "C16_MANIFEST_MISMATCH",
        manifest_edit=lambda m: next(f for f in m["files"] if f["path"] == "anchors.jsonl").__setitem__("records", 1))

    def drop_anchors(p):
        p.pop("anchors")
    var("X21_missing_population_strict", "C16_FILE_MISSING", drop_anchors)

    def dup_shard(p):
        pass
    shard = canonical.dumps_jsonl([pop["identities"][0]])
    var("X22_duplicate_key_across_shards", "C16_DUPLICATE_KEY", dup_shard,
        raw={"identities.0001.jsonl": shard})

    var("X23_non_object_and_null_lines", "JSONL_NOT_OBJECT", raw={"taxonomy.0001.jsonl": b"null\n[1,2]\n\"text\"\n"})
    var("X24_non_canonical_file_name", "C16_FILE_NAME", raw={"extra-records.jsonl": canonical.dumps_jsonl([pop["taxonomy"][0]])})

    def kind_mismatch(p):
        p["taxonomy"] = p["taxonomy"] + []
    var("X25_record_kind_in_wrong_file", "C16_KIND_MISMATCH",
        raw={"anchors.0001.jsonl": canonical.dumps_jsonl([pop["taxonomy"][0]])})

    def missing_field(p):
        d = next(d for d in p["identities"] if d["doc_id"] == DOC["mixed-pdf"])
        del d["integrity"]
    var("X26_identity_missing_field_excluded_from_cross_checks", "SCHEMA", missing_field)

    def quote_denied(p):
        d = next(d for d in p["identities"] if d["doc_id"] == DOC["extract-pdf"])
        d["research_eligibility"]["quoting_permitted"] = False
    var("X27_identity_denies_quotation", "C16_QUOTE_NOT_PERMITTED", quote_denied)

    def other_image_ocr(p):
        a = next(a for a in p["anchors"] if a["locator"]["kind"] == "IMAGE_SEQUENCE")
        a["derivative_text_sha256"] = H("image-ocr:1")
        rename_anchor(p, a)
    var("X28_image_locator_with_another_images_ocr", "C16_ANCHOR_IMAGE", other_image_ocr)

    def method_mismatch(p):
        a = next(a for a in p["anchors"] if a["locator"]["kind"] == "GENERATED_SEGMENT")
        a["extraction"]["method"] = "HTML"
    var("X29_anchor_method_not_of_derivative", "C16_ANCHOR_DERIVATIVE", method_mismatch)

    def pipeline_mismatch(p):
        a = next(a for a in p["anchors"] if a["anchor_id"] == pop_anchor(p, "native_cite_judgment"))
        a["extraction"]["pipeline_version"] = "9.9.9"
    var("X30_anchor_pipeline_mismatch", "C16_ANCHOR_DERIVATIVE", pipeline_mismatch)

    def span_on_image_with_document_text(p):
        a = next(a for a in p["anchors"] if a["locator"]["kind"] == "IMAGE_SEQUENCE")
        d = next(d for d in p["identities"] if d["doc_id"] == DOC["word-screenshots"])
        a["derivative_text_sha256"] = d["text_derivatives"][0]["derivative_text_sha256"]
        rename_anchor(p, a)
    var("X31_image_span_counted_into_document_text", "C16_ANCHOR_SPAN_NOT_PERMITTED", span_on_image_with_document_text)

    def reviewed_unresolved_member(p):
        comp = next(d for d in p["identities"] if d["doc_id"] == DOC["compilation-pdf"])
        anc = {"contract": CONTRACT_ID, "record_kind": "evidence_anchor", "anchor_id": "", "doc_id": comp["doc_id"],
               "original_sha256": comp["source_copy"]["sha256"], "representation_sha256": comp["source_copy"]["sha256"],
               "derivative_text_sha256": comp["text_derivatives"][0]["derivative_text_sha256"], "image_sha256": None,
               "locator": {"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": 25, "citable_as_source_page": True},
               "text_span": {"passage_id": None, "char_start": 0, "char_end": 10, "text_sha256": H("span:comp")}, "bbox": None,
               "extraction": {"method": "NATIVE_TEXT_LAYER", "pipeline_name": "mimamsa-corpus-text", "pipeline_version": "1.0.0", "ocr_config": None},
               "quality": {"text_reliability": "reliable", "ocr_mean_confidence": None, "low_confidence": False},
               "verification": {"state": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None}, "quoting_permitted": True, "quote": None}
        anc["anchor_id"] = canonical.anchor_id(anc)
        rva = review_record("RV-FIXTURE-0031", anc["anchor_id"])
        anc["verification"] = {"state": "DOCUMENTARY_CHECKED", "review_ref": "RV-FIXTURE-0031", "review_binding": binding(rva)}
        p["anchors"].append(anc)
        r = rel("cites_provision", "compilation-pdf", {"resolved": True, "node_id": "PROV:AA-1950:s.69"}, "DOCUMENT_TEXT_REVIEWED",
                [anc["anchor_id"]], verification="DOCUMENTARY_CHECKED", review="RV-FIXTURE-0032", date="2019-03-01")
        r["subject"]["graph_node_ref"] = U()
        r["subject"]["compilation_member_seq"] = 3          # member 3 has an unresolved page range
        r.pop("graph_projection")
        r["relationship_id"] = canonical.relationship_id(r)
        rvr = review_record("RV-FIXTURE-0032", r["relationship_id"])
        r["review_binding"] = binding(rvr)
        p["relationships"].append(r)
        p["reviewed_records"] += [rva, rvr]
    var("X32_reviewed_compilation_evidence_unresolved_member", "C16_COMPILATION_MEMBER", reviewed_unresolved_member)

    def search_without_coverage(p):
        d = next(d for d in p["identities"] if d["doc_id"] == DOC["scan-pdf"])
        d["text_derivatives"] = []
        d["research_eligibility"]["source_page_citation_permitted"] = False
        p["anchors"] = [a for a in p["anchors"] if a["doc_id"] != DOC["scan-pdf"]]
        a = next(a for a in p["admissions"] if a["subject"]["doc_id"] == DOC["scan-pdf"])
        next(g for g in a["gates"] if g["gate_id"] == "G06_TEXT_DERIVATIVE_VERIFIED").update(result="NOT_APPLICABLE", evidence_ref=None)
        readmit(a)
    var("X33_searchable_identity_without_derivative_uses_na", "C16_SEARCH_WITHOUT_COVERAGE", search_without_coverage)

    def receipt_other_copy(p):
        a = next(a for a in p["admissions"] if a["application_eligible"])
        a["gates"][0]["receipt"]["subject_sha256"] = H("another-copy")
    var("X34_receipt_for_another_copy", "C16_RECEIPT_MISMATCH", receipt_other_copy)

    def receipt_other_register(p):
        a = next(a for a in p["admissions"] if a["application_eligible"])
        next(g for g in a["gates"] if g["gate_id"] == "G03_RESTRICTED_REGISTER")["receipt"]["register_sha256"] = H("older-register")
    var("X35_register_receipt_for_another_revision", "C16_RECEIPT_MISMATCH", receipt_other_register)
    return X


def pop_anchor(p, key):
    return ANCHOR_KEYS[key]


def rename_anchor(p, a):
    """Recompute an anchor id after a locator change and repoint the relationships that cite it."""
    old = a["anchor_id"]
    a["anchor_id"] = canonical.anchor_id(a)
    for r in p["relationships"]:
        if old in r["anchors"]:
            r["anchors"] = sorted(a["anchor_id"] if x == old else x for x in r["anchors"])
            r["relationship_id"] = canonical.relationship_id(r)


ANCHOR_KEYS: dict[str, str] = {}


# ----------------------------------------------------------------------------------------- WP06 release fixtures
E5 = H("model:e5-small-onnx")
XENC = H("model:cross-encoder-onnx")
REL_FULL = "R16-knowledge-20261201-0a0b0c0d"
REL_DELTA = "R17-knowledge-20261215-1a1b1c1d"
REL_MODEL = "R18-intelligence-20261220-2a2b2c2d"
ACCEL_VERIFY = {
    "KNOWLEDGE_ROWS": ["SHA256_EACH_FILE", "ROW_COUNTS", "ROWS_ALLOWLIST_AND_TYPES", "ROWS_REDERIVE_COMPARE", "SOURCE_DIGEST_EQUALS_SITE"],
    "GRAPH": ["SHA256_EACH_FILE", "GRAPH_DIGEST", "GRAPH_STRUCTURAL_RECHECK", "SAMPLED_REBUILD_PARITY", "SOURCE_DIGEST_EQUALS_SITE"],
    "LEXICAL_INDEX": ["SHA256_EACH_FILE", "SQLITE_QUICK_CHECK", "SAMPLED_POSTINGS_REDERIVE", "SAMPLED_QUERY_PARITY", "SOURCE_DIGEST_EQUALS_SITE"],
    "TEXT_STORE": ["SHA256_EACH_FILE", "SQLITE_QUICK_CHECK", "TEXT_STORE_BIND_EXACT", "PAGE_HASH_ON_READ", "SOURCE_DIGEST_EQUALS_SITE"],
    "VECTOR_PACK": ["SHA256_EACH_FILE", "VECTOR_TRAILER", "VECTOR_KEYS_RECOMPUTED", "VECTOR_SPOT_REEMBED", "SOURCE_DIGEST_EQUALS_SITE"],
}


def fe(path):
    return {"path": path, "sha256": H("file:" + path), "bytes": 1000 + len(path)}


def component(cid, kind, fmt, paths, *, transport="FULL", model=None, count=1, verify=None, fallback=None, tables=None):
    accel = kind in ACCEL_VERIFY
    c = {"component_id": cid, "kind": kind, "format": fmt, "authority": "ACCELERATOR" if accel else "AUTHORITATIVE",
         "transport": transport, "files": [fe(p) for p in paths], "result_digest": H(f"result:{cid}:{transport}"),
         "result_count": count, "source_digest": H(f"source:{cid}") if accel else None,
         "builder": {"name": f"{cid}-builder", "version": "1.0.0", "commit": "c8fa5290", "config_sha256": None} if accel else None,
         "model_sha256": model, "verify": verify or ACCEL_VERIFY.get(kind) or ["SHA256_EACH_FILE", "RESULT_DIGEST", "RESTRICTED_REGISTER"],
         "fallback": fallback if fallback else ("REBUILD_LOCALLY_CHEAP" if accel and kind != "VECTOR_PACK" else ("SERVE_LEXICAL_ONLY" if accel else None)),
         "disk_budget_bytes": 10 ** 9 if accel else None}
    if kind == "TEXT_STORE":
        c["binding"] = "BIND_EXACT_TO_GENERATION_RECORDS"
    if tables:
        c["tables"] = tables
    return c


def knowledge_manifest(mode, level="FULL", vectors=True):
    delta = mode == "DELTA"
    t = "DELTA" if delta else "FULL"
    rows = [{"table": tb, "file": f"accelerators/rows/{tb}.jsonl", "row_count": 10, "rows_sha256": H("rows:" + tb)}
            for tb in ("graph_edges", "graph_nodes", "taxonomy_nodes")]
    comps = [
        component("originals", "ORIGINALS", "vault-sha256", ["originals/" + H("o1")], transport=t, count=2383),
        component("text", "TEXT_DERIVATIVES", "page-marker-v1", ["text/" + H("t1") + ".txt"], transport=t, count=2383),
        component("records", "RECORDS", "canonical-jsonl", ["data/documents.jsonl", "data/derived_text.jsonl", "data/candidates.jsonl",
                                                            "corpus-v2/identities.jsonl", "corpus-v2/relationships.jsonl",
                                                            "corpus-v2/anchors.jsonl", "corpus-v2/taxonomy.jsonl", "corpus-v2/GENERATION.json"],
                  transport=t, count=41000, verify=["SHA256_EACH_FILE", "RESULT_DIGEST", "RESTRICTED_REGISTER", "CONTRACT_VALIDATION"]),
        component("research", "RESEARCH_AIDS", "jsonl", ["research/a4_provision_versions.jsonl"], count=488),
        component("integrity", "INTEGRITY_REGISTER", "canonical-jsonl", ["registers/integrity.jsonl"], transport=t, count=2383),
        component("admission", "ADMISSION_REGISTER", "canonical-jsonl", ["corpus-v2/admissions.jsonl"], transport=t, count=3500,
                  verify=["SHA256_EACH_FILE", "RESULT_DIGEST", "RESTRICTED_REGISTER", "CONTRACT_VALIDATION"]),
        component("knowledge-rows", "KNOWLEDGE_ROWS", "mimamsa-knowledge-rows/1", [r["file"] for r in rows], tables=rows, count=30),
        component("graph", "GRAPH", "c15-graph-rows-v1", ["accelerators/graph/nodes.jsonl", "accelerators/graph/edges.jsonl"], count=180000),
        component("lexical-index", "LEXICAL_INDEX", "mimamsa-index-sqlite-1", ["accelerators/search-index/search.sqlite",
                                                                               "accelerators/search-index/MANIFEST.json"]),
        component("text-store", "TEXT_STORE", "mimamsa-text-store/1", ["accelerators/text-store/text.sqlite",
                                                                       "accelerators/text-store/MANIFEST.json"]),
    ]
    if vectors:
        comps.append(component("vectors-e5", "VECTOR_PACK", "MIMVEC01", ["accelerators/vectors/e5.mimvec"], transport=t, model=E5, count=310000))
    acct = [{"kind": c["kind"], "status": "SHIPPED", "reason": "shipped in this release"} for c in comps]
    if not vectors:
        acct.append({"kind": "VECTOR_PACK", "status": "OMITTED_DEGRADED", "reason": "no vectors for the installed embedder: lexical search only"})
    return {"contract": CONTRACT_ID, "record_kind": "knowledge_release_manifest", "manifest_format": "MKR-1", "release_class": "KNOWLEDGE",
            "release_id": REL_DELTA if delta else REL_FULL, "release_sequence": 17 if delta else 16,
            "base": {"mode": mode, "base_release_id": REL_FULL if delta else None,
                     "base_manifest_sha256": H("manifest:" + REL_FULL) if delta else None},
            "corpus_generations": [{"corpus_generation_id": CG, "manifest_sha256": H("generation-manifest")}],
            "compatibility": {"knowledge_format": "1.0", "min_app_version": "0.16.0", "max_app_version": None,
                              "contracts": {"v1": "1.0.0", "corpus": CONTRACT_ID}, "knowledge_schema_version": 1,
                              "graph_builder_version": "c15-graph-1", "index_format": "mimamsa-index-sqlite-1",
                              "text_store_format": "mimamsa-text-store/1", "vector_store_format": "MIMVEC01",
                              "required_models": [{"role": "EMBEDDER", "model_id": "multilingual-e5-small (fixture)", "sha256": E5},
                                                  {"role": "RERANKER", "model_id": "cross-encoder (fixture)", "sha256": XENC}]},
            "components": comps,
            "signing_purpose": "release",
            "capability": {"declared_service_level": level, "accounting": acct, "semantic_search_promised": vectors,
                           "pending_future_gates": FUTURE_GATES},
            "heavy_compute_on_site": {"ocr": "NONE", "embedding": "NONE", "graph_rebuild": "ONLY_IF_ACCELERATOR_REJECTED"},
            "notes": "synthetic fixture"}


def intelligence_manifest():
    nxt = H("model:next")
    comps = [component("model-embedder", "MODEL_FILE", "onnx", ["models/embedder/model.onnx", "models/embedder/tokenizer.json"],
                       model=nxt, verify=["SHA256_EACH_FILE", "RESULT_DIGEST", "ONNX_LOAD_SELFTEST"]),
             component("vectors-next", "VECTOR_PACK", "MIMVEC01", ["accelerators/vectors/next.mimvec"], model=nxt, count=310000,
                       fallback="REFUSE_RELEASE"),
             component("integrity", "INTEGRITY_REGISTER", "canonical-jsonl", ["registers/integrity-models.jsonl"], count=3)]
    return {"contract": CONTRACT_ID, "record_kind": "knowledge_release_manifest", "manifest_format": "MKR-1", "release_class": "INTELLIGENCE",
            "release_id": REL_MODEL, "release_sequence": 18,
            "base": {"mode": "FULL", "base_release_id": None, "base_manifest_sha256": None},
            "corpus_generations": [{"corpus_generation_id": CG, "manifest_sha256": H("generation-manifest")}],
            "compatibility": {"knowledge_format": "1.0", "min_app_version": "0.16.0", "max_app_version": None,
                              "contracts": {"v1": "1.0.0", "corpus": CONTRACT_ID}, "knowledge_schema_version": 1,
                              "graph_builder_version": "c15-graph-1", "index_format": "mimamsa-index-sqlite-1",
                              "text_store_format": "mimamsa-text-store/1", "vector_store_format": "MIMVEC01",
                              "required_models": [{"role": "EMBEDDER", "model_id": "next embedder (fixture)", "sha256": nxt}]},
            "components": comps,
            "signing_purpose": "model",
            "capability": {"declared_service_level": "FULL", "semantic_search_promised": True,
                           "pending_future_gates": FUTURE_GATES + ["FG-MODEL-TRUST-PURPOSE"], "accounting": [
                {"kind": "MODEL_FILE", "status": "SHIPPED", "reason": "new embedder"},
                {"kind": "VECTOR_PACK", "status": "SHIPPED", "reason": "full vectors for the new embedder, built upstream"},
                {"kind": "RULE_PACK", "status": "NOT_APPLICABLE", "reason": "no rule pack exists; refused at AUTH-LEDGER v0"},
                {"kind": "INTEGRITY_REGISTER", "status": "SHIPPED", "reason": "model hashes"}]},
            "heavy_compute_on_site": {"ocr": "NONE", "embedding": "NONE", "graph_rebuild": "NONE"}, "notes": "synthetic fixture"}


def activation_record():
    comps = knowledge_manifest("DELTA")["components"]
    return {"contract": CONTRACT_ID, "record_kind": "knowledge_activation_record", "seq": 2,
            "previous_record_sha256": H("activation:1"), "txn_id": "TX-00000002-" + H("txn")[:12], "action": "ACTIVATE",
            "target": "KNOWLEDGE", "release_id": REL_DELTA, "release_class": "KNOWLEDGE", "release_sequence": 17,
            "previous_active_release_id": REL_FULL, "app_version": "0.16.0",
            "components": [{"component_id": c["component_id"], "result": "VERIFIED_USED", "failed_checks": []}
                           for c in comps if c["component_id"] != "graph"] +
                          [{"component_id": "graph", "result": "ACCELERATOR_REBUILT_LOCALLY", "failed_checks": ["SAMPLED_REBUILD_PARITY"]}],
            "exclusion_state": {"sequence": 4, "digest": H("exclusions:4"), "items_suppressed": 2},
            "result": "ACTIVE_AFTER_LOCAL_REBUILD", "service_level": "FULL", "degradation_acknowledged_by": None,
            "active_models_release_id": None,
            "preflight": {"measured_required_bytes": 3 * 10 ** 10, "free_bytes": 9 * 10 ** 10, "headroom_fraction": 0.1,
                          "retained_releases": [REL_DELTA, REL_FULL], "result": "PASS"},
            "reason": "graph accelerator failed sampled rebuild parity; rebuilt locally", "actor": {"role": "ADMIN", "id": "admin-fixture"},
            "at": "2026-12-15T09:30:00Z"}


FUTURE_GATES = ["FG-CALIBRATED-SAMPLES", "FG-DISK-PREFLIGHT", "FG-JOURNAL-DURABILITY", "FG-REAL-RESTORE-TEST",
                "FG-RECEIPTS", "FG-ROW-LOADER", "FG-SITE-IMPORTER"]


def release_negatives():
    N = {}
    x = knowledge_manifest("DELTA")
    x["base"]["base_manifest_sha256"] = None
    N["N23_delta_release_without_base_manifest"] = (x, "SCHEMA", "base_manifest_sha256", 0)
    x = knowledge_manifest("FULL")
    x["components"].append(component("model", "MODEL_FILE", "onnx", ["models/x.onnx"], model=E5,
                                     verify=["SHA256_EACH_FILE", "RESULT_DIGEST", "ONNX_LOAD_SELFTEST"]))
    N["N24_knowledge_release_carries_model"] = (x, "SCHEMA", "kind", 0)
    x = knowledge_manifest("FULL")
    x["components"][-1]["fallback"] = None
    N["N25_accelerator_without_fallback"] = (x, "SCHEMA", "fallback", 0)
    x = knowledge_manifest("FULL")
    x["heavy_compute_on_site"]["embedding"] = "FULL_CORPUS"
    N["N26_release_requires_site_embedding"] = (x, "SCHEMA", "embedding", 0)
    x = activation_record()
    x["components"][0]["result"] = "FAILED"
    N["N27_activation_active_with_failed_component"] = (x, "SCHEMA", "result", 0)
    x = knowledge_manifest("FULL")
    x["components"] = [c for c in x["components"] if c["kind"] != "ADMISSION_REGISTER"]
    x["capability"]["accounting"] = [a for a in x["capability"]["accounting"] if a["kind"] != "ADMISSION_REGISTER"]
    N["N28_knowledge_release_without_admission_register"] = (x, "KR_ACCOUNTING", None, 0)
    x = knowledge_manifest("FULL", level="FULL", vectors=False)
    x["capability"]["semantic_search_promised"] = True
    N["N37_full_capability_claimed_while_degraded"] = (x, "KR_FULL_CAPABILITY_CLAIM", None, 0)
    x = knowledge_manifest("FULL")
    x["components"].append({**component("pg", "KNOWLEDGE_ROWS", "mimamsa-knowledge-rows/1", ["accelerators/rows/x.jsonl"],
                                        tables=[{"table": "graph_nodes", "file": "accelerators/rows/x.jsonl", "row_count": 1, "rows_sha256": H("x")}]),
                            "kind": "PG_KNOWLEDGE_DATA"})
    N["N38_postgresql_archive_component"] = (x, "SCHEMA", "kind", 0)
    x = knowledge_manifest("FULL")
    rows = next(c for c in x["components"] if c["kind"] == "KNOWLEDGE_ROWS")
    rows["tables"][0]["table"] = "app_users"
    N["N39_knowledge_rows_table_not_allowlisted"] = (x, "SCHEMA", "table", 0)
    x = knowledge_manifest("FULL")
    ts = next(c for c in x["components"] if c["kind"] == "TEXT_STORE")
    ts["binding"] = None
    N["N40_text_store_without_authoritative_binding"] = (x, "SCHEMA", "binding", 0)
    x = knowledge_manifest("FULL")
    x["components"][1]["files"].append(fe("originals/" + H("o1")))
    N["N41_component_path_overlap"] = (x, "KR_PATH_OVERLAP", None, 0)
    x = knowledge_manifest("FULL")
    x["components"][0]["files"].append(fe("sessions/user/working.docx"))
    N["N42_component_file_in_reserved_namespace"] = (x, "KR_NAMESPACE", None, 0)
    x = knowledge_manifest("FULL")
    li = next(c for c in x["components"] if c["kind"] == "LEXICAL_INDEX")
    li["verify"] = ["SHA256_EACH_FILE", "SQLITE_QUICK_CHECK", "SOURCE_DIGEST_EQUALS_SITE"]
    N["N43_index_accepted_on_source_digest_alone"] = (x, "SCHEMA", "verify", 0)
    x = activation_record()
    x["result"] = "ACTIVE_FULL"
    N["N44_local_rebuild_reported_as_normal_acceptance"] = (x, "SCHEMA", "result", 0)
    x = activation_record()
    x["components"][-1]["result"] = "ACCELERATOR_DEGRADED"
    x.update(result="ACTIVE_DEGRADED", service_level="DEGRADED_LEXICAL_ONLY")
    N["N45_degraded_without_acknowledgement"] = (x, "SCHEMA", "degradation_acknowledged_by", 0)
    x = knowledge_manifest("FULL")
    x["components"] = [c for c in x["components"] if c["kind"] != "INTEGRITY_REGISTER"]
    next(a for a in x["capability"]["accounting"] if a["kind"] == "INTEGRITY_REGISTER").update(status="NOT_APPLICABLE", reason="claimed empty")
    N["N49_full_release_with_mandatory_payload_not_applicable"] = (x, "KR_MANDATORY_COMPONENT", None, 0)
    x = knowledge_manifest("FULL")
    x["compatibility"]["required_models"] = [m for m in x["compatibility"]["required_models"] if m["role"] != "EMBEDDER"]
    x["components"] = [c for c in x["components"] if c["kind"] != "VECTOR_PACK"]
    next(a for a in x["capability"]["accounting"] if a["kind"] == "VECTOR_PACK").update(status="NOT_APPLICABLE", reason="no embedder")
    N["N50_full_service_without_embedder_declaration"] = (x, "KR_FULL_CAPABILITY_CLAIM", None, 0)
    x = knowledge_manifest("FULL")
    x["capability"]["semantic_search_promised"] = False
    N["N51_full_service_without_semantic_promise"] = (x, "SCHEMA", "semantic_search_promised", 0)
    x = intelligence_manifest()
    x["signing_purpose"] = "release"
    N["N52_intelligence_release_not_model_signed"] = (x, "SCHEMA", "signing_purpose", 0)
    x = activation_record()
    x["preflight"]["result"] = "FAIL"
    N["N53_activation_after_failed_disk_preflight"] = (x, "SCHEMA", "preflight", 0)
    x = knowledge_manifest("FULL")
    x["capability"]["pending_future_gates"] = []
    N["N54_release_claims_no_pending_future_gates"] = (x, "SCHEMA", "pending_future_gates", 0)
    return N


def outputs() -> dict[str, bytes]:
    REVIEWS.clear()
    ids = build_identities()
    A = build_anchors(ids)
    bind_native_anchor(A)
    ANCHOR_KEYS.clear()
    ANCHOR_KEYS.update({k: v["anchor_id"] for k, v in A.items()})
    R = build_relationships(ids, A)
    T = build_taxonomy()
    ADM = build_admissions()
    pop = {"identities": list(ids.values()), "anchors": list(A.values()), "relationships": R, "taxonomy": T,
           "admissions": ADM, "reviewed_records": list(REVIEWS)}
    files = {f"positive/exchange/{k}": v for k, v in exchange_files(pop).items()}
    files["positive/legally_validated_ledger_v1.json"] = canonical.canonical_bytes(
        legally_validated(next(r for r in R if r["category"] == "follows"))) + b"\n"
    for key in ("word-screenshots", "reconstructed-pdf", "extract-pdf", "compilation-pdf"):
        files[f"positive/identity_{key.replace('-', '_')}.json"] = json.dumps(ids[key], indent=1, sort_keys=True, ensure_ascii=False).encode() + b"\n"
    files["positive/relationships_ar_22_23_30.jsonl"] = canonical.dumps_jsonl(
        [r for r in R if r["subject"]["doc_id"] == DOC["word-screenshots"]])
    release_fixtures = {"knowledge_release_full": knowledge_manifest("FULL"), "knowledge_release_delta": knowledge_manifest("DELTA"),
                        "knowledge_release_degraded_lexical_only": knowledge_manifest("FULL", level="DEGRADED_LEXICAL_ONLY", vectors=False),
                        "intelligence_release_model_change": intelligence_manifest(), "knowledge_activation_record": activation_record()}
    for name, rec in release_fixtures.items():
        files[f"positive/{name}.json"] = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False).encode() + b"\n"
    manifest = {"description": "C16 fixture manifest. kind=record: one JSON record; kind=jsonl: records validated singly; "
                               "kind=exchange_dir: a strict exchange directory; kind=exchange_case: a JSON object {expect_code, mode, "
                               "ledger, files} validated as one exchange. expect=invalid lists the rule code that must be raised and, "
                               "for SCHEMA, a JSON path fragment showing the intended reason.",
                "positive": [{"file": "positive/exchange", "kind": "exchange_dir", "ledger": 0},
                             {"file": "positive/legally_validated_ledger_v1.json", "kind": "record", "ledger": 1},
                             {"file": "positive/relationships_ar_22_23_30.jsonl", "kind": "jsonl", "ledger": 0}] +
                            [{"file": f"positive/identity_{k.replace('-', '_')}.json", "kind": "record", "ledger": 0}
                             for k in ("word-screenshots", "reconstructed-pdf", "extract-pdf", "compilation-pdf")] +
                            [{"file": f"positive/{n}.json", "kind": "record", "ledger": 0} for n in sorted(release_fixtures)],
                "negative": []}
    for name, (rec, code, hint, ledger) in sorted({**negatives(ids, A, R, T, ADM), **release_negatives()}.items()):
        files[f"negative/{name}.json"] = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False).encode() + b"\n"
        manifest["negative"].append({"file": f"negative/{name}.json", "kind": "record", "expect_code": code,
                                     "schema_path_contains": hint, "ledger": ledger})
    unsorted = list(reversed(canonical.dumps_jsonl(R).decode().splitlines(keepends=True)))
    files["negative/N17_relationships_not_in_canonical_order.jsonl"] = "".join(unsorted).encode()
    manifest["negative"].append({"file": "negative/N17_relationships_not_in_canonical_order.jsonl", "kind": "jsonl",
                                 "expect_code": "C16_JSONL", "schema_path_contains": None, "ledger": 0})
    for name, (meta, xfiles) in sorted(exchange_negatives(pop).items()):
        case = dict(meta, files={k: v.decode("utf-8") for k, v in sorted(xfiles.items())})
        files[f"negative/exchange/{name}.json"] = json.dumps(case, indent=1, sort_keys=True, ensure_ascii=False).encode() + b"\n"
        manifest["negative"].append({"file": f"negative/exchange/{name}.json", "kind": "exchange_case", "expect_code": meta["expect_code"],
                                     "schema_path_contains": None, "ledger": 0})
    manifest["negative"].sort(key=lambda x: x["file"])
    files["FIXTURES.json"] = json.dumps(manifest, indent=1, sort_keys=True).encode() + b"\n"
    return files


def main(argv):
    check = "--check" in argv
    out = outputs()
    diff = []
    for rel_path, data in sorted(out.items()):
        p = HERE / rel_path
        if check:
            if not p.is_file() or p.read_bytes() != data:
                diff.append(rel_path)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    stale = sorted(str(p.relative_to(HERE)).replace("\\", "/") for p in HERE.rglob("*")
                   if p.is_file() and p.suffix in (".json", ".jsonl") and str(p.relative_to(HERE)).replace("\\", "/") not in out)
    if check and (diff or stale):
        print("fixtures differ from builder output:", ", ".join(diff + [f"stale {s}" for s in stale]))
        return 1
    if not check:
        for s in stale:
            (HERE / s).unlink()
    print("fixtures " + ("match builder output" if check else "written"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
