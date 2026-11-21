"""First checks against a live site: read robots.txt and a few listing pages, report what is there.

Used before a source module exists, to confirm seed URLs and learn the page layout.
Fetches HTML/JSON listing pages only; never downloads documents (PDF links are listed, not followed).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

from .config import Config, url_host
from .http import Blocked, CrawlError, FetchError, PoliteClient, is_pdf_url
from .state import StateDB

KEYWORDS = re.compile(
    r"\b(acts?|rules?|regulations?|manuals?|judge?ments?|orders?|notifications?|documents?|publications?|"
    r"army|air force|navy|armed forces|tribunal|court[- ]martial|pension|gazette|archive|e-?book)\b", re.I)
CAPTCHA_RE = re.compile(r"<(?:input|img|div|iframe|canvas)[^>]*captcha", re.I)


@dataclass
class ProbeResult:
    url: str
    final_url: str | None = None
    status: int | None = None
    outcome: str = "ok"            # ok | blocked | failed | skipped | not_html
    error: str | None = None
    content_type: str | None = None
    nbytes: int = 0
    title: str | None = None
    links_total: int = 0
    offsite_links: int = 0
    pdf_links: list[tuple[str, str]] = field(default_factory=list)       # (text, url), on-site only
    keyword_links: list[tuple[str, str]] = field(default_factory=list)   # (text, url), on-site only
    forms: int = 0
    captcha: bool = False
    js_shell: bool = False        # page has almost no links/text: content is probably rendered by JavaScript


def probe_url(cfg: Config, db: StateDB, client: PoliteClient, source: str, url: str) -> ProbeResult:
    res = ProbeResult(url=url)
    is_new = db.enqueue(url, source, url_host(url), "listing", priority=1, meta={"role": "probe"})
    if not is_new:
        db.requeue(url)
    retry = dict(max_retries=cfg.setting(source, "max_retries"),
                 backoff_base=cfg.setting(source, "backoff_base_seconds"))
    if is_pdf_url(url):
        db.mark_skipped(url, "probe never downloads documents")
        res.outcome, res.error = "skipped", "probe never downloads documents"
        return res
    try:
        r = client.get(url)
    except Blocked as e:
        db.mark_skipped(url, f"blocked: {e}")
        res.outcome, res.error = "blocked", str(e)
        return res
    except FetchError as e:
        db.mark_attempt_failed(url, error=str(e), status_code=e.status_code, retryable=e.retryable, **retry)
        res.outcome, res.error, res.status = "failed", str(e), e.status_code
        return res
    except CrawlError as e:
        db.mark_skipped(url, str(e))
        res.outcome, res.error = "skipped", str(e)
        return res

    res.final_url, res.status, res.content_type, res.nbytes = r.url, r.status, r.content_type, len(r.content)
    if r.status != 200:
        db.mark_attempt_failed(url, error=f"HTTP {r.status}", status_code=r.status, retryable=False, **retry)
        res.outcome, res.error = "failed", f"HTTP {r.status}"
        return res
    db.mark_fetched(url, status_code=200, sha256=hashlib.sha256(r.content).hexdigest(), nbytes=len(r.content),
                    content_type=r.content_type, etag=r.headers.get("etag"),
                    last_modified=r.headers.get("last-modified"))
    if r.content_type not in ("text/html", "application/xhtml+xml"):
        res.outcome = "not_html"
        return res

    html = r.text()
    soup = BeautifulSoup(html, "html.parser")
    res.title = " ".join(soup.title.get_text(" ", strip=True).split()) if soup.title else None
    res.forms = len(soup.find_all("form"))
    res.captcha = bool(CAPTCHA_RE.search(html))
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        link = urldefrag(urljoin(r.url, href)).url
        if link in seen:
            continue
        seen.add(link)
        res.links_total += 1
        if not cfg.is_url_allowed(source, link)[0]:
            res.offsite_links += 1
            continue
        text = " ".join(a.get_text(" ", strip=True).split())[:120]
        if is_pdf_url(link):
            res.pdf_links.append((text, link))
        elif KEYWORDS.search(text) or KEYWORDS.search(urlsplit(link).path.replace("-", " ").replace("_", " ")):
            res.keyword_links.append((text, link))
    body_text = soup.get_text(" ", strip=True)
    res.js_shell = res.links_total < 5 and len(body_text) < 400
    return res


def results_to_markdown(source: str, results: list[ProbeResult], max_links: int = 40) -> str:
    lines = [f"## {source}", ""]
    for r in results:
        lines += [f"### {r.url}", ""]
        if r.outcome != "ok":
            lines += [f"**{r.outcome}**" + (f": {r.error}" if r.error else "")
                      + (f" ({r.content_type}, {r.nbytes} bytes)" if r.outcome == "not_html" else ""), ""]
            continue
        if r.final_url != r.url:
            lines.append(f"Redirected to: {r.final_url}  ")
        lines += [f"Title: {r.title or '—'}  ",
                  f"{r.nbytes} bytes; {r.links_total} links ({r.offsite_links} off the allow-list, not followed); "
                  f"{len(r.pdf_links)} PDF links; {r.forms} form(s); "
                  f"CAPTCHA marker: {'YES' if r.captcha else 'no'}; "
                  f"JavaScript-only page: {'likely' if r.js_shell else 'no'}", ""]
        for label, items in (("PDF links (not downloaded)", r.pdf_links), ("Links worth following", r.keyword_links)):
            if items:
                lines += [f"{label}:", ""]
                lines += [f"- {t or '(no text)'} — {u}" for t, u in items[:max_links]]
                if len(items) > max_links:
                    lines.append(f"- … and {len(items) - max_links} more")
                lines.append("")
    return "\n".join(lines)
