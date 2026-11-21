"""Armed Forces Tribunal: list judgments bench by bench and queue their PDFs.

The benches publish in two styles (seen in pages saved from the live sites in 2023; the sites may
have changed since, so the first run against each bench must be read by a person):

  joodb  Principal Bench and the benches hosted on www.aftdelhi.nic.in (e.g. Chandigarh): a listing
         component whose rows are <div class="tr ..."> with "Label: <span>value</span>" fields and
         a "ViewPDF" link. "Results 1 - N of M" says how many there are; `limit=0` asks for all.
  table  Lucknow, Kolkata, Jabalpur: an HTML table of links to PDFs, sometimes over several pages
         (Kolkata: /judgements/index/page:2 ...).

Discovery reads listing pages only and queues every on-site PDF link with whatever the row says
about it. It downloads no judgments. Nothing is inferred: a field the row does not give is absent.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

from .config import Config, url_host
from .http import Blocked, CrawlError, FetchError, PoliteClient
from .state import StateDB

log = logging.getLogger("mimamsa.aft")

RESULTS = re.compile(r"Results\s+(\d+)\s*-\s*(\d+)\s+of\s+(\d+)", re.I)
YEAR = re.compile(r"(?<!\d)(19[5-9]\d|20[0-4]\d)(?!\d)")
CAPTCHA = re.compile(r"<(?:input|img|div|iframe|canvas)[^>]*captcha", re.I)
MAX_PAGES = 60


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _is_pdf(url: str) -> bool:
    return urlsplit(url).path.lower().endswith(".pdf")


@dataclass
class Row:
    url: str
    title: str | None
    fields: dict[str, str] = field(default_factory=dict)


def parse_joodb(html: str, base_url: str) -> tuple[list[Row], tuple[int, int, int] | None]:
    """Rows of the aftdelhi.nic.in listing component, and (first, last, total) from 'Results a - b of c'."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[Row] = []
    for tr in soup.find_all("div", class_="tr"):
        link = next((a for a in tr.find_all("a", href=True)
                     if _is_pdf(urljoin(base_url, a["href"]))), None)
        if link is None:
            continue
        fields: dict[str, str] = {}
        for span in tr.find_all("span"):
            prev = span.previous_sibling
            label = str(prev) if isinstance(prev, str) else ""
            m = re.search(r"([A-Za-z][A-Za-z .]*?)\s*:\s*(?:\xa0|\s)*$", label)
            if m and _text(span):
                fields.setdefault(m.group(1).strip().lower().rstrip("."), _text(span))
        judges = re.search(r"Judge?ment given by\s*:\s*(.+?)(?:Subject|Status|$)", _text(tr), re.I)
        if judges:
            fields.pop("judgement given by", None)              # the span holds only the first member
            fields["judgment given by"] = judges.group(1).strip(" ;,")
        h3 = tr.find("h3")
        heading = _text(h3) if h3 else None
        title = fields.get("case no") or heading
        if heading:
            fields.setdefault("heading", heading)
        rows.append(Row(urldefrag(urljoin(base_url, link["href"])).url, title, fields))
    m = RESULTS.search(soup.get_text(" "))
    return rows, (tuple(int(x) for x in m.groups()) if m else None)


def parse_table(html: str, base_url: str) -> list[Row]:
    """Every PDF link in a table, with the header names when the table has them."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[Row] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        url = urldefrag(urljoin(base_url, a["href"].strip())).url
        if not _is_pdf(url) or url in seen:
            continue
        seen.add(url)
        fields: dict[str, str] = {}
        td = a.find_parent("td")
        # the sites sometimes put part of a name outside the link ("J<a>yoti</a>"): read the cell unbroken
        title = " ".join(td.get_text("", strip=False).split()) if td else _text(a)
        tr = a.find_parent("tr")
        table = a.find_parent("table")
        if td is not None and tr is not None:
            cells = tr.find_all("td", recursive=False)
            heads = [_text(th).lower() for th in table.find_all("th")] if table else []
            if heads and len(heads) == len(cells):               # a labelled table (Kolkata)
                for h, c in zip(heads, cells):
                    if _text(c):
                        fields[h] = _text(c)
                title = fields.get("title") or fields.get("description") or title
            else:                                                # name | subject pairs side by side (Lucknow)
                nxt = td.find_next_sibling("td")
                if nxt is not None and _text(nxt) and not nxt.find("a"):
                    fields["subject"] = _text(nxt)
        if not title:
            title = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
        rows.append(Row(url, title, fields))
    return rows


@dataclass
class BenchResult:
    key: str
    name: str
    status: str = "ok"            # ok | not_configured | blocked | failed | skipped
    reason: str | None = None
    pages: int = 0
    rows: int = 0
    queued: int = 0
    already_known: int = 0
    listed_total: int | None = None
    dropped: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    doc_id = property(lambda self: self.key)       # so the CLI summary can treat benches like targets


def _get(cfg: Config, db: StateDB, client: PoliteClient, source: str, url: str, bench: str, refresh: bool) -> str:
    is_new = db.enqueue(url, source, url_host(url), "listing", priority=1, meta={"role": "aft_listing", "bench": bench})
    if not is_new and refresh:
        db.requeue(url)
    retry = dict(max_retries=cfg.setting(source, "max_retries"), backoff_base=cfg.setting(source, "backoff_base_seconds"))
    try:
        r = client.get(url)
    except Blocked as e:
        db.mark_skipped(url, f"blocked: {e}")
        raise
    except FetchError as e:
        db.mark_attempt_failed(url, error=str(e), status_code=e.status_code, retryable=e.retryable, **retry)
        raise
    except CrawlError as e:
        db.mark_skipped(url, str(e))
        raise
    if r.status != 200:
        db.mark_attempt_failed(url, error=f"HTTP {r.status}", status_code=r.status, retryable=False, **retry)
        raise FetchError(f"{url}: HTTP {r.status}", retryable=False, status_code=r.status)
    db.mark_fetched(url, status_code=200, sha256=hashlib.sha256(r.content).hexdigest(), nbytes=len(r.content),
                    content_type=r.content_type, etag=r.headers.get("etag"), last_modified=r.headers.get("last-modified"))
    html = r.text()
    if CAPTCHA.search(html) and ".pdf" not in html.lower():
        raise Blocked(f"{url}: the page carries a CAPTCHA and lists no judgments")
    return html


def _with_param(url: str, **params) -> str:
    sep = "&" if "?" in url else "?"
    return url + sep + "&".join(f"{k}={v}" for k, v in params.items())


def _discover_bench(cfg: Config, db: StateDB, client: PoliteClient, source: str, bench: dict, refresh: bool) -> BenchResult:
    res = BenchResult(bench["key"], bench.get("name", bench["key"]))
    urls = list(bench.get("listing_urls") or [])
    style = bench.get("style")
    if not urls or style not in ("joodb", "table"):
        res.status, res.reason = "not_configured", "no listing_urls / style for this bench in sources.yaml"
        return res
    max_pages = int(bench.get("max_pages", MAX_PAGES))
    page_link = re.compile(bench["page_link_pattern"]) if bench.get("page_link_pattern") else None
    todo, done, rows = list(urls), set(), []

    while todo and res.pages < max_pages:
        base = todo.pop(0)
        if base in done:
            continue
        done.add(base)
        if style == "joodb":
            url = _with_param(base, limit=0) if "limit=" not in base and "start=" not in base else base
            html = _get(cfg, db, client, source, url, bench["key"], refresh)
            res.pages += 1
            page_rows, results = parse_joodb(html, url)
            rows += page_rows
            if results:
                first, last, total = results
                res.listed_total = total
                if last < total and page_rows:                  # the site did not return everything: page on
                    nxt = _with_param(base.split("?")[0], limit=len(page_rows), start=last)
                    if nxt not in done:
                        todo.append(nxt)
            elif not page_rows:
                res.warnings.append(f"{url}: no result rows and no 'Results a - b of c' line; layout may have changed")
        else:
            html = _get(cfg, db, client, source, base, bench["key"], refresh)
            res.pages += 1
            page_rows = parse_table(html, base)
            rows += page_rows
            if not page_rows:
                res.warnings.append(f"{base}: no PDF links found; layout may have changed")
            if page_link:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    nxt = urldefrag(urljoin(base, a["href"])).url
                    if page_link.search(nxt) and nxt not in done and nxt not in todo and cfg.is_url_allowed(source, nxt)[0]:
                        todo.append(nxt)
    if todo:
        res.warnings.append(f"stopped after {max_pages} listing pages; {len(todo)} more were not read")

    seen: set[str] = set()
    for row in rows:
        if row.url in seen:
            continue
        seen.add(row.url)
        ok, why = cfg.is_url_allowed(source, row.url)
        if not ok:
            res.dropped.append((row.url, why))
            continue
        path = unquote(urlsplit(row.url).path)
        year = row.fields.get("year") if YEAR.fullmatch(row.fields.get("year", "")) else None
        if not year:
            m = YEAR.findall(path)
            year = m[-1] if m else None
        is_new = db.enqueue(row.url, source, url_host(row.url), "document", priority=50, meta={
            "category": "judgment", "bench": bench["key"], "bench_name": bench.get("name"), "title": row.title,
            "case_number": row.fields.get("case no"), "year": year, "fields": row.fields,
            "filename": path.rsplit("/", 1)[-1], "parent_doc_id": f"aft-{bench['key']}"})
        res.queued += is_new
        res.already_known += not is_new
    res.rows = len(seen)
    if res.listed_total is not None and res.rows < res.listed_total:
        res.warnings.append(f"the site says {res.listed_total} results; {res.rows} PDF links were read")
    return res


def discover(cfg: Config, db: StateDB, client: PoliteClient, source: str = "aft", *,
             only: list[str] | None = None, refresh: bool = False) -> list[BenchResult]:
    """`only` names bench keys. Reads listing pages; downloads no judgments."""
    benches = cfg.source(source).get("benches") or []
    if only:
        unknown = set(only) - {b["key"] for b in benches}
        if unknown:
            raise KeyError(f"not a bench of {source}: {', '.join(sorted(unknown))}")
        benches = [b for b in benches if b["key"] in only]
    out: list[BenchResult] = []
    for b in benches:
        try:
            out.append(_discover_bench(cfg, db, client, source, b, refresh))
        except Blocked as e:
            log.error("BLOCKED on %s: %s", b["key"], e)
            out.append(BenchResult(b["key"], b.get("name", b["key"]), "blocked", str(e)))
        except FetchError as e:
            out.append(BenchResult(b["key"], b.get("name", b["key"]), "failed", str(e)))
        except CrawlError as e:
            out.append(BenchResult(b["key"], b.get("name", b["key"]), "skipped", str(e)))
    return out


def results_to_markdown(results: list[BenchResult]) -> str:
    lines = ["| Bench | Result | Listing pages | Judgment links | Newly queued | Site's own count |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in results:
        lines.append(f"| {r.name} | {r.status}{': ' + r.reason if r.reason else ''} | {r.pages} | {r.rows} | "
                     f"{r.queued} | {r.listed_total if r.listed_total is not None else ''} |")
    for r in results:
        for w in r.warnings:
            lines.append(f"- ⚠ {r.key}: {w}")
        if r.dropped:
            lines.append(f"- {r.key}: {len(r.dropped)} link(s) off the allow-list were not queued, e.g. {r.dropped[0][0]}")
    return "\n".join(lines) + "\n"
