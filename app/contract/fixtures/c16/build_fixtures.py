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
TOOLS = {"name": "c16-fixture-producer", "version": "1.0.0", "commit": None, "config_sha256": None}


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
             carrier="USER_SUPPLIED", observations=None, restr=None, alternates=None, history=None):
    rec = {"contract": CONTRACT_ID, "record_kind": "document_identity", "doc_id": DOC.get(key, key),
           "source_copy": {"sha256": SHA[key], "bytes": 100000 + len(key) * 1000, "mime_type": mime, "detected_format": fmt,
                           "page_count": pages, "physical_pagination": pagination,
                           "vault_path": f"vault/sha256/{SHA[key][:2]}/{SHA[key]}"},
           "representation": rep, "work_identity": work,
           "embedded_images": [] if images is None else images, "text_derivatives": derivs,
           "provenance": {"acquisition": prov or v1_provenance(), "carrier_provenance": carrier,
                          "observations": observations or [], "processing_history": history or []},
           "restriction": restr or restriction(),
           "integrity": {"source_integrity": "DECLARED_HASH_ONLY", "basis": "producer-computed SHA-256 (fixture)"},
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
    return ids


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
                                 derivative_text_sha256=d["derivative_text_sha256"], image_sha256=H("image:2"),
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
         "review_ref": review, "approval_ref": None, "validates_relationship_id": None, "proposition_ref": proposition,
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
    return R


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


def gates(**over):
    ids = ["G01_HASH_VERIFIED", "G02_FORMAT_DETECTED", "G03_RESTRICTED_REGISTER", "G04_ACCESS_MARKING_REVIEWED",
           "G05_IDENTITY_RECORD_VALID", "G06_TEXT_DERIVATIVE_VERIFIED", "G07_EMBEDDED_IMAGES_ACCOUNTED",
           "G08_RELEVANCE_ASSESSED", "G09_DUPLICATE_RESOLVED", "G10_SCHEMA_VALID"]
    return [{"gate_id": g, "result": over.get(g, "PASS"), "evidence_ref": None} for g in ids]


def admission(key, decision, g, *, eligible=False, dup=None, rid=None, reasons=("fixture",), doc=None, sha=None, disp=None):
    a = {"contract": CONTRACT_ID, "record_kind": "corpus_admission", "admission_id": "",
         "subject": {"doc_id": doc or DOC[key], "source_copy_sha256": sha or SHA[key]}, "corpus_generation_id": CG,
         "decision": decision, "source_disposition": disp, "duplicate_of": dup, "restriction_id": rid, "gates": g,
         "application_eligible": eligible, "publication_effect": "NONE", "legal_effect": "NONE",
         "decided_by": {"kind": "AUTOMATED_RULE", "id": "c16-fixture-admission"}, "decided_at": None,
         "rule_set": {"id": "c16-admission", "version": "1.0"}, "reasons": list(reasons), "supersedes_admission_id": None}
    a["admission_id"] = canonical.admission_id(a)
    return a


def build_admissions():
    return [
        admission("official-pdf", "ADMITTED_AS_PRIMARY", gates(G07_EMBEDDED_IMAGES_ACCOUNTED="NOT_APPLICABLE"), eligible=True,
                  reasons=["all gates passed (fixture)"]),
        admission("word-screenshots", "HELD_EXTRACTION_INCOMPLETE",
                  gates(G04_ACCESS_MARKING_REVIEWED="NOT_RUN", G07_EMBEDDED_IMAGES_ACCOUNTED="FAIL"),
                  reasons=["embedded image 3 not yet read (ocr_state QUEUED)"],
                  disp={"system": "c16-local-reconcile", "value": "NEW_DOCUMENT", "secondary_flags": []}),
        admission("reconstructed-pdf", "ADMITTED_AS_ALTERNATE_COPY", gates(G07_EMBEDDED_IMAGES_ACCOUNTED="NOT_APPLICABLE"),
                  dup={"sha256": SHA["scan-pdf"], "doc_id": DOC["scan-pdf"], "relation": "RECONSTRUCTION_OF"},
                  reasons=["searchable reconstruction kept beside its original; original remains the evidence copy"]),
        admission("word-uninventoried", "HELD_EXTRACTION_INCOMPLETE",
                  gates(G03_RESTRICTED_REGISTER="NOT_RUN", G04_ACCESS_MARKING_REVIEWED="NOT_RUN", G05_IDENTITY_RECORD_VALID="NOT_RUN",
                        G06_TEXT_DERIVATIVE_VERIFIED="NOT_RUN", G07_EMBEDDED_IMAGES_ACCOUNTED="NOT_RUN", G08_RELEVANCE_ASSESSED="NOT_RUN"),
                  reasons=["embedded images not inventoried"]),
        admission(None, "EXCLUDED_RESTRICTED", gates(G03_RESTRICTED_REGISTER="FAIL"), rid="RM-999",
                  doc="local-restricted-fixture", sha=SHA["restricted-copy"], reasons=["matches the restricted-material register (fixture id)"]),
        admission(None, "REJECTED_EXACT_DUPLICATE", gates(),
                  dup={"sha256": SHA["duplicate-copy"], "doc_id": None, "relation": "BYTE_IDENTICAL"},
                  doc="local-duplicate-fixture", sha=SHA["duplicate-copy"], reasons=["bytes already held at the canonical revision"]),
    ]


def legally_validated(base):
    r = {"contract": CONTRACT_ID, "record_kind": "corpus_relationship", "relationship_id": "", "category": "legally_validated",
         "subject": copy.deepcopy(base["subject"]), "target": copy.deepcopy(base["target"]), "evidentiary_basis": "LEGAL_REVIEW",
         "source": {"producer": TOOLS, "rule_id": "LEGAL-REVIEW", "rule_version": "1.0", "author_id": None},
         "classification_provenance": None, "anchors": [], "verification": "LEGAL_REVIEWED", "review_ref": None,
         "approval_ref": "AP-FIXTURE-0001", "validates_relationship_id": base["relationship_id"], "proposition_ref": None,
         "temporal_scope": {"from": None, "from_status": "NOT_DETERMINED", "to": None, "to_status": "NOT_DETERMINED"},
         "has_legal_effect": True, "is_finding": True,
         "uncertainty": "Representation test only: a legal approval overlay (impossible while AUTH-LEDGER is at version 0)."}
    r["relationship_id"] = canonical.relationship_id(r)
    return r


def negatives(ids, A, R, T, ADM):
    N = {}

    def m(name, rec, expect_code, path_hint=None, ledger=0):
        N[name] = (rec, expect_code, path_hint, ledger)

    folder = next(r for r in R if r["evidentiary_basis"] == "FOLDER_PATH")
    x = copy.deepcopy(folder)
    x.update(verification="DOCUMENTARY_CHECKED", is_finding=True, review_ref="RV-FIXTURE-0002")
    x["relationship_id"] = canonical.relationship_id(x)
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
    x["anchor_id"] = canonical.anchor_id(x)
    m("N05_ocr_anchor_quotable", x, "SCHEMA", "quoting_permitted")
    lv = legally_validated(next(r for r in R if r["category"] == "follows"))
    m("N06_legally_validated_at_ledger_v0", lv, "LEDGER_V0_NO_APPROVAL", None, 0)
    x = copy.deepcopy(lv)
    x["approval_ref"] = None
    m("N07_legally_validated_without_approval", x, "SCHEMA", "approval_ref", 1)
    x = copy.deepcopy(ADM[1])
    x["application_eligible"] = True
    x["decision"] = "ADMITTED_AS_PRIMARY"
    x["admission_id"] = canonical.admission_id(x)
    m("N08_admission_eligible_with_failed_gate", x, "SCHEMA", "gates")
    x = copy.deepcopy(next(r for r in R if r["category"] == "follows"))
    x["anchors"] = []
    x["relationship_id"] = canonical.relationship_id(x)
    m("N09_treatment_without_anchor", x, "SCHEMA", "anchors")
    x = copy.deepcopy(ids["word-screenshots"])
    x["embedded_images"] = []
    m("N10_word_screenshots_without_image_inventory", x, "SCHEMA", "embedded_images")
    x = copy.deepcopy(A["docx_generated"])
    x["locator"]["citable_as_source_page"] = True
    x["anchor_id"] = canonical.anchor_id(x)
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
    return N


def outputs() -> dict[str, bytes]:
    ids = build_identities()
    A = build_anchors(ids)
    R = build_relationships(ids, A)
    T = build_taxonomy()
    ADM = build_admissions()
    files = {
        "positive/identities.jsonl": canonical.dumps_jsonl(list(ids.values())),
        "positive/anchors.jsonl": canonical.dumps_jsonl(list(A.values())),
        "positive/relationships.jsonl": canonical.dumps_jsonl(R),
        "positive/taxonomy.jsonl": canonical.dumps_jsonl(T),
        "positive/admissions.jsonl": canonical.dumps_jsonl(ADM),
        "positive/legally_validated_ledger_v1.json": canonical.canonical_bytes(legally_validated(next(r for r in R if r["category"] == "follows"))) + b"\n",
    }
    for key in ("word-screenshots", "reconstructed-pdf", "extract-pdf", "compilation-pdf"):
        files[f"positive/identity_{key.replace('-', '_')}.json"] = json.dumps(ids[key], indent=1, sort_keys=True, ensure_ascii=False).encode() + b"\n"
    files["positive/relationships_ar_22_23_30.jsonl"] = canonical.dumps_jsonl(
        [r for r in R if r["subject"]["doc_id"] == DOC["word-screenshots"]])
    manifest = {"description": "C16 fixture manifest. kind=record: one JSON record; kind=exchange: a set of JSONL files "
                               "validated together. expect=invalid lists the rule code that must be raised and, for SCHEMA, a "
                               "JSON path fragment showing the intended reason.",
                "positive": [{"file": "positive/identities.jsonl", "kind": "exchange_set",
                              "with": ["positive/anchors.jsonl", "positive/relationships.jsonl", "positive/taxonomy.jsonl",
                                       "positive/admissions.jsonl"], "ledger": 0},
                             {"file": "positive/legally_validated_ledger_v1.json", "kind": "record", "ledger": 1},
                             {"file": "positive/relationships_ar_22_23_30.jsonl", "kind": "jsonl", "ledger": 0}] +
                            [{"file": f"positive/identity_{k.replace('-', '_')}.json", "kind": "record", "ledger": 0}
                             for k in ("word-screenshots", "reconstructed-pdf", "extract-pdf", "compilation-pdf")],
                "negative": []}
    for name, (rec, code, hint, ledger) in sorted(negatives(ids, A, R, T, ADM).items()):
        files[f"negative/{name}.json"] = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False).encode() + b"\n"
        manifest["negative"].append({"file": f"negative/{name}.json", "kind": "record", "expect_code": code,
                                     "schema_path_contains": hint, "ledger": ledger})
    unsorted = list(reversed(canonical.dumps_jsonl(R).decode().splitlines(keepends=True)))
    files["negative/N17_relationships_not_in_canonical_order.jsonl"] = "".join(unsorted).encode()
    manifest["negative"].append({"file": "negative/N17_relationships_not_in_canonical_order.jsonl", "kind": "jsonl",
                                 "expect_code": "C16_JSONL", "schema_path_contains": None, "ledger": 0})
    manifest["negative"].sort(key=lambda x: x["file"])
    files["FIXTURES.json"] = json.dumps(manifest, indent=1, sort_keys=True).encode() + b"\n"
    return files


def main(argv):
    check = "--check" in argv
    diff = []
    for rel_path, data in sorted(outputs().items()):
        p = HERE / rel_path
        if check:
            if not p.is_file() or p.read_bytes() != data:
                diff.append(rel_path)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    if check and diff:
        print("fixtures differ from builder output:", ", ".join(diff))
        return 1
    print("fixtures " + ("match builder output" if check else "written"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
