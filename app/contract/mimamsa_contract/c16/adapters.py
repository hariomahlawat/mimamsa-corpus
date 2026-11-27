"""Backward-compatible adapters between existing corpus formats and mimamsa-corpus-contract/2.0.

Every adapter is pure and deterministic (no clock, no network, no file reads). Values an adapter cannot establish
are emitted as UNRESOLVED or as the most conservative state; nothing is promoted. See C16_COMPATIBILITY_MATRIX.md.

  identity_from_v1_document     contract v1 document (+ derived_text)          -> document_identity
  anchor_from_v1_page_anchor    v1 page_anchor (PageKey/SpanKey)               -> evidence_anchor
  anchor_to_v1_page_anchor      evidence_anchor                                -> v1 page_anchor or None
  relationship_from_v1_candidate v1 graph_edge candidate                       -> corpus_relationship or None
  graph_projection              corpus_relationship                            -> C15 graph edge (+ review overlay)
  from_pr76_inventory_row       PR #76 LOCAL_INVENTORY.jsonl row               -> identity, admission, relationships
  from_v7_record                Cycle 15 candidate package v7 records.jsonl row -> identity, anchors, relationships
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

from . import canonical
from .schemas import CONTRACT_ID

PRODUCER = {"name": "mimamsa-contract-c16-adapters", "version": "1.0.0", "commit": None, "config_sha256": None}
UNRESOLVED = lambda reason, note=None: {"unresolved": reason, "note": note} if note else {"unresolved": reason}  # noqa: E731

# ---------------------------------------------------------------------------------------------------------------
# C15 graph mapping (contract section 7). Existing C15 edge types are reused; three classification types and two
# architecture section 5 types already in the v1 candidate vocabulary are proposed additions to GraphModel.EdgeType.
CATEGORY_TO_EDGE = {
    "classified_under_subject": "CLASSIFIED_UNDER_SUBJECT",       # proposed (C16)
    "classified_under_chapter": "CLASSIFIED_UNDER_CHAPTER",       # proposed (C16)
    "associated_with_provision": "ASSOCIATED_WITH_PROVISION",     # proposed (C16)
    "cites_provision": "CITES_PROVISION",                         # C15 existing
    "interprets_provision": "INTERPRETS_PROVISION",               # architecture s.5 / v1 candidate enum; proposed for C15
    "refers_to_judgment": "CITES_JUDGMENT",                       # C15 existing
    "follows": "FOLLOWS_PROPOSITION",                             # C15 existing
    "distinguishes": "DISTINGUISHES_PROPOSITION",                 # architecture s.5 / v1 candidate enum; proposed for C15
    "overrules": "OVERRULES_OR_LIMITS_PROPOSITION",               # C15 existing
}
PROPOSED_EDGE_TYPES = {"CLASSIFIED_UNDER_SUBJECT", "CLASSIFIED_UNDER_CHAPTER", "ASSOCIATED_WITH_PROVISION",
                       "INTERPRETS_PROVISION", "DISTINGUISHES_PROPOSITION"}
PROPOSED_NODE_KINDS = {"subject": "SUBJ:", "chapter": "CHAP:"}
V1_RELATION_TO_CATEGORY = {
    "CITES_PROVISION": "cites_provision", "INTERPRETS_PROVISION": "interprets_provision",
    "CITES_JUDGMENT": "refers_to_judgment", "FOLLOWS_PROPOSITION": "follows",
    "DISTINGUISHES_PROPOSITION": "distinguishes", "OVERRULES_OR_LIMITS_PROPOSITION": "overrules",
}
BUILDER_VERIFICATION = ("CANDIDATE", "EXTRACTED_STRUCTURE", "CURATED_NAVIGATION")


def c15_reference_id(raw: str) -> str:
    """Same as GraphIds.Reference: REF:<first 16 hex of sha256(raw)>."""
    return "REF:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def c16_edge_id(edge_type: str, from_id: str, to_id: str, origin: str, relationship_id: str) -> str:
    """Edge id for C16-origin edges: E + 20 hex of sha256(type|from|to|origin|relationship_id). The relationship id
    is the discriminator, so two relationships with the same endpoints (e.g. the same file classified from two
    folders) stay two edges, unlike GraphIds.EdgeId which keys on (source doc, page, quote)."""
    return "E" + hashlib.sha256(f"{edge_type}|{from_id}|{to_id}|{origin}|{relationship_id}".encode("utf-8")).hexdigest()[:20]


def graph_projection(rel: dict, anchors: dict | None = None) -> dict | None:
    """The C15 graph edge a relationship becomes, plus a graph_edge_reviews overlay row where the relationship
    carries a review. legally_validated returns only a review overlay on the validated relationship's edge (the
    caller must supply that relationship's projection to resolve its edge id) and is refused at AUTH-LEDGER v0 by
    the consumer. Returns None for categories with no edge."""
    cat = rel["category"]
    if cat == "legally_validated":
        return {"edge": None, "review": {"validates_relationship_id": rel["validates_relationship_id"],
                                          "review_state": "LEGAL_REVIEWED", "approval_ref": rel["approval_ref"]}}
    etype = CATEGORY_TO_EDGE.get(cat)
    if etype is None:
        return None
    subj = rel["subject"]["graph_node_ref"]
    from_id = subj if isinstance(subj, str) else f"DOC:{rel['subject']['doc_id']}"
    tgt = rel["target"]
    to_id = tgt["node_id"] if tgt["resolved"] else c15_reference_id(tgt["raw_reference"])
    basis = rel["evidentiary_basis"]
    origin = "C16_" + ("DOCUMENT_TEXT" if basis.startswith("DOCUMENT_TEXT") else basis)
    page = None
    if anchors:
        for aid in rel["anchors"]:
            a = anchors.get(aid)
            if a and a["locator"].get("citable_as_source_page"):
                page = a["locator"]["physical_page"]
                break
    ver = rel["verification"]
    ts = rel["temporal_scope"]
    edge = {
        "id": c16_edge_id(etype, from_id, to_id, origin, rel["relationship_id"]), "type": etype, "from": from_id,
        "to": to_id, "origin": origin, "source_doc_id": rel["subject"]["doc_id"],
        "source_copy_sha256": rel["subject"]["source_copy_sha256"], "page": page, "quote": None,
        "temporal_from": ts["from"], "temporal_from_status": ts["from_status"], "temporal_to": ts["to"],
        "temporal_to_status": ts["to_status"],
        # GraphStore publication refuses reviewed values: the edge carries a builder value, the review is an overlay.
        "verification": ver if ver in BUILDER_VERIFICATION else "CANDIDATE",
        "review_state": "UNREVIEWED", "uncertainty": rel["uncertainty"], "has_legal_effect": rel["has_legal_effect"],
        "relationship_id": rel["relationship_id"],
        "needs_node_resolution": from_id.startswith(("INSTCODE:", "DOC:")),
    }
    review = None
    if ver == "DOCUMENTARY_CHECKED":
        review = {"edge_id": edge["id"], "review_state": "DOCUMENTARY_CHECKED", "review_ref": rel["review_ref"]}
    return {"edge": edge, "review": review}


# ---------------------------------------------------------------------------------------------------------------
# contract v1

def _v1_representation(doc: dict) -> tuple[str, str]:
    mime, method = doc["source_copy"]["mime_type"], doc.get("text_method")
    if mime == "application/pdf":
        return ({"ocr": "SCANNED_PDF", "mixed": "MIXED_PDF"}.get(method, "NATIVE_DIGITAL_PDF"), "PHYSICAL_PAGES")
    if mime.endswith("wordprocessingml.document"):
        return "WORD_IMAGES_NOT_INVENTORIED", "NONE_FLOW_DOCUMENT"
    if mime == "text/html":
        return "HTML_PAGE", "NONE_FLOW_DOCUMENT"
    if mime == "text/plain":
        return "PLAIN_TEXT", "NONE_FLOW_DOCUMENT"
    return "IMAGE_FILE", "SINGLE_IMAGE"


_FORMAT = {"application/pdf": "PDF", "text/html": "HTML", "text/plain": "TXT", "image/png": "PNG", "image/jpeg": "JPEG",
           "image/tiff": "TIFF", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX"}
_V1_METHOD = {"pdf_text": "NATIVE_TEXT_LAYER", "ocr": "OCR_PAGE_IMAGE", "html": "HTML", "none": "NONE"}


def _work_kind(doc_type: str) -> str:
    return {"judgment": "JUDGMENT", "order": "ORDER", "act": "INSTRUMENT", "rules": "INSTRUMENT",
            "regulations": "INSTRUMENT", "notification": "NOTIFICATION", "manual": "MANUAL",
            "book_historical": "COMMENTARY_OR_NOTE"}.get(doc_type, "UNKNOWN")


def identity_from_v1_document(doc: dict, derived: list[dict] | None = None, *, corpus_generation_id: str,
                              instrument_code: str | None = None) -> dict:
    """v1 document (+ its derived_text records) -> document_identity. v1 ids are kept unchanged."""
    sc = doc["source_copy"]
    kind, pagination = _v1_representation(doc)
    v1c = sc.get("completeness") or "NOT_CHECKED"
    wk = _work_kind(doc["doc_type"])
    j = doc.get("judicial") or {}
    work = {"work_kind": wk, "identity_basis": "METADATA_CANDIDATE", "identity_verification": "CANDIDATE",
            "proceeding_numbers_as_printed": list(j.get("case_numbers") or [])}
    if wk in ("JUDGMENT", "ORDER"):
        work["judgment_id"] = j.get("judgment_identity_id") or UNRESOLVED("NOT_DETERMINED")
        work["graph_node_ref"] = f"JUD:{doc['doc_id']}"
    elif wk in ("INSTRUMENT", "NOTIFICATION"):
        work["instrument_code"] = instrument_code or UNRESOLVED("NOT_DETERMINED")
        work["graph_node_ref"] = f"INSTCODE:{instrument_code}" if instrument_code else UNRESOLVED("NOT_DETERMINED")
    else:
        work["graph_node_ref"] = UNRESOLVED("NOT_DETERMINED")
    ders = []
    for t in derived or []:
        methods = sorted({_V1_METHOD[p["method"]] for p in t["pages"]}) or ["NONE"]
        ocr = any(m.startswith("OCR") for m in methods)
        tools = (t["pipeline"].get("tools") or {})
        ders.append({
            "derivative_id": f"{t['doc_id']}@{t['pipeline']['name']}/{t['pipeline']['version']}",
            "pipeline_name": t["pipeline"]["name"], "pipeline_version": t["pipeline"]["version"],
            "derivative_text_sha256": t["text_sha256"],
            "pagination_basis": "SOURCE_PHYSICAL" if pagination == "PHYSICAL_PAGES" else "GENERATED_SEGMENT",
            "methods": methods,
            "ocr_config": ({"engine": tools.get("ocr", "unknown"), "engine_version": "unknown", "languages": ["eng"],
                            "config_sha256": hashlib.sha256(canonical.canonical_bytes(tools)).hexdigest()} if ocr else None),
            "text_reliability": "not_assessed", "quoting_permitted": False,  # reliability not assessed here; the app's TextQuality decides
            "coverage": {"units_total": len(t["pages"]), "units_with_text": sum(1 for p in t["pages"] if p["char_count"] > 0),
                         "images_total": 0 if kind != "WORD_IMAGES_NOT_INVENTORIED" else UNRESOLVED("NOT_YET_PROCESSED"),
                         "images_text_extracted": 0},
        })
    restricted = doc["restriction"]["eligibility"] == "RESTRICTED"
    return {
        "contract": CONTRACT_ID, "record_kind": "document_identity", "doc_id": doc["doc_id"],
        "source_copy": {"sha256": sc["sha256"], "bytes": sc["bytes"], "mime_type": sc["mime_type"],
                        "detected_format": _FORMAT[sc["mime_type"]],
                        "page_count": sc.get("page_count") if pagination == "PHYSICAL_PAGES" and sc.get("page_count") is not None
                        else (None if pagination == "NONE_FLOW_DOCUMENT" else UNRESOLVED("NOT_YET_PROCESSED")),
                        "physical_pagination": pagination, "vault_path": sc["vault_path"]},
        "representation": {"representation_kind": kind,
                           "origin_status": "CARRIER_ISSUED_COPY_CLAIMED" if (doc["provenance"].get("source_url") and doc["provenance"]["acquisition_channel"] == "CRAWLER" and doc["status_axes"]["source_authenticity"]["policy_v1"]["carrier_provenance"] in ("ISSUING_AUTHORITY", "GOVERNMENT_HOSTED_COPY")) else "ACQUIRED_COPY_ORIGIN_UNDETERMINED",
                           # v1 completeness is byte completeness against the carrier; C16 completeness is about the
                           # work, which v1 never established: COMPLETE maps to NOT_CHECKED (contract section 6.2)
                           "content_scope": "UNDETERMINED",
                           "completeness": "NOT_CHECKED" if v1c == "COMPLETE" else v1c,
                           "completeness_basis": f"v1 source_copy.completeness={v1c}"},
        "work_identity": work,
        "embedded_images": UNRESOLVED("NOT_YET_PROCESSED") if kind == "WORD_IMAGES_NOT_INVENTORIED" else [],
        "text_derivatives": ders,
        "provenance": {"acquisition": doc["provenance"], "observations": [], "processing_history": [],
                       "carrier_provenance": doc["status_axes"]["source_authenticity"]["policy_v1"]["carrier_provenance"]},
        "restriction": doc["restriction"],
        "integrity": {"source_integrity": doc["status_axes"]["source_integrity"]["value"],
                      "basis": "copied from v1 status_axes.source_integrity"},
        "status_axes": doc["status_axes"],
        "research_eligibility": {"state": "NOT_ELIGIBLE" if restricted else "NOT_ASSESSED", "quoting_permitted": False,
                                 "source_page_citation_permitted": False, "whole_work_claims_permitted": False,
                                 "graph_evidence_permitted": False,
                                 "basis": ["RESTRICTED"] if restricted else ["ELIGIBILITY_NOT_ASSESSED"]},
        "corpus_generation_id": corpus_generation_id,
    }


def anchor_from_v1_page_anchor(pa: dict, *, doc_id: str, method: str = "NATIVE_TEXT_LAYER",
                               text_reliability: str = "not_assessed", ocr_config: dict | None = None,
                               ocr_mean_confidence=None) -> dict:
    """v1 page_anchor -> evidence_anchor. A span is kept only when it is bound (pipeline name, version and
    derivative hash all present), exactly as the v1 SPAN_UNBOUND rule; otherwise the anchor is page-only."""
    bound = all(pa.get(k) for k in ("pipeline_name", "pipeline_version", "derivative_text_sha256"))
    has_span = pa.get("char_start") is not None and pa.get("char_end") is not None and pa.get("text_sha256")
    ocr = method.startswith("OCR")
    a = {
        "contract": CONTRACT_ID, "record_kind": "evidence_anchor", "anchor_id": "", "doc_id": doc_id,
        "original_sha256": pa["source_copy_sha256"], "representation_sha256": pa["source_copy_sha256"],
        "derivative_text_sha256": pa.get("derivative_text_sha256") if bound and has_span else None, "image_sha256": None,
        "locator": {"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": pa["page"], "citable_as_source_page": True,
                    "paragraph_label": pa.get("paragraph_label")},
        "text_span": ({"passage_id": pa.get("passage_id"), "char_start": pa["char_start"], "char_end": pa["char_end"],
                       "text_sha256": pa["text_sha256"]} if bound and has_span else None),
        "extraction": {"method": method, "pipeline_name": pa.get("pipeline_name") or "unknown",
                       "pipeline_version": pa.get("pipeline_version") or "unknown", "ocr_config": ocr_config},
        "quality": {"text_reliability": text_reliability,
                    "ocr_mean_confidence": (ocr_mean_confidence if ocr_mean_confidence is not None else UNRESOLVED("NOT_DETERMINED")) if ocr else None,
                    "low_confidence": False},
        "verification": {"state": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None},
        "quoting_permitted": False, "quote": None,
    }
    a["anchor_id"] = canonical.anchor_id(a)
    return a


def anchor_to_v1_page_anchor(a: dict) -> dict | None:
    """evidence_anchor -> v1 page_anchor (PageKey, plus SpanKey fields when bound). None when the anchor has no
    citable source page (generated segment, image sequence, text flow, unmapped reconstruction): v1 cannot carry
    it and the consumer must not invent a page."""
    loc = a["locator"]
    if not loc.get("citable_as_source_page"):
        return None
    out = {"source_copy_sha256": a["original_sha256"], "page": loc["physical_page"],
           "paragraph_label": loc.get("paragraph_label")}
    span = a.get("text_span")
    # a span measured on a reconstruction never binds to the original's derivative
    if span and a["representation_sha256"] == a["original_sha256"] and a.get("derivative_text_sha256"):
        out.update(passage_id=span.get("passage_id"), char_start=span["char_start"], char_end=span["char_end"],
                   text_sha256=span["text_sha256"], pipeline_name=a["extraction"]["pipeline_name"],
                   pipeline_version=a["extraction"]["pipeline_version"], derivative_text_sha256=a["derivative_text_sha256"])
    if a.get("quoting_permitted") and a.get("quote"):
        out["quote"] = a["quote"]
    return out


def relationship_from_v1_candidate(c: dict, *, subject_sha256: str, subject_node: str, source_date: str | None,
                                   anchors: list[dict]) -> dict | None:
    """v1 graph_edge candidate -> corpus_relationship, for the six citation/treatment relations in C16 scope.
    Statutory amendment relations (AMENDS_PROVISION_VERSION etc.) stay v1 candidates / A4 records: None."""
    p = c["payload"]
    cat = V1_RELATION_TO_CATEGORY.get(p["relation"])
    if cat is None:
        return None
    tgt = p["target"]
    target = ({"resolved": True, "node_id": tgt["node_id"]} if tgt["resolved"] and tgt.get("node_id") else
              {"resolved": False, "node_id": None, "raw_reference": tgt.get("raw_reference") or "unresolved",
               "unresolved": UNRESOLVED("NOT_DETERMINED")})
    status = c["status"]
    rel = {
        "contract": CONTRACT_ID, "record_kind": "corpus_relationship", "relationship_id": "", "category": cat,
        "subject": {"doc_id": c["source_doc_id"], "source_copy_sha256": subject_sha256, "graph_node_ref": subject_node},
        "target": target,
        "evidentiary_basis": "DOCUMENT_TEXT_REVIEWED" if status == "DOCUMENTARY_CHECKED" else "DOCUMENT_TEXT_EXTRACTED",
        "source": {"producer": {"name": c["extractor"]["name"], "version": c["extractor"]["version"],
                                "commit": c["extractor"]["artefact_commit"], "config_sha256": None},
                   "rule_id": "V1-" + p["relation"].replace("_", "-"), "rule_version": c["extractor"]["version"][:32],
                   "author_id": c["extractor"].get("author_id")},
        "anchors": sorted(a["anchor_id"] for a in anchors),
        "verification": "DOCUMENTARY_CHECKED" if status == "DOCUMENTARY_CHECKED" else "CANDIDATE",
        "review_ref": c.get("review_ref") if status == "DOCUMENTARY_CHECKED" else None,
        "approval_ref": None, "validates_relationship_id": None,
        "proposition_ref": UNRESOLVED("NOT_DETERMINED") if cat in ("follows", "distinguishes", "overrules") else None,
        "temporal_scope": {"from": source_date, "from_status": "AS_OF_SOURCE_DATE" if source_date else "NOT_RECORDED",
                           "to": None, "to_status": "NOT_APPLICABLE"},
        "has_legal_effect": bool(p["has_legal_effect"]), "is_finding": status == "DOCUMENTARY_CHECKED",
        "uncertainty": ("Extracted citation candidate; a citation does not establish how the source treated the target."
                        if cat in ("cites_provision", "refers_to_judgment") else
                        "Treatment candidate; requires legal review before any reliance."),
    }
    rel["relationship_id"] = canonical.relationship_id(rel)
    return rel


# ---------------------------------------------------------------------------------------------------------------
# PR #76 local-collection reconciliation (LOCAL_INVENTORY.jsonl rows; read-only)

PR76_DISPOSITION_TO_DECISION = {
    "EXACT_DUPLICATE": "REJECTED_EXACT_DUPLICATE",
    "VERIFIED_ALTERNATE_COPY": "ADMITTED_AS_ALTERNATE_COPY",
    "PROBABLE_DUPLICATE": "HELD_IDENTITY_UNRESOLVED",
    "NEW_DOCUMENT": "ADMITTED_AS_PRIMARY",
    "IMPROVED_SOURCE_COPY": "HELD_IDENTITY_UNRESOLVED",
    "HISTORICAL_RECOVERY_MATCH": "HELD_IDENTITY_UNRESOLVED",
    "IDENTITY_UNRESOLVED": "HELD_IDENTITY_UNRESOLVED",
    "RELEVANCE_UNRESOLVED": "HELD_RELEVANCE_UNRESOLVED",
    "NON_RELEVANT": "REJECTED_NON_RELEVANT",
    "ACCESS_RESTRICTED": "HELD_ACCESS_MARKING_REVIEW",   # a detected marking is not a register entry
    "INTEGRITY_FAILURE": "QUARANTINED_INTEGRITY",
    "UNSUPPORTED_FORMAT": "UNSUPPORTED_FORMAT",
}
_PR76_FORMAT = {"PDF": ("PDF", "application/pdf"), "DOCX": ("DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                "DOC": ("DOC", "application/msword"), "RTF": ("RTF", "application/rtf"), "TXT": ("TXT", "text/plain")}

# Filename provision-list rule (C16-FN-PROVLIST 1.0). Abbreviation readings are candidates: the table records the
# reading used and the alternatives that remain open. It is deliberately small; an unknown abbreviation yields no
# relationship rather than a guess.
ABBREVIATIONS = {
    "AR": {"code": "AR-1954", "prefix": "r", "expansion": "Army Rules, 1954",
           "alternatives": ["Regulations for the Army (para), if the owner used AR for Regulations"]},
    "AA": {"code": "AA-1950", "prefix": "s", "expansion": "Army Act, 1950", "alternatives": []},
}
ABBREV_LEXICON_REF = "docs/architecture/c16/C16_CORPUS_INTEGRATION_CONTRACT.md#83-filename-and-folder-classification-rules"
FN_PROVLIST = re.compile(r"^\s*(?P<abbr>[A-Z]{2,4})\s*(?:Rule|Rules|Sec|Section|s\.|r\.)?\s*"
                         r"(?P<nums>\d{1,3}[A-Z]?(?:\s*(?:,|&|and)\s*\d{1,3}[A-Z]?)*)\s*[-–—]")


def slug(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80] or "unnamed"


def local_doc_id(sha256: str) -> str:
    return f"local-{sha256[:16]}"


def _classification(category, *, doc_id, sha, subject_node, target, basis, collection, rel_path, inventory_id,
                    component, matched, expansion, verification, uncertainty):
    rel = {
        "contract": CONTRACT_ID, "record_kind": "corpus_relationship", "relationship_id": "", "category": category,
        "subject": {"doc_id": doc_id, "source_copy_sha256": sha, "graph_node_ref": subject_node},
        "target": {"resolved": True, "node_id": target}, "evidentiary_basis": basis,
        "source": {"producer": PRODUCER, "rule_id": "C16-FOLDER-SUBJECT" if basis == "FOLDER_PATH" else "C16-FN-PROVLIST",
                   "rule_version": "1.0", "author_id": None},
        "classification_provenance": {"collection": collection, "relative_path": rel_path, "inventory_id": inventory_id,
                                      "path_component": component, "matched_text": matched,
                                      "abbreviation_expansion": expansion},
        "anchors": [], "verification": verification, "review_ref": None, "approval_ref": None,
        "validates_relationship_id": None, "proposition_ref": None,
        "temporal_scope": {"from": None, "from_status": "NOT_APPLICABLE", "to": None, "to_status": "NOT_APPLICABLE"},
        "has_legal_effect": False, "is_finding": False, "uncertainty": uncertainty,
    }
    rel["relationship_id"] = canonical.relationship_id(rel)
    return rel


def classify_path(rel_path: str, *, doc_id: str, sha: str, subject_node, collection: str,
                  inventory_id: str | None = None) -> list[dict]:
    """Folder components -> classified_under_subject (SUBJ:local:<slug>), and a filename provision list
    ('AR 22, 23, 30 - ...') -> one associated_with_provision per number. Each relationship keeps its own path."""
    parts = unicodedata.normalize("NFC", rel_path.replace("\\", "/")).split("/")
    out = []
    for i, folder in enumerate(parts[:-1]):
        out.append(_classification(
            "classified_under_subject", doc_id=doc_id, sha=sha, subject_node=subject_node,
            target=f"SUBJ:local:{slug(folder)}", basis="FOLDER_PATH", collection=collection, rel_path="/".join(parts),
            inventory_id=inventory_id, component=i, matched=folder, expansion=None, verification="CURATED_NAVIGATION",
            uncertainty="Owner folder label; a navigation aid, not a finding about the document."))
    m = FN_PROVLIST.match(parts[-1])
    if m and m["abbr"] in ABBREVIATIONS:
        ab = ABBREVIATIONS[m["abbr"]]
        for n in re.findall(r"\d{1,3}[A-Z]?", m["nums"]):
            out.append(_classification(
                "associated_with_provision", doc_id=doc_id, sha=sha, subject_node=subject_node,
                target=f"PROV:{ab['code']}:{ab['prefix']}.{n}", basis="FILENAME_PATTERN", collection=collection,
                rel_path="/".join(parts), inventory_id=inventory_id, component=-1, matched=f"{m['abbr']} {n}",
                expansion={"abbreviation": m["abbr"], "expansion": ab["expansion"], "lexicon_ref": ABBREV_LEXICON_REF,
                           "alternatives": ab["alternatives"]},
                verification="CANDIDATE",
                uncertainty="Read from the owner's file name by rule C16-FN-PROVLIST; the abbreviation reading and the "
                            "provision are candidates, not a finding that the judgment concerns this provision."))
    return out


def _gate(gid, result, ev=None):
    return {"gate_id": gid, "result": result, "evidence_ref": ev}


def from_pr76_inventory_row(row: dict, *, collection: str, corpus_generation_id: str,
                            primary_sha256: str | None = None) -> tuple[dict, dict, list[dict]]:
    """One PR #76 LOCAL_INVENTORY.jsonl row -> (document_identity, corpus_admission, classification relationships).
    Conservative by construction: nothing becomes application-eligible, Word files are WORD_IMAGES_NOT_INVENTORIED
    until an image inventory exists (the review finding that embedded screenshots were not extracted)."""
    sha = row["sha256"]
    doc_id = local_doc_id(sha)
    fmt = row.get("detected_format") or ""
    detected, mime = _PR76_FORMAT.get(fmt, (None, None))
    is_pdf, is_word = detected == "PDF", detected in ("DOCX", "DOC", "RTF")
    ocr_pages = row.get("ocr_required_pages") or []
    pages = row.get("page_count")
    if is_pdf:
        kind = "SCANNED_PDF" if pages and len(ocr_pages) >= pages else ("MIXED_PDF" if ocr_pages else "NATIVE_DIGITAL_PDF")
        pagination = "PHYSICAL_PAGES"
    elif is_word:
        kind, pagination = "WORD_IMAGES_NOT_INVENTORIED", "NONE_FLOW_DOCUMENT"
    else:
        kind, pagination = "PLAIN_TEXT", "NONE_FLOW_DOCUMENT"
    ctype = row.get("candidate_document_type") or "legal_reference"
    wk = {"judgment": "JUDGMENT", "order": "ORDER", "act": "INSTRUMENT", "rules": "INSTRUMENT",
          "manual": "MANUAL", "notification": "NOTIFICATION"}.get(ctype, "UNKNOWN")
    subject_node = f"JUD:{doc_id}" if wk in ("JUDGMENT", "ORDER") else UNRESOLVED("NOT_DETERMINED")
    work = {"work_kind": wk, "graph_node_ref": subject_node, "identity_basis": "METADATA_CANDIDATE",
            "identity_verification": "CANDIDATE",
            "proceeding_numbers_as_printed": list((row.get("metadata_candidate") or {}).get("case_numbers") or [])}
    if wk in ("JUDGMENT", "ORDER"):
        work["judgment_id"] = UNRESOLVED("NOT_DETERMINED")
    if wk in ("INSTRUMENT", "NOTIFICATION"):
        work["instrument_code"] = UNRESOLVED("NOT_DETERMINED")
    ders = []
    if row.get("derivative_sha256"):
        method = {"pymupdf-native": "NATIVE_TEXT_LAYER", "docx-xml": "DOCX_XML", "utf8-replace": "PLAIN_TEXT"}.get(row.get("extraction_method"), "NONE")
        units = pages if is_pdf and pages else 1
        ders.append({"derivative_id": f"{doc_id}@c16-local-reconcile/{row.get('classification_version', 0)}",
                     "pipeline_name": "c16-local-reconcile", "pipeline_version": str(row.get("classification_version", 0)),
                     "derivative_text_sha256": row["derivative_sha256"],
                     "pagination_basis": "SOURCE_PHYSICAL" if is_pdf else "GENERATED_SEGMENT",
                     "methods": [method], "ocr_config": None, "text_reliability": "not_assessed", "quoting_permitted": False,
                     "coverage": {"units_total": units, "units_with_text": max(0, units - len(ocr_pages)) if is_pdf else (1 if row.get("text_available") else 0),
                                  "images_total": UNRESOLVED("NOT_YET_PROCESSED") if is_word else 0, "images_text_extracted": 0}})
    identity = {
        "contract": CONTRACT_ID, "record_kind": "document_identity", "doc_id": doc_id,
        "source_copy": {"sha256": sha, "bytes": row["size_bytes"], "mime_type": mime or "application/pdf",
                        "detected_format": detected or "PDF",
                        "page_count": (pages if pages is not None else UNRESOLVED("NOT_YET_PROCESSED")) if is_pdf else None,
                        "physical_pagination": pagination,
                        "vault_path": f"vault/sha256/{sha[:2]}/{sha}"},
        "representation": {"representation_kind": kind, "origin_status": "ACQUIRED_COPY_ORIGIN_UNDETERMINED",
                           "content_scope": "UNDETERMINED", "completeness": "NOT_CHECKED"},
        "work_identity": work,
        "embedded_images": UNRESOLVED("NOT_YET_PROCESSED") if is_word else [],
        "text_derivatives": ders,
        "provenance": {"acquisition": {"acquisition_channel": "MANUAL_OWNER", "source_url": None, "retrieved_at": None,
                                       "original_filename": row.get("filename"), "hf": None},
                       "carrier_provenance": "USER_SUPPLIED",
                       "observations": [{"collection": collection, "relative_path": unicodedata.normalize("NFC", row["relative_path"].replace("\\", "/")),
                                         "inventory_id": row.get("inventory_id"), "observed_at": None}],
                       "processing_history": []},
        "restriction": {"access_marking": None, "eligibility": "NOT_ASSESSED", "restriction_id": None},
        "integrity": {"source_integrity": "DECLARED_HASH_ONLY", "basis": "SHA-256 computed by the PR #76 reconciliation; not re-verified against an independent manifest"},
        "research_eligibility": {"state": "NOT_ASSESSED", "quoting_permitted": False, "source_page_citation_permitted": False,
                                 "whole_work_claims_permitted": False, "graph_evidence_permitted": False,
                                 "basis": ["ELIGIBILITY_NOT_ASSESSED"] + (["EMBEDDED_IMAGES_NOT_EXTRACTED"] if is_word else [])},
        "corpus_generation_id": corpus_generation_id,
    }
    disp = row.get("disposition") or "IDENTITY_UNRESOLVED"
    decision = PR76_DISPOSITION_TO_DECISION.get(disp, "HELD_IDENTITY_UNRESOLVED")
    if decision == "ADMITTED_AS_PRIMARY" and is_word:
        decision = "HELD_EXTRACTION_INCOMPLETE"
    elif decision == "ADMITTED_AS_PRIMARY" and ocr_pages:
        decision = "HELD_OCR_REQUIRED"
    dup = None
    if decision == "ADMITTED_AS_ALTERNATE_COPY":
        if primary_sha256 and primary_sha256 != sha:
            dup = {"sha256": primary_sha256, "doc_id": local_doc_id(primary_sha256), "relation": "NORMALIZED_TEXT_IDENTICAL"}
        else:
            decision = "HELD_IDENTITY_UNRESOLVED"
    if decision == "REJECTED_EXACT_DUPLICATE":
        dup = {"sha256": sha, "doc_id": None, "relation": "BYTE_IDENTICAL"}
    rel = row.get("relevance")
    gates = [
        _gate("G01_HASH_VERIFIED", "PASS", "c16_reconcile sha256"),
        _gate("G02_FORMAT_DETECTED", "PASS" if detected else "FAIL"),
        _gate("G03_RESTRICTED_REGISTER", "NOT_RUN"),
        _gate("G04_ACCESS_MARKING_REVIEWED", "FAIL" if row.get("restricted") else "NOT_RUN"),
        _gate("G05_IDENTITY_RECORD_VALID", "NOT_RUN"),
        _gate("G06_TEXT_DERIVATIVE_VERIFIED", "FAIL" if row.get("parsing_error") else "NOT_RUN"),
        _gate("G07_EMBEDDED_IMAGES_ACCOUNTED", "NOT_RUN" if is_word else "NOT_APPLICABLE"),
        _gate("G08_RELEVANCE_ASSESSED", {True: "PASS", False: "FAIL"}.get(rel, "NOT_RUN")),
        _gate("G09_DUPLICATE_RESOLVED", "PASS" if disp in ("NEW_DOCUMENT", "EXACT_DUPLICATE", "VERIFIED_ALTERNATE_COPY") else "NOT_RUN"),
        _gate("G10_SCHEMA_VALID", "NOT_RUN"),
    ]
    adm = {"contract": CONTRACT_ID, "record_kind": "corpus_admission", "admission_id": "",
           "subject": {"doc_id": doc_id, "source_copy_sha256": sha}, "corpus_generation_id": corpus_generation_id,
           "decision": decision,
           "source_disposition": {"system": "c16-local-reconcile", "value": disp,
                                  "secondary_flags": sorted(row.get("secondary_flags") or [])},
           "duplicate_of": dup, "restriction_id": None, "gates": gates, "application_eligible": False,
           "publication_effect": "NONE", "legal_effect": "NONE",
           "decided_by": {"kind": "AUTOMATED_RULE", "id": "c16-admission-adapter"}, "decided_at": None,
           "rule_set": {"id": "c16-admission", "version": "1.0"},
           "reasons": [f"derived from PR #76 disposition {disp}"], "supersedes_admission_id": None}
    adm["admission_id"] = canonical.admission_id(adm)
    rels = classify_path(row["relative_path"], doc_id=doc_id, sha=sha, subject_node=subject_node,
                         collection=collection, inventory_id=row.get("inventory_id"))
    return identity, adm, rels


# ---------------------------------------------------------------------------------------------------------------
# Cycle 15 candidate package v7 (records.jsonl, schema mimamsa-c14-document-candidate-v1)

def from_v7_record(rec: dict, *, corpus_generation_id: str, pipeline=("c15-candidate-v7", "physical-page-v1")) -> tuple[list[dict], list[dict]]:
    """v7 record -> (evidence anchors, relationships). v7 offsets are one-based physical pages and zero-based
    code-point offsets into that page's text, the same convention as v1; the v7 derivative is not in the
    [[page N]] format, so spans bind to the v7 derivative hash and the consumer re-derives before serving."""
    doc_id, sha, dsha = rec["doc_id"], rec["original_sha256"], rec["derivative_sha256"]
    anchors, rels = [], []

    def anchor(m):
        a = {"contract": CONTRACT_ID, "record_kind": "evidence_anchor", "anchor_id": "", "doc_id": doc_id,
             "original_sha256": sha, "representation_sha256": sha, "derivative_text_sha256": dsha, "image_sha256": None,
             "locator": {"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": m["page"], "citable_as_source_page": True},
             "text_span": {"passage_id": None, "char_start": m["start"], "char_end": m["end"],
                           "text_sha256": hashlib.sha256(m["text"].encode("utf-8")).hexdigest()},
             "extraction": {"method": "NATIVE_TEXT_LAYER", "pipeline_name": pipeline[0], "pipeline_version": pipeline[1], "ocr_config": None},
             "quality": {"text_reliability": "not_assessed", "ocr_mean_confidence": None, "low_confidence": False},
             "verification": {"state": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "review_ref": None},
             "quoting_permitted": False, "quote": None}
        a["anchor_id"] = canonical.anchor_id(a)
        return a

    date = rec.get("decision_date_metadata")
    date = date if isinstance(date, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", date) else None
    for field, cat, rule in (("provision_mentions", "cites_provision", "V7-PROVISION-MENTION"),
                             ("citation_mentions", "refers_to_judgment", "V7-CITATION-MENTION")):
        for m in rec.get(field) or []:
            a = anchor(m)
            anchors.append(a)
            r = {"contract": CONTRACT_ID, "record_kind": "corpus_relationship", "relationship_id": "", "category": cat,
                 "subject": {"doc_id": doc_id, "source_copy_sha256": sha, "graph_node_ref": f"JUD:{doc_id}"},
                 "target": {"resolved": False, "node_id": None, "raw_reference": m["text"], "unresolved": UNRESOLVED("NOT_DETERMINED")},
                 "evidentiary_basis": "DOCUMENT_TEXT_EXTRACTED",
                 "source": {"producer": {"name": pipeline[0], "version": pipeline[1], "commit": None, "config_sha256": None},
                            "rule_id": rule, "rule_version": "v7", "author_id": None},
                 "anchors": [a["anchor_id"]], "verification": "CANDIDATE", "review_ref": None, "approval_ref": None,
                 "validates_relationship_id": None, "proposition_ref": None,
                 "temporal_scope": {"from": date, "from_status": "AS_OF_SOURCE_DATE", "to": None, "to_status": "NOT_APPLICABLE"} if date
                 else {"from": None, "from_status": "NOT_RECORDED", "to": None, "to_status": "NOT_APPLICABLE"},
                 "has_legal_effect": False, "is_finding": False,
                 "uncertainty": "Mention located by pattern in the v7 candidate package; target not resolved."}
            r["relationship_id"] = canonical.relationship_id(r)
            rels.append(r)
    return anchors, rels
