#!/usr/bin/env python3
"""Provenance controls over audit registers (CSV) and audit JSON (stdlib only; structural, not legal).

Rules are keyed on column-name conventions used across PILOT-01, R23-VERIFY-01, ACQ-02,
ARMY-RULES-CHAIN-01, SOURCE-CONFLICTS-01 and WS-A/B/C registers, so new registers are covered
automatically when they reuse a convention:

  IMG-1  page-image register rows (page_image_checks*.csv, identity_transcription_register*.csv) carry a
         64-hex render_png_sha256.
  IMG-2  a row whose evidence_level starts IMAGE_CHECKED carries render evidence: a 64-hex render hash in
         the row, or a check id (PIC-n / WSA-PIC-n / WSB-PIC-n / WSC-PIC-n) that resolves to a page-image
         register row with a 64-hex render hash.
         Render evidence also resolves (a) through the row's document SHA-256 when another register row or
         an audit source JSON pairs that document hash with a render hash or check id, and (b) through
         foreign keys (instrument_id / instrument_ref / register_link -> instr_id, check_id, ...).
  IMG-3  status LOCATED_IMAGE_CHECKED, wording_read_from PAGE_IMAGE, or copy_fidelity PAGE_IMAGE_CHECKED
         require the same render evidence.
  RV-1   REQUIRES_VERIFICATION / text-layer / hint / locator-only evidence never coexists in the same row
         with an image-checked or verified claim (evidence_level IMAGE_CHECKED, copy_fidelity
         PAGE_IMAGE_CHECKED/CUSTODIAN_AUTHENTICATED, status exactly LOCATED or LOCATED_IMAGE_CHECKED).
  CA-1   document_authority / carrier_provenance / copy_fidelity / amendment_chain_status values (first
         token) are in the policy v1 enumerations (or n/a / blank); copy_fidelity is not an authenticity value.
  CA-2   no self-contradictory carrier/authority pair (USER_SUPPLIED + CUSTODIAN_AUTHENTICATED;
         UNVERIFIED_MANUAL/GOVERNMENT_ISSUED_MANUAL on a judicial or enacted carrier row is left to the validator).
  ACQ-1  acquisition-request rows (files with request_id or queue_id) are never marked fetched/downloaded/
         executed without an approval reference (approval_ref / approval_reference / approved_by column with
         a PR/issue/approval identifier).
  APR-1  no legal-advisor / JAG approval state in any state-like CSV column or JSON key (status, state,
         decision, determination, review, approval, clearance), unless negated or pending. Text inside
         quotation marks (quoted statute/manual wording) is ignored; only explicit state tokens
         (APPROVED, ADVISOR_APPROVED, JAG_APPROVED/VALIDATED, LEGAL_APPROVAL, ACCEPTED_FOR_CANDIDATE ...)
         or explicit phrases ("approved by JAG", "legally approved") count. See approval_claims().

Known violations in frozen or not-yet-integrated registers are pinned in provenance_baseline.json; any
violation not in the baseline fails (exit 1). Baseline entries that no longer occur are reported.
Usage: python3 tools/legal_audit/check_provenance.py [ROOT_DIR ...] [--baseline FILE] [--no-baseline]
"""
from __future__ import annotations
import argparse, csv, io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / "legal_knowledge" / "audit_work"
BASELINE = Path(__file__).resolve().parent / "provenance_baseline.json"
HEX = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
CHECK_ID = re.compile(r"\b(?:WS[ABC]-)?PIC-\d+\b")
RENDER_COLS = ("render_png_sha256", "render_sha256", "page_render_sha256")
DOC_SHA_COLS = ("sha256", "file_sha256", "document_sha256", "copy_sha256")
ID_COLS = ("instr_id", "check_id", "chain_id", "change_id", "supp_id")
FK_COLS = ("instrument_id", "instrument_ref", "register_link")
ENUMS = {
    "document_authority": {"ENACTED_OR_NOTIFIED_PRIMARY", "OFFICIAL_JUDICIAL_DECISION", "GOVERNMENT_COMPILATION",
                           "GOVERNMENT_ISSUED_MANUAL", "UNVERIFIED_MANUAL", "THIRD_PARTY_COMMENTARY", "UNKNOWN"},
    "carrier_provenance": {"ISSUING_AUTHORITY", "GOVERNMENT_HOSTED_COPY", "THIRD_PARTY_ARCHIVAL_FACSIMILE",
                           "USER_SUPPLIED", "THIRD_PARTY_TRANSCRIPTION", "UNKNOWN"},
    "copy_fidelity": {"NOT_CHECKED", "HASH_ONLY", "PAGE_IMAGE_CHECKED", "CUSTODIAN_AUTHENTICATED"},
    "amendment_chain_status": {"NOT_CHECKED", "PARTIAL", "CHECKED_FOR_RELEVANT_PERIOD", "NOT_APPLICABLE"},
}
NA = {"", "n/a", "N/A", "NA", "-"}
WEAK_EVIDENCE = re.compile(r"^(REQUIRES_VERIFICATION|TEXT_LAYER|HINT|LOCATOR_TEXT_ONLY|TEXT_ONLY|COMPILATION_ONLY)")
STATE_COL = re.compile(r"(status|state|decision|determination|review|approval|clearance)", re.I)
# Approval detection (shared with tests/test_legal_audit_register_semantics.py via approval_claims()).
# (1) Quoted text is removed first: a register may quote statute or manual wording such as
#     'any person approved of by the Judge Advocate General'; quoted source text is never a state.
# (2) Only explicit review/approval STATE tokens (case-sensitive, upper-case/underscore style) or explicit
#     approval phrases naming a legal authority count; the bare English word "approved" does not.
QUOTED = re.compile(r"\u201c[^\u201d]*\u201d|\u2018[^\u2019]*\u2019|\"[^\"]*\"|(?<![A-Za-z0-9])'[^']*'(?![A-Za-z0-9])")
STATE_TOKEN = re.compile(r"(?<![A-Za-z_])((?:ADVISOR|JAG|LEGAL|LEGALLY|FORMALLY|OPERATIONALLY)[ _-]?"
                         r"(?:APPROVED|VALIDATED|CLEARED|ADJUDICATED|ACCEPTED|VERIFIED)|LEGAL[ _]APPROVAL|"
                         r"ACCEPTED_FOR_CANDIDATE|APPROVED|ADJUDICATED)(?![A-Za-z_])")
APPROVAL_PHRASE = re.compile(r"\b(?:JAG|Judge Advocate General|legal[ _-]advis[eo]r|advis[eo]r|legal|legally|formally|operationally)"
                             r"[ _-]+(?:has[ ]+|have[ ]+)?(?:approved|validated|cleared|adjudicated|verified|accepted)\b|"
                             r"\bapproved[ ]+by[ ]+(?:the[ ]+)?(?:JAG|Judge Advocate General|legal(?:[ ]+advis[eo]r)?|advis[eo]r|legal branch)\b", re.I)
NEGATION = re.compile(r"(UN|NOT[ _-]?|NO[ _-]|0 |NEVER[ _-]|LACKS? |WITHOUT )$", re.I)
PENDING_AFTER = re.compile(r"^[ _-]?(PENDING|REQUIRED|AWAITED|NOT[ _]YET)", re.I)


def approval_claims(text):
    """Explicit legal-advisor/JAG approval claims in a state value, ignoring quoted text and
    negated/pending forms ("unapproved", "NOT_APPROVED", "JAG_APPROVAL_PENDING", "approved pending")."""
    t = QUOTED.sub(" ", text or "")
    hits = []
    for rx in (STATE_TOKEN, APPROVAL_PHRASE):
        for m in rx.finditer(t):
            if NEGATION.search(t[max(0, m.start() - 8):m.start()]) or PENDING_AFTER.match(t[m.end():]):
                continue
            hits.append(m.group(0))
    return hits

FETCHED = re.compile(r"(?<![A-Za-z])(FETCHED|DOWNLOADED|ACQUIRED|EXECUTED|RETRIEVED|HELD)(?![A-Za-z])", re.I)
NOT_FETCHED = re.compile(r"\b(NOT|NO|UN)[ _-]?(YET[ _-])?(EXECUTED|FETCHED|DOWNLOADED|ACQUIRED)\b|\bPROPOSED\b|\bPENDING\b", re.I)
APPROVAL_REF_COL = re.compile(r"^(approval_ref|approval_reference|approved_by|approval|authorisation_ref|authorization_ref)$", re.I)
APPROVAL_REF = re.compile(r"(PR ?#\d+|#\d+|issue ?\d+|APPROVAL-[\w-]+|ACQ-\d+-APPROVAL|owner approval [\w-]+)", re.I)


def first(v):
    return re.split(r"[\s(;:]", (v or "").strip(), maxsplit=1)[0]


def read_csv(p: Path):
    try:
        return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"), newline="")))
    except (UnicodeDecodeError, csv.Error):
        return []


def row_key(row, cols):
    for k in ("check_id", "instr_id", "request_id", "queue_id", "row_id", "change_id", "chain_id", "supp_id", "intake_id",
              "provision", "target", "record_id", "conflict_id", "update_id", "gap_id", "cc_id", "item"):
        if k in cols and row.get(k):
            v = row[k]
            if k == "provision" and "version" in cols:
                v += "@" + row.get("version", "")
            if k == "provision" and "event" in cols:
                v += "@" + row.get("event", "")[:40]
            return f"{k}={v}"
    return None


def is_pic_register(p: Path):
    return p.name.startswith("page_image_checks") or p.name.startswith("identity_transcription_register")


def scan(dirs):
    files = sorted({p for d in dirs for p in Path(d).rglob("*.csv")})
    renders = {}
    tables = {}
    for p in files:
        rows = read_csv(p)
        tables[p] = rows
        if is_pic_register(p):
            for r in rows:
                cid = (r.get("check_id") or "").strip()
                if cid:
                    renders.setdefault(cid, False)
                    renders[cid] = renders[cid] or bool(HEX.fullmatch((r.get("render_png_sha256") or "").strip()[:64]))
    out = []

    def v(rule, p, r, cols, n, msg):
        rel = None
        for d in dirs:
            try:
                rel = str(p.relative_to(d)); break
            except ValueError:
                continue
        out.append({"rule": rule, "file": rel or str(p), "row": row_key(r, cols) or f"line={n}", "detail": msg})

    def direct_ok(r, cols):
        if any(HEX.search(r.get(c) or "") for c in RENDER_COLS if c in cols):
            return True
        ids = set()
        for c in cols:
            if c not in RENDER_COLS:
                ids |= set(CHECK_ID.findall(r.get(c) or ""))
        return any(renders.get(i) for i in ids)

    def doc_shas(r, cols):
        return {m for c in DOC_SHA_COLS if c in cols for m in HEX.findall(r.get(c) or "")}

    # document-hash index: documents for which some register row or audit source has a page render
    doc_render = set()
    for p, rows in tables.items():
        if rows:
            cols = list(rows[0])
            for r in rows:
                if direct_ok(r, cols):
                    doc_render |= doc_shas(r, cols)
    for d in dirs:
        for sp in Path(d).rglob("sources/*.json"):
            try:
                objs = json.loads(sp.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            for o in objs if isinstance(objs, list) else [objs]:
                if isinstance(o, dict) and HEX.fullmatch(o.get("sha256") or "") and (
                        o.get("render_sha256") or (re.search(r"render", o.get("pinpoint") or "", re.I) and HEX.search(o.get("pinpoint") or ""))
                        or any(renders.get(i) for i in CHECK_ID.findall(o.get("page_image_check_id") or ""))):
                    doc_render.add(o["sha256"])
    # foreign-key index
    by_id = {}
    for p, rows in tables.items():
        if rows:
            cols = list(rows[0])
            for r in rows:
                for c in ID_COLS:
                    if c in cols and r.get(c):
                        by_id.setdefault(r[c].strip(), []).append((r, cols))
    memo = {}

    def render_ok(r, cols, depth=0):
        key = id(r)
        if key in memo:
            return memo[key]
        ok = direct_ok(r, cols) or bool(doc_shas(r, cols) & doc_render)
        if not ok and depth < 3:
            for c in FK_COLS:
                for ref in re.findall(r"[A-Za-z0-9][\w.-]*", r.get(c) or "") if c in cols else []:
                    for rr, cc in by_id.get(ref, []):
                        if rr is not r and render_ok(rr, cc, depth + 1):
                            ok = True
        memo[key] = ok
        return ok

    for p, rows in tables.items():
        if not rows:
            continue
        cols = list(rows[0])
        for n, r in enumerate(rows, 2):
            ev = (r.get("evidence_level") or "").strip()
            st = (r.get("status") or "").strip()
            cf = first(r.get("copy_fidelity"))
            # IMG-1
            if is_pic_register(p) and "render_png_sha256" in cols and not HEX.fullmatch((r.get("render_png_sha256") or "").strip()[:64]):
                v("IMG-1", p, r, cols, n, f"render_png_sha256 = {r.get('render_png_sha256')!r}")
            # IMG-2 / IMG-3
            claims = []
            if ev.startswith("IMAGE_CHECKED"):
                claims.append("evidence_level IMAGE_CHECKED")
            if first(st) == "LOCATED_IMAGE_CHECKED":
                claims.append("status LOCATED_IMAGE_CHECKED")
            if first(r.get("wording_read_from")) == "PAGE_IMAGE":
                claims.append("wording_read_from PAGE_IMAGE")
            if cf == "PAGE_IMAGE_CHECKED" and not is_pic_register(p):
                claims.append("copy_fidelity PAGE_IMAGE_CHECKED")
            if claims and not is_pic_register(p) and not render_ok(r, cols):
                v("IMG-2" if claims[0].startswith("evidence") else "IMG-3", p, r, cols, n,
                  "; ".join(claims) + " without a 64-hex render hash or a resolvable check id")
            # RV-1
            weak = [c for c in cols if WEAK_EVIDENCE.match((r.get(c) or "").strip()) and c in ("evidence_level", "continuation_pages_status")]
            if weak:
                strong = []
                if ev.startswith("IMAGE_CHECKED"):
                    strong.append("evidence_level IMAGE_CHECKED")
                if cf in ("PAGE_IMAGE_CHECKED", "CUSTODIAN_AUTHENTICATED") and "evidence_level" in weak:
                    strong.append(f"copy_fidelity {cf}")
                if st in ("LOCATED", "LOCATED_IMAGE_CHECKED", "VERIFIED", "SOURCE_VERIFIED") and "evidence_level" in weak:
                    strong.append(f"status {st}")
                if strong:
                    v("RV-1", p, r, cols, n, f"{'/'.join(weak)} weak but {', '.join(strong)}")
            # CA-1 / CA-2
            for col, enum in ENUMS.items():
                for c in cols:
                    if c == col or c.endswith("_" + col):
                        val = (r.get(c) or "").strip()
                        if val in NA:
                            continue
                        if first(val) not in enum:
                            v("CA-1", p, r, cols, n, f"{c} = {val[:60]!r} not in policy v1 {col} values")
            if first(r.get("carrier_provenance")) == "USER_SUPPLIED" and cf == "CUSTODIAN_AUTHENTICATED":
                v("CA-2", p, r, cols, n, "USER_SUPPLIED copy claimed CUSTODIAN_AUTHENTICATED")
            # ACQ-1
            if "request_id" in cols or "queue_id" in cols:
                cells = [(c, r.get(c) or "") for c in cols if re.search(r"status|state|downloaded|fetched|action", c, re.I)]
                fetched = [c for c, val in cells
                           if (re.match(r"^(downloaded|fetched)", c, re.I) and first(val).upper() in ("YES", "TRUE", "Y"))
                           or (FETCHED.search(val) and not NOT_FETCHED.search(val) and not re.match(r"^(downloaded|fetched)", c, re.I))]
                if fetched:
                    refs = [r.get(c) or "" for c in cols if APPROVAL_REF_COL.match(c)]
                    if not any(APPROVAL_REF.search(x) for x in refs):
                        v("ACQ-1", p, r, cols, n, f"{'/'.join(fetched)} indicates fetched without an approval reference")
            # APR-1
            for c in cols:
                if not STATE_COL.search(c) or "NOT_legal_approval" in c:
                    continue
                val = r.get(c) or ""
                if approval_claims(val):
                    v("APR-1", p, r, cols, n, f"{c} = {val[:80]!r}")
    # APR-1 over JSON (state-like keys anywhere in the document)
    for d in dirs:
        for p in sorted(Path(d).rglob("*.json")):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            stack = [("", obj)]
            while stack:
                key, o = stack.pop()
                if isinstance(o, dict):
                    stack += [(k, x) for k, x in o.items()]
                elif isinstance(o, list):
                    stack += [(key, x) for x in o]
                elif isinstance(o, str) and STATE_COL.search(key) and not key.endswith(("_note", "_notes", "rationale")):
                    if approval_claims(o):
                        out.append({"rule": "APR-1", "file": str(p.relative_to(d)), "row": f"key={key}", "detail": o[:80]})
    return sorted(out, key=lambda x: (x["rule"], x["file"], x["row"], x["detail"])), files


def ident(x):
    return (x["rule"], x["file"], x["row"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*", type=Path)
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    ap.add_argument("--no-baseline", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    dirs = a.dirs or [DEFAULT_DIR]
    viol, files = scan(dirs)
    base = [] if a.no_baseline or not a.baseline.is_file() else json.loads(a.baseline.read_text(encoding="utf-8"))["known_violations"]
    known = {ident(b) for b in base}
    new = [x for x in viol if ident(x) not in known]
    seen = {ident(x) for x in viol}
    absent = [b for b in base if ident(b) not in seen]
    if a.json:
        print(json.dumps({"violations": viol, "new": new, "baseline_absent": absent}, indent=1))
    else:
        print(f"files={len(files)} violations={len(viol)} known={len(viol) - len(new)} new={len(new)} baseline_absent={len(absent)}")
        for x in new:
            print("NEW", x["rule"], x["file"], x["row"], "-", x["detail"])
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
