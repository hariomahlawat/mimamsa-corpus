"""CALIBRATION-02 shared evidence-classification rule (stdlib). Used by check_calibration02.py and reconcile.py.

A reviewer's evidence_state is the CLAIMED state and is never altered. This module derives a separate EFFECTIVE status
for downstream calculation from two registers:
- registers/held_sources_scratchpad.csv: which bytes are held (sha256 -> held paths);
- registers/source_authentication_register.csv: source-specific provenance for each file relied on as primary, with
  authentication_state (PROVENANCE_DOCUMENTED | AUTHENTICATION_PENDING) and effective_source_class.

A file extension, directory name or matching SHA-256 establishes neither legal authority nor authenticity. Only a
register row with documented, source-specific provenance makes held bytes effective primary evidence. Bytes held under
both an official-claimed and a secondary path, with no register row, are AUTHENTICATION_PENDING: an open question, not
a finding of inauthenticity.

Effective statuses for a finding whose claimed state is VERIFIED_AGAINST_HELD_PRIMARY_SOURCE:
  EFFECTIVE_PRIMARY_VERIFIED       register PROVENANCE_DOCUMENTED with a PRIMARY_* class, bytes held, locator given
  AUTHENTICATION_PENDING           register says pending, or bytes are held under both official-claimed and secondary paths
  PROVENANCE_UNKNOWN               held pdf/doc with no register row (not primary until documented)
  NOT_PRIMARY_DERIVED_TEXT         only derived text (.txt/.json/.html) of the bytes is held          [protocol error]
  NOT_PRIMARY_MIRROR_OR_SECONDARY  register class MIRROR/SECONDARY, or held only under secondary paths [protocol error]
  SOURCE_NOT_HELD_IN_INDEX         sha256 malformed or not in the held index                          [protocol error]
  HASH_MISMATCH                    a held file's bytes do not hash to the cited sha256 (when files are checked) [protocol error]
  HELD_FILE_MISSING                a held path is absent under the verification root (when files are checked)  [protocol error]
  PINPOINT_MISSING                 no locator                                                          [protocol error]
Findings with any other claimed state pass through unchanged as their effective status."""
import csv, hashlib, re
from pathlib import Path

VERIFIED = "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE"
EFFECTIVE_PRIMARY = "EFFECTIVE_PRIMARY_VERIFIED"
PENDING = "AUTHENTICATION_PENDING"
UNKNOWN = "PROVENANCE_UNKNOWN"
DERIVED = "NOT_PRIMARY_DERIVED_TEXT"
MIRROR = "NOT_PRIMARY_MIRROR_OR_SECONDARY"
NOTHELD = "SOURCE_NOT_HELD_IN_INDEX"
MISMATCH = "HASH_MISMATCH"
MISSING_FILE = "HELD_FILE_MISSING"
NOPIN = "PINPOINT_MISSING"
PROTOCOL_ERRORS = {DERIVED, MIRROR, NOTHELD, MISMATCH, NOPIN, MISSING_FILE}
NOT_EFFECTIVE_PRIMARY = {PENDING, UNKNOWN}
PRIMARY_EXT = (".pdf", ".doc", ".docx")
DERIVED_EXT = (".txt", ".json", ".html", ".htm", ".md")


def _secondary(p):
    return "/secondary/" in "/" + p.lower()


class Evidence:
    def __init__(self, held_rows, register_rows, root=None):
        self.held = {}
        for r in held_rows:
            self.held.setdefault(r["sha256"], []).append(r["scratchpad_relative_path"])
        self.register = {r["sha256"]: r for r in register_rows}
        self.root = Path(root) if root else None
        self._hash_cache = {}

    @classmethod
    def from_dir(cls, c2, root=None):
        c2 = Path(c2)
        def rows(n):
            p = c2 / "registers" / n
            return list(csv.DictReader(open(p, newline="", encoding="utf-8"))) if p.exists() else []
        return cls(rows("held_sources_scratchpad.csv"), rows("source_authentication_register.csv"), root)

    def _file_hash(self, rel):
        if rel not in self._hash_cache:
            p = self.root / rel
            self._hash_cache[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        return self._hash_cache[rel]

    def source_status(self, sha):
        """(status, detail) for held bytes, independent of any reviewer claim."""
        if not re.fullmatch(r"[0-9a-f]{64}", sha or ""):
            return NOTHELD, "sha256 missing or malformed"
        paths = self.held.get(sha)
        if not paths:
            return NOTHELD, "sha256 not in the held-source index"
        if self.root is not None:
            for p in paths:
                h = self._file_hash(p)
                if h is None:
                    return MISSING_FILE, f"{p} not found under the verification root"
                if h != sha:
                    return MISMATCH, f"{p} hashes to {h}, not {sha}"
        reg = self.register.get(sha)
        if reg:
            cls_, st = reg.get("effective_source_class", ""), reg.get("authentication_state", "")
            if st == PENDING or cls_ == PENDING:
                return PENDING, f"authentication register: {st}"
            if cls_.startswith(("MIRROR", "SECONDARY")):
                return MIRROR, f"authentication register class {cls_}"
            if st == "PROVENANCE_DOCUMENTED" and cls_.startswith("PRIMARY_"):
                # the file-type rule applies even when a register row exists: a register cannot make derived text primary
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

    def classify_finding(self, f):
        """(effective_status, detail) for one reviewer finding row; the claimed state is not modified."""
        if f.get("evidence_state") != VERIFIED:
            return f.get("evidence_state", ""), "reviewer state (not a primary-verification claim)"
        st, detail = self.source_status(f.get("source_sha256", ""))
        if st in (EFFECTIVE_PRIMARY, PENDING, UNKNOWN) and not f.get("locator", "").strip():
            return NOPIN, "no locator for a primary-verification claim"
        return st, detail

    def counts_as_primary(self, f):
        return self.classify_finding(f)[0] == EFFECTIVE_PRIMARY
