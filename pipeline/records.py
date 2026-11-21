"""Stage 'records': build metadata, section records and relations from what the crawler saved.

Input : state/crawl.sqlite (which file came from where) and the raw files under data/raw/.
Output: data/meta/<doc_id>.json, data/sections/<doc_id>/<key>.json, data/relations.jsonl.

India Code publishes each Act as structured records (one per section, rule, notification ...), so
sections are taken from those records, not cut out of the PDF. Fields the records do not give are
null. Re-running rewrites the outputs for the sources it handles and keeps what the extract stage
added to existing metadata (text_method, page_count, ...).
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .amendments import parse_note, split_footnotes
from .common import SCHEMA_VERSION, Paths, connect, html_to_text, iso_date, slug, write_json

# India Code collection -> (doc_type, doc_id prefix, relation to the parent Act)
COLLECTIONS = {
    "RULE": ("rules", "rules", "implements"),
    "REGULATION": ("regulations", "regs", "implements"),
    "NOTIFICATION": ("notification", "notif", "implements"),
    "ORDER": ("executive_order", "xorder", "implements"),
    "CIRCULAR": ("notification", "circ", "implements"),
    "SCHEDULE": ("schedule", "sched", None),
    "ACT_AMENDMENT": ("act", "act", "amends"),
}
REFERENCE_FIELDS = ("dc.identifier.notification_reference", "dc.identifier.regulation_reference",
                    "dc.identifier.order_reference", "dc.identifier.notification_no")
# "The Indian Penal Code, 45 of 1860 (Rep., Act 45 of 2023)" -> title, number, repealing instrument
REPEAL_TITLE = re.compile(r"^(?P<title>.+?),?\s+(?P<no>\d+)\s+of\s+(?P<year>\d{4})\s*,?\s*\(Rep\.,\s*(?P<by>[^)]+)\)\s*$")
EXTRACT_FIELDS = ("page_count", "text_method", "text_path", "text_quality", "needs_ocr", "pages_without_text",
                  "ocr_confidence", "ocr_low_confidence_pages", "access_marking")


def md(rec: dict, key: str) -> str | None:
    vals = (rec.get("metadata") or {}).get(key) or []
    return vals[0].get("value") if vals else None


def _load_pages(paths: Paths, rows) -> dict[str, tuple[dict, str]]:
    """uuid -> (record, raw_path of the JSON page it came from)."""
    out: dict[str, tuple[dict, str]] = {}
    for r in rows:
        payload = json.loads(paths.raw_file(r["raw_path"]).read_text(encoding="utf-8"))
        for o in payload["_embedded"]["searchResult"].get("_embedded", {}).get("objects", []):
            rec = o["_embedded"]["indexableObject"]
            out[rec["uuid"]] = (rec, r["raw_path"])
    return out


def section_key(number: str) -> str:
    return "s" + (re.sub(r"[^0-9a-z]+", "-", (number or "").lower()).strip("-") or "x")


def build_section(rec: dict, raw_path: str, parent: str, key: str) -> dict:
    name = (rec.get("name") or "").strip()
    text = html_to_text(md(rec, "dc.identifier.section_page_note"))
    history, notes = [], []
    for note in split_footnotes(html_to_text(md(rec, "dc.identifier.section_footnote"))):
        entry = parse_note(note, "footnote")
        (history if entry else notes).append(entry or note)
    gone = re.match(r"^\[?\s*(omitted|repealed|rep\b)", name, re.I)
    if gone:                                   # the note sits in the section text itself
        entry = parse_note(text, "inline")
        if entry:
            entry["footnote_text"] = re.sub(r"\s*\n\s*", " ", text)
            history.append(entry)
    if gone:
        status = "omitted" if gone.group(1).lower() == "omitted" else "repealed"
        note = next((h["footnote_text"] for h in history if h["action"] in ("omitted", "repealed")), None)
        status_note = note or f"Source heading reads {name!r}"
    elif history:
        status, status_note = "amended", f"{len(history)} amendment note(s) on this section"
    else:
        status, status_note = "in_force", None
    if md(rec, "dc.identifier.act_repealed") == "true":
        status, status_note = "repealed", "The Act is marked repealed on India Code"
    page = md(rec, "dc.identifier.page_number")
    order = md(rec, "dc.identifier.order_number")
    return {
        "schema_version": SCHEMA_VERSION,
        "section_id": f"{parent}#{key}",
        "parent_doc_id": parent,
        "unit": "section",
        "number": md(rec, "dc.identifier.section_number") or "",
        "heading": name or None,
        "chapter": None,
        "order": int(order) if order and order.isdigit() else 0,
        "text": text or None,
        "page_start": int(page) if page and page.isdigit() and int(page) > 0 else None,
        "page_end": None,
        "status": status,
        "status_note": status_note,
        "amendment_history": history,
        "notes": notes,
        "source_record": {"system": "indiacode", "record_id": rec["uuid"], "handle": rec.get("handle"),
                          "listing_raw_path": raw_path},
        "field_provenance": {"text": "crawler", "heading": "crawler", "status": "rule", "amendment_history": "rule"},
    }


def _base_doc(row, paths: Paths, aliases: dict[str, list[str]]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": row["source"],
        "source_url": row["url"],
        "source_aliases": [u for u in aliases.get(row["sha256"], []) if u != row["url"]],
        "retrieved_at": row["fetched_at"],
        "sha256": row["sha256"],
        "raw_path": row["raw_path"],
        "mime_type": row["content_type"] or "application/octet-stream",
        "page_count": None, "access_marking": None, "text_method": None, "ocr_confidence": None,
        "ocr_low_confidence_pages": [], "text_path": None, "text_quality": None, "needs_ocr": None,
        "pages_without_text": [],
        "relations": [],
    }


def _status_from_flag(rec: dict, as_of: str) -> tuple[str, str | None]:
    flag = md(rec, "dc.identifier.repealed") or md(rec, "dc.identifier.act_repealed")
    if flag == "true":
        return "repealed", f"Marked repealed on India Code (read {as_of})"
    if flag == "false":
        return "in_force", f"Listed as not repealed on India Code (read {as_of})"
    return "unknown", None


def _edge(src: str, typ: str, target: str | None, raw: str | None, evidence: str, eff: str | None = None) -> dict:
    return {"schema_version": SCHEMA_VERSION, "source_doc_id": src, "type": typ, "target_doc_id": target,
            "target_ref_raw": raw, "effective_date": eff, "evidence": evidence, "confidence": "extracted"}


def build_indiacode(paths: Paths) -> dict:
    conn = connect(paths.db)
    rows = conn.execute(
        """SELECT u.url, u.source, u.doc_id_hint, u.sha256, u.fetched_at, u.meta, f.raw_path, f.content_type
           FROM urls u JOIN files f ON f.sha256 = u.sha256
           WHERE u.source='indiacode' AND u.kind='document' AND u.status='fetched' ORDER BY u.url""").fetchall()
    aliases: dict[str, list[str]] = defaultdict(list)
    for a in conn.execute("SELECT sha256, url FROM aliases"):
        aliases[a["sha256"]].append(a["url"])
    by_parent: dict[str, list] = defaultdict(list)
    for r in rows:
        by_parent[json.loads(r["meta"])["parent_doc_id"]].append(r)

    repealed_by: list[tuple[str, str, str]] = []      # (doc_id, "Act 45 of 2023", record title)
    docs: dict[str, dict] = {}
    sections: dict[str, dict] = {}
    edges: list[dict] = []
    problems: list[str] = []

    for parent, prow in sorted(by_parent.items()):
        metas = [(r, json.loads(r["meta"])) for r in prow]
        records = _load_pages(paths, [r for r, m in metas if m.get("category") == "linked_records"])
        act = next((rec for rec, _ in records.values() if md(rec, "dc.identifier.collection") == "ACT"), None)
        act_page = next((p for rec, p in records.values() if rec is act), None)
        if act is None:
            repealed = [(r, m) for r, m in metas if m.get("repeal_record")]
            if not repealed:
                problems.append(f"{parent}: no ACT record in the saved pages; skipped")
                continue
            for r, m in repealed:
                rr = m["repeal_record"]
                parsed = REPEAL_TITLE.match(rr.get("title") or "")
                as_of = (r["fetched_at"] or "")[:10]
                doc_id = parent if r["doc_id_hint"] else f"{parent}-alt-{r['sha256'][:6]}"
                d = _base_doc(r, paths, aliases)
                d.update({
                    "doc_id": doc_id, "doc_type": "act",
                    "title": (parsed.group("title").strip() if parsed else rr.get("title")),
                    "number": f"{int(parsed.group('no'))} of {parsed.group('year')}" if parsed else None,
                    "issuing_authority": None,
                    "issue_date": iso_date(rr.get("date_issued")),      # the record gives a year only -> null
                    "effective_date": None,
                    "status": "repealed",
                    "status_note": (f"Kept in India Code's '{rr.get('collection_name')}' collection; record title "
                                    f"reads {rr.get('title')!r} (read {as_of})"),
                    "status_as_of": as_of,
                    "language": m.get("language_by_filename"),
                    "parent_doc_id": None if r["doc_id_hint"] else parent,
                    "original_filename": m.get("filename"),
                    "source_record": {"system": "indiacode", "record_id": m.get("item_uuid") or "",
                                      "collection": rr.get("collection_name"), "act_id": None,
                                      "handle": rr.get("handle"), "listing_raw_path": None},
                    "field_provenance": {"title": "rule", "number": "rule", "status": "crawler", "language": "rule"},
                })
                docs[doc_id] = d
                if parsed and r["doc_id_hint"]:
                    repealed_by.append((doc_id, parsed.group("by").strip(), rr.get("title")))
            continue
        as_of = max(r["fetched_at"] for r in prow)[:10]

        # ---- sections
        act_sections = []
        used: Counter = Counter()
        for rec, page in sorted(records.values(), key=lambda x: (int(md(x[0], "dc.identifier.order_number") or 0)
                                                                 if (md(x[0], "dc.identifier.order_number") or "").isdigit()
                                                                 else 0, x[0]["uuid"])):
            if md(rec, "dc.identifier.collection") != "SECTION":
                continue
            key = section_key(md(rec, "dc.identifier.section_number"))
            used[key] += 1
            if used[key] > 1:                  # two records with the same number: keep both, say so
                problems.append(f"{parent}: section number {md(rec, 'dc.identifier.section_number')!r} "
                                f"appears {used[key]} times; later one stored as {key}-dup{used[key]}")
                key = f"{key}-dup{used[key]}"
            sec = build_section(rec, page, parent, key)
            sections[sec["section_id"]] = sec
            act_sections.append(sec)
            for h in sec["amendment_history"]:
                edges.append(_edge(sec["section_id"], "amended_by", None, h["by_ref_raw"] or h["footnote_text"][:200],
                                   h["footnote_text"], h["effective_date"]))

        # ---- the Act's own files
        tally = Counter(s["status"] for s in act_sections)
        changed = sum(v for k, v in tally.items() if k != "in_force")
        if md(act, "dc.identifier.repealed") == "true":
            a_status, a_note = "repealed", f"Marked repealed on India Code (read {as_of})"
        elif changed:
            a_status = "amended"
            a_note = (f"Not repealed on India Code (read {as_of}); {changed} of {len(act_sections)} sections carry "
                      f"amendment notes ({', '.join(f'{v} {k}' for k, v in sorted(tally.items()) if k != 'in_force')})")
        else:
            a_status, a_note = "in_force", f"Listed as not repealed on India Code (read {as_of}); no amendment notes"
        number = (f"{md(act, 'dc.identifier.act_number')} of {md(act, 'dc.date.act_year')}"
                  if md(act, "dc.identifier.act_number") and md(act, "dc.date.act_year") else None)
        year = md(act, "dc.date.act_year")
        authority = "Parliament" if year and year.isdigit() and int(year) >= 1950 else None

        for r, m in metas:
            if m.get("category") != "act":
                continue
            lang = m.get("language_by_filename")
            is_text = bool(r["doc_id_hint"])
            doc_id = parent if is_text else f"{parent}-{'hi' if lang == 'hi' else 'alt-' + r['sha256'][:6]}"
            d = _base_doc(r, paths, aliases)
            d.update({
                "doc_id": doc_id, "doc_type": "act", "title": act.get("name"), "number": number,
                "issuing_authority": authority,
                "issue_date": iso_date(md(act, "dc.date.enact_date")),
                "effective_date": iso_date(md(act, "dc.date.enforcement_date")),
                "status": a_status, "status_note": a_note, "status_as_of": as_of,
                "language": lang, "parent_doc_id": None if is_text else parent,
                "original_filename": m.get("filename"),
                "source_record": {"system": "indiacode", "record_id": act["uuid"], "collection": "ACT",
                                  "act_id": md(act, "dc.identifier.act_id"), "handle": act.get("handle"),
                                  "listing_raw_path": act_page},
                "field_provenance": {"title": "crawler", "number": "crawler", "issue_date": "crawler",
                                     "effective_date": "crawler", "status": "rule", "issuing_authority": "rule",
                                     "language": "rule"},
            })
            docs[doc_id] = d

        # ---- rules, regulations, schedules, notifications ...
        pending = []
        for r, m in metas:
            if m.get("category") in ("act", "linked_records"):
                continue
            rec_page = records.get(m.get("item_uuid"))
            if rec_page is None:
                problems.append(f"{parent}: file {m.get('filename')} has no matching record; skipped")
                continue
            rec, page = rec_page
            coll = md(rec, "dc.identifier.collection")
            if coll not in COLLECTIONS:
                problems.append(f"{parent}: collection {coll!r} not mapped; {m.get('filename')} skipped")
                continue
            doc_type, prefix, _ = COLLECTIONS[coll]
            title = (rec.get("name") or "").strip()
            base = f"{parent}-sched-{slug(title, 40)}" if coll == "SCHEDULE" else f"{prefix}-{slug(title)}"
            pending.append((base, r, m, rec, page, coll, doc_type, title))
        counts = Counter(p[0] for p in pending)
        for base, r, m, rec, page, coll, doc_type, title in pending:
            doc_id = base if counts[base] == 1 and base not in docs else f"{base}-{rec['uuid'][:8]}-{r['sha256'][:4]}"
            status, note = _status_from_flag(rec, as_of)
            d = _base_doc(r, paths, aliases)
            d.update({
                "doc_id": doc_id, "doc_type": doc_type, "title": title or None,
                "number": next((md(rec, k) for k in REFERENCE_FIELDS if md(rec, k)), None),
                "issuing_authority": md(rec, "dc.identifier.ministry_name"),
                "issue_date": iso_date(md(rec, "dc.date.issued")),
                "effective_date": None,
                "status": status, "status_note": note, "status_as_of": as_of,
                "language": None, "parent_doc_id": parent, "original_filename": m.get("filename"),
                "source_record": {"system": "indiacode", "record_id": rec["uuid"], "collection": coll,
                                  "act_id": md(rec, "dc.identifier.act_id"), "handle": rec.get("handle"),
                                  "listing_raw_path": page},
                "field_provenance": {"title": "crawler", "number": "crawler", "issue_date": "crawler",
                                     "issuing_authority": "crawler", "status": "rule"},
            })
            if not d["title"]:
                problems.append(f"{parent}: record {rec['uuid']} has no title")
                continue
            rel = COLLECTIONS[coll][2]
            if rel:
                e = _edge(doc_id, rel, parent, act.get("name"),
                          f"India Code lists this {coll} record under act_id {md(rec, 'dc.identifier.act_id')} "
                          f"({act.get('name')}).")
                d["relations"].append(e)
                edges.append(e)
            docs[doc_id] = d

    conn.close()

    # ---- "Rep., Act 45 of 2023" on a repealed record -> a `repeals` edge from that Act, when it is in the corpus
    by_number = defaultdict(list)
    for d in docs.values():
        if d["doc_type"] == "act" and d["number"] and not d.get("parent_doc_id"):
            by_number[d["number"]].append(d["doc_id"])
    for doc_id, by_raw, title in repealed_by:
        m = re.search(r"(\d+)\s+of\s+(\d{4})", by_raw)
        targets = by_number.get(f"{int(m.group(1))} of {m.group(2)}", []) if m else []
        evidence = f"India Code record title: {title}"
        if len(targets) == 1:
            e = _edge(targets[0], "repeals", doc_id, by_raw, evidence)
            docs[targets[0]]["relations"].append(e)
        else:                                   # the repealing Act is not (uniquely) in the corpus
            e = _edge(doc_id, "superseded_by", None, by_raw, evidence)
            docs[doc_id]["relations"].append(e)
        edges.append(e)

    # ---- remove outputs of an earlier run that this run no longer produces
    if paths.meta.exists():
        for old in paths.meta.glob("*.json"):
            if old.stem not in docs and json.loads(old.read_text(encoding="utf-8")).get("source") == "indiacode":
                old.unlink()
                (paths.text / f"{old.stem}.txt").unlink(missing_ok=True)
    for parent in {sid.split("#")[0] for sid in sections}:
        for old in (paths.sections / parent).glob("*.json"):
            if f"{parent}#{old.stem}" not in sections:
                old.unlink()

    # ---- write (keeping what the extract stage already established)
    for doc_id, d in docs.items():
        path = paths.meta / f"{doc_id}.json"
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            if old.get("sha256") == d["sha256"]:
                for k in EXTRACT_FIELDS:
                    if k in old:
                        d[k] = old[k]
                for k, v in (old.get("field_provenance") or {}).items():
                    d["field_provenance"].setdefault(k, v)
        write_json(path, d)
    for sid, s in sections.items():
        parent, key = sid.split("#")
        write_json(paths.sections / parent / f"{key}.json", s)
    paths.data.mkdir(parents=True, exist_ok=True)
    with (paths.data / "relations.jsonl").open("w", encoding="utf-8") as fh:
        for e in edges:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return {"documents": len(docs), "sections": len(sections), "relations": len(edges), "problems": problems,
            "doc_types": dict(Counter(d["doc_type"] for d in docs.values())),
            "section_status": dict(Counter(s["status"] for s in sections.values()))}
