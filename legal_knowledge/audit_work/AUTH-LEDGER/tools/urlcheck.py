"""Strict validation of first-class provenance locators (AUTH-LEDGER-02, Fable finding D-01).

A locator is accepted only if it is ONE unambiguous HTTPS URL that every reasonable URL handler would read the same way.
Nothing is normalised or repaired: a URL that would need normalising is rejected with a reason. The parser is the
standard library's RFC 3986 splitter (urllib.parse.urlsplit); the checks below are applied to its components and are
cross-checked against an independent strict authority grammar, so a disagreement between the two is itself a rejection.

D-01 root cause: the AUTH-LEDGER-01 check tested for literal '.' and '..' path segments only. Percent-encoded dot
segments (%2e%2e), encoded separators (%2f, %5c), double encoding (%252e) and malformed escapes (%zz) passed, so an
otherwise permitted host could carry a path that a downstream handler decodes into traversal.

Rejected (each with a stated reason):
  - anything but the lower-case scheme 'https'; scheme-relative or opaque forms
  - characters outside the RFC 3986 URI character set: spaces, controls, DEL, non-ASCII, backslash, '"', '<', '>',
    '^', '`', '{', '|', '}', and '[' / ']' (no IP-literal hosts)
  - malformed or lower-case percent escapes; escapes of unreserved characters (%2e, %41, %7e ...: an encoded form of a character
    that needs no encoding is an ambiguous second spelling); escapes of '/', '\\', '%' (double encoding), ';', and
    of control characters, DEL or NUL
  - userinfo ('@' anywhere in the authority); any explicit port (':443' included); a host that is not a lower-case
    DNS name of at least two labels (IP addresses, trailing dots, empty labels, '_' and upper case are rejected)
  - literal '.' / '..' segments, empty segments ('//'), ';' path parameters (servlet containers read '..;' as '..')
  - an empty query ('?' with nothing after it) and any fragment
The host and path rules per evidence class are in strength.CLASS_HOSTS / class_path_problem()."""
import re
import unicodedata
import urllib.parse

MAX_LEN = 2048
LOOKALIKES = {"\u2215", "\u2044", "\u29f8", "\ufffd"}  # division slash, fraction slash, big solidus, replacement character
_URI_CHARS = re.compile(r"[A-Za-z0-9\-._~:/?#@!$&'()*+,;=%]*")  # RFC 3986 reserved + unreserved + '%' (no '[' ']')
_PCT = re.compile(r"%(..)?", re.S)
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_UNRESERVED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_FORBIDDEN_ESCAPES = {0x2F: "an encoded '/'", 0x5C: "an encoded '\\'", 0x25: "an encoded '%' (double encoding)", 0x3B: "an encoded ';'",
                      0x3F: "an encoded '?'", 0x23: "an encoded '#'"}


def _escape_problem(part, where):
    for m in _PCT.finditer(part):
        hx = m.group(1)
        if hx is None or not re.fullmatch(r"[0-9A-Fa-f]{2}", hx):
            return f"malformed percent escape in the {where}"
        b = int(hx, 16)
        if chr(b) in _UNRESERVED:
            return f"percent-encoded unreserved character %{hx} in the {where} (ambiguous spelling; %2e is an encoded dot)"
        if hx != hx.upper():
            return f"lower-case percent escape %{hx} in the {where} (a second spelling of %{hx.upper()}; RFC 3986 6.2.2.1)"
        if b in _FORBIDDEN_ESCAPES:
            return f"{_FORBIDDEN_ESCAPES[b]} (%{hx}) in the {where}"
        if b < 0x20 or b == 0x7F:
            return f"percent-encoded control character %{hx} in the {where}"
    return ""


def _decoded_problem(part, where):
    """The percent-decoded bytes must be strict UTF-8 with no control, format (bidi) or compatibility characters: a
    decoded fullwidth dot or solidus would be read as '.' or '/' by a handler that applies NFKC (Fable F-07)."""
    try:
        dec = urllib.parse.unquote_to_bytes(part).decode("utf-8")
    except UnicodeDecodeError:
        return f"percent-encoded bytes in the {where} are not valid UTF-8"
    for ch in dec:
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp") or (cat == "Zs" and ch != " "):
            return f"decoded {where} contains a control, format, separator or unassigned character U+{ord(ch):04X}"
    bad = sorted(set(dec) & LOOKALIKES)
    if bad:
        return f"decoded {where} contains a slash look-alike or replacement character U+{ord(bad[0]):04X} (Fable R-05)"
    if unicodedata.normalize("NFKC", dec) != dec:
        return f"decoded {where} contains compatibility characters (e.g. fullwidth '.' or '/') that NFKC would change"
    return ""


def parse(url):
    """Return (host, path_segments, query) for a strictly valid HTTPS locator. The common second spellings of a URL
    (case, explicit port, escapes of unreserved characters, lower-case escapes) are rejected. NOT every equivalent
    spelling is: '@' versus '%40' and other reserved-character escapes, query-parameter order, and different paths that
    serve one resource (e.g. archive.org /details/<item> and /download/<item>/<file>) are not canonicalised (Fable
    F-03); contradiction checks therefore remain exact-string (rule 1) and RULE_DECISION_PACK.md C covers aliases; raise ValueError(reason) otherwise."""
    if not isinstance(url, str) or not url:
        raise ValueError("locator is empty")
    if len(url) > MAX_LEN:
        raise ValueError(f"locator longer than {MAX_LEN} characters")
    if not _URI_CHARS.fullmatch(url):
        bad = sorted({c for c in url if not _URI_CHARS.fullmatch(c)})
        raise ValueError(f"character(s) outside the RFC 3986 URI set: {''.join(bad)!r}")
    if not url.startswith("https://"):
        raise ValueError("scheme must be exactly lower-case 'https' with an authority ('https://')")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise ValueError("scheme must be 'https'")
    netloc = parts.netloc
    # independent authority grammar: host[:port]; the stdlib split must agree with it
    m = re.fullmatch(r"([^:@/?#]+)(?::([^@/?#]*))?", netloc)
    if "@" in netloc or not m:
        raise ValueError("authority must be a bare host (no userinfo)")
    host, port = m.group(1), m.group(2)
    if port is not None:
        raise ValueError(f"explicit port {port!r} is not allowed (even ':443' is a second spelling that would evade exact-string contradiction checks)")
    labels = host.split(".")
    if len(labels) < 2 or not all(_LABEL.fullmatch(x) for x in labels) or len(host) > 253:
        raise ValueError(f"host {host!r} is not a lower-case DNS name of two or more labels")
    if not re.fullmatch(r"[a-z]{2,63}", labels[-1]):
        raise ValueError(f"host {host!r} has a non-alphabetic top-level label (IP-address forms such as 1.0x7f are rejected: Fable F-15)")
    try:
        sp = parts.port
    except ValueError:
        raise ValueError("port is malformed")
    if parts.hostname != host or sp is not None:
        raise ValueError("authority parsing is ambiguous (parsers disagree)")
    if "#" in url or parts.fragment:
        raise ValueError("a fragment is not allowed in a provenance locator")
    if url.endswith("?") or ("?" in url and not parts.query):
        raise ValueError("an empty query is not allowed")
    path = parts.path or "/"
    if not path.startswith("/"):
        raise ValueError("path must be absolute")
    for where, part in (("path", path), ("query", parts.query)):
        p = _escape_problem(part, where)
        if p:
            raise ValueError(p)
    for where, part in (("path", path), ("query", parts.query)):
        p = _decoded_problem(part, where)
        if p:
            raise ValueError(p)
    segs = path.split("/")[1:]
    if any(s == "" for s in segs[:-1]):
        raise ValueError("empty path segment ('//') is not allowed")
    for s in segs:
        if s in (".", ".."):
            raise ValueError(f"dot segment {s!r} in the path")
        if ";" in s:
            raise ValueError("';' path parameters are not allowed")
        dec = urllib.parse.unquote_to_bytes(s).decode("utf-8")  # already proven strict UTF-8 by _decoded_problem
        if set(dec) <= {".", " "} and dec != "":
            raise ValueError("a path segment decodes to dots and/or spaces only (traversal look-alike: Fable R-05)")
        if "/" in dec or "\\" in dec:
            raise ValueError("a path segment decodes to a separator")
    return host, segs, parts.query


def problem(url):
    """'' when the locator is strictly valid, else the reason."""
    try:
        parse(url)
    except ValueError as e:
        return str(e)
    return ""
