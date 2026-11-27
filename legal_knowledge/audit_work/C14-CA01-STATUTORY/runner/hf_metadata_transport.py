"""Bounded metadata protocol, without the SDK's implicit pagination.

No credentials, sockets, network client or activation in this module.
The exchange callback must be an independently commissioned HTTPS GET
transport with bounded reads, no redirects and no retry.
"""
from __future__ import annotations

import json
import math
import re
import time
from types import SimpleNamespace
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

from hf_inventory_metadata import HEX40, REPO, STORES
from hf_inventory_provider import ENDPOINT

ROOTS = ("data/raw", "legal_knowledge/preservation")
MAX_PAGES = 160
MAX_PAGE_BYTES = 4_000_000
MAX_TOTAL_BYTES = 48_000_000
MAX_SECONDS = 180
MAX_CURSOR = 8192
MAX_LINK_BYTES = 3 * MAX_CURSOR + 1024
MAX_CREDENTIAL_BYTES = 128_000

_REPO_ROUTE = f"/api/datasets/{REPO}"
_CREDENTIAL_ROUTE = "/api/whoami-v2"
_LINK_ITEM = re.compile(
    r'[ \t]*<([^<>\s]+)>[ \t]*;[ \t]*rel=(?:"(next|prev|first|last)"|(next|prev|first|last))[ \t]*'
)
_BAD_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")


def _check_revision(revision):
    if not isinstance(revision, str) or not HEX40.fullmatch(revision):
        raise ValueError("full immutable revision required")


def _tree_route(revision, scope):
    # SDK 2.4 quotes the entire repo-relative path as one URL segment.
    return f"{_REPO_ROUTE}/tree/{revision}/{quote(scope, safe='')}"


def _split_metadata_url(url):
    if (not isinstance(url, str) or not url.startswith(ENDPOINT + "/")
            or len(url) > MAX_LINK_BYTES or any(not 33 <= ord(c) <= 126 for c in url)
            or "#" in url or _BAD_PERCENT.search(url)):
        raise ValueError("invalid metadata URL")
    try:
        parts = urlsplit(url)
    except ValueError:
        raise ValueError("invalid metadata URL") from None
    if (parts.scheme, parts.netloc) != ("https", "huggingface.co"):
        raise ValueError("metadata URL escaped exact origin")
    return parts


def _tree_parameters(query, recursive, *, continuation=False):
    try:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True,
                          max_num_fields=4, encoding="ascii", errors="strict")
    except ValueError:
        raise ValueError("invalid tree query") from None
    supplied = dict(pairs)
    if len(supplied) != len(pairs) or set(supplied) - {"recursive", "expand", "limit", "cursor"}:
        raise ValueError("unsupported tree query")

    required = {"recursive": str(recursive).lower(), "expand": "false"}
    for key, value in required.items():
        if supplied.get(key, value if continuation else None) != value:
            raise ValueError("tree query changed approved scope")

    # The Hub sets a default page size of 1000 when expand is false. Permit
    # that exact limit only when a continuation explicitly returns it.
    if "limit" in supplied and ("cursor" not in supplied or supplied["limit"] != "1000"):
        raise ValueError("invalid tree page limit")
    cursor = supplied.get("cursor")
    if cursor is None:
        if continuation:
            raise ValueError("pagination cursor missing")
    elif not 0 < len(cursor) <= MAX_CURSOR or any(not 33 <= ord(c) <= 126 for c in cursor):
        raise ValueError("invalid continuation cursor")
    return {**required, **{key: supplied[key] for key in ("limit", "cursor") if key in supplied}}


def metadata_request_target(url, revision):
    """Validate the exact outbound metadata URL and return an HTTP request target."""
    _check_revision(revision)
    parts = _split_metadata_url(url)
    if parts.path in (_CREDENTIAL_ROUTE, f"{_REPO_ROUTE}/revision/{revision}"):
        if parts.query or url.endswith("?"):
            raise ValueError("identity route does not accept a query")
        return parts.path

    routes = {_tree_route(revision, scope): scope in STORES for scope in (*ROOTS, *STORES)}
    if parts.path not in routes:
        raise ValueError("metadata route outside approved scope")
    parameters = _tree_parameters(parts.query, routes[parts.path])
    query = urlencode(parameters)
    if parts.query != query:
        raise ValueError("noncanonical metadata query")
    return f"{parts.path}?{query}"


def _parse_json(body):
    def unique(pairs):
        mapping = {}
        for key, value in pairs:
            if key in mapping:
                raise ValueError("duplicate metadata key")
            mapping[key] = value
        return mapping

    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite metadata number")
        return number

    try:
        return json.loads(body.decode("utf-8"), object_pairs_hook=unique,
                          parse_float=finite, parse_constant=finite)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("invalid metadata JSON") from None


def _continuation(link, route, recursive):
    if link is None:
        return None
    # Model the SDK's next relation without accepting arbitrary Link extensions
    # or following other relations. Missing, malformed or ambiguous next targets
    # never become requests outside the approved tree.
    offset = 0
    continuation = None
    while True:
        item = _LINK_ITEM.match(link, offset)
        if item is None:
            raise ValueError("unsupported pagination header")
        target, quoted_relation, bare_relation = item.groups()
        if (quoted_relation or bare_relation) == "next":
            if continuation is not None:
                raise ValueError("ambiguous pagination header")
            parts = _split_metadata_url(target)
            if parts.path != route:
                raise ValueError("pagination escaped exact metadata route")
            parameters = _tree_parameters(parts.query, recursive, continuation=True)
            continuation = (f"{ENDPOINT}{route}?{urlencode(parameters)}", parameters["cursor"])
        offset = item.end()
        if offset == len(link):
            return continuation
        if link[offset] != ",":
            raise ValueError("unsupported pagination header")
        offset += 1


class MetadataAPI:
    endpoint = ENDPOINT

    def __init__(self, revision, exchange, *, clock=time.monotonic):
        _check_revision(revision)
        self.revision = revision
        self.exchange = exchange
        self.clock = clock
        self.deadline = clock() + MAX_SECONDS
        self.requests = 0
        self.bytes = 0

    def remaining(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError("metadata deadline exceeded")
        return remaining

    def _get(self, url, *, endpoint_cap=MAX_PAGE_BYTES):
        if self.requests >= MAX_PAGES:
            raise ValueError("metadata request budget exhausted")
        cap = min(endpoint_cap, MAX_PAGE_BYTES, MAX_TOTAL_BYTES - self.bytes)
        if cap <= 0:
            raise ValueError("metadata byte budget exhausted")
        remaining = self.remaining()
        self.requests += 1
        body, link = self.exchange(url, cap, remaining)
        if not isinstance(body, bytes) or len(body) > cap:
            raise ValueError("metadata response exceeded budget")
        self.bytes += len(body)
        self.remaining()
        if link is not None and (not isinstance(link, str) or len(link) > MAX_LINK_BYTES
                                 or any(c != "\t" and not 32 <= ord(c) <= 126 for c in link)):
            raise ValueError("invalid pagination header")
        data = _parse_json(body)
        self.remaining()
        return data, link

    def credential_info(self):
        """Return permission evidence for in-memory validation without account profile data."""
        data, link = self._get(ENDPOINT + _CREDENTIAL_ROUTE, endpoint_cap=MAX_CREDENTIAL_BYTES)
        auth = data.get("auth") if isinstance(data, dict) else None
        token = auth.get("accessToken") if isinstance(auth, dict) else None
        if link is not None or not isinstance(token, dict) or not isinstance(token.get("role"), str):
            raise ValueError("invalid credential permission response")
        return {"auth": auth}

    def dataset_info(self, repo, *, revision):
        if repo != REPO or revision != self.revision:
            raise ValueError("wrong repository or revision")
        data, link = self._get(f"{ENDPOINT}{_REPO_ROUTE}/revision/{revision}")
        if link is not None or not isinstance(data, dict):
            raise ValueError("unexpected identity response")
        return SimpleNamespace(id=data.get("id"), sha=data.get("sha"), private=data.get("private"))

    def list_repo_tree(self, repo, *, path_in_repo, recursive, expand, revision, repo_type):
        if (repo != REPO or revision != self.revision or repo_type != "dataset"
                or expand is not False or type(recursive) is not bool
                or path_in_repo not in (STORES if recursive else ROOTS)):
            raise ValueError("tree request outside approved scope")
        route = _tree_route(revision, path_in_repo)
        query = urlencode({"recursive": str(recursive).lower(), "expand": "false"})
        url = f"{ENDPOINT}{route}?{query}"
        seen_cursors = set()
        while url is not None:
            data, link = self._get(url)
            if not isinstance(data, list) or len(data) > 1000:
                raise ValueError("invalid metadata page")
            following = _continuation(link, route, recursive)
            url = None
            if following is not None:
                url, cursor = following
                if cursor in seen_cursors:
                    raise ValueError("pagination loop")
                seen_cursors.add(cursor)

            entries = []
            for row in data:
                if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                    raise ValueError("invalid metadata row")
                match row.get("type"):
                    case "directory":
                        entries.append(SimpleNamespace(path=row["path"]))
                    case "file":
                        lfs = row.get("lfs")
                        if lfs is not None and not isinstance(lfs, dict):
                            raise ValueError("invalid LFS metadata")
                        entries.append(SimpleNamespace(
                            path=row["path"], size=row.get("size"),
                            lfs=SimpleNamespace(sha256=lfs.get("oid"), size=lfs.get("size")) if lfs else None,
                        ))
                    case _:
                        raise ValueError("unknown metadata entry type")
            yield from entries
