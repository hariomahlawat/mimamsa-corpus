"""India Code (indiacode.gov.in): find an Act through the site's REST API and queue its files.

The site moved from www.indiacode.nic.in to indiacode.gov.in and is now a DSpace 9 application
whose pages are built in the browser from a public REST API at <base_url>/server/api. This
module reads that API (checked against the live site on 2026-11-21):

  search   GET /discover/search/objects?query=dc.identifier.collection:ACT AND dc.title:"<title>"
  files    GET /core/items/<uuid>/bundles?embed=bitstreams      (ORIGINAL bundle = the PDFs)
  linked   GET /discover/search/objects?f.act_id=<act id>,equals (sections, rules, schedules ...)

Every record carries `dc.identifier.collection` (ACT, SECTION, RULE, SCHEDULE, NOTIFICATION ...)
and, when it belongs to an Act, `dc.identifier.act_id`. Section records hold the section text
and its amendment footnotes, so the pages of linked records are queued as documents too.

Discovery never guesses: a target resolves only when exactly one ACT record has the same
title (ignoring case, punctuation and a leading "The") and, when both are known, the same year.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import quote

from .config import Config, url_host
from .http import Blocked, CrawlError, FetchError, PoliteClient
from .state import StateDB

log = logging.getLogger("mimamsa.indiacode")

PAGE_SIZE = 100
MAX_LINKED_PAGES = 50            # safety stop: 5,000 linked records for one Act would be a surprise
YEAR_FIELDS = ("dc.date.rule_year", "dc.date.regulation_year", "dc.date.notification_year",
               "dc.date.statute_year", "dc.date.ordinance_year", "dc.date.circular_year")


_ACT_FILE = re.compile(r"^([ah])\d{4}-?\d+\.pdf$", re.I)


def file_language(filename: str | None) -> str | None:
    """India Code names an Act's files a<year>-<no>.pdf (English) and h<year><no>.pdf (Hindi); seen on
    all six Acts checked on 2026-11-21. This is a naming convention, not a guarantee: the text
    extraction stage should confirm the language from the content."""
    m = _ACT_FILE.match(filename or "")
    return {"a": "en", "h": "hi"}[m.group(1).lower()] if m else None


def normalise_title(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
    return re.sub(r"^the ", "", s)


def md(item: dict, key: str) -> str | None:
    """First value of a DSpace metadata field, or None."""
    vals = (item.get("metadata") or {}).get(key) or []
    return vals[0].get("value") if vals else None


def search_objects(payload: dict) -> tuple[list[dict], dict]:
    """(records, page info) from a /discover/search/objects answer."""
    sr = payload["_embedded"]["searchResult"]
    objs = [o["_embedded"]["indexableObject"] for o in sr.get("_embedded", {}).get("objects", [])]
    return objs, sr.get("page", {})


def original_bitstreams(payload: dict) -> list[dict]:
    """Files in the ORIGINAL bundle of a /core/items/<uuid>/bundles?embed=bitstreams answer."""
    out = []
    for bundle in payload.get("_embedded", {}).get("bundles", []):
        if bundle.get("name") != "ORIGINAL":
            continue
        for bs in bundle.get("_embedded", {}).get("bitstreams", {}).get("_embedded", {}).get("bitstreams", []):
            checksum = bs.get("checkSum") or {}
            out.append({
                "url": bs["_links"]["content"]["href"],
                "filename": bs.get("name"),
                "size": bs.get("sizeBytes"),
                "md5": checksum.get("value") if checksum.get("checkSumAlgorithm") == "MD5" else None,
                "bitstream_uuid": bs.get("uuid"),
            })
    return out


@dataclass
class TargetResult:
    doc_id: str
    title: str
    status: str                         # resolved | already_known | unresolved | failed | skipped | blocked
    reason: str | None = None
    act_url: str | None = None          # API URL of the Act record
    act_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    act_pdfs: int = 0
    linked: dict[str, int] = field(default_factory=dict)        # collection -> number of records
    linked_pages: int = 0
    subordinate_files: dict[str, int] = field(default_factory=dict)   # collection -> files queued
    newly_queued: int = 0
    dropped: list[tuple[str, str]] = field(default_factory=list)
    candidates: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class _Api:
    """Listing requests against the API, with crawl-state bookkeeping."""

    def __init__(self, cfg: Config, db: StateDB, client: PoliteClient, source: str, refresh: bool):
        self.cfg, self.db, self.client, self.source, self.refresh = cfg, db, client, source, refresh
        self.base = cfg.source(source)["base_url"].rstrip("/") + "/server/api"
        self.retry = dict(max_retries=cfg.setting(source, "max_retries"),
                          backoff_base=cfg.setting(source, "backoff_base_seconds"))

    def peek(self, url: str) -> dict:
        """Read a JSON listing without a crawl-state row of its own. Used for pages that are also
        queued as documents: the queue row then belongs to the document, and `fetch` saves it."""
        r = self.client.get(url)
        if r.status != 200:
            raise FetchError(f"{url}: HTTP {r.status}", retryable=False, status_code=r.status)
        try:
            return json.loads(r.content)
        except ValueError:
            raise FetchError(f"{url}: not JSON ({r.content_type})", retryable=False) from None

    def get(self, url: str, *, doc_id: str, role: str) -> dict:
        db = self.db
        is_new = db.enqueue(url, self.source, url_host(url), "listing", doc_id_hint=doc_id, priority=1,
                            meta={"role": role})
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
        except CrawlError as e:               # off allow-list, robots
            db.mark_skipped(url, str(e))
            raise
        problem, payload = None, None
        if r.status != 200:
            problem = f"HTTP {r.status}"
        else:
            try:
                payload = json.loads(r.content)
            except ValueError:
                problem = f"not JSON ({r.content_type})"
        if problem:
            db.mark_attempt_failed(url, error=problem, status_code=r.status, retryable=False, **self.retry)
            raise FetchError(f"{url}: {problem}", retryable=False, status_code=r.status)
        db.mark_fetched(url, status_code=200, sha256=hashlib.sha256(r.content).hexdigest(), nbytes=len(r.content),
                        content_type=r.content_type, etag=r.headers.get("etag"),
                        last_modified=r.headers.get("last-modified"))
        return payload


def _known_act(db: StateDB, source: str, doc_id: str) -> str | None:
    row = db.conn.execute(
        "SELECT url FROM urls WHERE source=? AND kind='listing' AND doc_id_hint=? AND status='fetched' "
        "AND json_extract(meta, '$.role')='act_item'", (source, doc_id)).fetchone()
    return row["url"] if row else None


def _queue_files(res: TargetResult, api: _Api, files: list[dict], *, doc_id_hint: str | None, priority: int,
                 discovered_from: str, meta: dict) -> int:
    queued = 0
    for f in files:
        ok, why = api.cfg.is_url_allowed(api.source, f["url"])
        if not ok:
            res.dropped.append((f["url"], why))
            continue
        queued += api.db.enqueue(f["url"], api.source, url_host(f["url"]), "document", doc_id_hint=doc_id_hint,
                                 discovered_from=discovered_from, priority=priority,
                                 meta={**meta, "filename": f["filename"], "md5": f["md5"], "size": f["size"]})
    res.newly_queued += queued
    return queued


def _discover_target(cfg: Config, db: StateDB, client: PoliteClient, source: str, t: dict,
                     refresh: bool) -> TargetResult:
    src = cfg.source(source)
    api = _Api(cfg, db, client, source, refresh)
    res = TargetResult(doc_id=t["doc_id"], title=t["title"], status="unresolved")
    doc_id = t["doc_id"]

    known = _known_act(db, source, doc_id)
    if known and not refresh:
        res.status, res.act_url = "already_known", known
        return res

    # 1. Find the Act record.
    uuid = t.get("item_uuid")
    if not uuid:
        core = re.sub(r"^the\s+", "", t["title"].strip(), flags=re.I)
        query = f'dc.identifier.collection:ACT AND dc.title:"{core}"'
        search_url = f"{api.base}/discover/search/objects?query={quote(query)}&size=20"
        records, _ = search_objects(api.get(search_url, doc_id=doc_id, role="search"))
        want, year = normalise_title(t["title"]), str(t["year"]) if t.get("year") else None
        # The record's act_year is the year of the Act NUMBER (CrPC 1973 is Act 2 of 1974), so it is
        # only compared when the title itself does not already carry the year.
        check_year = year is not None and year not in t["title"]
        hits = [r for r in records
                if md(r, "dc.identifier.collection") == "ACT" and normalise_title(r.get("name")) == want
                and (not check_year or md(r, "dc.date.act_year") in (None, year))]
        if len(hits) > 1:
            # India Code also holds state copies of central Acts (with state amendments) under the
            # same title. Keep the copy for the jurisdiction the target names (default CENTRAL).
            state = str(t.get("state", "CENTRAL")).upper()
            in_state = [r for r in hits if (md(r, "dc.identifier.state_name") or "").upper() == state]
            if in_state:
                hits = in_state
        if len(hits) != 1:
            res.reason = (f"{len(hits)} exact title matches among {len(records)} search results; "
                          "set item_uuid on this target in sources.yaml")
            res.candidates = [(f"{r.get('name')} ({md(r, 'dc.date.act_year')}, "
                               f"{md(r, 'dc.identifier.state_name')}, repealed={md(r, 'dc.identifier.repealed')})",
                               r["uuid"])
                              for r in (hits or records)[:10]]
            return res
        uuid = hits[0]["uuid"]

    # 2. The Act record itself.
    act_url = f"{api.base}/core/items/{uuid}"
    act = api.get(act_url, doc_id=doc_id, role="act_item")
    res.act_url, res.act_id = act_url, md(act, "dc.identifier.act_id")
    for key in ("dc.title", "dc.identifier.act_number", "dc.date.act_year", "dc.date.enact_date",
                "dc.date.enforcement_date", "dc.date.last_modified", "dc.identifier.repealed",
                "dc.identifier.ministry_name", "dc.identifier.department_name", "dc.identifier.act_id"):
        if md(act, key) is not None:
            res.metadata[key] = md(act, key)
    year = md(act, "dc.date.act_year") or (str(t["year"]) if t.get("year") else None)

    if t.get("repealed_record"):
        # A repealed central Act kept in India Code's "Repeal Acts" collection: a bare record (title such
        # as "The Indian Penal Code, 45 of 1860 (Rep., Act 45 of 2023)") with one PDF, no section records.
        coll = api.get(f"{act_url}/owningCollection", doc_id=doc_id, role="collection").get("name")
        res.metadata["owning collection"] = coll or ""
        if "repeal" not in (coll or "").lower():
            res.warnings.append(f"record {uuid} is in collection {coll!r}, expected the Repeal Acts collection")
        core = normalise_title(re.sub(r"\b\d{4}\b", "", t["title"]))
        if core not in normalise_title(act.get("name")):
            res.warnings.append(f"record title {act.get('name')!r} does not contain target title {t['title']!r}")
        files = original_bitstreams(api.get(f"{act_url}/bundles?embed=bitstreams&size=20", doc_id=doc_id,
                                            role="bundles"))
        res.act_pdfs = len(files)
        for f in files:
            _queue_files(res, api, [f], doc_id_hint=doc_id if len(files) == 1 else None, priority=10,
                         discovered_from=act_url,
                         meta={"category": "act", "title": act.get("name"), "parent_doc_id": doc_id, "year": year,
                               "item_uuid": uuid, "role": "act_text" if len(files) == 1 else "act_other_file",
                               "language_by_filename": file_language(f["filename"]),
                               "repeal_record": {"title": act.get("name"), "handle": act.get("handle"),
                                                 "date_issued": md(act, "dc.date.issued"),
                                                 "state_name": md(act, "dc.identifier.state_name"),
                                                 "collection_name": coll}})
        if len(files) != 1:
            res.warnings.append(f"expected one file on a repealed-Act record, found {len(files)}; none tagged")
        res.status = "resolved"
        return res

    if md(act, "dc.identifier.collection") != "ACT":
        res.warnings.append(f"record {uuid} is in collection {md(act, 'dc.identifier.collection')!r}, not ACT")
    if normalise_title(act.get("name")) != normalise_title(t["title"]):
        res.warnings.append(f"record title {act.get('name')!r} differs from target title {t['title']!r}")

    # 3. The Act's own files.
    files = original_bitstreams(api.get(f"{act_url}/bundles?embed=bitstreams&size=20", doc_id=doc_id, role="bundles"))
    res.act_pdfs = len(files)
    main = [f for f in files if file_language(f["filename"]) == "en"]
    for f in files:
        is_main = len(main) == 1 and f is main[0]
        _queue_files(res, api, [f], doc_id_hint=doc_id if is_main else None, priority=10, discovered_from=act_url,
                     meta={"category": "act", "title": act.get("name"), "parent_doc_id": doc_id, "year": year,
                           "item_uuid": uuid, "role": "act_text" if is_main else "act_other_file",
                           "language_by_filename": file_language(f["filename"])})
    if not files:
        res.warnings.append("the Act record has no files in its ORIGINAL bundle")
    elif len(main) != 1:
        res.warnings.append(f"could not tell which of {len(files)} files is the Act text; none tagged with the doc_id")

    # 4. Everything linked to the Act: sections, rules, schedules, notifications ...
    if res.act_id and src.get("collect_subordinate", True):
        total, seen, others = None, 0, []
        for page in range(MAX_LINKED_PAGES):
            url = (f"{api.base}/discover/search/objects?f.act_id={quote(res.act_id)},equals"
                   f"&sort=dc.date.accessioned,ASC&size={PAGE_SIZE}&page={page}")
            records, info = search_objects(api.peek(url))
            total = info.get("totalElements", total)
            if not records:
                break
            seen += len(records)
            res.linked_pages += 1
            # The page itself is source data (section text and footnotes): queue it as a document.
            res.newly_queued += db.enqueue(
                url, source, url_host(url), "document", discovered_from=act_url, priority=20,
                meta={"category": "linked_records", "title": f"{act.get('name')}: linked records, page {page + 1}",
                      "parent_doc_id": doc_id, "year": year, "act_id": res.act_id, "records": len(records)})
            for r in records:
                coll = md(r, "dc.identifier.collection") or "UNKNOWN"
                res.linked[coll] = res.linked.get(coll, 0) + 1
                if coll not in ("ACT", "SECTION"):
                    others.append(r)
            if total is not None and seen >= total:
                break
        else:
            res.warnings.append(f"stopped after {MAX_LINKED_PAGES} pages of linked records")
        if total is not None and seen != total:
            res.warnings.append(f"linked records: read {seen}, the API reports {total}")

        for r in others:
            coll = md(r, "dc.identifier.collection") or "UNKNOWN"
            r_url = f"{api.base}/core/items/{r['uuid']}"
            r_files = original_bitstreams(api.get(f"{r_url}/bundles?embed=bitstreams&size=20", doc_id=doc_id,
                                                  role="bundles"))
            r_year = next((md(r, k) for k in YEAR_FIELDS if md(r, k)), None)
            n = _queue_files(res, api, r_files, doc_id_hint=None, priority=50, discovered_from=r_url,
                             meta={"category": coll.lower(), "title": r.get("name"), "parent_doc_id": doc_id,
                                   "year": r_year, "item_uuid": r["uuid"]})
            res.subordinate_files[coll] = res.subordinate_files.get(coll, 0) + n
            if not r_files:
                res.warnings.append(f"{coll} record {r.get('name')!r} has no files")

        titles = [normalise_title(r.get("name")) for r in others]
        for want in t.get("expect_subordinate", []):
            if not any(normalise_title(want) in have for have in titles):
                res.warnings.append(f"expected subordinate document not linked to the Act: {want!r}")
    elif not res.act_id:
        res.warnings.append("the Act record has no dc.identifier.act_id; linked records not collected")

    res.status = "resolved"
    return res


def discover(cfg: Config, db: StateDB, client: PoliteClient, source: str = "indiacode", *,
             only: list[str] | None = None, refresh: bool = False) -> list[TargetResult]:
    """Read API listings only and queue the files they name. Downloads no documents."""
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
        except (KeyError, TypeError) as e:
            results.append(TargetResult(t["doc_id"], t["title"], "failed",
                                        reason=f"API answer not in the expected shape: {e!r}"))
    return results


def results_to_markdown(results: list[TargetResult]) -> str:
    lines = []
    for r in results:
        lines += [f"### {r.doc_id} — {r.status}", ""]
        if r.reason:
            lines += [f"Reason: {r.reason}", ""]
        if r.act_url:
            lines += [f"Act record: {r.act_url}  "]
        if r.status == "resolved":
            linked = ", ".join(f"{n} {c}" for c, n in sorted(r.linked.items())) or "none"
            sub = ", ".join(f"{n} from {c}" for c, n in sorted(r.subordinate_files.items())) or "none"
            lines += [f"Act files: {r.act_pdfs}; linked records: {linked} (in {r.linked_pages} page(s)); "
                      f"subordinate files: {sub}; newly queued: {r.newly_queued}", ""]
            if r.metadata:
                lines += ["| Field on the record | Value |", "| --- | --- |"]
                lines += [f"| {k} | {v} |" for k, v in r.metadata.items()] + [""]
        for url, why in r.dropped:
            lines.append(f"- dropped {url} ({why})")
        for w in r.warnings:
            lines.append(f"- ⚠ {w}")
        for title, ref in r.candidates:
            lines.append(f"- candidate: {title} — {ref}")
        lines.append("")
    return "\n".join(lines)
