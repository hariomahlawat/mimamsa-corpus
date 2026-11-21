"""India Code (indiacode.nic.in): find an Act's page, list its PDFs and subordinate legislation.

STATUS: the page parsers below were written WITHOUT access to the live site (it was not
reachable from the build environment). They are deliberately loose (they look for link
shapes, not exact markup) and they raise structure warnings when a page does not contain
what an Act page should. Treat every result as unverified until `discover` has been run
against real pages and the output checked by a person.

Discovery never guesses: a target resolves only when exactly one search result has the
same title (ignoring case, punctuation and a leading "The"). Otherwise it is reported as
unresolved with the candidates, to be fixed by setting `handle_url` on the target.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote_plus, urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

from .config import Config, url_host
from .http import Blocked, CrawlError, FetchError, PoliteClient, is_pdf_url
from .state import StateDB

log = logging.getLogger("mimamsa.indiacode")

CATEGORIES = ("rules", "regulations", "notifications", "orders", "circulars", "ordinances", "statutes")
METADATA_LABELS = {
    "act id": "act_id", "act number": "act_number", "enactment date": "enactment_date",
    "act year": "act_year", "short title": "short_title", "long title": "long_title",
    "ministry": "ministry", "department": "department", "enforcement date": "enforcement_date",
}
GENERIC_LINK_TEXT = {"", "view", "download", "pdf", "click here", "open", "view pdf"}
DATE_RE = re.compile(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+,?\s+\d{4}\b")
CAPTCHA_RE = re.compile(r"<(?:input|img|div|iframe)[^>]*captcha", re.I)


def normalise_title(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return re.sub(r"^the ", "", s)


@dataclass
class DocLink:
    url: str
    title: str | None
    category: str            # act | rules | regulations | ... | unknown
    date_raw: str | None     # as printed in the listing row; not parsed, not guessed


@dataclass
class ActPage:
    url: str
    metadata: dict[str, str] = field(default_factory=dict)
    act_pdfs: list[DocLink] = field(default_factory=list)
    subordinate: list[DocLink] = field(default_factory=list)
    section_links: int = 0
    dropped: list[tuple[str, str]] = field(default_factory=list)   # (url, reason)
    warnings: list[str] = field(default_factory=list)
    has_captcha: bool = False


def _abs(base: str, href: str) -> str:
    return urldefrag(urljoin(base, href.strip())).url


def parse_search_results(html: str, base_url: str) -> list[tuple[str, str]]:
    """(title, url) for every link to a /handle/ page, in page order, de-duplicated."""
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        url = _abs(base_url, a["href"])
        title = " ".join(a.get_text(" ", strip=True).split())
        if "/handle/" in urlsplit(url).path and title and url not in seen:
            seen.add(url)
            out.append((title, url))
    return out


def _category(a, url: str) -> str:
    for parent in a.parents:
        marks = " ".join([parent.get("id") or "", *(parent.get("class") or [])]).lower()
        for c in CATEGORIES:
            if re.search(rf"\b{c}\b", marks):
                return c
    hay = (urlsplit(url).path + "?" + urlsplit(url).query).lower()
    for c in CATEGORIES:
        if re.search(rf"[/=]{c}(/|&|$)", hay):
            return c
    return "unknown"


def _row_info(a) -> tuple[str | None, str | None]:
    """Title and printed date for a document link, taken from its table row / list item."""
    text = " ".join(a.get_text(" ", strip=True).split())
    row = a.find_parent(["tr", "li"])
    row_text = " ".join(row.get_text(" ", strip=True).split()) if row else text
    m = DATE_RE.search(row_text)
    title = text
    if text.lower() in GENERIC_LINK_TEXT and row is not None:
        cells = [" ".join(c.get_text(" ", strip=True).split()) for c in row.find_all(["td", "th"])] or [row_text]
        cands = [c for c in cells if c and c.lower() not in GENERIC_LINK_TEXT
                 and not c.isdigit() and not DATE_RE.fullmatch(c)]
        title = max(cands, key=len) if cands else ""
    return (title or None), (m.group(0) if m else None)


def parse_act_page(html: str, url: str, is_allowed: Callable[[str], tuple[bool, str]]) -> ActPage:
    soup = BeautifulSoup(html, "html.parser")
    page = ActPage(url=url, has_captcha=bool(CAPTCHA_RE.search(html)))

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"], recursive=False)
        if len(cells) == 2:
            label = " ".join(cells[0].get_text(" ", strip=True).split()).rstrip(":").strip().lower()
            if label in METADATA_LABELS:
                page.metadata[METADATA_LABELS[label]] = " ".join(cells[1].get_text(" ", strip=True).split())

    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        link = _abs(url, href)
        path = urlsplit(link).path
        if "show-data" in path:
            page.section_links += 1
            continue
        if not is_pdf_url(link) or link in seen:
            continue
        seen.add(link)
        ok, why = is_allowed(link)
        if not ok:
            page.dropped.append((link, why))
            continue
        title, date_raw = _row_info(a)
        if "/bitstream/" in path:
            page.act_pdfs.append(DocLink(link, title, "act", date_raw))
        else:
            page.subordinate.append(DocLink(link, title, _category(a, link), date_raw))

    if not page.metadata:
        page.warnings.append("no Act metadata table found (Act ID, Act Number, Enactment Date ...)")
    if not page.act_pdfs:
        page.warnings.append("no Act PDF (/bitstream/....pdf) link found")
    if len(page.act_pdfs) > 1:
        page.warnings.append(f"{len(page.act_pdfs)} Act PDFs found; none is tagged with the doc_id, review needed")
    unknown = sum(1 for d in page.subordinate if d.category == "unknown")
    if unknown:
        page.warnings.append(f"{unknown} PDF link(s) with no recognisable category")
    return page


@dataclass
class TargetResult:
    doc_id: str
    title: str
    status: str                         # resolved | already_known | unresolved | failed | skipped | blocked
    reason: str | None = None
    act_url: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    act_pdfs: int = 0
    subordinate: dict[str, int] = field(default_factory=dict)
    newly_queued: int = 0
    section_links: int = 0
    dropped: list[tuple[str, str]] = field(default_factory=list)
    candidates: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _fetch_listing(cfg: Config, db: StateDB, client: PoliteClient, source: str, url: str, *,
                   doc_id: str, role: str, discovered_from: str | None, refresh: bool) -> str:
    db.enqueue(url, source, url_host(url), "listing", doc_id_hint=doc_id, discovered_from=discovered_from,
               priority=1, meta={"role": role})
    if refresh:
        db.requeue(url)
    try:
        r = client.get(url)
    except Blocked as e:
        db.mark_skipped(url, f"blocked: {e}")
        raise
    except FetchError as e:
        db.mark_attempt_failed(url, error=str(e), status_code=e.status_code, retryable=e.retryable,
                               max_retries=cfg.setting(source, "max_retries"),
                               backoff_base=cfg.setting(source, "backoff_base_seconds"))
        raise
    except CrawlError as e:               # off allow-list, robots
        db.mark_skipped(url, str(e))
        raise
    if r.status != 200:
        db.mark_attempt_failed(url, error=f"HTTP {r.status}", status_code=r.status, retryable=False,
                               max_retries=cfg.setting(source, "max_retries"),
                               backoff_base=cfg.setting(source, "backoff_base_seconds"))
        raise FetchError(f"{url}: HTTP {r.status}", retryable=False, status_code=r.status)
    db.mark_fetched(url, status_code=200, sha256=hashlib.sha256(r.content).hexdigest(), nbytes=len(r.content),
                    content_type=r.content_type, etag=r.headers.get("etag"),
                    last_modified=r.headers.get("last-modified"))
    return r.text()


def _known_act_url(db: StateDB, source: str, doc_id: str) -> str | None:
    row = db.conn.execute(
        "SELECT url FROM urls WHERE source=? AND kind='listing' AND doc_id_hint=? AND status='fetched' "
        "AND json_extract(meta, '$.role')='act_page'", (source, doc_id)).fetchone()
    return row["url"] if row else None


def _discover_target(cfg: Config, db: StateDB, client: PoliteClient, source: str, t: dict,
                     refresh: bool) -> TargetResult:
    src = cfg.source(source)
    res = TargetResult(doc_id=t["doc_id"], title=t["title"], status="unresolved")

    act_url = _known_act_url(db, source, t["doc_id"])
    if act_url and not refresh:
        res.status, res.act_url = "already_known", act_url
        return res
    act_url = act_url or t.get("handle_url")

    if not act_url:
        template = src.get("search_url_template")
        if not template:
            res.reason = "no handle_url on the target and no search_url_template on the source"
            return res
        search_url = template.format(query=quote_plus(t["title"]))
        html = _fetch_listing(cfg, db, client, source, search_url, doc_id=t["doc_id"], role="search",
                              discovered_from=None, refresh=refresh)
        results = parse_search_results(html, search_url)
        want = normalise_title(t["title"])
        hits = [(title, url) for title, url in results if normalise_title(title) == want]
        if len({u for _, u in hits}) != 1:
            res.reason = (f"{len(hits)} exact title matches among {len(results)} search results; "
                          "set handle_url on this target in sources.yaml")
            res.candidates = (hits or results)[:10]
            if not results and CAPTCHA_RE.search(html):
                raise Blocked(f"{search_url}: no results and the page carries a CAPTCHA")
            return res
        act_url = hits[0][1]

    html = _fetch_listing(cfg, db, client, source, act_url, doc_id=t["doc_id"], role="act_page",
                          discovered_from=None, refresh=refresh)
    page = parse_act_page(html, act_url, lambda u: cfg.is_url_allowed(source, u))
    if page.has_captcha and not page.metadata and not page.act_pdfs:
        raise Blocked(f"{act_url}: page has a CAPTCHA and no Act content")

    res.act_url, res.metadata, res.section_links = act_url, page.metadata, page.section_links
    res.dropped, res.warnings, res.act_pdfs = page.dropped, list(page.warnings), len(page.act_pdfs)
    printed = page.metadata.get("short_title")
    if printed and normalise_title(printed) != normalise_title(t["title"]):
        res.warnings.append(f"page short title {printed!r} differs from target title {t['title']!r}")

    year = str(t["year"]) if t.get("year") else None
    for d in page.act_pdfs:
        hint = t["doc_id"] if len(page.act_pdfs) == 1 else None
        res.newly_queued += db.enqueue(
            d.url, source, url_host(d.url), "document", doc_id_hint=hint, discovered_from=act_url, priority=10,
            meta={"category": "act", "title": d.title or t["title"], "parent_doc_id": t["doc_id"], "year": year})
    if src.get("collect_subordinate", True):
        for d in page.subordinate:
            res.subordinate[d.category] = res.subordinate.get(d.category, 0) + 1
            res.newly_queued += db.enqueue(
                d.url, source, url_host(d.url), "document", discovered_from=act_url, priority=50,
                meta={"category": d.category, "title": d.title, "date_raw": d.date_raw,
                      "parent_doc_id": t["doc_id"], "year": None})
    listed = [normalise_title(d.title or "") for d in page.subordinate]
    for want in t.get("expect_subordinate", []):
        if not any(normalise_title(want) in have for have in listed):
            res.warnings.append(f"expected subordinate document not listed on the Act page: {want!r}")
    res.status = "resolved"
    return res


def discover(cfg: Config, db: StateDB, client: PoliteClient, source: str = "indiacode", *,
             only: list[str] | None = None, refresh: bool = False) -> list[TargetResult]:
    """Fetch listing pages only (search + Act page) and queue the documents they list.
    Downloads no documents."""
    src = cfg.source(source)
    targets = [t for key in ("targets", "also_search") for t in (src.get(key) or [])]
    if only:
        unknown = set(only) - {t["doc_id"] for t in targets}
        if unknown:
            raise KeyError(f"not a target of {source}: {', '.join(sorted(unknown))}")
        targets = [t for t in targets if t["doc_id"] in only]
    results: list[TargetResult] = []
    for t in targets:
        try:
            results.append(_discover_target(cfg, db, client, source, t, refresh))
        except Blocked as e:
            log.error("BLOCKED, stopping %s: %s", source, e)
            results.append(TargetResult(t["doc_id"], t["title"], "blocked", reason=str(e)))
            break
        except FetchError as e:
            results.append(TargetResult(t["doc_id"], t["title"], "failed", reason=str(e)))
        except CrawlError as e:
            results.append(TargetResult(t["doc_id"], t["title"], "skipped", reason=str(e)))
    return results


def results_to_markdown(results: list[TargetResult]) -> str:
    lines = []
    for r in results:
        lines += [f"### {r.doc_id} — {r.status}", ""]
        if r.reason:
            lines += [f"Reason: {r.reason}", ""]
        if r.act_url:
            lines += [f"Act page: {r.act_url}  "]
        if r.status == "resolved":
            sub = ", ".join(f"{n} {c}" for c, n in sorted(r.subordinate.items())) or "none"
            lines += [f"Act PDFs: {r.act_pdfs}; subordinate documents: {sub}; newly queued: {r.newly_queued}  ",
                      f"Section links seen (not queued): {r.section_links}", ""]
            if r.metadata:
                lines += ["| Printed on the page | Value |", "| --- | --- |"]
                lines += [f"| {k} | {v} |" for k, v in r.metadata.items()] + [""]
        for url, why in r.dropped:
            lines.append(f"- dropped {url} ({why})")
        for w in r.warnings:
            lines.append(f"- ⚠ {w}")
        for title, url in r.candidates:
            lines.append(f"- candidate: {title} — {url}")
        lines.append("")
    return "\n".join(lines)
