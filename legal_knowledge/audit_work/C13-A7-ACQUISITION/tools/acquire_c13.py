#!/usr/bin/env python3
"""C13 A7 Part 3: targeted acquisition strictly within the staging allow-list (config/sources.yaml at a4c0c382).

Groups (see README):
  G1  10 Gazette instruments LOCATED_NOT_ACQUIRED in C10/C12, from egazette.gov.in (pins: archive.org md5/bytes)
  G2  archive.org-pinned Gazette issues from the open PRs that the corpus does not hold (PR_PIN_CHECK_C13.csv
      NOT_IN_CORPUS), tried first at the government host egazette.gov.in under the file name the archive.org item
      carries (the rule that holds for every G1 pair), then at archive.org (whose download answers a redirect to a
      storage node; the redirect is recorded, never followed, because no node is allow-listed)
  G3  Supreme Court orders (Ram Avtar C.A. 418/2012 of 10-12-2014; Girish Kumar clarification 2026 INSC 1113):
      looked up in the allow-listed SC open-data bucket index; fetched only on an exact match
  G4  the 19 truncated HC files: the HC open-data index is searched for any other file of the same case
  G5  the 46 first-tier excluded titles that met the C12 party and court tests but were not in the C12 cap of 25
      (crawler-logged sha256 must match)
  G6  targets that need a host outside the allow-list, a login/CAPTCHA, or have no locator: recorded, not requested

Policy: tools/a7net.py (allow-list only, NEVER_CONTACT, HTTPS only, robots.txt, >= 2 s per host, no From header
unless MIMAMSA_CONTACT_EMAIL is set, every request logged, TLS always verified).

Usage:  python -I acquire_c13.py --plan       # write acquisition/TARGETS_C13.csv (no network)
        python -I acquire_c13.py --dry-run    # counts per host from the plan (no network)
        python -I acquire_c13.py              # live run (resumable)
        python -I acquire_c13.py --manifest   # (re)build ACQUISITION_MANIFEST_C13.csv from results + bytes on disk
        python -I acquire_c13.py --check      # re-hash stored bytes and compare with the manifest
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a7net  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "acquisition"
AUDIT = HERE.parents[1]
REPO = HERE.parents[3]
C12 = AUDIT / "C12-CONSOLIDATION"
C11 = AUDIT / "C11-JUDICIAL-QUALITY"
STORE = Path("/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13_a7_acquired")
TARGETS = OUT / "TARGETS_C13.csv"
RESULTS = OUT / "fetch_results_c13.json"
LOG = OUT / "REQUEST_LOG_C13.csv"
MANIFEST = OUT / "ACQUISITION_MANIFEST_C13.csv"
STAGING = "a4c0c382"
FOUO_SHA256 = "4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14"
SC_BUCKET = "https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com"
HC_BUCKET = "https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com"
MARKING_RE = re.compile(r"for official use only|\brestricted\b|\bconfidential\b|\bsecret\b", re.I)
RELEVANCE_RE = re.compile(r"army act|air force act|navy act|armed forces tribunal|\bAFT\b|court[- ]martial|summary of evidence|"
                          r"disability pension|entitlement rules|invalided|release medical board", re.I)

COLS = ["target_id", "group", "priority", "description", "action", "url", "fallback_url", "host", "allow_listed",
        "expected_sha256", "expected_md5", "expected_bytes", "existing_sha256", "original_filename", "match_rule",
        "selection_reason", "provenance"]


def allow_list() -> tuple[set[str], set[str]]:
    txt = subprocess.run(["git", "-C", str(REPO), "show", f"{STAGING}:config/sources.yaml"], check=True,
                         capture_output=True, text=True).stdout
    cfg = yaml.safe_load(txt)
    hosts = set()
    for s in cfg["sources"].values():
        hosts.update(h.lower() for h in s.get("allowed_hosts", []))
    blocked = {h.lower() for h in cfg.get("blocked_hosts", [])} | set(a7net.NEVER_CONTACT)
    hosts = {h for h in hosts if not a7net.under(h, blocked)}
    return hosts, blocked


ALLOWED, FORBIDDEN = allow_list()


def row(**kw) -> dict:
    r = {c: "" for c in COLS}
    r.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
    if r["url"].startswith("https://"):
        h = a7net.host_of(r["url"])
        r["host"] = h
        r["allow_listed"] = "YES" if h in ALLOWED and not a7net.under(h, FORBIDDEN) else "NO"
        if r["action"] in ("FETCH", "LOOKUP") and r["allow_listed"] != "YES":
            r["action"] = "BLOCKED_HOST_NOT_ALLOW_LISTED"
    return r


def egazette_from_archive(ident: str, fname: str) -> str | None:
    m = re.match(r"in\.gazette\.(?:central\.)?[we]\.(\d{4})", ident)
    return f"https://egazette.gov.in/WriteReadData/{m.group(1)}/{fname}" if m else None


def plan() -> list[dict]:
    rows = []
    # G1
    c12 = list(csv.DictReader(open(C12 / "acquisition" / "TARGETS.csv")))
    for t in c12:
        if t["workstream_target"] == "4" and t["url"].startswith("https://egazette.gov.in/"):
            rows.append(row(target_id="C13-G1-" + t["target_id"].split("-", 1)[1], group="G1", priority="1",
                            description=t["description"], action="FETCH", url=t["url"], fallback_url="",
                            expected_md5=t["expected_md5"], expected_bytes=t["expected_bytes"],
                            original_filename=t["original_filename"], match_rule="md5+bytes equal the archive.org pin",
                            selection_reason="C12 LOCATED_NOT_ACQUIRED; egazette TLS chain now verifiable (allowlist/EGAZETTE_TLS_C13.md)",
                            provenance=f"C12 acquisition/TARGETS.csv {t['target_id']}"))
    # G2
    for r in csv.DictReader(open(HERE.parent / "pr_review" / "PR_PIN_CHECK_C13.csv")):
        m = re.match(r"https://archive\.org/download/([^/]+)/(.+)$", r["url"])
        if not m or r["corpus_status"] != "NOT_IN_CORPUS":
            continue
        ident, fname = m.group(1), m.group(2)
        eg = egazette_from_archive(ident, fname)
        rows.append(row(target_id=f"C13-G2-{r['doc_id']}", group="G2", priority="2",
                        description=f"PR #{r['pr']} {r['source']}: {r['title']}", action="FETCH",
                        url=eg or r["url"], fallback_url=r["url"] if eg else "",
                        expected_md5=r["pinned_md5"], expected_bytes=r["pinned_bytes"], original_filename=fname,
                        match_rule="md5+bytes equal the PR pin (= live archive.org metadata 2026-11-25)",
                        selection_reason="pinned in an open crawler PR; not held in the corpus by sha256/md5",
                        provenance=f"PR #{r['pr']} config/sources.yaml {r['source']}; archive item {ident}"))
    # G3
    rows.append(row(target_id="C13-G3-RAM-AVTAR-2014", group="G3", priority="1",
                    description="Union of India v. Ram Avtar, C.A. 418/2012, order of 10-12-2014 (SC)", action="LOOKUP",
                    url=f"{SC_BUCKET}/metadata/parquet/year=2014/metadata.parquet",
                    fallback_url="https://www.sci.gov.in/ (judgment search; CAPTCHA) - not used",
                    match_rule="index row: case number contains 418 and 2012, decision date 2014-12-10, a party 'Ram Avtar'",
                    selection_reason="C12 target 3 BLOCKED (official host not allow-listed); the SC open-data bucket is allow-listed",
                    provenance="C12 acquisition TARGETS T3; CYCLE13_EXECUTION_PLAN A6"))
    rows.append(row(target_id="C13-G3-GIRISH-2026-INSC-1113", group="G3", priority="1",
                    description="Girish Kumar clarification order, 2026 INSC 1113 (SC)", action="LOOKUP",
                    url=f"{SC_BUCKET}/metadata/parquet/year=2026/metadata.parquet",
                    fallback_url="https://www.sci.gov.in/ / https://api.sci.gov.in/ - not allow-listed, not used",
                    match_rule="index row whose citation field equals '2026 INSC 1113'",
                    selection_reason="C12 target 2 BLOCKED; the SC open-data bucket is allow-listed",
                    provenance="C12 acquisition TARGETS T2; CYCLE13_EXECUTION_PLAN A6"))
    # G4
    raw = {r["sha256"]: r for r in csv.DictReader(io.StringIO(subprocess.run(
        ["git", "-C", "/home/user/c7", "show", "ad77758d:data/raw_manifest.csv"], check=True, capture_output=True,
        text=True).stdout))}
    for x in csv.DictReader(open(C12 / "copy_verification_c12" / "COPY_VERIFICATION_MANIFEST.csv")):
        if x["verification_status"] != "BYTE_VERIFIED_INCOMPLETE_DOCUMENT":
            continue
        u = raw[x["computed_sha256"]]["source_url"]
        part = u.split("/data/pdf/")[1].rsplit("/", 1)[0]
        rows.append(row(target_id=f"C13-G4-{x['computed_sha256'][:12]}", group="G4", priority="2",
                        description=f"truncated copy of {x['source_id']}", action="LOOKUP",
                        url=f"{HC_BUCKET}/metadata/parquet/{part}/metadata.parquet", fallback_url=u,
                        existing_sha256=x["computed_sha256"], original_filename=u.rsplit("/", 1)[-1],
                        match_rule="another index row for the same CNR (file name prefix before '_<n>_') with a different PDF",
                        selection_reason="C12 BYTE_VERIFIED_INCOMPLETE_DOCUMENT; the recorded URL is known to serve the same truncated bytes (C12)",
                        provenance="C12 copy_verification_c12/COPY_VERIFICATION_MANIFEST.csv"))
    # G5
    t1 = {r["rank"]: r for r in csv.DictReader(open(C12 / "acquisition" / "T1_PRIORITISATION.csv"))}
    man = {r["rank"]: r for r in csv.DictReader(open(C11 / "excluded" / "RE_ACQUISITION_MANIFEST.csv"))}
    for rank, t in sorted(t1.items(), key=lambda kv: int(kv[0])):
        if t["selected"] != "NO":
            continue
        m = man[rank]
        rows.append(row(target_id=f"C13-G5-EXC-{rank.zfill(4)}", group="G5", priority="3",
                        description=f"{m['court']} {m['decided']} {m['title'][:120]}", action="FETCH", url=m["source_url"],
                        expected_sha256=m["sha256"], original_filename=m["source_url"].rsplit("/", 1)[-1],
                        match_rule="sha256 equals the crawler-logged value",
                        selection_reason=f"T1 rank {rank}; party={t['party_class']}; court={t['court_class']}; qualified in C12, outside the cap of 25",
                        provenance=f"C11 RE_ACQUISITION_MANIFEST.csv {m['doc_id']}; C12 T1_PRIORITISATION.csv"))
    # G6
    blocked = [
        ("DESW-ER-2023-50MB", "https://desw.gov.in/sites/default/files/Entitlement%20Rules%202023.pdf", "Entitlement Rules 2023, 49.9 MB DESW copy (PR #9)"),
        ("DESW-GMO-2023", "https://desw.gov.in/sites/default/files/2026-10/GMO%202023.pdf", "Guide to Medical Officers (Military Pensions) 2023 (PR #9)"),
        ("DESW-PRA-2008", "https://desw.gov.in/", "Pension Regulations for the Army 2008 Parts I and II (C12)"),
        ("DESW-ER-2008", "https://desw.gov.in/", "Entitlement Rules 2008 (C12)"),
        ("DESW-CIRCULARS", "https://desw.gov.in/", "DESW circulars amending PRA 2008 / ER 2008 (C12)"),
        ("SCI-OFFICIAL-GIRISH", "https://www.sci.gov.in/judgements-judgement-date/", "Girish Kumar clarification, official SCI copy (judgment search has a CAPTCHA)"),
        ("SCI-OFFICIAL-RAM-AVTAR", "https://www.sci.gov.in/judgements-judgement-date/", "Ram Avtar order, official SCI copy (judgment search has a CAPTCHA)"),
    ]
    for key, url, desc in blocked:
        rows.append(row(target_id=f"C13-G6-{key}", group="G6", priority="-", description=desc, action="FETCH", url=url,
                        selection_reason="host not in config/sources.yaml at staging; proposal only (AUTHORISED_SCOPE_C13.md)",
                        provenance="PR #9 / C12 TARGETS / C13 brief"))
    for key, desc, why in [
        ("SRO-258-2002", "S.R.O. 258 of 27-11-2002 (Army Rules r.22, AR-030)",
         "NO_LOCATOR: not on archive.org per ARMY-RULES-CHAIN-01 AR-030; no egazette file URL known (the interactive egazette search was not used); A3 or the owner must supply a locator"),
        ("R15-MILITARY-SECRETARY", "Instrument inserting '[or Military Secretary]' in Army Rule 15 (OQ-A-10/GAP-15)",
         "NO_LOCATOR: the instrument is unidentified (number and date unknown); nothing to request"),
        ("AF-NAVY-RULES", "Official Air Force Rules 1969 / Navy rules copies (A5)",
         "NOT_IN_A7_TARGET_LIST_WITH_LOCATOR: no pinned official URL supplied; out of this run"),
        ("A4-A6-REQUESTS", "ACQUISITION_REQUESTS_*.csv from A4/A6",
         "NONE_FOUND: claude/c13-a4-statutory is at a4c0c382 (no commits); claude/c13-a6-forms has no such file (checked 2026-11-25)"),
    ]:
        rows.append(row(target_id=f"C13-G6-{key}", group="G6", priority="-", description=desc, action=why.split(":")[0],
                        selection_reason=why, provenance="CYCLE13_EXECUTION_PLAN A3/A5/A6; C13 brief"))
    with open(TARGETS, "w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(Counter((r["group"], r["action"]) for r in rows))
    return rows


def analyse_pdf(path: Path) -> dict:
    data = path.read_bytes()
    out = {"bytes": len(data), "md5": hashlib.md5(data).hexdigest(), "is_pdf": data[:5] == b"%PDF-",
           "eof_at_end": b"%%EOF" in data[-2048:]}
    text = ""
    try:
        import pymupdf
        doc = pymupdf.open(str(path))
        out["pages"] = doc.page_count
        chars = []
        for i in range(doc.page_count):
            t = doc[i].get_text("text")
            chars.append(len(t.strip()))
            if i < 6:
                text += t
        out["pages_with_text"] = sum(1 for c in chars if c >= 50)
        out["opens"] = True
        doc.close()
    except Exception as e:  # noqa: BLE001
        out.update({"opens": False, "pages": None, "pages_with_text": None, "open_error": str(e)[:200]})
    if not out["is_pdf"]:
        out["completeness"] = "NOT_A_PDF"
    elif not out["opens"]:
        out["completeness"] = "INCOMPLETE_DOES_NOT_OPEN"
    elif not out["eof_at_end"]:
        out["completeness"] = "INCOMPLETE_NO_TRAILING_EOF"
    elif out["pages_with_text"] < out["pages"]:
        out["completeness"] = f"STRUCTURALLY_COMPLETE; text layer on {out['pages_with_text']}/{out['pages']} pages (OCR needed for the rest)"
    else:
        out["completeness"] = f"COMPLETE (%%EOF at end; opens; text on all {out['pages']} pages)"
    mk = sorted({m.group(0).lower() for m in MARKING_RE.finditer(text)})
    out["access_marking_scan_first_6_pages"] = ";".join(mk) or "none found in text layer"
    out["access_eligibility"] = ("HOLD_MARKING_TERM_FOUND_NEEDS_HUMAN_CHECK" if mk else
                                 ("PUBLIC_OFFICIAL_SOURCE_NO_MARKING_IN_TEXT_LAYER" if out.get("pages_with_text") else
                                  "PUBLIC_OFFICIAL_SOURCE_NO_TEXT_LAYER_MARKING_NOT_CHECKED"))
    rel = sorted({m.group(0).lower() for m in RELEVANCE_RE.finditer(text)})
    out["relevance_keywords_first_6_pages"] = ";".join(rel)
    return out


def store(body: bytes, filename: str) -> tuple[str, Path, bool]:
    sha = hashlib.sha256(body).hexdigest()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename) or "download.pdf"
    d = STORE / sha[:2] / sha
    d.mkdir(parents=True, exist_ok=True)
    p = d / safe
    existed = p.exists()
    if not existed:
        tmp = d / (safe + ".part")
        tmp.write_bytes(body)
        tmp.rename(p)
    return sha, p, existed


def filename_from(headers: dict, url: str, fallback: str) -> str:
    cd = headers.get("content-disposition", "")
    m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
    return unquote(m.group(1)) if m else (fallback or unquote(urlsplit(url).path.rsplit("/", 1)[-1]))


def read_parquet(body: bytes) -> list[dict]:
    import pyarrow.parquet as pq
    return pq.read_table(io.BytesIO(body)).to_pylist()


def fetch_doc(net, t: dict, url: str, attempts: list) -> dict | None:
    r = net.get(url, t["target_id"])
    body = r.pop("body", None)
    attempts.append({k: v for k, v in r.items()})
    if r.get("http_status") != 200 or not body:
        return None
    if body[:5] != b"%PDF-":
        attempts[-1]["status"] = "HTTP_200_NOT_PDF"
        attempts[-1]["note"] = body[:160].decode("latin-1")
        return None
    sha = hashlib.sha256(body).hexdigest()
    if sha == FOUO_SHA256:
        attempts[-1]["status"] = "RESTRICTED_COPY_REFUSED"
        return None
    md5 = hashlib.md5(body).hexdigest()
    checks = []
    if t["expected_sha256"]:
        checks.append(("sha256", sha == t["expected_sha256"]))
    if t["expected_md5"]:
        checks.append(("md5", md5 == t["expected_md5"]))
    if t["expected_bytes"]:
        checks.append(("bytes", len(body) == int(t["expected_bytes"])))
    if t["existing_sha256"]:
        checks.append(("differs_from_truncated", sha != t["existing_sha256"]))
    integrity = ("PIN_VERIFIED: " + ",".join(k for k, _ in checks)) if checks and all(v for _, v in checks) else \
        ("PIN_MISMATCH: " + ",".join(k for k, v in checks if not v)) if checks else "NO_PIN"
    fname = filename_from(r.get("headers") or {}, r["url"], t["original_filename"])
    sha, path, existed = store(body, fname)
    a = analyse_pdf(path)
    return {"status": "DOWNLOADED", "url": r["url"], "requested_url": url, "sha256": sha, "path": str(path),
            "original_filename": fname, "already_in_store": existed, "robots": r.get("robots"),
            "http_headers": r.get("headers"), "redirect_chain": r.get("chain"), "integrity": integrity,
            "retrieved_at": a7net.now(), **a}


def lookup(net, t: dict, attempts: list, cache: dict) -> tuple[list[str], str]:
    """Return candidate PDF URLs for a LOOKUP target and a note."""
    url = t["url"]
    if url not in cache:
        r = net.get(url, t["target_id"], "metadata index")
        body = r.pop("body", None)
        attempts.append({k: v for k, v in r.items()})
        cache[url] = read_parquet(body) if r.get("http_status") == 200 and body else None
    rows = cache[url]
    if rows is None:
        return [], f"index not available ({attempts[-1]['status'] if attempts else 'cached failure'})"
    tid = t["target_id"]
    if tid == "C13-G3-RAM-AVTAR-2014":
        hits = []
        for x in rows:
            blob = json.dumps(x, default=str).upper()
            if "RAM AVTAR" in blob and "2014-12-10" in blob.replace("10-12-2014", "2014-12-10"):
                hits.append(x)
        note = f"{len(rows)} index rows; {len(hits)} with 'RAM AVTAR' and 2014-12-10"
        cands = [f"{SC_BUCKET}/data/pdf/year=2014/english/{quote(str(x['path']))}_EN.pdf" for x in hits if x.get("path")
                 and re.search(r"\b418\b", json.dumps(x, default=str))]
        return cands, note + f"; {len(cands)} also carry 418"
    if tid == "C13-G3-GIRISH-2026-INSC-1113":
        hits = [x for x in rows if "2026 INSC 1113" in json.dumps(x, default=str).upper()]
        note = f"{len(rows)} index rows; {len(hits)} carrying '2026 INSC 1113'"
        return [f"{SC_BUCKET}/data/pdf/year=2026/english/{quote(str(x['path']))}_EN.pdf" for x in hits if x.get("path")], note
    if t["group"] == "G4":
        stem = t["original_filename"].split("_", 1)[0]
        own = t["original_filename"]
        hits = [x for x in rows if stem in str(x.get("pdf_link") or "")]
        others = sorted({str(x.get("pdf_link")).rsplit("/", 1)[-1] for x in hits} - {own})
        part = url.split("/metadata/parquet/")[1].rsplit("/", 1)[0]
        note = f"{len(rows)} index rows; {len(hits)} for CNR {stem}; other files: {others or 'none'}"
        return [f"{HC_BUCKET}/data/pdf/{part}/{quote(o)}" for o in others if o.lower().endswith(".pdf")], note
    return [], "no lookup rule"


def run(dry: bool) -> int:
    targets = list(csv.DictReader(open(TARGETS)))
    act = [t for t in targets if t["action"] in ("FETCH", "LOOKUP")]
    print(f"{len(targets)} targets; {len(act)} to request; per host: {dict(Counter(t['host'] for t in act))}")
    for t in act:
        assert t["host"] in ALLOWED and not a7net.under(t["host"], FORBIDDEN), t
    if dry:
        print("blocked/not requested:", dict(Counter(t["action"] for t in targets if t not in act)))
        return 0
    net = a7net.Net("acquire_c13", ALLOWED, FORBIDDEN, LOG)
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    cache: dict = {}
    for t in act:
        tid = t["target_id"]
        if tid in results and results[tid].get("final"):
            continue
        attempts: list = []
        res = None
        note = ""
        if t["action"] == "LOOKUP":
            cands, note = lookup(net, t, attempts, cache)
            for u in cands:
                res = fetch_doc(net, t, u, attempts)
                if res:
                    break
            if res is None:
                res = {"status": "LOOKUP_NO_MATCH" if not cands else attempts[-1]["status"], "note": note}
        else:
            for u in [t["url"]] + ([t["fallback_url"]] if t["fallback_url"].startswith("https://") else []):
                res = fetch_doc(net, t, u, attempts)
                if res:
                    break
            if res is None:
                last = attempts[-1]
                res = {"status": last["status"], "url": last.get("url"), "error": last.get("error", "")}
        res["lookup_note"] = note
        res["attempts"] = attempts
        res["final"] = True
        results[tid] = res
        RESULTS.write_text(json.dumps(results, indent=1, default=str))
        print(tid, res["status"], res.get("integrity", ""), res.get("sha256", "")[:12], (res.get("completeness") or res.get("note") or res.get("error") or "")[:90], flush=True)
    net.close()
    return 0


MCOLS = ["target_id", "group", "description", "action", "status", "requested_url", "final_url", "host", "allow_listed",
         "robots", "http_status_chain", "content_type", "etag", "last_modified", "retrieved_at", "sha256", "md5", "bytes",
         "original_filename", "integrity", "pages", "pages_with_text", "completeness", "access_marking_scan_first_6_pages",
         "access_eligibility", "relevance_keywords_first_6_pages", "corpus_duplicate", "stored_path", "lookup_note",
         "attempts", "selection_reason", "provenance"]


def manifest() -> int:
    targets = list(csv.DictReader(open(TARGETS)))
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    idx = io.StringIO(__import__("gzip").decompress((HERE.parent / "pr_review" / "CORPUS_BYTE_INDEX.csv.gz").read_bytes()).decode())
    corpus = {r["sha256"]: r["path"] for r in csv.DictReader(idx)}
    rows = []
    for t in targets:
        r = results.get(t["target_id"], {})
        h = r.get("http_headers") or {}
        sha = r.get("sha256", "")
        if sha:                                   # re-hash bytes on disk
            data = Path(r["path"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == sha, t["target_id"]
        rows.append({
            "target_id": t["target_id"], "group": t["group"], "description": t["description"], "action": t["action"],
            "status": r.get("status", t["action"] if t["action"] not in ("FETCH", "LOOKUP") else "NOT_RUN"),
            "requested_url": r.get("requested_url", t["url"]), "final_url": r.get("url", ""), "host": t["host"],
            "allow_listed": t["allow_listed"], "robots": r.get("robots", "") or "",
            "http_status_chain": " > ".join(r.get("redirect_chain") or []), "content_type": h.get("content-type", ""),
            "etag": h.get("etag", ""), "last_modified": h.get("last-modified", ""), "retrieved_at": r.get("retrieved_at", ""),
            "sha256": sha, "md5": r.get("md5", ""), "bytes": r.get("bytes", ""), "original_filename": r.get("original_filename", ""),
            "integrity": r.get("integrity", ""), "pages": r.get("pages", ""), "pages_with_text": r.get("pages_with_text", ""),
            "completeness": r.get("completeness", ""), "access_marking_scan_first_6_pages": r.get("access_marking_scan_first_6_pages", ""),
            "access_eligibility": r.get("access_eligibility", ""), "relevance_keywords_first_6_pages": r.get("relevance_keywords_first_6_pages", ""),
            "corpus_duplicate": corpus.get(sha, "") if sha else "", "stored_path": r.get("path", ""),
            "lookup_note": r.get("lookup_note", "") or r.get("note", ""),
            "attempts": " || ".join(f"{a.get('status')} {a.get('url', '')}" + (f" [{a.get('error', '')[:80]}]" if a.get("error") else "")
                                    for a in r.get("attempts", [])),
            "selection_reason": t["selection_reason"], "provenance": t["provenance"]})
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, MCOLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(Counter((r["group"], r["status"], r["integrity"].split(":")[0]) for r in rows))
    return 0


def check() -> int:
    bad = 0
    n = 0
    for r in csv.DictReader(open(MANIFEST)):
        if r["sha256"]:
            n += 1
            p = Path(r["stored_path"])
            if not p.exists():
                print("MISSING (local store cleared?)", r["target_id"], p)
                continue
            if hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]:
                bad += 1
                print("MISMATCH", r["target_id"])
    print(f"CHECK {'OK' if not bad else 'FAIL'}: {n} stored files re-hashed, {bad} mismatches")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--manifest", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.plan:
        plan()
        sys.exit(0)
    sys.exit(manifest() if a.manifest else check() if a.check else run(a.dry_run))
