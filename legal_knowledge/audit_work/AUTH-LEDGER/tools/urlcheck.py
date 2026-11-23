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
import urllib.parse

MAX_LEN = 2048
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


def parse(url):
    """Return (host, path_segments, query) for a strictly valid HTTPS locator. Every second spelling of a URL (case,
    explicit default port, needless or lower-case escapes) is rejected, so exact-string contradiction checks cannot be
    evaded by re-spelling a recorded locator; raise ValueError(reason) otherwise."""
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
    if labels[-1].isdigit():
        raise ValueError(f"host {host!r} looks like an IP address")
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
    segs = path.split("/")[1:]
    if any(s == "" for s in segs[:-1]):
        raise ValueError("empty path segment ('//') is not allowed")
    for s in segs:
        if s in (".", ".."):
            raise ValueError(f"dot segment {s!r} in the path")
        if ";" in s:
            raise ValueError("';' path parameters are not allowed")
        dec = urllib.parse.unquote(s, errors="strict")
        if dec in (".", "..") or "/" in dec or "\\" in dec:  # defence in depth: already excluded by the escape rules
            raise ValueError("a path segment decodes to traversal or a separator")
    return host, segs, parts.query


def problem(url):
    """'' when the locator is strictly valid, else the reason."""
    try:
        parse(url)
    except ValueError as e:
        return str(e)
    return ""
