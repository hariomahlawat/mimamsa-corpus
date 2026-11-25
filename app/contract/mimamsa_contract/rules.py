"""Semantic rules that JSON Schema cannot express. Each rule has a stable code (see README, 'Rule codes')."""
from __future__ import annotations

from .issues import Issue
from .restricted import RestrictedRegister
from .schemas import validator

NO_LEGAL_EFFECT_RELATIONS = frozenset({
    "CITES_PROVISION", "QUOTES_PROVISION", "CITES_JUDGMENT", "UPLOAD_REFERENCES_PROVISION", "UPLOAD_REFERENCES_CASE",
})


def schema_issues(kind: str, record: dict, where: str) -> list[Issue]:
    out = []
    for err in sorted(validator(kind).iter_errors(record), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path)
        out.append(Issue("SCHEMA", f"{loc or '<root>'}: {err.message[:300]}", where))
    return out


def _restricted(reg: RestrictedRegister, where: str, **kw) -> list[Issue]:
    reason = reg.match(**kw)
    if reason:
        # The message deliberately does not echo the matched value.
        return [Issue("RESTRICTED_MATERIAL", f"item must be excluded from every derivative and bundle ({reason})", where)]
    return []


def _approval_issues(axes: dict, where: str, ledger_version: int | None) -> list[Issue]:
    out = []
    la = axes.get("legal_approval", {})
    val = la.get("value")
    if val and val != "T0_RESEARCH_ONLY" and not la.get("approval_ref"):
        out.append(Issue("APPROVAL_REF_REQUIRED", f"legal_approval {val} requires approval_ref", where))
    if ledger_version == 0 and val and val != "T0_RESEARCH_ONLY":
        out.append(Issue("LEDGER_V0_NO_APPROVAL", "AUTH-LEDGER is at version 0: legal_approval must be T0_RESEARCH_ONLY", where))
    return out


def document_rules(rec: dict, reg: RestrictedRegister, where: str, ledger_version: int | None = None) -> list[Issue]:
    out: list[Issue] = []
    sc = rec.get("source_copy", {})
    sha = sc.get("sha256", "")
    out += _restricted(reg, where, sha256=sha, doc_id=rec.get("doc_id"))
    for alt in rec.get("alternate_copy_sha256", []):
        out += _restricted(reg, where, sha256=alt)
    hf = (rec.get("provenance") or {}).get("hf") or {}
    if hf.get("path"):
        out += _restricted(reg, where, path=hf["path"])
    restriction = rec.get("restriction", {})
    if restriction.get("eligibility") == "RESTRICTED":
        out.append(Issue("RESTRICTED_MATERIAL", "record self-declares eligibility RESTRICTED; it must not be exchanged", where))
    if sha and sc.get("vault_path") and sc["vault_path"] != f"vault/sha256/{sha[:2]}/{sha}":
        out.append(Issue("VAULT_PATH_MISMATCH", "vault_path must be vault/sha256/<sha[:2]>/<sha>", where))
    if sha and sha in rec.get("alternate_copy_sha256", []):
        out.append(Issue("ALTERNATE_IS_SELF", "alternate_copy_sha256 must not contain the record's own copy", where))
    axes = rec.get("status_axes", {})
    pub = axes.get("publication", {}).get("value")
    if pub == "PUBLISHED" and restriction.get("eligibility") != "ELIGIBLE_ALL_USERS":
        out.append(Issue("PUBLISH_WITHOUT_ELIGIBILITY", "PUBLISHED requires eligibility ELIGIBLE_ALL_USERS", where))
    if restriction.get("access_marking") and restriction.get("eligibility") == "ELIGIBLE_ALL_USERS" and not restriction.get("basis"):
        out.append(Issue("MARKING_WITHOUT_DECISION", "a printed access marking with ELIGIBLE_ALL_USERS needs a recorded basis", where))
    if pub == "EXCLUDED_RESTRICTED":
        out.append(Issue("RESTRICTED_MATERIAL", "EXCLUDED_RESTRICTED items are never exchanged", where))
    out += _approval_issues(axes, where, ledger_version)
    if rec.get("text_method") == "ocr" and rec.get("ocr_confidence") is None:
        out.append(Issue("OCR_CONFIDENCE_MISSING", "text_method ocr should carry ocr_confidence", where, "warning"))
    for fld, origin in (rec.get("field_origin") or {}).items():
        if fld not in rec and fld not in (rec.get("judicial") or {}):
            out.append(Issue("FIELD_ORIGIN_UNKNOWN_FIELD", f"field_origin names absent field {fld}", where, "warning"))
    return out


def derived_text_rules(rec: dict, reg: RestrictedRegister, where: str) -> list[Issue]:
    out: list[Issue] = []
    out += _restricted(reg, where, sha256=rec.get("source_copy_sha256"), doc_id=rec.get("doc_id"))
    if rec.get("text_path"):
        out += _restricted(reg, where, path=rec["text_path"])
    if rec.get("text_sha256"):
        out += _restricted(reg, where, sha256=rec["text_sha256"])
    pages = rec.get("pages", [])
    if any(p.get("method") == "ocr" for p in pages) and rec.get("quoting_permitted"):
        out.append(Issue("OCR_QUOTING", "OCR-derived text is for search only: quoting_permitted must be false", where))
    page_nums = [p.get("page") for p in pages]
    if len(page_nums) != len(set(page_nums)):
        out.append(Issue("DUPLICATE_PAGE", "page numbers must be unique", where))
    known = set(page_nums)
    seen = set()
    for psg in rec.get("passages", []):
        pid = psg.get("passage_id")
        if pid in seen:
            out.append(Issue("DUPLICATE_PASSAGE", f"duplicate passage_id {pid}", where))
        seen.add(pid)
        if psg.get("page") not in known:
            out.append(Issue("PASSAGE_PAGE_UNKNOWN", f"{pid} points to a page not listed in pages", where))
        if psg.get("char_end", 0) < psg.get("char_start", 0):
            out.append(Issue("ANCHOR_RANGE", f"{pid}: char_end < char_start", where))
    return out


def candidate_rules(rec: dict, reg: RestrictedRegister, where: str) -> list[Issue]:
    out: list[Issue] = []
    out += _restricted(reg, where, doc_id=rec.get("source_doc_id"))
    for a in rec.get("anchors", []):
        out += _restricted(reg, where, sha256=a.get("source_copy_sha256"))
        cs, ce = a.get("char_start"), a.get("char_end")
        if cs is not None and ce is not None and ce < cs:
            out.append(Issue("ANCHOR_RANGE", "char_end < char_start", where))
    status = rec.get("status")
    if status in ("DOCUMENTARY_CHECKED", "REJECTED_ON_REVIEW") and not rec.get("review_ref"):
        out.append(Issue("REVIEW_REF_REQUIRED", f"status {status} requires review_ref", where))
    ctype = rec.get("candidate_type")
    restriction = rec.get("capability_restriction")
    if ctype in ("outcome", "holding", "form") and restriction == "NONE_RECORDED":
        out.append(Issue("RESTRICTION_REQUIRED", f"{ctype} candidates must carry their capability restriction", where))
    if ctype == "holding" and restriction != "HIDDEN_FROM_USERS":
        out.append(Issue("HOLDINGS_HIDDEN", "holdings are hidden from Users in contract v1 (D-08 bar not met)", where))
    payload = rec.get("payload") or {}
    if ctype == "graph_edge":
        rel = payload.get("relation")
        expected = rel not in NO_LEGAL_EFFECT_RELATIONS
        if rel and payload.get("has_legal_effect") is not expected:
            out.append(Issue("EDGE_LEGAL_EFFECT_FLAG", f"{rel}: has_legal_effect must be {expected}", where))
        if expected and payload.get("confidence") == "human_verified" and not rec.get("review_ref"):
            out.append(Issue("LEGAL_EFFECT_EDGE_UNREVIEWED", "a legal-effect edge marked human_verified needs a review_ref", where))
        tgt = payload.get("target") or {}
        if tgt.get("resolved") and not tgt.get("node_id"):
            out.append(Issue("EDGE_TARGET", "resolved target needs node_id", where))
        if tgt.get("resolved") is False and not tgt.get("raw_reference"):
            out.append(Issue("EDGE_TARGET", "unresolved target keeps its raw_reference", where))
    ev = rec.get("evaluation_ref")
    if ev is not None and ev.get("human_checked") is None:
        out.append(Issue("EVALUATION_HUMAN_FLAG", "evaluation_ref should state human_checked", where, "warning"))
    return out


def record_issues(kind: str, rec: dict, reg: RestrictedRegister, where: str, ledger_version: int | None = None) -> list[Issue]:
    issues = schema_issues(kind, rec, where)
    if kind == "document":
        issues += document_rules(rec, reg, where, ledger_version)
    elif kind == "derived_text":
        issues += derived_text_rules(rec, reg, where)
    elif kind == "candidate":
        issues += candidate_rules(rec, reg, where)
    return issues
