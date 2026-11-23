"""Fail-closed discovery guard for read-only source discovery (stdlib). Used by Cycle 5 correction discovery and
specified for future discovery agents. It is NOT the crawler. The crawler PR stack (#7, #8, #9, #17, #23) is not
modified; see reports/DISCOVERY_SAFETY_POLICY.md for the separate crawler proposal.

Rules (DISCOVERY_SAFETY_POLICY.md):
- robots.txt must be ESTABLISHED before any other request to a host:
    200 + text body          -> rules parsed (urllib.robotparser); explicit Disallow respected
    404 / 410                -> NO_ROBOTS_FILE (RFC 9309: no rules) -> allowed
    anything else (401, 403, 429, 5xx, timeout, TLS error, connection error, non-text body, redirect
    to another host, empty status) -> UNAVAILABLE: no further automated request to that host
- each redirect hop to a different host is a new host: it needs its own robots decision and must be allowed
- blocked hosts (repository policy) and bare-IP hosts are always refused; TLS verification is never disabled
- response classification separates METADATA_OR_LISTING / HEADERS_ONLY_DOCUMENT_INDICATED / DOCUMENT_PAYLOAD /
  UNKNOWN using method, content type, content disposition, size and (when bytes are available) file signature,
  never the URL extension alone
- a GET that returns DOCUMENT_PAYLOAD without an acquisition approval reference is a violation"""
import ipaddress
import re
from urllib import robotparser
from urllib.parse import parse_qs, urlsplit

BLOCKED_HOST_SUFFIXES = ("aftjabalpur.in",)
DOC_TYPES = ("application/pdf", "application/msword", "application/vnd.openxmlformats", "application/zip",
             "application/x-zip", "application/octet-stream", "application/vnd.ms-", "image/tiff", "image/jp2")
LISTING_TYPES = ("text/html", "application/json", "application/xml", "text/xml", "text/plain", "application/ld+json")
MAGIC = {b"%PDF": "pdf", b"PK\x03\x04": "zip/ooxml", b"\xd0\xcf\x11\xe0": "ole/doc", b"II*\x00": "tiff", b"MM\x00*": "tiff"}
LOG_V2_COLUMNS = ["utc_time", "method", "url", "final_url", "redirect_hosts", "http_status", "content_type",
                  "content_disposition", "content_length", "payload_class", "file_signature", "robots_state",
                  "purpose", "acquisition_approval_ref", "note"]


def host_of(url):
    return (urlsplit(url).hostname or "").lower()


def host_blocked(host):
    host = (host or "").lower().rstrip(".")
    if not host:
        return True
    try:
        ipaddress.ip_address(host)
        return True  # bare-IP routes are never used
    except ValueError:
        pass
    return any(host == s or host.endswith("." + s) for s in BLOCKED_HOST_SUFFIXES)


def robots_decision(status, body=b"", content_type="", final_host=None, requested_host=None, error=None):
    """Return (state, parser_or_None). state in RULES_PARSED | NO_ROBOTS_FILE | UNAVAILABLE."""
    if error or status in (None, "", 0, "000"):
        return "UNAVAILABLE", None
    try:
        status = int(status)
    except (TypeError, ValueError):
        return "UNAVAILABLE", None
    if final_host and requested_host and final_host != requested_host:
        return "UNAVAILABLE", None  # robots redirected off-host: policy not established for this host
    if status in (404, 410):
        return "NO_ROBOTS_FILE", None
    if status != 200:
        return "UNAVAILABLE", None
    if content_type and not content_type.lower().startswith("text/"):
        return "UNAVAILABLE", None
    text = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else str(body)
    if "<html" in text[:500].lower():
        return "UNAVAILABLE", None  # an HTML error page served as robots.txt is not a robots policy
    rp = robotparser.RobotFileParser()
    rp.parse(text.splitlines())
    return "RULES_PARSED", rp


def may_request(url, robots_by_host, user_agent="*"):
    """(allowed, reason). robots_by_host maps host -> (state, parser)."""
    h = host_of(url)
    if host_blocked(h):
        return False, "BLOCKED_HOST"
    if urlsplit(url).scheme != "https":
        return False, "NON_HTTPS"
    if h not in robots_by_host:
        return False, "ROBOTS_NOT_ESTABLISHED"
    state, rp = robots_by_host[h]
    if state == "UNAVAILABLE":
        return False, "ROBOTS_UNAVAILABLE"
    if state == "RULES_PARSED" and not rp.can_fetch(user_agent, url):
        return False, "ROBOTS_DISALLOW"
    return True, state


def redirect_chain_allowed(chain, robots_by_host, user_agent="*"):
    """Every hop (including the final URL) must itself be allowed."""
    for u in chain:
        ok, why = may_request(u, robots_by_host, user_agent)
        if not ok:
            return False, f"{why}:{host_of(u)}"
    return True, "ALL_HOPS_ALLOWED"


def url_suggests_document(url):
    """Heuristic flag only (never sufficient): path extension or a filename/type query parameter."""
    p = urlsplit(url)
    if re.search(r"\.(pdf|docx?|zip|tiff?)$", p.path, re.I):
        return True
    q = parse_qs(p.query)
    vals = [v for vs in q.values() for v in vs]
    return any(re.search(r"\.(pdf|docx?|zip|tiff?)$", v, re.I) for v in vals) or bool(
        re.search(r"(showfile|download|bitstream|getfile|viewfile)", p.path + "?" + p.query, re.I))


def signature(first_bytes):
    for m, kind in MAGIC.items():
        if first_bytes and first_bytes.startswith(m):
            return kind
    return ""


def head_allows_get(content_type):
    """GET is permitted only when HEAD reported an explicit listing/metadata content type (FD-02)."""
    ct = (content_type or "").split(";")[0].strip().lower()
    return bool(ct) and ct.startswith(LISTING_TYPES)


def classify_response(method, status, content_type="", content_disposition="", content_length=None, first_bytes=b""):
    ct = (content_type or "").split(";")[0].strip().lower()
    cd = (content_disposition or "").lower()
    sig = signature(first_bytes)
    doc_indicated = bool(sig) or ct.startswith(DOC_TYPES) or "attachment" in cd or re.search(r"filename=.*\.(pdf|docx?|zip)", cd) is not None
    if method.upper() == "HEAD":
        return ("HEADERS_ONLY_DOCUMENT_INDICATED" if doc_indicated else "HEADERS_ONLY"), sig
    if doc_indicated:
        return "DOCUMENT_PAYLOAD", sig
    if ct.startswith(LISTING_TYPES):
        return "METADATA_OR_LISTING", sig
    return "UNKNOWN", sig


def validate_log_v2(rows):
    """Errors for a v2 request log (list of dicts with LOG_V2_COLUMNS)."""
    err, unavailable, decided = [], set(), set()
    for i, r in enumerate(rows, 2):
        h = host_of(r["url"])
        if r["method"].upper() == "NONE":
            continue  # decision record: no request was made
        if r.get("purpose") == "robots":
            decided.add(h)
        elif h not in decided:
            err.append(f"row {i}: request to {h} before a robots decision for that host")
        if host_blocked(h) or any(host_blocked(x) for x in (r.get("redirect_hosts") or "").split(";") if x):
            err.append(f"row {i}: blocked host")
        if r.get("robots_state") == "UNAVAILABLE":
            if r.get("purpose") != "robots":
                err.append(f"row {i}: request to {h} although its robots policy is UNAVAILABLE")
            unavailable.add(h)
        elif h in unavailable and r.get("purpose") != "robots":
            err.append(f"row {i}: request to {h} after robots UNAVAILABLE")
        if r.get("robots_state") == "ROBOTS_DISALLOW":
            err.append(f"row {i}: request made to a robots-disallowed URL")
        if r["method"].upper() == "GET" and r.get("payload_class") in ("DOCUMENT_PAYLOAD", "UNKNOWN") and not (r.get("acquisition_approval_ref") or "").strip():
            err.append(f"row {i}: GET returned {r.get('payload_class')} without an acquisition approval reference")
        if r.get("purpose") == "robots" and r.get("robots_state") == "RULES_PARSED" and r.get("http_status") != "200":
            err.append(f"row {i}: robots RULES_PARSED with status {r.get('http_status')}")
    return err


def legacy_log_findings(rows):
    """What a v1 log (utc, method, url, status, bytes, purpose) can and cannot show. Returns (errors, suspects)."""
    err, sus = [], []
    for i, r in enumerate(rows, 2):
        if len(r) < 3 or r[1] == "method":
            continue
        method, url = r[1].upper(), r[2]
        if host_blocked(host_of(url)) and host_of(url):
            err.append(f"line {i}: blocked host")
        if method == "GET" and url_suggests_document(url):
            sus.append(f"line {i}: GET to a document-like URL (v1 log has no content type): {url[:120]}")
    return err, sus
