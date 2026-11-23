"""Evidence strength, identity, fidelity, association and contradiction checks for ledger entries (independent
reimplementation; no C6-01 code is imported). Every reference resolves by EXACT key in a designated key column.

FULL locator (the only strength an ADD/CORRECTION may rely on), from the entry's first_class_record_ref:
  RET  a PILOT-01 / R23-VERIFY-01 sources/*.json retrieval record whose OWN sha256 equals the key and whose locator has a URL,
       and which does not disclaim authenticity (authenticity UNCONFIRMED) or report NOT_FOUND / CONFLICTING
  COR  a PILOT-01 code-register row whose official_sha256 equals the key, with an official corroboration URL
  DL   a PILOT-01 discovery-register row whose downloaded_sha256 equals the key, with a URL (identifier-only -> IDENTIFIER_SHA, rejected)
  ARC  an ACQ-02 supplement row whose sha256 equals the key, with archive size, md5 and sha1 all OK
Anything else (snapshot entries, sha256 mentioned inside another record, md5-only rows) is not first-class."""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AW, PKG, LedgerError, read_csv  # noqa: E402
import urlcheck  # noqa: E402

URL = re.compile(r"https?://[^ ;),|]+")
# Allow-lists (Fable review F-02): a retrieval record is first-class only with an official or archival-facsimile
# authenticity value, and every first-class locator host must suit the class.
RET_AUTHENTICITY = {"OFFICIAL_COURT_ARCHIVE", "ORIGINAL_OFFICIAL", "ARCHIVAL_FACSIMILE_OF_OFFICIAL", "OFFICIAL_COMPILATION"}
COURT_HOSTS = ("sci.gov.in",)
# path shapes of every committed court locator (Fable F-06); a new shape needs a reviewed change here
COURT_PATH = re.compile(r"/(?:jonew/(?:judis|bosir/orderpdf)|judgment/judis)/\d+\.pdf|/supremecourt/\d{4}/\d+/[A-Za-z0-9_-]+\.pdf")
GOV_HOSTS = (".gov.in", ".nic.in")
ARCHIVE_HOSTS = ("archive.org",)
CLASS_HOSTS = {
    "PRIMARY_OFFICIAL_COURT_COPY": COURT_HOSTS, "NON_PRIMARY_OFFICIAL_COURT_RENDITION": COURT_HOSTS,
    "PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE": ARCHIVE_HOSTS, "PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN": GOV_HOSTS,
    "NON_PRIMARY_OFFICIAL_PUBLICATION_COPY": GOV_HOSTS + ARCHIVE_HOSTS, "NON_PRIMARY_PARLIAMENTARY_RECORD": GOV_HOSTS + ARCHIVE_HOSTS,
}


def class_path_problem(host, segs, cls, query=""):
    """'' when the strictly parsed locator's host and path suit the class, else the reason. Hosts: exact or dot-suffix
    match on the allow-list; archive.org only as the item host itself, for /download/<item>/<file...> or /details/<item>
    (never web.archive.org captures of other sites: re-review N-03)."""
    allowed = CLASS_HOSTS.get(cls)
    if allowed is None:
        return f"class {cls} has no locator host rule"
    if host == "archive.org" or host.endswith(".archive.org"):
        if "archive.org" not in allowed or host != "archive.org":
            return f"host {host} does not suit class {cls}"
        item = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
        ok = ((len(segs) >= 3 and segs[0] == "download" and item.fullmatch(segs[1]) and all(segs[2:]))
              or (len(segs) == 2 and segs[0] == "details" and item.fullmatch(segs[1])))
        if ok and not query:
            return ""
        if ok:
            return "archive.org locators carry no query (it would be ignored by the server: Fable F-03)"
        return "archive.org locator must be /download/<item>/<file> or /details/<item>"
    # exact host, or a sub-domain of a listed domain; a bare public suffix (gov.in, nic.in) is never a document host (F-06)
    if not any((not a.startswith(".") and (host == a or host.endswith("." + a))) or (a.startswith(".") and host.endswith(a))
               for a in allowed):
        return f"host {host} does not suit class {cls}"
    if not segs or segs[-1] == "":
        return "locator names a site root or a directory, not a document (no trailing '/')"
    if allowed is COURT_HOSTS and not COURT_PATH.fullmatch("/" + "/".join(segs)):
        return "court locator path is not a known Supreme Court document path (/jonew/..., /judgment/..., /supremecourt/<year>/<n>/...pdf)"
    return ""


def locator_problem(url, cls):
    """'' when the locator is strictly valid (urlcheck.parse: D-01) and suits the class, else the reason."""
    try:
        host, segs, query = urlcheck.parse(url)
    except ValueError as e:
        return str(e)
    return class_path_problem(host, segs, cls, query)


def host_ok(url, cls):
    return locator_problem(url, cls) == ""


CSV_KEYS = {  # path -> (key column, own-sha256 column)
    "PILOT-01/registers/source_code_resolution_v3.csv": ("code", "official_sha256"),
    "PILOT-01/registers/source_discovery_2026-11-22.csv": ("target_id", "downloaded_sha256"),
    "ACQ-02/supplement_inventory.csv": ("supp_id", "sha256"),
    "WS-B-JUDGMENTS/tools/held_copies.csv": ("spec_key", "sha256"),
    "R23-VERIFY-01/registers/amendment_search_2026-11-22.csv": ("target", "sha256"),
}
SNAPSHOTS = ("ACQ-01/archive_org_metadata_snapshot.json", "ACQ-02/archive_org_metadata_snapshot_acq02.json")
IDENTITY_KEYS = {  # path -> (key column, sha column)
    "ACQ-02/page_image_checks_acq02.csv": ("check_id", "document_sha256"),
    "WS-A-STATUTORY/identity_transcription_register.csv": ("check_id", "file_sha256"),
    "ARMY-RULES-CHAIN-01/page_image_checks_chain.csv": ("check_id", "document_sha256"),
    "R23-VERIFY-01/registers/page_image_checks.csv": ("check_id", "document_sha256"),
    "CALIBRATION-02/reviews/A/page_image_checks_A.csv": ("check_id", "document_sha256"),
    "CALIBRATION-02/reviews/C/page_image_checks_C.csv": ("check_id", "document_sha256"),
    "SOURCE-LIBRARY-C5/inputs/page_image_checks_c5.csv": ("check_id", "document_sha256"),
    "C6-01-PROVENANCE/inputs/page_image_checks_c6.csv": ("check_id", "document_sha256"),
}
_cache = {}


def _rows(rel):
    if rel not in _cache:
        p = AW / rel
        if not p.is_file():
            raise LedgerError(f"evidence file not found: {rel}")
        if rel.endswith(".json"):
            with open(p, encoding="utf-8") as f:
                _cache[rel] = json.load(f)
        else:
            _cache[rel] = read_csv(p)
    return _cache[rel]


def _split(ref):
    path, sep, key = ref.partition("#")
    if not sep or not key:
        raise LedgerError(f"reference without an exact row key: {ref!r}")
    return path.strip(), key.strip()


def _json_source(path):
    return re.fullmatch(r"(PILOT-01|R23-VERIFY-01)/sources/[A-Za-z0-9_.-]+\.json", path) is not None


def resolve(ref):
    """Return (path, record) for an exact reference, or raise. No substring or prefix matching."""
    path, key = _split(ref)
    if _json_source(path):
        hits = [o for o in _rows(path) if o.get("source_id") == key]
    elif path in CSV_KEYS:
        hits = [r for r in _rows(path) if r[CSV_KEYS[path][0]] == key]
    elif path in SNAPSHOTS:  # '<archive identifier>/<file name>', both parts exact
        ident, _, name = key.partition("/")
        item = _rows(path).get(ident)
        hits = [f for f in ((item or {}).get("pdf_files", []) + (item or {}).get("files", [])) if f.get("name") == name] if name else []
    elif path in IDENTITY_KEYS:
        hits = [r for r in _rows(path) if r[IDENTITY_KEYS[path][0]] == key]
    elif path == "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv":
        hits = [r for r in read_csv(AW / path) if r["instr_id"] == key]
    elif path == "AUTH-LEDGER/evidence/copy_facts.csv":
        hits = [r for r in read_csv(PKG / "evidence/copy_facts.csv") if r["copy_id"] == key]
    else:
        raise LedgerError(f"unsupported evidence file for exact resolution: {path}")
    if len(hits) != 1:
        raise LedgerError(f"reference {ref!r} resolves to {len(hits)} records (exactly one required)")
    return path, hits[0]


def disclaimed(o):
    return str(o.get("authenticity", "")).upper() == "UNCONFIRMED" or o.get("verification_state") in ("NOT_FOUND", "CONFLICTING")


def first_class(ref, sha, cls=None):
    """(kind, strength, url) for the entry's first-class record. Raises unless the record is first-class for THIS sha256
    and, when a class is given, its locator host suits the class."""
    kind, st, url = _first_class(ref, sha)
    why = locator_problem(url, cls) if cls is not None else ""
    if why:
        raise LedgerError(f"{ref}: locator {url!r} rejected for class {cls}: {why}")
    return kind, st, url


def _untruncated(ref, text, m):
    """The URL taken from free text must be the whole whitespace-delimited token, apart from trailing separator
    punctuation; otherwise the extraction would silently cut the recorded URL at ')', ',', ';' or '|' (Fable F-08)."""
    tok = re.match(r"\S+", text[m.start():]).group(0)
    if tok.rstrip(",;|)") != m.group(0):
        raise LedgerError(f"{ref}: recorded locator {tok!r} contains a separator character; the URL would be truncated")


def _first_class(ref, sha):
    path, rec = resolve(ref)
    if _json_source(path):
        if (rec.get("sha256") or "") != sha:
            raise LedgerError(f"{ref}: the record's own sha256 is not the entry key (a mention inside another record is a lead only)")
        if disclaimed(rec):
            raise LedgerError(f"{ref}: the retrieval record disclaims authenticity or reports NOT_FOUND/CONFLICTING")
        if str(rec.get("authenticity", "")) not in RET_AUTHENTICITY:
            raise LedgerError(f"{ref}: retrieval record authenticity {rec.get('authenticity')!r} is not an official or archival-facsimile value")
        m = URL.search(rec.get("locator") or "")
        if not m:
            raise LedgerError(f"{ref}: retrieval record has no URL locator")
        _untruncated(ref, rec.get("locator"), m)
        return "RET", "FULL", m.group(0)
    if path in CSV_KEYS and path in ("PILOT-01/registers/source_code_resolution_v3.csv", "PILOT-01/registers/source_discovery_2026-11-22.csv", "ACQ-02/supplement_inventory.csv"):
        own = (rec.get(CSV_KEYS[path][1]) or "").strip()[:64]
        if own != sha:
            raise LedgerError(f"{ref}: the record's own sha256 is not the entry key")
        if path.endswith("source_code_resolution_v3.csv"):
            u = (rec.get("official_corroboration_url") or "").strip()
            if not URL.match(u):
                raise LedgerError(f"{ref}: corroboration record has no URL")
            return "COR", "FULL", u
        if path.endswith("source_discovery_2026-11-22.csv"):
            m = URL.search(rec.get("candidate_url_or_identifier") or "")
            if not m:
                raise LedgerError(f"{ref}: download record gives an identifier, not a URL (IDENTIFIER_SHA is below FULL)")
            _untruncated(ref, rec.get("candidate_url_or_identifier"), m)
            return "DL", "FULL", m.group(0)
        ok = lambda v: (v or "").strip().lower() in ("yes", "true")
        if not (ok(rec.get("archive_size_ok")) and ok(rec.get("archive_md5_ok")) and ok(rec.get("archive_sha1_ok"))):
            raise LedgerError(f"{ref}: archive size/md5/sha1 not all OK (below FULL)")
        return "ARC", "FULL", (rec.get("url") or "").strip()
    raise LedgerError(f"{ref}: not a first-class record type")


def identity_ok(refs, sha, court, title, p1):
    """At least one identity reference must hold for THIS sha256: a page-image check with a 64-hex render hash
    (C6 checks only when identity_result=CONFIRMED), an ARMY-RULES-CHAIN-01 instrument row at IMAGE_CHECKED, or, for a
    court copy only, the page-1 text rule (two title words plus a year or case number)."""
    reasons = []
    for ref in refs:
        kind, _, r = ref.partition(":")
        if not r:
            continue
        if kind == "T":
            if court and text_identity(title, p1):
                return True
            reasons.append(f"{ref}: text identity fails or not a court copy")
            continue
        try:
            path, rec = resolve(r)
        except LedgerError as e:
            raise LedgerError(f"identity reference: {e}")
        if path == "ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv":
            m = re.search(r"[0-9a-f]{64}", rec.get("sha256", ""))
            if m and m.group(0) == sha and rec.get("evidence_level", "").startswith("IMAGE_CHECKED"):
                return True
            reasons.append(f"{r}: not an IMAGE_CHECKED row for this sha256")
            continue
        col = IDENTITY_KEYS[path][1]
        rsha = (rec.get(col) or "").strip()[:64]
        render = (rec.get("render_png_sha256") or "").strip()[:64]
        if rsha != sha or not re.fullmatch(r"[0-9a-f]{64}", render):
            reasons.append(f"{r}: not an image check of this sha256 with a render hash")
            continue
        if path.startswith("C6-01-PROVENANCE/") and rec.get("identity_result") != "CONFIRMED":
            reasons.append(f"{r}: identity_result {rec.get('identity_result')} (only CONFIRMED counts)")
            continue
        return True
    raise LedgerError("no valid identity evidence: " + "; ".join(reasons or ["no identity references"]))


def title_keys(title):
    t = re.sub(r"\(.*?\)", " ", title)
    stop = {"union", "india", "versus", "with", "court", "supreme", "gazette", "extraordinary", "army", "rules", "amendment", "part", "section"}
    return [w for w in re.findall(r"[A-Za-z]{4,}", t) if w.lower() not in stop][:4]


def text_identity(title, p1):
    keys = title_keys(title)
    nums = re.findall(r"\d{3,5}", re.sub(r"\(.*?\)", " ", title))
    p1 = (p1 or "").lower()
    return bool(keys) and all(k.lower() in p1 for k in keys[:2]) and any(n in p1 for n in nums)


def fidelity_issue(sha):
    """Copy-fidelity facts (evidence/copy_structure.csv). Returns '' if no issue; raises if the facts are absent."""
    rows = {r["sha256"]: r for r in read_csv(PKG / "evidence/copy_structure.csv")}
    st = rows.get(sha)
    if st is None:
        raise LedgerError(f"{sha[:12]}: no copy-structure facts; a primary class cannot be judged for fidelity (fail closed)")
    if st["signed_range_covers_file"] == "NO":
        return f"embedded signature byte range {st['signature_byte_ranges']} does not span the held file"
    if st["producer"].startswith("Internet Archive"):
        return f"archive.org derivative (producer {st['producer']})"
    return ""


def url_pairs():
    """Committed (exact URL string, sha256) pairs, used for contradiction detection (rule 1: exact string only)."""
    pairs = set()
    for r in _rows("PILOT-01/registers/source_code_resolution_v3.csv"):
        if (r.get("official_corroboration_url") or "").strip() and re.fullmatch(r"[0-9a-f]{64}", (r.get("official_sha256") or "").strip()):
            pairs.add((r["official_corroboration_url"].strip(), r["official_sha256"].strip()))
    for rel in [x for x in __import__("pins").EVIDENCE_INPUTS if _json_source(x)]:
        for o in _rows(rel):
            m = URL.search(o.get("locator") or "")
            if m and re.fullmatch(r"[0-9a-f]{64}", o.get("sha256") or ""):
                pairs.add((m.group(0), o["sha256"]))
    for r in _rows("PILOT-01/registers/source_discovery_2026-11-22.csv"):
        m = URL.search(r.get("candidate_url_or_identifier") or "")
        if m and re.fullmatch(r"[0-9a-f]{64}", (r.get("downloaded_sha256") or "").strip()):
            pairs.add((m.group(0), r["downloaded_sha256"].strip()))
    for r in _rows("ACQ-02/supplement_inventory.csv"):
        if (r.get("url") or "").strip() and re.fullmatch(r"[0-9a-f]{64}", (r.get("sha256") or "").strip()):
            pairs.add((r["url"].strip(), r["sha256"].strip()))
    for rel in [x for x in __import__("pins").EVIDENCE_INPUTS if _json_source(x)]:
        for o in _rows(rel):  # further URLs in a locator are paired only when the locator names no other sha256
            loc, s = o.get("locator") or "", o.get("sha256") or ""
            if re.fullmatch(r"[0-9a-f]{64}", s) and not (set(re.findall(r"[0-9a-f]{64}", loc)) - {s}):
                for u in URL.findall(loc)[1:]:
                    pairs.add((u, s))
    for r in _rows("WS-B-JUDGMENTS/tools/held_copies.csv"):
        if re.fullmatch(r"[0-9a-f]{64}", r.get("sha256", "")) and r.get("official_url", "").strip():
            pairs.add((r["official_url"].strip(), r["sha256"]))
    return pairs


def contradiction(url, sha):
    return sorted(s for u, s in url_pairs() if u == url and s != sha)
