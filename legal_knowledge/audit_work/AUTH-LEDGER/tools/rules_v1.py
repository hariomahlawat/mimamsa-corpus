"""Copy-status rule, version 1 (an independent reimplementation; the frozen Cycle 4 module is not imported here).

For every held sha256 it returns the same status as CALIBRATION-02/tools/evidence_classification.py Evidence.source_status
on the frozen baseline (a test proves equality for every held sha256). It adds one controlled extension that the
baseline never exercises: a register row with a NON_PRIMARY_* class and PROVENANCE_DOCUMENTED maps to
DOCUMENTED_NON_PRIMARY, which is never EFFECTIVE_PRIMARY and so can never yield an exact anchor. Any other unknown class
on a documented row is an error (fail closed), not a silent "incomplete row"."""
import re

RULE_VERSION = 1
EFFECTIVE_PRIMARY = "EFFECTIVE_PRIMARY_VERIFIED"
PENDING = "AUTHENTICATION_PENDING"
UNKNOWN = "PROVENANCE_UNKNOWN"
DERIVED = "NOT_PRIMARY_DERIVED_TEXT"
MIRROR = "NOT_PRIMARY_MIRROR_OR_SECONDARY"
NOTHELD = "SOURCE_NOT_HELD_IN_INDEX"
DOC_NON_PRIMARY = "DOCUMENTED_NON_PRIMARY"
PRIMARY_EXT = (".pdf", ".doc", ".docx")
DERIVED_EXT = (".txt", ".json", ".html", ".htm", ".md")
PRIMARY_CLASSES = ("PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE", "PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN", "PRIMARY_OFFICIAL_COURT_COPY")
NON_PRIMARY_CLASSES = ("NON_PRIMARY_OFFICIAL_PUBLICATION_COPY", "NON_PRIMARY_OFFICIAL_COURT_RENDITION", "NON_PRIMARY_PARLIAMENTARY_RECORD")
COPY_CLASS = {EFFECTIVE_PRIMARY: "DOCUMENTED_PRIMARY_COPY", PENDING: "AUTHENTICATION_PENDING_COPY", UNKNOWN: "PROVENANCE_UNDOCUMENTED_COPY",
              DERIVED: "DERIVED_TEXT_ONLY", MIRROR: "MIRROR_OR_SECONDARY_COPY", DOC_NON_PRIMARY: "DOCUMENTED_NON_PRIMARY_COPY"}


class RuleError(Exception):
    pass


def _secondary(p):
    return "/secondary/" in "/" + p.lower()


def copy_status(sha, held_paths, reg):
    """(status, detail). held_paths: list of held relative paths for sha; reg: effective register row or None."""
    if not re.fullmatch(r"[0-9a-f]{64}", sha or ""):
        return NOTHELD, "sha256 missing or malformed"
    paths = held_paths or []
    if not paths:
        return NOTHELD, "sha256 not in the held-source index"
    if reg:
        cls_, st = reg.get("effective_source_class", ""), reg.get("authentication_state", "")
        if st == PENDING or cls_ == PENDING:
            return PENDING, f"authentication register: {st}"
        if cls_.startswith(("MIRROR", "SECONDARY")):
            return MIRROR, f"authentication register class {cls_}"
        if st == "PROVENANCE_DOCUMENTED" and cls_.startswith("PRIMARY_"):
            if cls_ not in PRIMARY_CLASSES:
                raise RuleError(f"{sha[:12]}: unsupported primary class {cls_}")
            if all(p.lower().endswith(DERIVED_EXT) for p in paths):
                return DERIVED, "only derived text of the source is held (register row notwithstanding)"
            if not any(p.lower().endswith(PRIMARY_EXT) for p in paths):
                return UNKNOWN, "no held pdf/doc for a register-documented source"
            if not reg.get("provenance_references", "").strip():
                return UNKNOWN, "authentication register row has no provenance_references"
            rp = {x.strip() for x in reg.get("held_paths", "").split(";") if x.strip()}
            if not rp:
                return UNKNOWN, "authentication register row has no held_paths"
            if rp != set(paths):
                return UNKNOWN, "authentication register held_paths differ from the held index"
            if any(_secondary(p) for p in paths):
                return PENDING, "documented provenance but the same bytes are also held under a secondary path"
            return EFFECTIVE_PRIMARY, f"authentication register: {cls_}"
        if st == "PROVENANCE_DOCUMENTED" and cls_.startswith("NON_PRIMARY_"):
            if cls_ not in NON_PRIMARY_CLASSES:
                raise RuleError(f"{sha[:12]}: unsupported non-primary class {cls_}")
            return DOC_NON_PRIMARY, f"documented non-primary copy: {cls_}"
        return UNKNOWN, f"authentication register row incomplete ({st}/{cls_})"
    prim = [p for p in paths if p.lower().endswith(PRIMARY_EXT) and not _secondary(p)]
    sec = [p for p in paths if _secondary(p)]
    if prim and sec:
        return PENDING, "same bytes held under official-claimed and secondary paths; no provenance record"
    if prim:
        return UNKNOWN, "held pdf/doc without a source-authentication register row"
    if sec:
        return MIRROR, "held only under secondary paths"
    if all(p.lower().endswith(DERIVED_EXT) for p in paths):
        return DERIVED, "only derived text of the source is held"
    return UNKNOWN, "held file type does not establish a primary source"
