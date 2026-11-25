"""Semantic rules that JSON Schema cannot express. Each rule has a stable code (README, 'Rule codes')."""
from __future__ import annotations

from dataclasses import dataclass, field

from .evidence import evidence_keys
from .issues import Issue
from .paths import path_hazard
from .restricted import RestrictedRegister
from .schemas import validator

NO_LEGAL_EFFECT_RELATIONS = frozenset({
    "CITES_PROVISION", "QUOTES_PROVISION", "CITES_JUDGMENT", "UPLOAD_REFERENCES_PROVISION", "UPLOAD_REFERENCES_CASE",
})

# Values above each axis's default that must cite an independent review record.
RAISED_NEEDS_REVIEW = {
    "source_authenticity": {"IDENTITY_CONFIRMED", "DISPUTED"},
    "evidence_fidelity": {"DOCUMENTARY_CHECKED", "FIDELITY_VERIFIED", "INCORRECT"},
    "dependency_freshness": {"CURRENT_FOR_CHECKED_SCOPE"},
}
APPROVED_TIERS = {"T1_LEGAL_ADVISER_REVIEWED", "T2_FORMAL_JAG_VALIDATED"}
OFFICIAL_AUTHORITIES = {"ENACTED_OR_NOTIFIED_PRIMARY", "OFFICIAL_JUDICIAL_DECISION", "GOVERNMENT_COMPILATION", "GOVERNMENT_ISSUED_MANUAL"}
OFFICIAL_CARRIERS = {"ISSUING_AUTHORITY", "GOVERNMENT_HOSTED_COPY"}
SITE_ONLY_CHANNELS = {"RELEASE_ACTIVATION", "SITE_ADMIN"}
# Reserved for future site-only state (agentic workflows, private drafts, final claims, serving policy). These are
# never exchanged in release bundles; reserving them now keeps later intelligence features from colliding with the
# interchange contract (PR #53 reconciliation).
RESERVED_RECORD_KINDS = {"working_document", "agent_workflow", "agent_task", "agent_private_draft", "final_claim",
                         "claim_verification", "output_authorization", "serving_epoch", "policy_witness", "rule_pack"}
RESERVED_PATH_PREFIXES = ("agent/", "private/", "workflows/", "claims/", "policy/")


@dataclass
class BundleContext:
    """Cross-record context available when validating a whole bundle."""
    ledger_version: int | None = None
    reviews: dict = field(default_factory=dict)        # review_record_id -> record
    approvals: dict = field(default_factory=dict)      # approval_record_id -> record
    appointments: dict = field(default_factory=dict)   # appointment_id -> record
    doc_ids: set = field(default_factory=set)
    copy_shas: set = field(default_factory=set)
    candidate_ids: set = field(default_factory=set)
    derivatives: set = field(default_factory=set)       # (copy sha, pipeline name, pipeline version, text sha)
    subject_commits: dict = field(default_factory=dict)  # subject id -> set of commits that produced it
    subject_authors: dict = field(default_factory=dict)  # subject id -> author_id (when recorded)
    release_commits: set = field(default_factory=set)   # manifest tools_commit and artefact commits


def schema_issues(kind: str, record: dict, where: str) -> list[Issue]:
    out = []
    for err in sorted(validator(kind).iter_errors(record), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path)
        out.append(Issue("SCHEMA", f"{loc or '<root>'}: {err.message[:300]}", where))
    return out


def restricted_scan(reg: RestrictedRegister, rec, where: str) -> list[Issue]:
    """Every string anywhere in the record (ids, parents, edge targets, raw citations, paths, evidence)."""
    hit = reg.deep_match(rec)
    if hit:
        # Message names the field, never the matched value.
        return [Issue("RESTRICTED_MATERIAL", f"field {hit[0]} refers to restricted material ({hit[1]}); item must be excluded", where)]
    return []


def _path_issues(where: str, *paths) -> list[Issue]:
    out = []
    for p in paths:
        if p:
            reason = path_hazard(p)
            if reason:
                out.append(Issue("PATH_HAZARD", f"unsafe path ({reason})", where))
    return out


def _review_issues(axis: str, val: dict, subject_ids: set, where: str, ctx: BundleContext | None) -> list[Issue]:
    v = val.get("value")
    if v not in RAISED_NEEDS_REVIEW.get(axis, ()):
        return []
    rid = val.get("review_record_id")
    if not rid:
        return [Issue("RAISED_VALUE_NEEDS_REVIEW", f"{axis}={v} requires review_record_id of an independent review", where)]
    if ctx is None:
        return [Issue("REVIEW_UNRESOLVED_OUTSIDE_BUNDLE", f"{axis}: {rid} cannot be resolved outside a bundle; raised values are only accepted with their review records", where)]
    rv = ctx.reviews.get(rid)
    if rv is None:
        return [Issue("REVIEW_UNRESOLVED", f"{axis}: review record not in bundle", where)]
    if rv.get("axis") != axis or rv.get("to_value") != v or (rv.get("subject") or {}).get("id") not in subject_ids:
        return [Issue("REVIEW_MISMATCH", f"{axis}: review record does not cover this subject, axis and value", where)]
    if axis == "source_authenticity" and v == "IDENTITY_CONFIRMED" and (rv.get("reviewer") or {}).get("kind") != "HUMAN":
        return [Issue("AI_REVIEW_CANNOT_CONFIRM_IDENTITY", "source identity can only be confirmed with a human review and verifiable evidence", where)]
    return []


def _authenticity_evidence_issues(axes: dict, where: str, ledger_version: int | None) -> list[Issue]:
    sa = axes.get("source_authenticity") or {}
    if sa.get("value") != "IDENTITY_CONFIRMED":
        return []
    ev = sa.get("authentication_evidence")
    pol = sa.get("policy_v1") or {}
    if not ev:
        return [Issue("AUTHENTICITY_EVIDENCE_REQUIRED", "IDENTITY_CONFIRMED needs authentication_evidence (custodian certificate, official-source record or AUTH-LEDGER entry)", where)]
    kind = ev.get("kind")
    if kind == "AUTH_LEDGER_ENTRY" and (ledger_version is None or ledger_version == 0):
        return [Issue("AUTHENTICITY_EVIDENCE_INVALID", "no AUTH-LEDGER entry can exist while the ledger is at version 0", where)]
    if kind == "CUSTODIAN_CERTIFICATE" and (pol.get("copy_fidelity") != "CUSTODIAN_AUTHENTICATED" or not ev.get("artefact_sha256")):
        return [Issue("AUTHENTICITY_EVIDENCE_INVALID", "custodian certificate needs copy_fidelity CUSTODIAN_AUTHENTICATED and the certificate artefact hash", where)]
    if kind == "OFFICIAL_SOURCE_RECORD" and (
            pol.get("carrier_provenance") not in OFFICIAL_CARRIERS or pol.get("document_authority") not in OFFICIAL_AUTHORITIES
            or pol.get("copy_fidelity") not in ("PAGE_IMAGE_CHECKED", "CUSTODIAN_AUTHENTICATED") or not ev.get("official_source_url")):
        return [Issue("AUTHENTICITY_EVIDENCE_INVALID", "official-source evidence needs an official carrier and authority, page-image checked fidelity and the source URL", where)]
    return []


def _legal_applicability_issues(axes: dict, subject_ids: set, where: str, ctx, ledger_version) -> list[Issue]:
    la = axes.get("legal_applicability") or {}
    v = la.get("value")
    if not v or v == "NOT_ESTABLISHED":
        return []
    out = []
    if ledger_version is None or ledger_version == 0:
        out.append(Issue("LEDGER_V0_NO_APPLICABILITY", f"legal_applicability {v} is a legal determination; not allowed while AUTH-LEDGER is at version 0", where))
    if not la.get("approval_record_id"):
        out.append(Issue("LEGAL_AXIS_NEEDS_APPROVAL", "legal_applicability above NOT_ESTABLISHED needs an approval record under a Legal Reviewer appointment", where))
        return out
    if ctx is None:
        out.append(Issue("APPROVAL_UNRESOLVED", "applicability approval cannot be resolved outside a bundle", where))
        return out
    ap = ctx.approvals.get(la["approval_record_id"])
    if ap is None or ap.get("tier") not in APPROVED_TIERS or ap.get("status") != "ACTIVE" or (ap.get("subject") or {}).get("id") not in subject_ids:
        out.append(Issue("APPROVAL_UNRESOLVED", "applicability approval record missing, not active, wrong tier or wrong subject", where))
    elif ap.get("appointment_id") not in ctx.appointments or ctx.appointments[ap["appointment_id"]].get("revoked"):
        out.append(Issue("APPOINTMENT_MISSING", "applicability approval lacks a valid appointment", where))
    return out


def _approval_issues(axes: dict, subject_ids: set, where: str, ctx: BundleContext | None, ledger_version: int | None) -> list[Issue]:
    out = []
    la = axes.get("legal_approval") or {}
    val = la.get("value")
    if not val or val == "T0_RESEARCH_ONLY":
        return out
    if ledger_version == 0:
        out.append(Issue("LEDGER_V0_NO_APPROVAL", "AUTH-LEDGER is at version 0: legal_approval must be T0_RESEARCH_ONLY", where))
    if ctx is None:
        out.append(Issue("APPROVAL_UNRESOLVED", "approval needs an approval record, appointment and artefact present in the same bundle", where))
        return out
    ap = ctx.approvals.get(la.get("approval_record_id"))
    if ap is None:
        out.append(Issue("APPROVAL_UNRESOLVED", "approval record not in bundle", where))
        return out
    appt = ctx.appointments.get(ap.get("appointment_id"))
    if appt is None:
        out.append(Issue("APPOINTMENT_MISSING", "approval cites an appointment that is not recorded", where))
    else:
        if appt.get("revoked"):
            out.append(Issue("APPOINTMENT_REVOKED", "appointment revoked", where))
        if appt.get("capacity") != ap.get("capacity"):
            out.append(Issue("APPROVAL_CAPACITY_MISMATCH", "approval capacity differs from appointment capacity", where))
        decided = (ap.get("decided_at") or "")[:10]
        if decided and (decided < appt.get("valid_from", "") or (appt.get("valid_until") and decided > appt["valid_until"])):
            out.append(Issue("APPOINTMENT_NOT_VALID_AT_DECISION", "approval decided outside the appointment's validity", where))
    if (ap.get("subject") or {}).get("id") not in subject_ids:
        out.append(Issue("APPROVAL_SUBJECT_MISMATCH", "approval record is for a different subject", where))
    if val in APPROVED_TIERS and (ap.get("tier") != val or ap.get("status") != "ACTIVE"):
        out.append(Issue("APPROVAL_TIER_MISMATCH", "approval record tier/status does not support this value", where))
    if val == "APPROVAL_RECORDED_UNCONFIRMED" and ap.get("tier") != "APPROVAL_RECORDED_UNCONFIRMED":
        out.append(Issue("APPROVAL_TIER_MISMATCH", "unconfirmed approval must cite an unconfirmed record", where))
    return out


def _contradictions(axes: dict, where: str) -> list[Issue]:
    out = []
    g = lambda a: (axes.get(a) or {}).get("value")  # noqa: E731
    sa = axes.get("source_authenticity") or {}
    pol = sa.get("policy_v1") or {}
    if g("source_authenticity") == "IDENTITY_CONFIRMED" and (
            pol.get("copy_fidelity") in ("NOT_CHECKED", "HASH_ONLY") or pol.get("document_authority") == "UNKNOWN"):
        out.append(Issue("AXIS_CONTRADICTION", "IDENTITY_CONFIRMED needs copy_fidelity above HASH_ONLY and a known document_authority", where))
    if g("publication") == "PUBLISHED" and g("source_integrity") in ("MISMATCH", "NOT_CHECKED"):
        out.append(Issue("AXIS_CONTRADICTION", f"PUBLISHED with source_integrity {g('source_integrity')}", where))
    if g("publication") == "PUBLISHED" and g("source_integrity") == "TRUNCATED_AT_SOURCE":
        out.append(Issue("PUBLISHED_TRUNCATED", "published copy is truncated at source; UI must warn", where, "warning"))
    if g("source_integrity") == "BYTE_VERIFIED" and not (axes.get("source_integrity") or {}).get("evidence_ref"):
        out.append(Issue("RAISED_VALUE_NEEDS_REVIEW", "BYTE_VERIFIED requires evidence_ref (verification record)", where))
    if g("legal_approval") in APPROVED_TIERS:
        if g("evidence_fidelity") in ("AUTOMATED_CANDIDATE_NOT_VERIFIED", "INCORRECT"):
            out.append(Issue("AXIS_CONTRADICTION", "legal approval on unverified or incorrect evidence", where))
        if g("legal_applicability") in ("NOT_ESTABLISHED", "UNRESOLVED", "CONFLICTING"):
            out.append(Issue("AXIS_CONTRADICTION", "legal approval while applicability is not established", where))
        if g("source_authenticity") != "IDENTITY_CONFIRMED":
            out.append(Issue("AXIS_CONTRADICTION", "legal approval without confirmed source identity", where))
    if g("dependency_freshness") == "CURRENT_FOR_CHECKED_SCOPE" and g("legal_applicability") in ("NOT_ESTABLISHED", "CONFLICTING"):
        out.append(Issue("AXIS_CONTRADICTION", "freshness current while applicability not established", where))
    return out


def _axes_issues(axes: dict, subject_ids: set, where: str, ctx, ledger_version) -> list[Issue]:
    out = []
    for axis in RAISED_NEEDS_REVIEW:
        if axis in axes:
            out += _review_issues(axis, axes[axis], subject_ids, where, ctx)
    out += _contradictions(axes, where)
    out += _authenticity_evidence_issues(axes, where, ledger_version)
    out += _legal_applicability_issues(axes, subject_ids, where, ctx, ledger_version)
    out += _approval_issues(axes, subject_ids, where, ctx, ledger_version)
    return out


def document_rules(rec: dict, reg: RestrictedRegister, where: str, ledger_version: int | None = None,
                   ctx: BundleContext | None = None) -> list[Issue]:
    out: list[Issue] = restricted_scan(reg, rec, where)
    sc = rec.get("source_copy", {})
    sha = sc.get("sha256", "")
    restriction = rec.get("restriction", {})
    if restriction.get("eligibility") == "RESTRICTED":
        out.append(Issue("RESTRICTED_MATERIAL", "record self-declares eligibility RESTRICTED; it must not be exchanged", where))
    if sha and sc.get("vault_path") and sc["vault_path"] != f"vault/sha256/{sha[:2]}/{sha}":
        out.append(Issue("VAULT_PATH_MISMATCH", "vault_path must be vault/sha256/<sha[:2]>/<sha>", where))
    if sha and sha in rec.get("alternate_copy_sha256", []):
        out.append(Issue("ALTERNATE_IS_SELF", "alternate_copy_sha256 must not contain the record's own copy", where))
    prov = rec.get("provenance") or {}
    out += _path_issues(where, (prov.get("hf") or {}).get("path"), (prov.get("git") or {}).get("path"))
    axes = rec.get("status_axes", {})
    pub = (axes.get("publication") or {}).get("value")
    if pub == "PUBLISHED" and restriction.get("eligibility") != "ELIGIBLE_ALL_USERS":
        out.append(Issue("PUBLISH_WITHOUT_ELIGIBILITY", "PUBLISHED requires eligibility ELIGIBLE_ALL_USERS", where))
    if restriction.get("access_marking") and restriction.get("eligibility") == "ELIGIBLE_ALL_USERS" and not restriction.get("basis"):
        out.append(Issue("MARKING_WITHOUT_DECISION", "a printed access marking with ELIGIBLE_ALL_USERS needs a recorded basis", where))
    if pub == "EXCLUDED_RESTRICTED":
        out.append(Issue("RESTRICTED_MATERIAL", "EXCLUDED_RESTRICTED items are never exchanged", where))
    out += _axes_issues(axes, {rec.get("doc_id"), sha}, where, ctx, ledger_version)
    if rec.get("text_method") == "ocr" and rec.get("ocr_confidence") is None:
        out.append(Issue("OCR_CONFIDENCE_MISSING", "text_method ocr should carry ocr_confidence", where, "warning"))
    for fld in (rec.get("field_origin") or {}):
        if fld not in rec and fld not in (rec.get("judicial") or {}):
            out.append(Issue("FIELD_ORIGIN_UNKNOWN_FIELD", f"field_origin names absent field {fld}", where, "warning"))
    return out


def derived_text_rules(rec: dict, reg: RestrictedRegister, where: str, ctx: BundleContext | None = None) -> list[Issue]:
    out: list[Issue] = restricted_scan(reg, rec, where)
    out += _path_issues(where, rec.get("text_path"))
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
    if rec.get("evidence_fidelity") == "DOCUMENTARY_CHECKED" and ctx is None:
        out.append(Issue("REVIEW_UNRESOLVED_OUTSIDE_BUNDLE", "documentary check can only be resolved inside a bundle", where, "warning"))
    return out


def candidate_rules(rec: dict, reg: RestrictedRegister, where: str, ctx: BundleContext | None = None) -> list[Issue]:
    out: list[Issue] = restricted_scan(reg, rec, where)
    for a in rec.get("anchors", []):
        cs, ce = a.get("char_start"), a.get("char_end")
        if cs is not None and ce is not None and ce < cs:
            out.append(Issue("ANCHOR_RANGE", "char_end < char_start", where))
        if a.get("source_copy_sha256") and isinstance(a.get("page"), int):
            _, span, reason = evidence_keys(a)
            if reason:
                out.append(Issue("SPAN_UNBOUND", reason, where, "warning"))
            elif span is not None and ctx is not None and (span.page.source_copy_sha256, span.pipeline_name,
                                                            span.pipeline_version, span.derivative_text_sha256) not in ctx.derivatives:
                out.append(Issue("DANGLING_SPAN_BINDING", "span names a derivative that is not in this bundle", where))
    ev = rec.get("evaluation_ref")
    out += _path_issues(where, (rec.get("extractor") or {}).get("artefact_path"), (ev or {}).get("report_path"))
    status = rec.get("status")
    rref = rec.get("review_ref")
    if status in ("DOCUMENTARY_CHECKED", "REJECTED_ON_REVIEW") and not rref:
        out.append(Issue("REVIEW_REF_REQUIRED", f"status {status} requires review_ref", where))
    if rref and ctx is not None:
        rv = ctx.reviews.get(rref)
        if rv is None or (rv.get("subject") or {}).get("id") != rec.get("candidate_id"):
            out.append(Issue("REVIEW_UNRESOLVED", "review_ref does not resolve to a review of this candidate in the bundle", where))
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
        if expected and payload.get("confidence") == "human_verified" and not rref:
            out.append(Issue("LEGAL_EFFECT_EDGE_UNREVIEWED", "a legal-effect edge marked human_verified needs a review_ref", where))
        tgt = payload.get("target") or {}
        if tgt.get("resolved") and not tgt.get("node_id"):
            out.append(Issue("EDGE_TARGET", "resolved target needs node_id", where))
        if tgt.get("resolved") is False and not tgt.get("raw_reference"):
            out.append(Issue("EDGE_TARGET", "unresolved target keeps its raw_reference", where))
    if ev is not None and ev.get("human_checked") is None:
        out.append(Issue("EVALUATION_HUMAN_FLAG", "evaluation_ref should state human_checked", where, "warning"))
    return out


def reviewed_record_rules(rec, reg, where, ctx=None):
    """Structural independence: reviewer differs from author, subject exists, reviewed commit is the producing commit."""
    out = restricted_scan(reg, rec, where)
    out += _path_issues(where, (rec.get("record_location") or {}).get("path"))
    reviewer = (rec.get("reviewer") or {}).get("reviewer_id", "")
    art = rec.get("reviewed_artefact") or {}
    author = art.get("author_id", "")
    if reviewer and author and reviewer.casefold() == author.casefold():
        out.append(Issue("REVIEW_NOT_INDEPENDENT", "reviewer_id equals the reviewed artefact's author_id", where))
    if rec.get("axis") == "source_authenticity" and rec.get("to_value") == "IDENTITY_CONFIRMED" and (rec.get("reviewer") or {}).get("kind") != "HUMAN":
        out.append(Issue("AI_REVIEW_CANNOT_CONFIRM_IDENTITY", "an AI review cannot confirm source identity", where))
    if ctx is None:
        out.append(Issue("REVIEW_UNRESOLVED_OUTSIDE_BUNDLE", "a review can only be checked against its subject inside a bundle", where, "warning"))
        return out
    sid = (rec.get("subject") or {}).get("id")
    if sid not in ctx.doc_ids | ctx.copy_shas | ctx.candidate_ids:
        out.append(Issue("DANGLING_REVIEW", "review subject not in bundle", where))
        return out
    recorded_author = ctx.subject_authors.get(sid)
    if recorded_author and recorded_author.casefold() != author.casefold():
        out.append(Issue("REVIEW_AUTHOR_MISMATCH", "author_id differs from the author recorded on the subject", where))
    if recorded_author and reviewer.casefold() == recorded_author.casefold():
        out.append(Issue("REVIEW_NOT_INDEPENDENT", "reviewer_id equals the subject's recorded author", where))
    commits = set(ctx.subject_commits.get(sid, set()))
    if sid not in ctx.candidate_ids:  # documents/copies: the producing pipeline is the release tools or artefact commit
        commits |= ctx.release_commits
    rc = art.get("reviewed_commit", "")
    if not any(c.startswith(rc) or rc.startswith(c) for c in commits if c and rc and len(rc) >= 7 and len(c) >= 7):
        out.append(Issue("REVIEW_COMMIT_MISMATCH", "reviewed_commit is not a commit that produced this subject or this release", where))
    return out


def approval_rules(rec, reg, where, ledger_version=None, ctx=None):
    out = restricted_scan(reg, rec, where)
    if ledger_version == 0:
        out.append(Issue("LEDGER_V0_NO_APPROVAL", "no approval record may be exchanged while AUTH-LEDGER is at version 0", where))
    if ctx is not None and rec.get("appointment_id") not in ctx.appointments:
        out.append(Issue("APPOINTMENT_MISSING", "approval cites an appointment that is not recorded", where))
    return out


def appointment_rules(rec, reg, where, ledger_version=None, ctx=None):
    out = restricted_scan(reg, rec, where)
    if ledger_version == 0:
        out.append(Issue("LEDGER_V0_NO_APPROVAL", "no appointment record may be exchanged while AUTH-LEDGER is at version 0", where))
    return out


def publication_rules(rec, reg, where, ctx=None):
    out = restricted_scan(reg, rec, where)
    if rec.get("channel") in SITE_ONLY_CHANNELS:
        out.append(Issue("PUBLICATION_CHANNEL_SITE_ONLY", "site publication acts (activation, Admin) cannot be carried in a bundle", where))
    if ctx is not None and rec.get("action") != "WITHDRAWN" and (rec.get("subject") or {}).get("doc_id") not in ctx.doc_ids:
        out.append(Issue("DANGLING_PUBLICATION_RECORD", "publication record subject not in bundle", where))
    return out


def record_issues(kind: str, rec: dict, reg: RestrictedRegister, where: str, ledger_version: int | None = None,
                  ctx: BundleContext | None = None) -> list[Issue]:
    if isinstance(rec, dict) and rec.get("record_kind") == "working_document":
        return [Issue("WORKING_DOCUMENT_IN_BUNDLE", "working documents (layer 9) are never exchanged", where)]
    if isinstance(rec, dict) and rec.get("record_kind") in RESERVED_RECORD_KINDS:
        return [Issue("RESERVED_RECORD_KIND", f"{rec.get('record_kind')} is reserved site-only state and never exchanged", where)]
    issues = schema_issues(kind, rec, where)
    if kind == "document":
        issues += document_rules(rec, reg, where, ledger_version, ctx)
    elif kind == "derived_text":
        issues += derived_text_rules(rec, reg, where, ctx)
    elif kind == "candidate":
        issues += candidate_rules(rec, reg, where, ctx)
    elif kind == "reviewed_record":
        issues += reviewed_record_rules(rec, reg, where, ctx)
    elif kind == "approval_record":
        issues += approval_rules(rec, reg, where, ledger_version, ctx)
    elif kind == "appointment_record":
        issues += appointment_rules(rec, reg, where, ledger_version, ctx)
    elif kind == "publication_record":
        issues += publication_rules(rec, reg, where, ctx)
    elif reg is not None:
        issues += restricted_scan(reg, rec, where)
    return issues
