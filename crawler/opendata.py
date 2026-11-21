"""Supreme Court and High Court judgments from the AWS Open Data buckets.

  indian-supreme-court-judgments   reported judgments, taken from the Supreme Court's e-SCR portal
  indian-high-court-judgments      25 High Courts, taken from the eCourts judgments portal

Both are maintained by a third party (Dattam Labs / P. Vanga), licensed CC-BY-4.0, and are copies of
official court records; every record made from them names the bucket as its source. They are used
because the courts' own judgment searches sit behind a CAPTCHA.

Each bucket has a small metadata index per year (parquet) and one PDF per judgment. The indexes carry
no judgment text, so discovery cannot apply the brief's keyword filter. Instead it PRE-SELECTS by
party names (config `party_terms`: Union of India, defence bodies, service ranks ...) and queues only
those PDFs; the pipeline's relevance stage then applies the keyword filter to the text and logs
rejects. Entries the pre-selection leaves out are counted, never silently dropped from the totals.

`--only` slices: Supreme Court "2013" or "2009-2025"; High Courts "delhi:2023" or "delhi:2010-2023".
"""
from __future__ import annotations

import hashlib
import io
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import quote

from .config import Config, url_host
from .http import Blocked, CrawlError, FetchError, PoliteClient
from .state import StateDB

log = logging.getLogger("mimamsa.opendata")
KEYS = re.compile(r"<Prefix>([^<]+)</Prefix>")
DROP_COLUMNS = {"raw_html"}


def read_parquet(content: bytes) -> list[dict]:
    import pyarrow.parquet as pq           # imported here so the rest of the crawler works without it
    return pq.read_table(io.BytesIO(content)).to_pylist()


def parse_years(spec: str | list | int) -> list[int]:
    """'2013' -> [2013]; '2009-2012' -> [2009..2012]; [2009, 2012] (config) -> the inclusive range."""
    if isinstance(spec, int):
        return [spec]
    if isinstance(spec, (list, tuple)):
        return list(range(int(spec[0]), int(spec[-1]) + 1))
    a, _, b = str(spec).partition("-")
    return list(range(int(a), int(b or a) + 1))


@dataclass
class SliceResult:
    key: str                       # "2013" or "delhi:2023"
    status: str = "ok"             # ok | already_known | no_index | failed | blocked | skipped
    reason: str | None = None
    index_rows: int = 0
    candidates: int = 0
    queued: int = 0
    no_pdf: int = 0
    warnings: list[str] = field(default_factory=list)

    doc_id = property(lambda self: self.key)


class _Bucket:
    def __init__(self, cfg: Config, db: StateDB, client: PoliteClient, source: str, refresh: bool):
        self.cfg, self.db, self.client, self.source, self.refresh = cfg, db, client, source, refresh
        src = cfg.source(source)
        self.base = src["base_url"].rstrip("/")
        self.terms = re.compile("|".join(f"(?:{t})" for t in src.get("party_terms") or [r"."]), re.I)
        self.retry = dict(max_retries=cfg.setting(source, "max_retries"),
                          backoff_base=cfg.setting(source, "backoff_base_seconds"))

    def known(self, url: str) -> bool:
        row = self.db.get(url)
        return bool(row) and row["status"] == "fetched" and not self.refresh

    def get(self, url: str, slice_key: str) -> bytes | None:
        """Fetch an index file. None = it does not exist (HTTP 404)."""
        db = self.db
        is_new = db.enqueue(url, self.source, url_host(url), "listing", priority=1,
                            meta={"role": "opendata_index", "slice": slice_key})
        if not is_new and self.refresh:
            db.requeue(url)
        try:
            r = self.client.get(url)
        except Blocked as e:
            db.mark_skipped(url, f"blocked: {e}")
            raise
        except FetchError as e:
            db.mark_attempt_failed(url, error=str(e), status_code=e.status_code, retryable=e.retryable, **self.retry)
            raise
        except CrawlError as e:
            db.mark_skipped(url, str(e))
            raise
        if r.status == 404:
            db.mark_attempt_failed(url, error="HTTP 404", status_code=404, retryable=False, **self.retry)
            return None
        if r.status != 200:
            db.mark_attempt_failed(url, error=f"HTTP {r.status}", status_code=r.status, retryable=False, **self.retry)
            raise FetchError(f"{url}: HTTP {r.status}", retryable=False, status_code=r.status)
        db.mark_fetched(url, status_code=200, sha256=hashlib.sha256(r.content).hexdigest(), nbytes=len(r.content),
                        content_type=r.content_type, etag=r.headers.get("etag"),
                        last_modified=r.headers.get("last-modified"))
        return r.content

    def queue(self, res: SliceResult, url: str, index_url: str, meta: dict) -> None:
        ok, why = self.cfg.is_url_allowed(self.source, url)
        if not ok:
            res.warnings.append(f"not queued ({why}): {url}")
            return
        res.queued += self.db.enqueue(url, self.source, url_host(url), "document", priority=50,
                                      discovered_from=index_url, meta=meta)


def _clean(row: dict) -> dict:
    return {k: (None if v is None else str(v)) for k, v in row.items() if k not in DROP_COLUMNS}


def _sci_year(b: _Bucket, year: int) -> SliceResult:
    res = SliceResult(str(year))
    index_url = f"{b.base}/metadata/parquet/year={year}/metadata.parquet"
    if b.known(index_url):
        res.status = "already_known"
        return res
    content = b.get(index_url, res.key)
    if content is None:
        res.status, res.reason = "no_index", "no metadata index for this year"
        return res
    for row in read_parquet(content):
        res.index_rows += 1
        parties = " ".join(str(row.get(k) or "") for k in ("title", "petitioner", "respondent"))
        if not b.terms.search(parties):
            continue
        res.candidates += 1
        path = row.get("path")
        if not path:
            res.no_pdf += 1
            continue
        b.queue(res, f"{b.base}/data/pdf/year={year}/english/{quote(str(path))}_EN.pdf", index_url, {
            "category": "judgment", "court_key": "sci", "title": row.get("title"), "year": str(year),
            "filename": f"{path}_EN.pdf", "parent_doc_id": "sci", "dataset": "indian-supreme-court-judgments",
            "index": _clean(row)})
    return res


def _hc_slice(b: _Bucket, court: dict, year: int) -> SliceResult:
    res = SliceResult(f"{court['key']}:{year}")
    code = court["code"]
    listing = f"{b.base}/?list-type=2&prefix=metadata/parquet/year={year}/court={code}/&delimiter=/"
    if b.known(listing):
        res.status = "already_known"
        return res
    content = b.get(listing, res.key)
    benches = [p.rstrip("/").rsplit("bench=", 1)[1] for p in KEYS.findall((content or b"").decode("utf-8", "replace"))
               if "bench=" in p]
    if not benches:
        res.status, res.reason = "no_index", "no metadata index for this court and year"
        return res
    for bench in benches:
        index_url = f"{b.base}/metadata/parquet/year={year}/court={code}/bench={bench}/metadata.parquet"
        content = b.get(index_url, res.key)
        if content is None:
            res.warnings.append(f"bench {bench}: index listed but not found")
            continue
        for row in read_parquet(content):
            res.index_rows += 1
            if not b.terms.search(str(row.get("title") or "")):
                continue
            res.candidates += 1
            name = str(row.get("pdf_link") or "").rsplit("/", 1)[-1]
            # The index's `pdf_exists` column is not used: it read "False" on every Delhi 2023 row while the
            # PDFs were in the bucket (checked 2026-11-21). A PDF that is really missing fails at download.
            if not name.lower().endswith(".pdf"):
                res.no_pdf += 1
                continue
            b.queue(res, f"{b.base}/data/pdf/year={year}/court={code}/bench={bench}/{quote(name)}", index_url, {
                "category": "judgment", "court_key": court["key"], "court_name": court.get("name"), "bench": bench,
                "title": row.get("title"), "year": str(year), "filename": name, "parent_doc_id": f"hc-{court['key']}",
                "dataset": "indian-high-court-judgments", "index": _clean(row)})
    return res


def discover(cfg: Config, db: StateDB, client: PoliteClient, source: str, *,
             only: list[str] | None = None, refresh: bool = False) -> list[SliceResult]:
    src = cfg.source(source)
    b = _Bucket(cfg, db, client, source, refresh)
    jobs: list = []
    if src.get("dataset") == "indian-supreme-court-judgments":
        years = sorted({y for spec in (only or [src["years"]]) for y in parse_years(spec)})
        jobs = [(_sci_year, (b, y), str(y)) for y in years]
    elif src.get("dataset") == "indian-high-court-judgments":
        courts = {c["key"]: c for c in src.get("courts") or []}
        slices = only or [f"{k}:{'-'.join(map(str, c['years']))}" for k, c in courts.items() if c.get("years")]
        for s in slices:
            key, _, yrs = s.partition(":")
            if key not in courts:
                raise KeyError(f"not a court of {source}: {key}")
            for y in parse_years(yrs or courts[key]["years"]):
                jobs.append((_hc_slice, (b, courts[key], y), f"{key}:{y}"))
    else:
        raise KeyError(f"{source}: unknown or missing `dataset`")
    out: list[SliceResult] = []
    for fn, args, key in jobs:
        try:
            out.append(fn(*args))
        except Blocked as e:
            log.error("BLOCKED, stopping %s: %s", source, e)
            out.append(SliceResult(key, "blocked", str(e)))
            break
        except FetchError as e:
            out.append(SliceResult(key, "failed", str(e)))
        except CrawlError as e:
            out.append(SliceResult(key, "skipped", str(e)))
    return out


def results_to_markdown(results: list[SliceResult]) -> str:
    done = [r for r in results if r.status == "ok"]
    lines = [f"{len(results)} slice(s): {len(done)} read, "
             f"{sum(r.status == 'already_known' for r in results)} already known, "
             f"{sum(r.status == 'no_index' for r in results)} without an index, "
             f"{sum(r.status in ('failed', 'blocked', 'skipped') for r in results)} failed.", "",
             f"Index entries read: {sum(r.index_rows for r in done)}; pre-selected by party names: "
             f"{sum(r.candidates for r in done)}; queued: {sum(r.queued for r in done)}; "
             f"pre-selected but without a PDF in the bucket: {sum(r.no_pdf for r in done)}.", ""]
    if 0 < len(done) <= 40:
        lines += ["| Slice | Index entries | Pre-selected | Queued | No PDF |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {r.key} | {r.index_rows} | {r.candidates} | {r.queued} | {r.no_pdf} |" for r in done]
    for r in results:
        if r.status in ("failed", "blocked", "skipped"):
            lines.append(f"- {r.key}: {r.status}: {r.reason}")
        for w in r.warnings[:5]:
            lines.append(f"- ⚠ {r.key}: {w}")
    return "\n".join(lines) + "\n"
