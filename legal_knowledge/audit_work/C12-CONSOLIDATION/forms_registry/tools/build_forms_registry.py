#!/usr/bin/env python3
"""C12 Workstream G - Form Discovery and Coverage Register builder.

Reads ONLY sources already held (scratchpad working store, read-only; c7 git
objects via `git cat-file`). Performs no downloads and writes only to this
workstream's outputs/ directory.

  python build_forms_registry.py            # (re)build outputs/
  python build_forms_registry.py --check    # rebuild in memory, compare byte-for-byte, exit 1 on drift

Every output row carries verification_status
DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED. Nothing produced here is a legal
determination, an approved template or a claim of completeness beyond the
stated examined ranges.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import spec_forms  # noqa: E402
import spec_sources  # noqa: E402

TOOL_VERSION = "c12-wsg-forms-registry/1.1.0"  # 1.1.0 = C12 remediation of review WSG-R01..R15
RECORDED_ON = "2026-11-24"
VERIFICATION_STATUS = "DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED"
WS_ROOT = os.path.dirname(HERE)
DEFAULT_SCRATCH = os.path.abspath(os.path.join(WS_ROOT, "..", "..", "..", "..", ".."))
DEFAULT_C7 = "/home/user/c7"
C5_REG = os.path.join(WS_ROOT, "..", "..", "SOURCE-LIBRARY-C5", "registers", "source_copy_register.csv")

# Blueprint vocabularies (FORM_DISCOVERY_AND_COVERAGE_REGISTER.md s.3; DOCUMENT_STUDIO s.3)
COVERAGE_STATES = {"NOT_STARTED", "PARTIAL", "INSPECTED_WITH_GAPS", "INSPECTED_NO_FORMS_FOUND", "INSPECTED_FORMS_FOUND", "INACCESSIBLE"}
AUTHORITY_TYPES = {"STATUTORY_PRESCRIBED", "OFFICIAL_SPECIMEN", "OFFICIAL_SERVICE_ADMINISTRATIVE", "OTHER_OR_UNDETERMINED"}
FIDELITY = {"DISCOVERED", "TRANSCRIBED", "FIDELITY_VERIFIED"}
STATUS_CATEGORIES = {
    "MANDATORY_FORM_WORDING", "MANDATORY_FORM_WORDING_WITH_VARIATION", "MANDATORY_WITH_ALTERNATIVE_PERMITTED",
    "MANDATORY_DOCUMENT_LIST", "QUALIFIED_AS_FAR_AS_PRACTICABLE", "PERMISSIVE_USE_AR4", "PERMISSIVE_ATTACHMENT_FORM_PRESCRIBED",
    "PERMISSIVE_USE_SPECIFIC_RULE",
    "SPECIMEN_OR_ILLUSTRATION", "REQUIREMENT_LANGUAGE_NOT_EXTRACTED", "UNDETERMINED",
}
SOURCE_BASIS = {"OFFICIAL_COPY", "MML_ONLY", "BOTH"}
DOC_RANGE_CAP = 400
# Labels this short/common occur in almost every form; a cross-copy hit on them is weak evidence (WSG-R10/R11).
GENERIC_LABELS_EXTRA = {"form of oath", "form of affirmation", "given under my hand at", "the president of india"}
SCOPE_STATEMENT = ("Army-first scope: this cycle registers forms from held Army Rules 1954 copies and from the AFT (Procedure) Rules 2008, "
                   "DPP Rules 1953, Indian Soldiers (Litigation) Rules 1938, TA Rules 1948, Indian Tolls Rules 1942 and Assam Rifles Act 1941 copies held. "
                   "Air Force and Navy rule-level instruments were NOT assessed (held derived texts heading-scanned only; official copies NOT_HELD); "
                   "the 67 families are not the military-law form universe.")
FUZZY_ACCEPT = 0.80
FUZZY_WEAK = 0.65
HEADING_RE = re.compile(
    r"^\s*(APPENDIX\b|APPENDJX\b|FORM\b|FORM[-\s]?[0-9IVX]+\b|FORMS\b|SCHEDULE|SCHUDULE|SPECIMEN|Specimen|"
    r"Form\s+of\s+(Oath|oath|Affirmation|affirmation|Pass|Notice|Delay)|Form\s+No\b|Form\s+[IVX]+\b|Form\s+[A-L]\b|PART\s+[IVX]+\s*(\(|$))")


# ------------------------------------------------------------------ helpers
def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fuzzy_best(label_n: str, text_n: str) -> float:
    if not label_n:
        return 0.0
    if contains(label_n, text_n):
        return 1.0
    lt = label_n.split()
    tt = text_n.split()
    n = len(lt)
    best = 0.0
    for w in (n - 1, n, n + 1):
        if w <= 0 or w > len(tt):
            continue
        for i in range(0, len(tt) - w + 1):
            cand = " ".join(tt[i:i + w])
            sm = difflib.SequenceMatcher(None, label_n, cand, autojunk=False)
            if sm.real_quick_ratio() < best or sm.quick_ratio() < best:
                continue
            r = sm.ratio()
            if r > best:
                best = r
    return round(best, 3)


def contains(needle_n: str, hay_n: str) -> bool:
    """Whole-word containment on normalised text."""
    return bool(needle_n) and (" " + needle_n + " ") in (" " + hay_n + " ")


def match(label: str, text_n: str, mode: str):
    ln = norm(label)
    if contains(ln, text_n):
        return "EXACT", 1.0
    r = fuzzy_best(ln, text_n)
    if r >= FUZZY_ACCEPT:
        return "FUZZY", r
    if r >= FUZZY_WEAK:
        return "WEAK", r
    return "NOT_FOUND", r


def fmt_match(m):
    kind, r = m
    return kind if kind in ("EXACT", "NOT_FOUND") else "%s:%.3f" % (kind, r)


def is_mml(key):
    spec = spec_sources.SOURCES.get(key)
    return bool(spec) and spec["evidence_class"].startswith("UNVERIFIED_MANUAL")


CITE_RE = re.compile(r"\[([A-Z0-9][A-Z0-9-]+) p\.(\d+)(?:-(\d+))?[^\]]*\]")
RULE_NUM_RE = re.compile(r"(?i)(?:\brules?\s+|\br\.\s*|\bAR\s+)(\d{1,3}[A-Z]?)(?!\d)")


def citations(text):
    """[(src_key, first_page, last_page)] for every '[KEY p.N(-M)...]' citation in text."""
    return [(m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))) for m in CITE_RE.finditer(text)]


def quoted_segments(text):
    """Single-quoted segments following each citation: {(key,a,b): [segment pieces split on '...']}."""
    out = []
    for m in CITE_RE.finditer(text):
        tail = text[m.end():]
        nxt = CITE_RE.search(tail)
        chunk = tail[:nxt.start()] if nxt else tail
        mm = re.search(r"\bMML\b", chunk)  # a later quotation attributed to an MML copy is not part of this citation
        if mm:
            chunk = chunk[:mm.start()]
        for q in re.findall(r"'((?:[^']|'(?=[a-z]))+)'", chunk):
            for piece in re.split(r"\.\.\.|…", q):
                if len(norm(piece).split()) >= 3:
                    out.append(((m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))), piece))
    return out


def verify_quotes(fam, st):
    """WSG-R08: every quoted piece cited to a native-text (exact-mode) source page must occur there
    (normalised whole-word match; the cited page plus the next page, to allow page breaks)."""
    errs = []
    for field in ("requirement_quote", "prescribing_provision"):
        for (key, a, b), piece in quoted_segments(fam[field]):
            spec = spec_sources.SOURCES.get(key)
            if not spec or spec["kind"] != "pdf" or spec["match_mode"] != "exact":
                continue
            rec = st.load(key)
            hay = re.sub(r"\bindiacode\b", " ", page_text_n(rec, a, min(b + 1, rec["page_count"])))  # drop page watermark
            hay = re.sub(r"\s+", " ", hay)
            if not contains(norm(piece), hay):
                errs.append("quote not found on cited page: %s %s [%s p.%d-%d] %r" % (fam["family_id"], field, key, a, b, piece[:80]))
    return errs


def visual_pages(vc):
    return range(vc["page"], vc.get("last_page", vc["page"]) + 1)


def rule_number_guard(families, visual_checks, sources):
    """WSG-R01: a rule number written by hand into title / prescribing_provision / requirement_quote is attributed
    to the first citation '[KEY p.N]' that follows it in the same text (within 160 characters), or else to the
    family's PRIMARY source. Numbers attributed to a native-text source are checked against that page's text by
    text_cited_rule_numbers_ok. Numbers attributed to an OCR-mode source are accepted ONLY if a recorded page-image
    check (spec_forms.VISUAL_CHECKS) of that source confirms the number - OCR digit confusion ('rule :l 7' for 27)
    therefore cannot pass silently."""
    errs = []
    confirmed = {}
    for vc in visual_checks:
        for n in vc["rule_numbers"]:
            confirmed.setdefault((vc["src"], n.upper()), set()).update(visual_pages(vc))
    for fam in families:
        prim = [o["src"] for o in fam["occurrences"] if o["role"] == "PRIMARY"][0]
        for text in (fam["title"], fam["prescribing_provision"], fam["requirement_quote"]):
            for m in RULE_NUM_RE.finditer(text):
                n = m.group(1).upper()
                nxt = CITE_RE.search(text, m.end())
                src = nxt.group(1) if (nxt and nxt.start() - m.end() <= 160) else prim
                if src not in sources or sources[src]["match_mode"] != "fuzzy":
                    continue
                if (src, n) not in confirmed:
                    errs.append("rule number %s in %s (attributed to OCR source %s) is not confirmed by a recorded page-image check"
                                % (n, fam["family_id"], src))
    return errs


def text_cited_rule_numbers_ok(fam, st):
    """Companion to rule_number_guard: a rule number attributed (same rule) to a native-text citation must occur
    as a token on one of the cited pages (or the page before, where the rule may begin)."""
    errs = []
    for field in ("title", "prescribing_provision", "requirement_quote"):
        text = fam[field]
        for m in RULE_NUM_RE.finditer(text):
            nxt = CITE_RE.search(text, m.end())
            if not nxt or nxt.start() - m.end() > 160:
                continue
            key = nxt.group(1)
            spec = spec_sources.SOURCES.get(key)
            if not spec or spec["match_mode"] != "exact" or spec["kind"] != "pdf":
                continue
            rec = st.load(key)
            pages = set()
            for pa, pb in re.findall(r"p\.(\d+)(?:-(\d+))?", nxt.group(0)):
                pages.update(range(max(1, int(pa) - 1), int(pb or pa) + 1))
            if not any(contains(norm(m.group(1)), rec["pages_n"][pg - 1]) for pg in pages if pg <= rec["page_count"]):
                errs.append("rule number %s not found on cited native-text page(s) %s (%s %s)" % (m.group(1), nxt.group(0), fam["family_id"], field))
    return errs


def is_generic_label(label):
    n = norm(label)
    return len(n.split()) <= 2 or n in GENERIC_LABELS_EXTRA


# ------------------------------------------------------------------ source loading
class Store:
    def __init__(self, scratch, c7):
        self.scratch = scratch
        self.c7 = c7
        self.cache = {}
        self.errors = []
        self.pymupdf_version = None

    def raw(self, root, path):
        if root == "scratch":
            with open(os.path.join(self.scratch, path), "rb") as fh:
                return fh.read()
        if root == "c7git":
            return subprocess.run(["git", "-C", self.c7, "cat-file", "blob", "%s:%s" % (spec_sources.C7_COMMIT, path)],
                                  check=True, capture_output=True).stdout
        raise ValueError(root)

    def load(self, key):
        if key in self.cache:
            return self.cache[key]
        spec = spec_sources.SOURCES[key]
        b = self.raw(spec["root"], spec["path"])
        got = sha256_bytes(b)
        if got != spec["sha256"]:
            raise SystemExit("SHA256 MISMATCH for %s: expected %s got %s" % (key, spec["sha256"], got))
        rec = {"key": key, "spec": spec, "bytes": len(b)}
        if spec["kind"] == "pdf":
            import pymupdf  # noqa
            self.pymupdf_version = pymupdf.VersionBind
            doc = pymupdf.open(stream=b, filetype="pdf")
            rec["pages"] = [doc[i].get_text() for i in range(len(doc))]
            rec["pages_n"] = [norm(t) for t in rec["pages"]]
            rec["page_count"] = len(doc)
        else:
            text = b.decode("utf-8-sig")
            lines = {}
            for raw_line in text.splitlines():
                m = re.match(r"^L(\d+)\|\s?(.*)$", raw_line)
                if m:
                    lines[int(m.group(1))] = m.group(2)
            rec["lines"] = lines
            rec["line_count"] = max(lines) if lines else 0
            osp = spec.get("original_path")
            if osp:
                ob = self.raw("scratch", osp)
                rec["original_sha_ok"] = sha256_bytes(ob) == spec["original_sha256"]
                if not rec["original_sha_ok"]:
                    raise SystemExit("ORIGINAL DOC SHA256 MISMATCH for %s" % key)
        self.cache[key] = rec
        return rec


def page_text_n(rec, a, b):
    return " ".join(rec["pages_n"][a - 1:b])


def find_line_anchor(rec, anchor, from_line):
    """First line (>= from_line) at which the normalised anchor begins, allowing the
    anchor to wrap over up to three consecutive lines."""
    an = norm(anchor)
    keys = sorted(k for k in rec["lines"] if k >= from_line)
    for idx in range(len(keys)):
        win = keys[idx:idx + 3]
        if contains(an, norm(" ".join(rec["lines"][kk] for kk in win))):
            start = idx
            for j in range(idx + 1, idx + 3):
                if j < len(keys) and contains(an, norm(" ".join(rec["lines"][kk] for kk in keys[j:idx + 3]))):
                    start = j
            return keys[start]
    return None


# ------------------------------------------------------------------ build
REG_COLS = [
    "candidate_id", "form_family_id", "occurrence_role", "instrument", "appendix_part_or_schedule", "printed_form_number", "printed_title",
    "source_key", "source_logical_id", "c5_copy_id", "source_copy_sha256", "source_file", "source_original_doc_sha256", "edition_or_version_evidence",
    "source_evidence_class", "locator_type", "locator_start", "locator_end", "locator_end_basis", "page_image_locator", "page_region_bbox",
    "anchor_text_as_printed", "anchor_match",
    "prescribing_provision", "requirement_language_as_printed", "form_authority_type_candidate", "status_category",
    "source_basis", "official_copy_extent", "field_set_version", "statutory_confirmation_status", "cross_cutting_caveat_as_printed",
    "applicability_conditions_as_printed", "signatory_as_printed", "competent_authority_as_printed", "procedural_dependencies",
    "companion_documents_as_printed", "version_amendment_history", "supersession_status", "alternate_occurrences",
    "field_transcription_scope", "fields_recorded", "fields_matched_in_this_copy", "fields_matched_non_generic", "fidelity_state",
    "pages_visually_inspected", "visual_check_refs",
    "applicability_state", "legal_approval_state", "publication_state", "dependency_freshness_state", "verification_status",
    "occurrence_note", "outstanding_uncertainties", "review_finding_refs",
]
FIELD_COLS = [
    "field_id", "form_family_id", "transcription_candidate_id", "seq", "field_label_as_printed", "field_kind",
    "mandatory_indication_as_printed", "primary_match", "match_method", "generic_label", "cross_copy_presence",
    "field_set_version", "official_copy_presence", "verification_status",
]
COV_COLS = [
    "coverage_id", "source_key", "source_logical_id", "c5_copy_id", "source_copy_sha256", "holding", "source_location", "evidence_class",
    "edition_evidence", "access_marking", "page_or_line_count", "segment_label", "expected_inspection_range", "text_extracted_range",
    "pages_visually_inspected", "pages_missing_unreadable_or_unexamined", "inspection_method", "inspection_date", "coverage_state",
    "candidate_occurrences_found", "candidate_ids", "unregistered_heading_hits", "excluded_ranges_and_reason", "notes",
    "scope_this_cycle", "coverage_method_limitation", "reviewer_evidence", "review_remediation_state", "legal_review_ref", "verification_status",
]
MATCH_METHOD = "normalised whole-word match (case and punctuation stripped) within the primary page/line range; fuzzy ratio for OCR sources"
FINDING_FAMILIES = {
    "WSG-R01": {"FF-AFTPR08-F3"},
    "WSG-R02": {"FF-AR54-APPV-FH", "FF-AFTPR08-F2"},
    "WSG-R06": {"FF-AFTPR08-F1"},
    "WSG-R09": {"FF-AR54-APPIII-P2", "FF-AR54-APPV-FI", "FF-AR54-APPIII-SGCM"},
    "WSG-R12": {"FF-DPPR53-S2"},
}


def occ_extent(o):
    note = o.get("note", "")
    if "NOT REPRODUCED" in note:
        return "PLACEHOLDER"
    if re.search(r"Amending text\b.*\bonly", note):
        return "AMENDING_TEXT_ONLY"
    return "FULL"


def family_basis(fam):
    """WSG-R04/R05: structured source basis. 'Official copy' = a held non-MML government copy (Gazette facsimile,
    India Code compilation or India Code bitstream); it does not mean authenticated or current."""
    occs = [o for o in fam["occurrences"] if occ_extent(o) != "PLACEHOLDER"]
    off = [o for o in occs if not is_mml(o["src"])]
    mml = [o for o in occs if is_mml(o["src"])]
    basis = "BOTH" if off and mml else ("OFFICIAL_COPY" if off else "MML_ONLY")
    extent = "NONE"
    if off:
        extent = "FULL_FORM_TEXT" if any(occ_extent(o) == "FULL" for o in off) else "AMENDING_TEXT_ONLY"
    prim = [o for o in fam["occurrences"] if o["role"] == "PRIMARY"][0]
    off_keys = ",".join(sorted({o["src"] for o in off}))
    if not is_mml(prim["src"]):
        fsv = "OFFICIAL_COPY_VERSION (%s)" % prim["src"]
    elif extent == "FULL_FORM_TEXT":
        fsv = ("MML_VERSION_UNVERIFIED (official copy held: %s; not used as primary because its OCR text layer is not reliable "
               "for transcription and its pages were not visually checked field by field)" % off_keys)
    elif extent == "AMENDING_TEXT_ONLY":
        fsv = "MML_VERSION_UNVERIFIED (official copy held for amending text only: %s)" % off_keys
    else:
        fsv = "MML_ONLY_UNVERIFIED"
    if fam["authority"] != "STATUTORY_PRESCRIBED":
        scs = "NOT_APPLICABLE (authority candidate is not STATUTORY_PRESCRIBED)"
    else:
        rule_off = any(not is_mml(k) for k, _a, _b in citations(fam["requirement_quote"]))
        if not rule_off:
            scs = "NOT_CONFIRMED_FROM_OFFICIAL_COPY: RULE_AND_FORM_TEXT_MML_ONLY"
        elif extent != "FULL_FORM_TEXT":
            scs = "NOT_CONFIRMED_FROM_OFFICIAL_COPY: RULE_TEXT_OFFICIAL_FORM_TEXT_MML_ONLY"
        elif is_mml(prim["src"]):
            scs = "RULE_AND_FORM_TEXT_IN_OFFICIAL_COPY (field list MML version)"
        else:
            scs = "RULE_AND_FORM_TEXT_IN_OFFICIAL_COPY"
    assert basis in SOURCE_BASIS
    return dict(source_basis=basis, official_copy_extent=extent, field_set_version=fsv, statutory_confirmation_status=scs)


def build(scratch, c7):
    st = Store(scratch, c7)
    errors = []
    reg_rows, field_rows = [], []
    fam_basis = {}
    occ_index = []  # (family, cand_id, src, start, end, ltype)

    # ---- guards (WSG-R01, WSG-R08)
    errors.extend(rule_number_guard(spec_forms.FAMILIES, spec_forms.VISUAL_CHECKS, spec_sources.SOURCES))
    vc_by_src = {}
    for vc in spec_forms.VISUAL_CHECKS:
        assert vc["src"] in spec_sources.SOURCES, vc["id"]
        vc_by_src.setdefault(vc["src"], []).append(vc)
    for fam in spec_forms.FAMILIES:
        errors.extend(verify_quotes(fam, st))
        errors.extend(text_cited_rule_numbers_ok(fam, st))

    # ---- resolve occurrences
    resolved = {}
    for fam in spec_forms.FAMILIES:
        fid = fam["family_id"]
        assert fam["authority"] in AUTHORITY_TYPES, fid
        assert fam["status"] in STATUS_CATEGORIES, (fid, fam["status"])
        counts = {}
        occs = []
        for o in fam["occurrences"]:
            rec = st.load(o["src"])
            counts[o["src"]] = counts.get(o["src"], 0) + 1
            cid = "FC-%s~%s~%d" % (fid[3:], o["src"], counts[o["src"]])
            mode = rec["spec"]["match_mode"]
            if rec["spec"]["kind"] == "pdf":
                a, b = o["pages"]
                if not (1 <= a <= b <= rec["page_count"]):
                    raise SystemExit("bad page range %s %s" % (cid, o["pages"]))
                tn = page_text_n(rec, a, b)
                am = match(o["anchor"], tn, mode)
                ltype, start, end = "PDF_PAGE", a, b
                if mode == "fuzzy":  # WSG-R01: digits in an OCR anchor must be exact tokens or visually confirmed
                    toks = set(tn.split())
                    seen = {pg for vc in vc_by_src.get(o["src"], []) for pg in visual_pages(vc)}
                    for d in re.findall(r"\d+", norm(o["anchor"])):
                        if d not in toks and not (set(range(a, b + 1)) & seen):
                            errors.append("OCR anchor digit %s not an exact token and page not visually checked: %s" % (d, cid))
            else:
                ln = find_line_anchor(rec, o["anchor"], o["from_line"])
                if ln is None:
                    am = ("NOT_FOUND", 0.0)
                    start = end = None
                    tn = ""
                else:
                    am = ("EXACT", 1.0)
                    start = ln
                    end = None  # set after all occurrences known
                    tn = None
                ltype = "DOC_DERIVED_LINE"
            occs.append(dict(o=o, cid=cid, rec=rec, mode=mode, ltype=ltype, start=start, end=end, tn=tn, am=am))
            if o["role"] == "PRIMARY" and am[0] not in ("EXACT", "FUZZY"):
                errors.append("PRIMARY anchor not matched: %s (%s)" % (cid, fmt_match(am)))
            if mode == "exact" and rec["spec"]["kind"] == "pdf" and am[0] != "EXACT":
                errors.append("exact-mode anchor not matched: %s %r (%s)" % (cid, o["anchor"], fmt_match(am)))
        resolved[fid] = occs

    # ---- set line-range ends: next anchored occurrence (any family) in same source, capped
    by_src = {}
    for fid, occs in resolved.items():
        for oc in occs:
            if oc["ltype"] == "DOC_DERIVED_LINE" and oc["start"] is not None:
                by_src.setdefault(oc["o"]["src"], set()).add(oc["start"])
    for fid, occs in resolved.items():
        for oc in occs:
            if oc["ltype"] == "DOC_DERIVED_LINE" and oc["start"] is not None:
                later = sorted(x for x in by_src[oc["o"]["src"]] if x > oc["start"])
                cands = [(oc["start"] + DOC_RANGE_CAP, "CAPPED_AT_%d_LINES (form end not established)" % DOC_RANGE_CAP),
                         (oc["rec"]["line_count"], "END_OF_FILE")]
                if later:
                    cands.append((later[0] - 1, "NEXT_REGISTERED_OCCURRENCE_START_MINUS_1"))
                oc["end"], oc["end_basis"] = min(cands, key=lambda x: (x[0], x[1]))
                lines = oc["rec"]["lines"]
                oc["tn"] = norm(" ".join(lines[k] for k in sorted(lines) if oc["start"] <= k <= oc["end"]))

    # ---- fields
    for fam in spec_forms.FAMILIES:
        fid = fam["family_id"]
        occs = resolved[fid]
        prim = [oc for oc in occs if oc["o"]["role"] == "PRIMARY"]
        if len(prim) != 1:
            raise SystemExit("family %s must have exactly one PRIMARY occurrence" % fid)
        prim = prim[0]
        basis = family_basis(fam)
        fam_basis[fid] = basis
        official_full = [oc for oc in occs if oc is not prim and not is_mml(oc["o"]["src"]) and occ_extent(oc["o"]) == "FULL"]
        official_amd = [oc for oc in occs if oc is not prim and not is_mml(oc["o"]["src"]) and occ_extent(oc["o"]) == "AMENDING_TEXT_ONLY"]
        per_occ_hits = {oc["cid"]: 0 for oc in occs}
        per_occ_ng = {oc["cid"]: 0 for oc in occs}
        for i, (label, kind) in enumerate(fam["fields"], 1):
            generic = is_generic_label(label)
            pm = match(label, prim["tn"], prim["mode"])
            if prim["mode"] == "exact" and pm[0] != "EXACT":
                errors.append("field not found exactly in primary: %s #%d %r (%s)" % (fid, i, label, fmt_match(pm)))
            if prim["mode"] == "fuzzy" and pm[0] not in ("EXACT", "FUZZY"):
                errors.append("field not matched (fuzzy) in primary: %s #%d %r (%s)" % (fid, i, label, fmt_match(pm)))
            if pm[0] in ("EXACT", "FUZZY"):
                per_occ_hits[prim["cid"]] += 1
                per_occ_ng[prim["cid"]] += 0 if generic else 1
            cross, off, amd = [], [], []
            for oc in occs:
                if oc is prim:
                    continue
                if not oc["tn"]:
                    cross.append("%s=NO_TEXT_RANGE" % oc["cid"])
                    continue
                m = match(label, oc["tn"], "fuzzy")
                if m[0] in ("EXACT", "FUZZY"):
                    per_occ_hits[oc["cid"]] += 1
                    per_occ_ng[oc["cid"]] += 0 if generic else 1
                cross.append("%s=%s%s" % (oc["cid"], fmt_match(m), " (generic label; weak evidence)" if generic else ""))
                if oc in official_full:
                    off.append((oc, m))
                if oc in official_amd:
                    amd.append((oc, m))
            if not is_mml(prim["o"]["src"]):
                ocp = "PRIMARY_IS_OFFICIAL_COPY"
            elif off:
                good = [o for o, m in off if m[0] in ("EXACT", "FUZZY")]
                amd_good = [o for o, m in amd if m[0] in ("EXACT", "FUZZY")]
                miss = ";".join("%s=%s" % (o["o"]["src"], fmt_match(m)) for o, m in off)
                if good:
                    ocp = "PRESENT_IN_OFFICIAL_COPY_TEXT_LAYER (%s)" % ";".join(o["o"]["src"] for o in good)
                elif amd_good:
                    ocp = ("PRESENT_IN_OFFICIAL_AMENDING_TEXT_LAYER (%s); not in pre-amendment official copy text layer (%s)"
                           % (";".join(o["o"]["src"] for o in amd_good), miss))
                else:
                    ocp = "NOT_FOUND_OR_WEAK_IN_OFFICIAL_COPY_TEXT_LAYER (%s; OCR - visual check needed; DIVERGENCE_QUEUE)" % miss
            elif basis["official_copy_extent"] == "AMENDING_TEXT_ONLY":
                ocp = "OFFICIAL_COPY_HOLDS_AMENDING_TEXT_ONLY"
            else:
                ocp = "NO_OFFICIAL_COPY_HELD"
            vn = spec_forms.FIELD_VISUAL_NOTES.get((fid, label))
            if vn:
                ocp = vn + "; DIVERGENCE_QUEUE"
            field_rows.append({
                "field_id": "%s#F%02d" % (fid, i), "form_family_id": fid, "transcription_candidate_id": prim["cid"], "seq": i,
                "field_label_as_printed": label, "field_kind": kind,
                "mandatory_indication_as_printed": "NONE_PRINTED_FOR_FIELD (form-level requirement only; see register requirement_language_as_printed)",
                "primary_match": fmt_match(pm), "match_method": MATCH_METHOD, "generic_label": "YES" if generic else "NO",
                "cross_copy_presence": " | ".join(sorted(cross)), "field_set_version": basis["field_set_version"],
                "official_copy_presence": ocp, "verification_status": VERIFICATION_STATUS,
            })

        all_ids = [oc["cid"] for oc in occs]
        caveat = spec_forms.AR4_1_VERBATIM if (fam["instrument"] == "Army Rules, 1954" and fam["part"].startswith("Appendix")) else ""
        for oc in occs:
            o, rec, spec = oc["o"], oc["rec"], oc["rec"]["spec"]
            is_prim = o["role"] == "PRIMARY"
            fidelity = "DISCOVERED"
            if is_prim and spec["text_quality"] == "TEXT" and oc["am"][0] == "EXACT":
                fidelity = "TRANSCRIBED"  # labels taken from a native text layer; each label matched (normalised whole-word) in that copy
            vcs = []
            if oc["ltype"] == "PDF_PAGE":
                vcs = [vc for vc in vc_by_src.get(o["src"], []) if set(visual_pages(vc)) & set(range(oc["start"], oc["end"] + 1))]
            refs = sorted(f for f, ids in FINDING_FAMILIES.items() if fid in ids)
            if caveat:
                refs.append("WSG-R03")
            if basis["source_basis"] == "BOTH" and is_mml(prim["o"]["src"]):
                refs.append("WSG-R04")
            if basis["source_basis"] == "MML_ONLY":
                refs.append("WSG-R05")
            if fam["status"] == "MANDATORY_WITH_ALTERNATIVE_PERMITTED":
                refs.append("WSG-R08")
            if oc["ltype"] == "DOC_DERIVED_LINE":
                refs.append("WSG-R10")
            reg_rows.append({
                "candidate_id": oc["cid"], "form_family_id": fid, "occurrence_role": o["role"], "instrument": fam["instrument"],
                "appendix_part_or_schedule": fam["part"], "printed_form_number": fam["number"], "printed_title": fam["title"],
                "source_key": o["src"], "source_logical_id": spec["c5_source_id"], "c5_copy_id": spec["c5_copy_id"],
                "source_copy_sha256": spec["sha256"], "source_file": spec["path"] if spec["root"] == "scratch" else "git:%s@%s:%s" % ("c7", spec_sources.C7_COMMIT, spec["path"]),
                "source_original_doc_sha256": spec.get("original_sha256", ""), "edition_or_version_evidence": spec["edition_evidence"],
                "source_evidence_class": spec["evidence_class"], "locator_type": oc["ltype"],
                "locator_start": "" if oc["start"] is None else oc["start"], "locator_end": "" if oc["end"] is None else oc["end"],
                "locator_end_basis": "PAGE_RANGE_AS_CITED" if oc["ltype"] == "PDF_PAGE" else oc.get("end_basis", "ANCHOR_NOT_FOUND"),
                "page_image_locator": "; ".join("%s: %s p.%s %s, %d dpi, %s" % (vc["id"], vc["src"], "-".join(str(x) for x in sorted({vc["page"], vc.get("last_page", vc["page"])})), vc["region"], vc["dpi"], vc["date"]) for vc in vcs),
                "page_region_bbox": "",
                "anchor_text_as_printed": o["anchor"], "anchor_match": fmt_match(oc["am"]),
                "prescribing_provision": fam["prescribing_provision"], "requirement_language_as_printed": fam["requirement_quote"],
                "form_authority_type_candidate": fam["authority"], "status_category": fam["status"],
                "source_basis": basis["source_basis"], "official_copy_extent": basis["official_copy_extent"],
                "field_set_version": basis["field_set_version"], "statutory_confirmation_status": basis["statutory_confirmation_status"],
                "cross_cutting_caveat_as_printed": caveat,
                "applicability_conditions_as_printed": fam["applicability"], "signatory_as_printed": fam["signatory"],
                "competent_authority_as_printed": fam["competent_authority"], "procedural_dependencies": fam["dependencies"],
                "companion_documents_as_printed": fam["companions"], "version_amendment_history": fam["version_history"],
                "supersession_status": fam["supersession"], "alternate_occurrences": ";".join(x for x in all_ids if x != oc["cid"]),
                "field_transcription_scope": fam["field_scope"] if is_prim else "CROSS_CHECK_ONLY (labels from primary)",
                "fields_recorded": len(fam["fields"]), "fields_matched_in_this_copy": per_occ_hits[oc["cid"]],
                "fields_matched_non_generic": per_occ_ng[oc["cid"]],
                "fidelity_state": fidelity, "pages_visually_inspected": o.get("visual", "NONE_THIS_CYCLE"),
                "visual_check_refs": ";".join(vc["id"] for vc in vcs),
                "applicability_state": "NOT_ESTABLISHED", "legal_approval_state": "RESEARCH_ONLY",
                "publication_state": "NOT_STAGED (no registry publication)", "dependency_freshness_state": "NOT_ASSESSED",
                "verification_status": VERIFICATION_STATUS, "occurrence_note": o.get("note", ""), "outstanding_uncertainties": fam["uncertainties"],
                "review_finding_refs": ";".join(sorted(set(refs))),
            })
            if oc["start"] is not None:
                occ_index.append((fid, oc["cid"], o["src"], oc["start"], oc["end"], oc["ltype"]))

    # ---- heading scan (all loaded pdf sources + coverage-only pdfs)
    for key in sorted(spec_sources.SOURCES):
        st.load(key)
    unreg = {}
    for key, rec in sorted(st.cache.items()):
        if rec["spec"]["kind"] != "pdf":
            continue
        covered = set()
        for (_f, _c, src, a, b, lt) in occ_index:
            if src == key:
                covered.update(range(a, b + 1))
        hits = []
        for pi, text in enumerate(rec["pages"], 1):
            for line in text.split("\n"):
                if HEADING_RE.match(line) and pi not in covered:
                    hits.append((pi, line.strip()[:90]))
        unreg[key] = hits

    cov_rows = coverage(st, occ_index, unreg)
    return dict(reg=reg_rows, fields=field_rows, cov=cov_rows, errors=errors, store=st, unreg=unreg, occ_index=occ_index, basis=fam_basis)


# ------------------------------------------------------------------ coverage
SEGMENTS = [
    # key, label, (a,b) or None=whole, method, visual, state, gaps/excluded, notes
    ("AR54-GAZ", "Rules text (S.R.O. 484 rr.1-205)", (1, 58), "pymupdf text layer (OCR of scan) + anchor/heading search; page image of p.2 upper part (AR 4) checked", "2 (upper 20% only)", "INSPECTED_WITH_GAPS",
     "Pages other than p.2 (upper part) not visually inspected; OCR quality varies (headers garbled).", "Oath/affirmation forms printed in rr.9, 45, 46, 109, 140 located."),
    ("AR54-GAZ", "Appendices I-V (arrangement p.58; forms pp.59-86)", (58, 86), "pymupdf text layer (OCR) + visual inspection of pp.59-61 (rendered 110 dpi) and p.72 (170 dpi)", "59-61; 72", "INSPECTED_WITH_GAPS",
     "Appendix II (Form of Charges) and Appendix III Part I (Forms as to courts-martial) are listed in the arrangement (p.58) but their text was not located on pp.59-86 of this copy; pp.62-71 and 73-86 not visually inspected. Field lists of forms also printed here are the MML 2 version (field_set_version).",
     "App. I Forms I-II, App. III Pts II-IV, App. IV Pts I-II (Forms 1, 2, A-G) and App. V (Forms H-L) located."),
    ("AR54-GAZ", "Other S.R.O.s in the same Gazette issue", (87, 88), "heading scan", "NONE", "INSPECTED_NO_FORMS_FOUND",
     "Excluded: not Army Rules (S.R.O. 486, 489 cantonment bye-laws etc.).", ""),
    ("AR54-IC", "Rules text with notes (whole compilation)", None, "pymupdf text layer + anchor search", "NONE", "INSPECTED_WITH_GAPS",
     "This compilation does not print the Appendices (forms) at all; rule text only.", "Used as primary for oath forms and for prescribing-provision quotations."),
    ("MML2", "Army Act 1950 with notes", (1, 123), "pymupdf text layer (typeset PDF) heading scan", "NONE", "INSPECTED_NO_FORMS_FOUND",
     "Heading scan only; forms embedded without headings could be missed.", "Negative result for this range only."),
    ("MML2", "Army Rules 1954 rules text with notes", (124, 230), "text layer + anchor search", "NONE", "INSPECTED_FORMS_FOUND", "",
     "Oath/affirmation forms located at pp.134, 167-169, 199, 207."),
    ("MML2", "Appendices I-V incl. editorial notes/memoranda", (231, 328), "text layer + anchor search + field transcription", "NONE_THIS_CYCLE (WS-C page images exist for pp.1, 339 only)", "INSPECTED_FORMS_FOUND",
     "Appendix I not reproduced (p.232). Editorial material stated not to form part of the Appendices (Notes p.234-235; 'Arrangement of the Court Room' p.272; Memoranda pp.304-315) excluded from candidate forms.",
     "Primary transcription source for App. II-V fields (UNVERIFIED_MANUAL)."),
    ("MML2", "General index", (329, 339), "heading scan", "NONE", "INSPECTED_NO_FORMS_FOUND", "Index entries only.", ""),
    ("MML-AR-DOC1", "Army Rules + appendices (DOC transcription)", None, "WS-C pinned derived line text; anchor search (lines)", "NONE", "PARTIAL",
     "No stable page mapping for DOC; occurrences located by anchor only; full-range inspection not performed.", ""),
    ("MML-AR-DOC", "Army Rules + appendices (DOC transcription)", None, "WS-C pinned derived line text; anchor search (lines)", "NONE", "PARTIAL",
     "As DOC-1.", ""),
    ("MML3", "Other Acts/instruments (whole PDF)", None, "text layer heading scan + anchor search", "NONE", "INSPECTED_WITH_GAPS",
     "TA Rules and Indian Tolls Rules blocks are duplicated within the PDF (~42 pages apart); schedules that are modifications/lists (TA Sch. II, II-A, III, IV; Act schedules) excluded as non-forms; CrPC/IPC/IEA forms not itemised (historical; out of military-forms scope this cycle).",
     "DPP Rules 1953, Indian Soldiers (Litigation) Rules 1938, TA Rules 1948, Indian Tolls Rules 1942, Assam Rifles Act 1941 schedule located."),
    ("MML3-DOC", "Other Acts/instruments (DOC transcription)", None, "derived line text; anchor search", "NONE", "PARTIAL", "Anchor-only.", ""),
    ("MML-AA-PDF", "Army Act with notes", None, "heading scan", "NONE", "INSPECTED_NO_FORMS_FOUND", "Heading scan only.", ""),
    ("MML-AA-DOC", "Army Act with notes (DOC)", None, "not scanned beyond anchor tooling", "NONE", "NOT_STARTED", "DOC duplicate of MML-AA-PDF content (WS-C pilot); not separately examined.", ""),
    ("MML1-DOC", "Part I commentary (DOC)", None, "line heading scan", "NONE", "INSPECTED_NO_FORMS_FOUND", "Heading scan only.", ""),
    ("AR-AMD-1965", "S.R.O. 116 of 1965", None, "text layer (OCR)", "NONE", "INSPECTED_NO_FORMS_FOUND",
     "Amending text only (App. I Form No. I wording substitutions at p.3) - recorded as version history, not as a form.", ""),
    ("AR-AMD-1993", "S.R.O. 17(E) of 1993", None, "text layer (OCR); page image of p.19 checked (150 dpi)", "19", "INSPECTED_WITH_GAPS",
     "Pages other than p.19 not visually inspected (incl. pp.20-21 Forms 1-A and I-B); OCR noisy.", "Inserted/amended forms: App. III Pt I IAFD-905 para 9; App. III Pt III (c); App. IV Forms B, C; App. V heading, Form I, Forms 1-A and I-B."),
    ("AA50-IC", "Army Act 1950 (whole)", None, "text layer heading scan", "NONE", "INSPECTED_NO_FORMS_FOUND",
     "Act prescribes forms by reference (ss.13, 17, 166, 168, 169, 191(2)(j)) but prints none.", ""),
    ("RA87-CH5", "Regulations for the Army 1987 Ch. V extract", None, "text layer", "NONE", "INSPECTED_NO_FORMS_FOUND",
     "5-page extract only; references IAFF-958, IAFF-3013, AFMSF-2A by number.", ""),
    ("AFT07-IC", "AFT Act 2007 (whole)", None, "text layer heading scan", "NONE", "INSPECTED_NO_FORMS_FOUND", "", ""),
    ("AFTPR08-C7", "AFT (Procedure) Rules 2008 incl. Appendix 'A'", None, "text layer (OCR) + anchor search; page images of pp.26, 27, 29 (part), 37, 38, 42 (part), 46, 47 checked", "26; 27; 29 (band); 37; 38; 42 (upper part); 46; 47", "INSPECTED_WITH_GAPS",
     "Pages other than those listed not visually inspected; OCR noisy (e.g. 'rule :l 7' for 'rule 27' on p.46); pp.43-45 (Form I body) not visually inspected.", "Forms I-III located pp.42-47. 2011 amendment examined separately (AFTPRA11-C7)."),
    ("AFTPRA11-C7", "AFT (Procedure) Amendment Rules 2011 (S.R.O. 05(E), 2 pp.)", None, "page images of pp.1-2 (110 dpi); English text p.2 read", "1-2", "INSPECTED_NO_FORMS_FOUND",
     "p.1 Hindi text not read for content (no form layout visible on the image).", "No form printed. Inserts r.7(2) and r.12A (affidavit supporting applications under r.8 and replies under r.12); recorded as an unexamined dependency of AFT Form I."),
    ("AFTPRAC09-C7", "AFT Practice Rules 2009 (12 pp.)", None, "text layer (OCR)", "NONE", "INSPECTED_WITH_GAPS",
     "Forms No. 1-9 are referenced (pp.4-9) but not printed; held copy appears to end at r.41 (forms annex absent).", ""),
    ("DPPR53-C7", "DPP Rules 1953 (6 pp.)", None, "text layer", "NONE", "INSPECTED_WITH_GAPS",
     "Schedules I-II referenced (rr.9, 29, 33) but not printed in this copy.", ""),
    ("DPPA50-C7", "DPP Act 1950", None, "text layer heading scan", "NONE", "INSPECTED_NO_FORMS_FOUND", "", ""),
    ("RAF2000-C7", "Regulations for the Air Force (reprint 2000)", None, "text layer heading scan only", "NONE", "PARTIAL",
     "NOT_ASSESSED for forms: Air Force forms outside the Army-first scope of this cycle; access marking reported by C5 must be checked before any reuse.", ""),
]

NOT_HELD = [
    ("C5-SRC-P0-RA-1987", "Regulations for the Army (Revised Edition) 1987 - complete (appendices/forms)", "NOT_HELD_LEAD_ONLY (C5); restriction suspected"),
    ("C5-SRC-P0-DSR-VOLS-SCRIBD", "Defence Service Regulations vols (Army)", "NOT_HELD_RESTRICTED_SUSPECTED (C5)"),
    ("C5-SRC-P0-RA-1962", "Regulations for the Army 1962", "NOT_HELD_NOT_FOUND_IN_SEARCHED_SOURCES (C5)"),
    ("C5-SRC-P0-ARMY-ORDERS-INSTRUCTIONS", "Army Orders / Army Instructions / SAOs (administrative formats)", "NOT_HELD_NOT_FOUND_IN_SEARCHED_SOURCES (C5); generally internal - out of public scope"),
    ("C5-AMD-AR-003", "S.R.O. 348 of 1960 (App. I Forms I, II)", "LOCATED_UNVERIFIED, not held (C5 amendment register)"),
    ("C5-AMD-AR-005", "S.R.O. 404 of 1960 (App. IV Pt II Forms A, E, F; App. V Form J)", "LOCATED_UNVERIFIED, not held (C5 amendment register)"),
    ("C5-AMD-AR-043", "S.R.O. 66 of 1969 (hint: App. I Form II)", "HINT_ONLY (C5)"),
    ("C5-AMD-AR-030", "S.R.O. 258 of 2002 (possible r.22 Explanation)", "GAP (C5)"),
    ("C5-AMD-AR-036", "Army Rules amendments after 06-06-2022", "GAP (C5)"),
    ("C5-SRC-P2-ARMY-RULES-1950-INTERIM", "Interim rules under AA 1950 (pre-1954)", "NOT_HELD_CANDIDATE_LOCATED (C5)"),
    ("IAFK-1162", "Current Appendix I enrolment form (per MML 2: not reproduced)", "No held copy"),
    ("C5-SRC-P1-TA-RULES-1948", "Territorial Army Rules 1948 - official copy with schedules", "NOT_HELD_CANDIDATE_LOCATED (C5); only MML vol 3 transcription held"),
    ("C5-SRC-P1-TA-REGULATIONS", "Territorial Army Regulations (Revised Edition 1976)", "NOT_HELD_CANDIDATE_LOCATED (C5)"),
    ("C5-SRC-P1-DPP-ACT-1950", "DPP Rules 1953 official copy WITH Schedules I-II", "Rules text held without schedules (DPPR53-C7); schedules only in MML vol 3"),
    ("AFT-PRACTICE-2009-FORMS", "AFT Practice Rules 2009 Forms No. 1-9", "Referenced in held copy; forms not held"),
    ("C5-SRC-P1-CCCM-ADJ-RULES", "Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules", "NOT_HELD_NOT_CHECKED (C5)"),
    ("C5-SRC-P1-PRA-2008-PT1/PT2", "Pension Regulations for the Army 2008 (claim/application formats)", "NOT_HELD_CANDIDATE_LOCATED (C5)"),
    ("C5-SRC-P1-ER-GMO-2023", "Entitlement Rules / GMO 2023 official text (medical board formats)", "NOT_HELD_CANDIDATE_LOCATED (C5); an image-only 35-page copy (29f6fa2c) is held but not examined"),
    ("REFERENCED-IAF-FORMS", "Army forms referenced by number in held texts: " + "; ".join(r[0] for r in spec_forms.REFERENCED_NOT_HELD), "Layouts not printed in any held copy"),
    ("MML-AUTHENTICATED-EDITIONS", "Authenticated official printings of the Manual of Military Law (any edition)", "Not held; all 8 MML files UNVERIFIED_MANUAL (WS-C)"),
    # WSG-R07: Air Force and Navy rule-level instruments (Army-first cycle; nothing is asserted about their contents)
    ("AIR-FORCE-RULES-1969", "Air Force Rules, 1969 (rule-level instrument under the Air Force Act 1950; name as given in review WSG-R07)", "NOT_HELD; not located in C5 registers or c7 git; not searched for this cycle", "OUT_OF_SCOPE_THIS_CYCLE (Air Force)"),
    ("AIR-FORCE-ACT-1950-OTHER-INSTRUMENTS", "Other rule-level instruments under the Air Force Act 1950", "NOT_IDENTIFIED / NOT_HELD; not assessed", "OUT_OF_SCOPE_THIS_CYCLE (Air Force)"),
    ("C5-SRC-P2-PEN-REGS-AF-NAVY", "Pension Regulations for the Air Force Parts I and II (1960) and Navy (Pension) Regulations 1964 - official copies", "NOT_HELD_CANDIDATE_LOCATED (C5); c7 holds a derived text of the Navy Pension Regulations 1964 only (heading-scan row)", "OUT_OF_SCOPE_THIS_CYCLE (Air Force/Navy)"),
    ("C5-SRC-P2-RNAVY-PT1/PT2/PT3", "Regulations for the Navy Part I, Part II (Discipline and Miscellaneous) and Part III - official copies", "NOT_HELD_CANDIDATE_LOCATED (C5); c7 holds derived texts only (heading-scan rows); raw files not examined here", "OUT_OF_SCOPE_THIS_CYCLE (Navy)"),
    ("C5-SRC-P2-INAS-1973", "Indian Naval Auxiliary Service Regulations 1973", "NOT_HELD_CANDIDATE_LOCATED (C5)", "OUT_OF_SCOPE_THIS_CYCLE (Navy)"),
    ("C5-SRC-P2-RNAVY-AMDT-2022-2024", "Naval Ceremonial, Conditions of Service and Miscellaneous (Amendment) Regulations 2022 and 2024", "NOT_HELD_CANDIDATE_LOCATED (C5)", "OUT_OF_SCOPE_THIS_CYCLE (Navy)"),
    ("NAVY-ACT-1957-OTHER-INSTRUMENTS", "Other rule-level instruments under the Navy Act 1957", "NOT_IDENTIFIED / NOT_HELD; not assessed", "OUT_OF_SCOPE_THIS_CYCLE (Navy)"),
]
OUT_OF_SCOPE_KEYS = {
    "RAF2000-C7": "OUT_OF_SCOPE_THIS_CYCLE (Air Force)",
    "C7TEXT:act-air-force-1950.txt": "OUT_OF_SCOPE_THIS_CYCLE (Air Force)",
    "C7TEXT:act-navy-1957.txt": "OUT_OF_SCOPE_THIS_CYCLE (Navy)",
    "C7TEXT:regs-regulations-for-the-navy-part-i.txt": "OUT_OF_SCOPE_THIS_CYCLE (Navy)",
    "C7TEXT:regs-regulations-for-the-navy-part-ii.txt": "OUT_OF_SCOPE_THIS_CYCLE (Navy)",
    "C7TEXT:regs-regulations-for-the-navy-part-iii.txt": "OUT_OF_SCOPE_THIS_CYCLE (Navy)",
    "C7TEXT:regs-regulations-for-the-navy-part-iv.txt": "OUT_OF_SCOPE_THIS_CYCLE (Navy)",
    "C7TEXT:regs-the-navy-pension-regulations-1964.txt": "OUT_OF_SCOPE_THIS_CYCLE (Navy)",
    "C7TEXT:act-bnss-2023-sched-the-second-schedule.txt": "OUT_OF_SCOPE_THIS_CYCLE (general criminal procedure forms)",
    "C7TEXT:act-crpc-1973-consolidated.txt": "OUT_OF_SCOPE_THIS_CYCLE (general criminal procedure forms; historical)",
}


def coverage(st, occ_index, unreg):
    rows = []
    n = 0
    for (key, label, rng, method, visual, state, gaps, notes) in SEGMENTS:
        assert state in COVERAGE_STATES, state
        rec = st.load(key)
        spec = rec["spec"]
        if spec["kind"] == "pdf":
            total = rec["page_count"]
            a, b = rng if rng else (1, total)
            count = "%d pages" % total
            rtxt = "pp.%d-%d" % (a, b)
            found = [(c, s, e) for (_f, c, src, s, e, lt) in occ_index if src == key and s <= b and e >= a]
            hits = [h for h in unreg.get(key, []) if a <= h[0] <= b]
        else:
            total = rec["line_count"]
            a, b = 1, total
            count = "%d lines (derived text)" % total
            rtxt = "L1-L%d" % total
            found = [(c, s, e) for (_f, c, src, s, e, lt) in occ_index if src == key]
            hits = []
        n += 1
        cand = sorted(set(c for c, _s, _e in found))
        if state == "INSPECTED_NO_FORMS_FOUND" and cand:
            raise SystemExit("coverage state contradiction for %s %s" % (key, label))
        hit_txt = "%d" % len(hits)
        if hits:
            hit_txt += " (" + "; ".join("p.%d '%s'" % (p, t) for p, t in hits[:12]) + (" ..." if len(hits) > 12 else "") + ")"
        rows.append({
            "coverage_id": "COV-%02d" % n, "source_key": key, "source_logical_id": spec["c5_source_id"], "c5_copy_id": spec["c5_copy_id"],
            "source_copy_sha256": spec["sha256"], "holding": "HELD",
            "source_location": spec["path"] if spec["root"] == "scratch" else "git:c7@%s:%s" % (spec_sources.C7_COMMIT, spec["path"]),
            "evidence_class": spec["evidence_class"], "edition_evidence": spec["edition_evidence"], "access_marking": spec["access_marking"],
            "page_or_line_count": count, "segment_label": label, "expected_inspection_range": rtxt, "text_extracted_range": rtxt if spec["kind"] == "pdf" else rtxt,
            "pages_visually_inspected": visual, "pages_missing_unreadable_or_unexamined": gaps or "(none recorded)",
            "inspection_method": method, "inspection_date": RECORDED_ON, "coverage_state": state,
            "candidate_occurrences_found": len(cand), "candidate_ids": ";".join(cand), "unregistered_heading_hits": hit_txt,
            "excluded_ranges_and_reason": gaps if "xclud" in gaps else "", "notes": notes, "verification_status": VERIFICATION_STATUS,
        })
    # amendment copies from C5 register (appendix-mention scan), excluding those already segmented
    seg_keys = {spec_sources.SOURCES[k]["c5_copy_id"] for k, *_ in SEGMENTS}
    if os.path.exists(C5_REG):
        with open(C5_REG, newline="") as fh:
            regrows = [r for r in csv.DictReader(fh) if ("-AR-AMD-" in r["copy_id"] or "-AA-AMD-" in r["copy_id"]) and r["copy_id"] not in seg_keys]
        for r in sorted(regrows, key=lambda x: x["copy_id"]):
            path = r["held_paths"].split(";")[0]
            b = st.raw("scratch", os.path.join("downloads", path) if not path.startswith("downloads/") else path)
            sha_ok = sha256_bytes(b) == r["sha256"]
            import pymupdf
            doc = pymupdf.open(stream=b, filetype="pdf")
            texts = [doc[i].get_text() for i in range(len(doc))]
            chars = sum(len(t.strip()) for t in texts)
            app = [i + 1 for i, t in enumerate(texts) if re.search(r"(?i)appendix", t)]
            n += 1
            if chars < 50:
                state, note = "INACCESSIBLE", "No usable text layer (image-only); visual inspection not performed in this cycle."
            else:
                state = "INSPECTED_NO_FORMS_FOUND"
                note = "Text-layer scan for 'Appendix'/form amendments: " + ("mentions on pp.%s (rule-text references only)" % ",".join(map(str, app)) if app else "none")
            rows.append({
                "coverage_id": "COV-%02d" % n, "source_key": "C5:" + r["copy_id"], "source_logical_id": r["source_id"], "c5_copy_id": r["copy_id"],
                "source_copy_sha256": r["sha256"] + ("" if sha_ok else " (HASH MISMATCH)"), "holding": "HELD", "source_location": path,
                "evidence_class": r["copy_evidence_class"] or r["text_layer_class"], "edition_evidence": "per C5 register", "access_marking": "NOT_CHECKED",
                "page_or_line_count": "%d pages" % len(doc), "segment_label": "Amending instrument (whole)", "expected_inspection_range": "pp.1-%d" % len(doc),
                "text_extracted_range": "pp.1-%d" % len(doc), "pages_visually_inspected": "NONE", "pages_missing_unreadable_or_unexamined": "(none recorded)" if chars >= 50 else "all pages (no text layer)",
                "inspection_method": "pymupdf text layer scan for Appendix/Form amendments", "inspection_date": RECORDED_ON, "coverage_state": state,
                "candidate_occurrences_found": 0, "candidate_ids": "", "unregistered_heading_hits": "", "excluded_ranges_and_reason": "",
                "notes": note, "verification_status": VERIFICATION_STATUS,
            })
    # c7 derived texts: heading scan only
    for path, title in spec_sources.GITTEXT_SCANS:
        txt = st.raw("c7git", path).decode("utf-8", "replace")
        hits = [l.strip() for l in txt.splitlines() if HEADING_RE.match(l)]
        n += 1
        rows.append({
            "coverage_id": "COV-%02d" % n, "source_key": "C7TEXT:" + os.path.basename(path), "source_logical_id": "(c7 derived text)", "c5_copy_id": "",
            "source_copy_sha256": sha256_bytes(txt.encode("utf-8")), "holding": "HELD (derived text in c7 git)", "source_location": "git:c7@%s:%s" % (spec_sources.C7_COMMIT, path),
            "evidence_class": "pipeline-derived text (not a source copy; raw PDF not examined here)", "edition_evidence": title, "access_marking": "NOT_CHECKED",
            "page_or_line_count": "%d lines" % len(txt.splitlines()), "segment_label": title, "expected_inspection_range": "whole text",
            "text_extracted_range": "whole text", "pages_visually_inspected": "NONE", "pages_missing_unreadable_or_unexamined": "Not itemised this cycle",
            "inspection_method": "heading-pattern scan of derived text only", "inspection_date": RECORDED_ON,
            "coverage_state": "PARTIAL" if hits else "INSPECTED_NO_FORMS_FOUND",
            "candidate_occurrences_found": 0, "candidate_ids": "", "unregistered_heading_hits": "%d" % len(hits), "excluded_ranges_and_reason": "",
            "notes": ("Form-like headings present; NOT itemised (outside Army-first scope of this cycle)" if hits else "No form-like headings found by scan"),
            "verification_status": VERIFICATION_STATUS,
        })
    for nh in NOT_HELD:
        sid, title, why = nh[:3]
        n += 1
        rows.append({
            "coverage_id": "COV-%02d" % n, "source_key": "NOT_HELD:" + sid, "source_logical_id": sid, "c5_copy_id": "", "source_copy_sha256": "",
            "holding": "NOT_HELD", "source_location": "", "evidence_class": why, "edition_evidence": "", "access_marking": "",
            "page_or_line_count": "", "segment_label": title, "expected_inspection_range": "UNKNOWN (not held)", "text_extracted_range": "",
            "pages_visually_inspected": "", "pages_missing_unreadable_or_unexamined": "entire source (not held)", "inspection_method": "",
            "inspection_date": RECORDED_ON, "coverage_state": "INACCESSIBLE", "candidate_occurrences_found": 0, "candidate_ids": "",
            "unregistered_heading_hits": "", "excluded_ranges_and_reason": "", "notes": "Known-needed source not held; no acquisition performed or authorised by this workstream.",
            "scope_this_cycle": nh[3] if len(nh) > 3 else "IN_SCOPE (Army-first cycle)",
            "verification_status": VERIFICATION_STATUS,
        })
    # ---- WSG-R06: a negative resting only on a heading/text-layer scan is not a visually confirmed negative
    for r in rows:
        r.setdefault("scope_this_cycle", OUT_OF_SCOPE_KEYS.get(r["source_key"], "IN_SCOPE (Army-first cycle)"))
        refs = []
        vis = r["pages_visually_inspected"]
        if r["coverage_state"] == "INSPECTED_NO_FORMS_FOUND" and (not vis or vis.startswith("NONE")):
            r["coverage_state"] = "PARTIAL"
            r["coverage_method_limitation"] = ("HEADING_SCAN_NO_FORMS_FOUND_NOT_VISUALLY_CONFIRMED" if "heading" in r["inspection_method"].lower()
                                               else "TEXT_LAYER_SCAN_NO_FORMS_FOUND_NOT_VISUALLY_CONFIRMED")
            refs.append("WSG-R06")
        elif r["coverage_state"] == "INSPECTED_NO_FORMS_FOUND":
            r["coverage_method_limitation"] = "VISUALLY_CONFIRMED_NO_FORMS (pages %s)" % vis
            refs.append("WSG-R06")
        else:
            r["coverage_method_limitation"] = ""
        if r["scope_this_cycle"].startswith("OUT_OF_SCOPE"):
            refs.append("WSG-R07")
        if r["source_key"] in ("AFTPR08-C7", "AR54-GAZ") and r["pages_visually_inspected"] not in ("NONE", ""):
            refs.append("WSG-R01" if r["source_key"] == "AFTPR08-C7" else "WSG-R04")
        r["reviewer_evidence"] = ("review_wsg_forms.md / review_wsg_forms_findings.csv (2026-11-24): " + ";".join(sorted(set(refs)))) if refs else ""
        r["review_remediation_state"] = "REMEDIATED_C12_PENDING_RE_REVIEW" if refs else ""
        r["legal_review_ref"] = ""
    return rows


# ------------------------------------------------------------------ serialisation
def to_csv(rows, cols):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue()


RECLASSIFIED = [  # WSG-R02 / R09 / R12: README 'shall' rule applied mechanically to every STATUTORY_PRESCRIBED candidate
    {"family": "FF-AR54-APPV-FH", "from": "STATUTORY_PRESCRIBED / MANDATORY_FORM_WORDING", "to": "OTHER_OR_UNDETERMINED / PERMISSIVE_USE_SPECIFIC_RULE", "basis": "AR 169 'may, if he thinks fit, by a warrant in one of the forms in Appendix V' (no 'shall')", "finding": "WSG-R02"},
    {"family": "FF-AFTPR08-F2", "from": "STATUTORY_PRESCRIBED / PERMISSIVE_ATTACHMENT_FORM_PRESCRIBED", "to": "OTHER_OR_UNDETERMINED / PERMISSIVE_ATTACHMENT_FORM_PRESCRIBED", "basis": "r.4(4) 'may attach ... a receipt slip in Form II which shall be signed' ('shall' governs signature, not use of the form)", "finding": "WSG-R02"},
    {"family": "FF-DPPR53-S2", "from": "STATUTORY_PRESCRIBED / MANDATORY_DOCUMENT_LIST", "to": "OTHER_OR_UNDETERMINED / MANDATORY_DOCUMENT_LIST", "basis": "r.33(3) prescribes accompanying documents, not form wording", "finding": "WSG-R12"},
    {"family": "FF-AR54-APPIII-SGCM", "from": "OTHER_OR_UNDETERMINED / PERMISSIVE_USE_AR4", "to": "OTHER_OR_UNDETERMINED / PERMISSIVE_USE_SPECIFIC_RULE", "basis": "AR 151(1) 'may be convened ... in accordance with the form in Appendix III'", "finding": "WSG-R09"},
]


def summary(res):
    reg, fields, cov = res["reg"], res["fields"], res["cov"]
    fams = sorted({r["form_family_id"] for r in reg})
    prim = [r for r in reg if r["occurrence_role"] == "PRIMARY"]

    def count(rows, key):
        out = {}
        for r in rows:
            out[r[key]] = out.get(r[key], 0) + 1
        return dict(sorted(out.items()))

    st = res["store"]
    inputs = {k: {"sha256": v["spec"]["sha256"], "bytes": v["bytes"], "location": v["spec"]["path"], "root": v["spec"]["root"]}
              for k, v in sorted(st.cache.items())}
    s = {
        "workstream": "C12-CONSOLIDATION / Workstream G - forms registry",
        "tool_version": TOOL_VERSION, "recorded_on": RECORDED_ON, "pymupdf_version": st.pymupdf_version,
        "python_version": "%d.%d.%d" % sys.version_info[:3],
        "scope_statement": SCOPE_STATEMENT,
        "register_definition": "docs/product/FORM_DISCOVERY_AND_COVERAGE_REGISTER.md and ADR-0003 @ origin/docs/mimamsa-product-blueprint-2026-11-24",
        "verification_status_all_rows": VERIFICATION_STATUS,
        "legal_disclaimer": "No form, field or classification here is legally approved, verified as current, or fit for issue. Classifications are candidates only.",
        "counts": {
            "unique_form_families": len(fams), "occurrences_total": len(reg), "occurrences_primary": len(prim),
            "occurrences_alternate": len(reg) - len(prim), "fields_recorded": len(fields),
            "families_by_instrument": count(prim, "instrument"), "families_by_authority_type_candidate": count(prim, "form_authority_type_candidate"),
            "families_by_status_category": count(prim, "status_category"), "occurrences_by_source": count(reg, "source_key"),
            "occurrence_anchor_match": count(reg, "anchor_match"),
            "fields_primary_match": count(fields, "primary_match"),
            "fidelity_state_by_occurrence": count(reg, "fidelity_state"),
            "coverage_rows": len(cov), "coverage_state": count(cov, "coverage_state"),
            "coverage_not_held_rows": sum(1 for r in cov if r["holding"] == "NOT_HELD"),
            "families_by_source_basis": count(prim, "source_basis"),
            "families_by_official_copy_extent": count(prim, "official_copy_extent"),
            "families_by_statutory_confirmation_status": count(prim, "statutory_confirmation_status"),
            "statutory_prescribed_mml_only_not_confirmed": sorted(r["form_family_id"] for r in prim if r["statutory_confirmation_status"].startswith("NOT_CONFIRMED")),
            "families_field_list_mml_version_with_official_copy_held": sorted(r["form_family_id"] for r in prim if r["field_set_version"].startswith("MML_VERSION")),
            "fields_generic_label": sum(1 for f in fields if f["generic_label"] == "YES"),
            "fields_official_copy_presence": count([{"k": f["official_copy_presence"].split(" (")[0].split(";")[0]} for f in fields], "k"),
            "coverage_method_limitation": count(cov, "coverage_method_limitation"),
            "coverage_scope_this_cycle": count(cov, "scope_this_cycle"),
            "doc_locator_end_basis": count([r for r in reg if r["locator_type"] == "DOC_DERIVED_LINE"], "locator_end_basis"),
            "visual_checks_recorded": len(spec_forms.VISUAL_CHECKS),
        },
        "reclassified_in_remediation": RECLASSIFIED,
        "unregistered_heading_hits_by_source": {k: len(v) for k, v in sorted(res["unreg"].items())},
        "referenced_forms_not_printed_in_any_held_copy": [{"form": a, "description": b, "where_referenced": c} for a, b, c in spec_forms.REFERENCED_NOT_HELD],
        "conflict_queue": sorted(r["form_family_id"] + ": " + r["outstanding_uncertainties"].split(" Interaction between any specific rule")[0]
                                 for r in prim if "CONFLICT_QUEUE" in r["outstanding_uncertainties"] or "CONFLICT_QUEUE" in r["supersession_status"]),
        "field_divergence_queue": [f["field_id"] + " '" + f["field_label_as_printed"] + "': " + f["official_copy_presence"]
                                   for f in fields if "DIVERGENCE_QUEUE" in f["official_copy_presence"]],
        "inputs": inputs,
        "denominator_note": "No aggregate coverage percentage is computed: denominators of unknown/not-held sources are unknown (register s.3).",
    }
    return json.dumps(s, indent=1, sort_keys=False, ensure_ascii=False) + "\n"


def render(res):
    reg = sorted(res["reg"], key=lambda r: (r["form_family_id"], r["occurrence_role"] != "PRIMARY", r["candidate_id"]))
    fields = sorted(res["fields"], key=lambda r: r["field_id"])
    return {
        "FORM_DISCOVERY_REGISTER.csv": to_csv(reg, REG_COLS),
        "FORM_FIELDS.csv": to_csv(fields, FIELD_COLS),
        "SOURCE_COVERAGE.csv": to_csv(res["cov"], COV_COLS),
        "SUMMARY.json": summary(res),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="rebuild in memory and compare to outputs/ byte-for-byte")
    ap.add_argument("--scratch", default=os.environ.get("FR_SCRATCH", DEFAULT_SCRATCH))
    ap.add_argument("--c7", default=os.environ.get("FR_C7", DEFAULT_C7))
    ap.add_argument("--out", default=os.path.join(WS_ROOT, "outputs"))
    a = ap.parse_args(argv)
    res = build(a.scratch, a.c7)
    if res["errors"]:
        for e in res["errors"]:
            print("ERROR:", e, file=sys.stderr)
        return 2
    files = render(res)
    if a.check:
        bad = []
        for name, content in files.items():
            p = os.path.join(a.out, name)
            if not os.path.exists(p) or open(p, encoding="utf-8").read() != content:
                bad.append(name)
        if bad:
            print("CHECK FAILED: drift in %s" % ", ".join(bad), file=sys.stderr)
            return 1
        print("CHECK OK: %d files reproduce byte-for-byte" % len(files))
        return 0
    os.makedirs(a.out, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(a.out, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
    print("wrote %s" % ", ".join(sorted(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
