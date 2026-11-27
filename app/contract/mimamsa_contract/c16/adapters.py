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


def graph_projection(rel: dict, anchors: dict | None = None, usable: set | None = None) -> dict | None:
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
    # an anchor locates the edge only when the consumer has verified it (evidence.usable_as_graph_evidence, with the
    # span checked against the derivative bytes): `usable` is that set of anchor ids; without it, no page is shown
    if anchors and usable:
        for aid in rel["anchors"]:
            a = anchors.get(aid)
            if a and aid in usable and a["locator"].get("citable_as_source_page"):
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


def anchor_to_v1_page_anchor(a: dict, identity: dict | None = None, *, span_verified: bool = False,
                             quote: str | None = None) -> dict | None:
    """evidence_anchor -> v1 page_anchor. PageKey only when the anchor is a citable page of its bound identity (page
    within the copy, copy permits page citation, anchor not INCORRECT); SpanKey fields only when the span was
    byte-verified against the derivative (evidence.verify_anchor_bytes) and measured on the original. No identity,
    a generated segment, an image sequence or an unmapped reconstruction never yields a page: no page is invented."""
    if identity is None or identity["source_copy"]["sha256"] != a["original_sha256"] or identity["doc_id"] != a["doc_id"]:
        return None
    loc = a["locator"]
    pc = identity["source_copy"]["page_count"]
    if not (loc.get("citable_as_source_page") and identity["research_eligibility"]["source_page_citation_permitted"]
            and a["verification"]["state"] != "INCORRECT" and isinstance(pc, int) and loc["physical_page"] <= pc):
        return None
    out = {"source_copy_sha256": a["original_sha256"], "page": loc["physical_page"],
           "paragraph_label": loc.get("paragraph_label")}
    span = a.get("text_span")
    if span and span_verified and a["representation_sha256"] == a["original_sha256"] and a.get("derivative_text_sha256"):
        out.update(passage_id=span.get("passage_id"), char_start=span["char_start"], char_end=span["char_end"],
                   text_sha256=span["text_sha256"], pipeline_name=a["extraction"]["pipeline_name"],
                   pipeline_version=a["extraction"]["pipeline_version"], derivative_text_sha256=a["derivative_text_sha256"])
        # The producer's quote field is never copied. A quotation is shown only when the caller passes the text
        # that evidence.verified_quote derived from the verified bytes after every quotation gate (anchor,
        # identity, derivative, page) agreed; it must equal the span exactly.
        if quote is not None and identity["research_eligibility"]["quoting_permitted"] and a.get("quoting_permitted") \
                and hashlib.sha256(quote.encode("utf-8")).hexdigest() == span["text_sha256"]:
            out["quote"] = quote
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
        "review_binding": None, "approval_ref": None, "validates_relationship_id": None,
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
# PR #76 local-collection reconciliation (LOCAL_INVENTORY.jsonl rows, methodology v2 and v3; read-only)

PR76_DISPOSITION_TO_DECISION = {
    "EXACT_DUPLICATE": "REJECTED_EXACT_DUPLICATE",
    "VERIFIED_ALTERNATE_COPY": "HELD_IDENTITY_UNRESOLVED",   # normalised-text equality is a review signal (PR #76 v3)
    "PROBABLE_DUPLICATE": "HELD_IDENTITY_UNRESOLVED",
    "NEW_DOCUMENT": "HELD_INTEGRITY_UNVERIFIED",             # provisional: hash declared, duplicates not resolved
    "IMPROVED_SOURCE_COPY": "HELD_IDENTITY_UNRESOLVED",
    "HISTORICAL_RECOVERY_MATCH": "HELD_IDENTITY_UNRESOLVED",
    "IDENTITY_UNRESOLVED": "HELD_IDENTITY_UNRESOLVED",
    "RELEVANCE_UNRESOLVED": "HELD_RELEVANCE_UNRESOLVED",
    "NON_RELEVANT": "REJECTED_NON_RELEVANT",
    "ACCESS_RESTRICTED": None,                               # local exclusion receipt only, never exported
    "INTEGRITY_FAILURE": "QUARANTINED_INTEGRITY",
    "UNSUPPORTED_FORMAT": "UNSUPPORTED_FORMAT",
}
_PR76_FORMAT = {"PDF": ("PDF", "application/pdf"),
                "DOCX": ("DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                "DOC": ("DOC", "application/msword"), "RTF": ("RTF", "application/rtf"), "TXT": ("TXT", "text/plain")}
_IMAGE_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "JPG": "image/jpeg", "GIF": "image/gif", "BMP": "image/bmp",
               "TIFF": "image/tiff", "EMF": "image/x-emf", "WMF": "image/x-wmf"}

# Abbreviation readings, version 1.2 (owner decisions of 2026-11-27, recorded in contract section 14):
# - AR, in the owner's local classified collection, means Army Rules, 1954 (a CANDIDATE association, never a finding);
#   elsewhere AR stays contextual and is not read by this adapter.
# - AFT means the Armed Forces Tribunal (the forum). Only an explicit statutory reference ("AFT Act",
#   "Armed Forces Tribunal Act, 2007", "s. N of the AFT Act") points to the Armed Forces Tribunal Act, 2007.
# - AA, AFA, NA: repository readings (LegalIdentifierResolver.Aliases; build_sample.py SUPPLEMENT).
ABBREV_SOURCES = ("owner decision 2026-11-27 (PR #77 residual corrections)",
                  "app/b1/src/Mimamsa.Core/Identifiers/LegalIdentifierResolver.cs#Aliases",
                  "app/b1/build/build_sample.py#SUPPLEMENT")
ABBREVIATIONS = {
    "AA": {"code": "AA-1950", "prefix": "s", "expansion": "Army Act (repository alias 'army act')", "alternatives": []},
    "AR": {"code": "AR-1954", "prefix": "r", "expansion": "Army Rules, 1954 (owner decision for the local classified collection)", "alternatives": []},
    "AFA": {"code": "AFA-1950", "prefix": "s", "expansion": "Air Force Act (repository alias 'air force act')", "alternatives": []},
    "NA": {"code": "NA-1957", "prefix": "s", "expansion": "Navy Act (repository alias 'navy act')", "alternatives": []},
    "AFT ACT": {"code": "AFT-2007", "prefix": "s", "expansion": "Armed Forces Tribunal Act, 2007 (explicit statutory reference; owner decision)", "alternatives": []},
}
# Bare "AFT" is the forum (owner decision): it is deliberately absent, so "AFT 14 - X v Y" yields no provision.
_AFT_ACT = re.compile(r"^\s*(?:AFT\s+Act|Armed\s+Forces\s+Tribunal\s+Act)(?:,?\s*2007)?\s*,?\s*(?:s\.|sec\.?|section)?\s*"
                      r"(?P<label>\d[\dA-Za-z ,&\u2013\u2014-]*?)\s*(?:[-\u2013\u2014]\s+(?P<rest>.*))?$", re.I)
_AFT_ACT_OF = re.compile(r"^\s*(?:s\.|sec\.?|section)\s*(?P<label>\d[\dA-Za-z ,&]*?)\s+of\s+the\s+(?:AFT|Armed\s+Forces\s+Tribunal)\s+Act\b", re.I)
ABBREV_LEXICON_REF = "; ".join(ABBREV_SOURCES)
_PROV_LABEL = re.compile(r"^\s*(?P<abbr>[A-Z][A-Z.]{1,7})\s*(?:Rule|Rules|Sec|Section|s\.|r\.)?\s*"
                         r"(?P<label>\d[\dA-Za-z ,&–—-]*?)\s*(?:[-–—]\s+(?P<rest>.*))?$")
_RANGE = re.compile(r"\d\s*(?:-|–|—|\bto\b)\s*\d", re.I)
SLUG_MAX = 150


def slug(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80] or "unnamed"


def local_subject_id(folders: list[str]) -> str:
    """SUBJ:local:<slug of every folder from the root, joined by '__'>, so 'A/Rules' and 'B/Rules' differ."""
    joined = "__".join(slug(f) for f in folders)
    if len(joined) > SLUG_MAX:
        joined = joined[:SLUG_MAX - 13] + "~" + hashlib.sha256("/".join(folders).encode("utf-8")).hexdigest()[:12]
    return f"SUBJ:local:{joined}"


def local_doc_id(sha256: str) -> str:
    return f"local-{sha256[:16]}"


def parse_provision_label(label: str) -> dict:
    """'AR 22, 23, 30 - X v Y' -> {abbr, numbers, ambiguity}. Ranges are preserved, never expanded."""
    m = _AFT_ACT.match(label) or _AFT_ACT_OF.match(label)
    if m:
        abbr = "AFT ACT"
    else:
        m = _PROV_LABEL.match(label)
        if not m:
            return {"abbr": None, "numbers": [], "ambiguity": None, "raw": None}
        abbr = m["abbr"].replace(".", "").upper()
    raw = m["label"].strip(" ,")
    if _RANGE.search(raw):
        return {"abbr": abbr, "numbers": [], "ambiguity": "PROVISION_RANGE_NOT_EXPANDED", "raw": f"{abbr} {raw}"}
    tokens = [t.strip() for t in re.split(r",|&|\band\b", raw) if t.strip()]
    if tokens and all(re.fullmatch(r"\d{1,3}[A-Z]{0,2}", t) for t in tokens):
        return {"abbr": abbr, "numbers": tokens, "ambiguity": None, "raw": f"{abbr} {raw}"}
    return {"abbr": abbr, "numbers": [], "ambiguity": "UNPARSED_PROVISION_LABEL", "raw": f"{abbr} {raw}"}


def _classification(category, *, doc_id, sha, subject_node, target, basis, collection, rel_path, inventory_id,
                    component, matched, expansion, verification, uncertainty, rule):
    rel = {
        "contract": CONTRACT_ID, "record_kind": "corpus_relationship", "relationship_id": "", "category": category,
        "subject": {"doc_id": doc_id, "source_copy_sha256": sha, "graph_node_ref": subject_node},
        "target": target, "evidentiary_basis": basis,
        "source": {"producer": PRODUCER, "rule_id": rule, "rule_version": "1.1", "author_id": None},
        "classification_provenance": {"collection": collection, "relative_path": rel_path, "inventory_id": inventory_id,
                                      "path_component": component, "matched_text": matched,
                                      "abbreviation_expansion": expansion},
        "anchors": [], "verification": verification, "review_ref": None, "review_binding": None, "approval_ref": None,
        "validates_relationship_id": None, "proposition_ref": None,
        "temporal_scope": {"from": None, "from_status": "NOT_APPLICABLE", "to": None, "to_status": "NOT_APPLICABLE"},
        "has_legal_effect": False, "is_finding": False, "uncertainty": uncertainty,
    }
    rel["relationship_id"] = canonical.relationship_id(rel)
    return rel


def _provision_relationships(label, *, component, basis, rule, ctx) -> list[dict]:
    p = parse_provision_label(label)
    ab = ABBREVIATIONS.get(p["abbr"] or "")
    # Only abbreviations with a repository-recorded statutory reading produce a signal: an unknown prefix (OA, WP,
    # CA ... are case-number prefixes) is not a provision and is left to PR #76's own filename metadata.
    if ab is None or (not p["numbers"] and p["ambiguity"] is None):
        return []
    expansion = ({"abbreviation": p["abbr"], "expansion": ab["expansion"], "lexicon_ref": ABBREV_LEXICON_REF,
                  "alternatives": ab["alternatives"]} if ab else None)
    unc = (f"Read from the owner's {'folder' if component >= 0 else 'file'} name by rule {rule}; the abbreviation "
           "reading and the provision are candidates, not a finding that the document concerns this provision.")
    out = []
    if p["ambiguity"] or ab["code"] is None:
        reason = "AMBIGUOUS_REFERENCE"
        note = p["ambiguity"] or "abbreviation has more than one reading"
        out.append(_classification("associated_with_provision", target={"resolved": False, "node_id": None, "raw_reference": p["raw"],
                                                                          "unresolved": {"unresolved": reason, "note": note}},
                                   basis=basis, component=component, matched=p["raw"], expansion=expansion,
                                   verification="CANDIDATE", uncertainty=unc, rule=rule, **ctx))
        return out
    for n in p["numbers"]:
        out.append(_classification("associated_with_provision", target={"resolved": True, "node_id": f"PROV:{ab['code']}:{ab['prefix']}.{n}"},
                                   basis=basis, component=component, matched=f"{p['abbr']} {n}", expansion=expansion,
                                   verification="CANDIDATE", uncertainty=unc, rule=rule, **ctx))
    return out


def classify_path(rel_path: str, *, doc_id: str, sha: str, subject_node, collection: str,
                  inventory_id: str | None = None) -> list[dict]:
    """One path -> its classifications (rules C16-FOLDER-SUBJECT, C16-FOLDER-PROVLIST, C16-FN-PROVLIST, version 1.1):
    - the leaf folder -> classified_under_subject SUBJ:local:<full folder path slug> (ancestors via taxonomy parents);
    - a folder named like a provision list -> candidate associated_with_provision (decision Q4);
    - a file name 'AR 22, 23, 30 - ...' -> one candidate association per number; ranges and unknown abbreviations stay
      unresolved candidates with the label preserved. Each relationship keeps its own path."""
    parts = unicodedata.normalize("NFC", rel_path.replace("\\", "/")).split("/")
    folders, leaf = parts[:-1], parts[-1]
    full = "/".join(parts)
    ctx = dict(doc_id=doc_id, sha=sha, subject_node=subject_node, collection=collection, rel_path=full, inventory_id=inventory_id)
    out = []
    if folders:
        out.append(_classification("classified_under_subject", target={"resolved": True, "node_id": local_subject_id(folders)},
                                   basis="FOLDER_PATH", component=len(folders) - 1, matched=folders[-1], expansion=None,
                                   verification="CURATED_NAVIGATION",
                                   uncertainty="Owner folder label; a navigation aid, not a finding about the document.",
                                   rule="C16-FOLDER-SUBJECT", **ctx))
    for i, folder in enumerate(folders):
        out += _provision_relationships(folder, component=i, basis="FOLDER_PATH", rule="C16-FOLDER-PROVLIST", ctx=ctx)
    stem = leaf.rsplit(".", 1)[0] if "." in leaf else leaf
    out += _provision_relationships(stem, component=-1, basis="FILENAME_PATTERN", rule="C16-FN-PROVLIST", ctx=ctx)
    return out


def local_subject_nodes(rel_paths: list[str], collection: str) -> list[dict]:
    """Taxonomy SUBJECT nodes for every folder prefix of the given paths (parent = the folder above)."""
    nodes = {}
    for rp in rel_paths:
        folders = unicodedata.normalize("NFC", rp.replace("\\", "/")).split("/")[:-1]
        for i in range(len(folders)):
            nid = local_subject_id(folders[:i + 1])
            nodes[nid] = {"contract": CONTRACT_ID, "record_kind": "taxonomy_node", "node_id": nid, "level": "SUBJECT",
                          "label": folders[i][:300] or "unnamed", "parent_ids": [local_subject_id(folders[:i])] if i else [],
                          "instrument_code": None, "provision": None, "maps_to_subject": None, "aliases": [],
                          "taxonomy_version": "c16-taxonomy-1.1",
                          "source": {"basis": "OWNER_FOLDER", "collection": collection, "relative_path": "/".join(folders[:i + 1])},
                          "verification": "CURATED_NAVIGATION"}
    return [nodes[k] for k in sorted(nodes)]


def _gate(gid, result, ev=None):
    return {"gate_id": gid, "result": result, "evidence_ref": ev}


def _images_from_row(row, sha):
    out = []
    for img in sorted(row.get("embedded_images") or [], key=lambda i: i["sequence"]):
        fmt = str(img.get("format") or "").upper()
        state = {"DONE": "DONE", "NOT_REQUIRED_DECORATIVE": "NOT_REQUIRED_DECORATIVE", "FAILED": "FAILED"}.get(img.get("ocr_state"), "QUEUED")
        out.append({"image_sequence_id": f"IMG:{sha}:{img['sequence']}", "sequence": img["sequence"],
                    "image_sha256": img["image_sha256"],
                    "location": {"kind": "DOCX_PART", "container_part": img.get("archive_path"), "pdf_page": None,
                                 "body_order": img["sequence"], "occurrence_ref": img.get("occurrence_id"),
                                 "relationship_id": img.get("relationship_id")},
                    "mime_type": _IMAGE_MIME.get(fmt, "application/octet-stream"),
                    "pixel_width": img.get("width"), "pixel_height": img.get("height"), "size_bytes": img.get("size_bytes"),
                    "ocr_state": state,
                    "ocr_derivative_sha256": img.get("ocr_derivative_sha256") if state == "DONE" else None})
    return out


def from_pr76_inventory(rows: list[dict], *, collection: str, corpus_generation_id: str, ocr_config: dict | None = None) -> dict:
    """PR #76 LOCAL_INVENTORY rows -> {identities, admissions, relationships, taxonomy, receipts}.

    - One identity and one admission per binary (sha256). Every path of that binary is an observation, and every
      path keeps its own classifications (bytes merged, classifications not).
    - Restricted rows (ACCESS_RESTRICTED or a restricted marking) produce only a minimal local exclusion receipt:
      no identity, path, file name or classification is exported.
    - Unknown formats are UNRECOGNISED_FORMAT / application/octet-stream, never PDF.
    - No gate passes without evidence: the PR #76 hash is DECLARED_HASH_ONLY (G01 NOT_RUN), a provisional
      NEW_DOCUMENT has unresolved duplicates (G09 NOT_RUN). Nothing is application-eligible.
    The output is a PARTIAL exchange (rules.exchange_issues(..., mode="partial")) until the producer adds a
    generation manifest and runs the gates."""
    by_sha: dict[str, list[dict]] = {}
    receipts = []
    for row in rows:
        if row.get("disposition") == "ACCESS_RESTRICTED" or row.get("restricted"):
            receipts.append({"record_kind": "local_exclusion_receipt", "sha256_prefix": (row.get("sha256") or "")[:12],
                             "reason": "ACCESS_MARKING_DETECTED", "exportable": False})
            continue
        if row.get("sha256"):
            by_sha.setdefault(row["sha256"], []).append(row)
    out = {"identities": [], "admissions": [], "relationships": [], "taxonomy": [], "receipts": receipts}
    paths = []
    for sha in sorted(by_sha):
        group = sorted(by_sha[sha], key=lambda r: unicodedata.normalize("NFC", r["relative_path"].replace("\\", "/")))
        row = group[0]
        ident, adm = _pr76_identity(row, group, sha, collection, corpus_generation_id, ocr_config)
        out["identities"].append(ident)
        out["admissions"].append(adm)
        for r in group:
            paths.append(r["relative_path"])
            out["relationships"] += classify_path(r["relative_path"], doc_id=ident["doc_id"], sha=sha,
                                                  subject_node=ident["work_identity"]["graph_node_ref"],
                                                  collection=collection, inventory_id=r.get("inventory_id"))
    out["taxonomy"] = local_subject_nodes(paths, collection)
    return out


def from_pr76_inventory_row(row: dict, *, collection: str, corpus_generation_id: str, **_) -> tuple:
    """Single-row convenience wrapper (kept for compatibility): (identity or None, admission or None, relationships)."""
    res = from_pr76_inventory([row], collection=collection, corpus_generation_id=corpus_generation_id)
    return (res["identities"][0] if res["identities"] else None, res["admissions"][0] if res["admissions"] else None,
            res["relationships"])


def _pr76_identity(row, group, sha, collection, gen, ocr_config):
    doc_id = local_doc_id(sha)
    fmt = (row.get("detected_format") or "").upper()
    detected, mime = _PR76_FORMAT.get(fmt, ("UNKNOWN", "application/octet-stream"))
    is_pdf, is_word, unknown = detected == "PDF", detected in ("DOCX", "DOC", "RTF"), detected == "UNKNOWN"
    v3 = (row.get("extraction_methodology_version") or 0) >= 3
    ocr_pages = row.get("ocr_required_pages") or []
    pages = row.get("page_count")
    images = _images_from_row(row, sha) if (is_word and v3) else None
    if unknown:
        kind, pagination = "UNRECOGNISED_FORMAT", "UNKNOWN"
    elif is_pdf:
        kind = "SCANNED_PDF" if pages and len(ocr_pages) >= pages else ("MIXED_PDF" if ocr_pages else "NATIVE_DIGITAL_PDF")
        pagination = "PHYSICAL_PAGES"
    elif is_word:
        pagination = "NONE_FLOW_DOCUMENT"
        kind = "WORD_IMAGES_NOT_INVENTORIED" if images is None or detected != "DOCX" else (
            "WORD_WITH_EMBEDDED_IMAGES" if images else "WORD_NATIVE_TEXT")
        if detected != "DOCX":
            images = None
    else:
        kind, pagination = "PLAIN_TEXT", "NONE_FLOW_DOCUMENT"
    ctype = row.get("candidate_document_type") or "legal_reference"
    wk = {"judgment": "JUDGMENT", "order": "ORDER", "act": "INSTRUMENT", "rules": "INSTRUMENT",
          "manual": "MANUAL", "notification": "NOTIFICATION"}.get(ctype, "UNKNOWN")
    if unknown:
        wk = "UNKNOWN"
    subject_node = f"JUD:{doc_id}" if wk in ("JUDGMENT", "ORDER") else UNRESOLVED("NOT_DETERMINED")
    work = {"work_kind": wk, "graph_node_ref": subject_node, "identity_basis": "METADATA_CANDIDATE",
            "identity_verification": "CANDIDATE",
            "proceeding_numbers_as_printed": list((row.get("metadata_candidate") or {}).get("case_numbers") or [])}
    if wk in ("JUDGMENT", "ORDER"):
        work["judgment_id"] = UNRESOLVED("NOT_DETERMINED")
    if wk in ("INSTRUMENT", "NOTIFICATION"):
        work["instrument_code"] = UNRESOLVED("NOT_DETERMINED")
    ders = []
    if row.get("derivative_sha256") and not row.get("derivative_withheld_reason") and not unknown:
        method = {"pymupdf-native": "NATIVE_TEXT_LAYER", "docx-xml": "DOCX_XML", "docx-xml+embedded-image-inventory": "DOCX_XML",
                  "utf8-replace": "PLAIN_TEXT"}.get(row.get("extraction_method"), "NONE")
        units = pages if is_pdf and pages else 1
        done = sum(1 for i in images or [] if i["ocr_state"] == "DONE")
        methods = [method] + (["OCR_EMBEDDED_IMAGE"] if done else [])
        ders.append({"derivative_id": f"{doc_id}@c16-local-reconcile/{row.get('extraction_methodology_version') or row.get('classification_version', 0)}",
                     "pipeline_name": "c16-local-reconcile",
                     "pipeline_version": str(row.get("extraction_methodology_version") or row.get("classification_version", 0)),
                     "derivative_text_sha256": row["derivative_sha256"],
                     "pagination_basis": "SOURCE_PHYSICAL" if is_pdf else "GENERATED_SEGMENT",
                     "methods": methods, "ocr_config": ocr_config if done else None, "text_reliability": "not_assessed",
                     "quoting_permitted": False,
                     "coverage": {"units_total": units,
                                  "units_with_text": max(0, units - len(ocr_pages)) if is_pdf else (1 if row.get("text_available") else 0),
                                  "images_total": len(images) if images is not None else (UNRESOLVED("NOT_YET_PROCESSED") if is_word else 0),
                                  "images_text_extracted": done}})
    observations = [{"collection": collection, "relative_path": unicodedata.normalize("NFC", r["relative_path"].replace("\\", "/")),
                     "inventory_id": r.get("inventory_id"), "observed_at": None} for r in group]
    basis = ["ELIGIBILITY_NOT_ASSESSED"]
    if images is None and is_word or any(i["ocr_state"] not in ("DONE", "NOT_REQUIRED_DECORATIVE") for i in images or []):
        basis.append("EMBEDDED_IMAGES_NOT_EXTRACTED")
    ident = {
        "contract": CONTRACT_ID, "record_kind": "document_identity", "doc_id": doc_id,
        "source_copy": {"sha256": sha, "bytes": row["size_bytes"], "mime_type": mime, "detected_format": detected,
                        "page_count": (pages if pages is not None else UNRESOLVED("NOT_YET_PROCESSED")) if is_pdf
                        else (UNRESOLVED("NOT_DETERMINED") if unknown else None),
                        "physical_pagination": pagination, "vault_path": f"vault/sha256/{sha[:2]}/{sha}"},
        "representation": {"representation_kind": kind, "origin_status": "ACQUIRED_COPY_ORIGIN_UNDETERMINED",
                           "content_scope": "UNDETERMINED", "completeness": "NOT_CHECKED"},
        "work_identity": work,
        "embedded_images": images if images is not None else (UNRESOLVED("NOT_YET_PROCESSED") if (is_word or unknown) else []),
        "text_derivatives": ders,
        "provenance": {"acquisition": {"acquisition_channel": "MANUAL_OWNER", "source_url": None, "retrieved_at": None,
                                       "original_filename": None, "hf": None},
                       "carrier_provenance": "USER_SUPPLIED", "observations": observations, "processing_history": []},
        "restriction": {"access_marking": None, "eligibility": "NOT_ASSESSED", "restriction_id": None},
        "integrity": {"source_integrity": "DECLARED_HASH_ONLY", "basis": "SHA-256 computed by the PR #76 reconciliation; not re-verified against an independent manifest"},
        "research_eligibility": {"state": "NOT_ASSESSED", "quoting_permitted": False, "source_page_citation_permitted": False,
                                 "whole_work_claims_permitted": False, "graph_evidence_permitted": False, "basis": basis},
        "corpus_generation_id": gen,
    }
    disp = row.get("disposition") or "IDENTITY_UNRESOLVED"
    decision = PR76_DISPOSITION_TO_DECISION.get(disp) or "HELD_IDENTITY_UNRESOLVED"
    if unknown:
        decision = "UNSUPPORTED_FORMAT"
    elif decision == "HELD_INTEGRITY_UNVERIFIED":
        if row.get("derivative_withheld_reason"):
            decision = "HELD_ACCESS_MARKING_REVIEW"
        elif row.get("ocr_required_pages") or row.get("ocr_required_images") or (images and any(i["ocr_state"] == "QUEUED" for i in images)):
            decision = "HELD_OCR_REQUIRED"
        elif kind == "WORD_IMAGES_NOT_INVENTORIED":
            decision = "HELD_EXTRACTION_INCOMPLETE"
    dup = None
    if decision == "REJECTED_EXACT_DUPLICATE":
        dup = {"sha256": sha, "doc_id": None, "relation": "BYTE_IDENTICAL", "held_at": "canonical-corpus (PR #76 canonical index)"}
    rel = row.get("relevance")
    gates = [
        _gate("G01_HASH_VERIFIED", "NOT_RUN"),                      # declared hash only
        _gate("G02_FORMAT_DETECTED", "PASS" if not unknown else "FAIL", "c16_reconcile magic-byte detection" if not unknown else None),
        _gate("G03_RESTRICTED_REGISTER", "NOT_RUN"),
        _gate("G04_ACCESS_MARKING_REVIEWED", "NOT_RUN"),
        _gate("G05_IDENTITY_RECORD_VALID", "NOT_RUN"),
        _gate("G06_TEXT_DERIVATIVE_VERIFIED", "FAIL" if row.get("parsing_error") else "NOT_RUN"),
        _gate("G07_EMBEDDED_IMAGES_ACCOUNTED", "NOT_APPLICABLE" if ident["embedded_images"] == [] else "NOT_RUN"),
        _gate("G08_RELEVANCE_ASSESSED", "FAIL" if rel is False else "NOT_RUN"),  # an automated signal is not an assessment
        _gate("G09_DUPLICATE_RESOLVED", "PASS" if disp == "EXACT_DUPLICATE" else "NOT_RUN",
              "PR #76 canonical exact-hash match" if disp == "EXACT_DUPLICATE" else None),
        _gate("G10_SCHEMA_VALID", "NOT_RUN"),
    ]
    adm = {"contract": CONTRACT_ID, "record_kind": "corpus_admission", "admission_id": "", "revision": 1,
           "supersedes_admission_id": None, "subject": {"doc_id": doc_id, "source_copy_sha256": sha},
           "corpus_generation_id": gen, "decision": decision,
           "source_disposition": {"system": "c16-local-reconcile", "value": disp,
                                  "secondary_flags": sorted({f for r in group for f in (r.get("secondary_flags") or [])})},
           "duplicate_of": dup, "restriction_id": None, "gates": gates, "application_eligible": False, "service_scope": "NONE",
           "publication_effect": "NONE", "legal_effect": "NONE",
           "decided_by": {"kind": "AUTOMATED_RULE", "id": "c16-admission-adapter"}, "decided_at": None,
           "rule_set": {"id": "c16-admission", "version": "1.1"},
           "reasons": [f"derived from PR #76 disposition {disp}"]}
    adm["admission_id"] = canonical.admission_id(adm)
    return ident, adm


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
