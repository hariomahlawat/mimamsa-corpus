#!/usr/bin/env python3
"""C12 judicial corpus recovery and controlled ingestion.

Sub-commands (run with `python -I -B`):

  build   [--stage DIR]   Process the 4 HF-held Supreme Court originals and the 25 first-tier files
                          acquired in C12; write the files to upload under DIR (repo-relative paths)
                          and the GitHub records next to this tool's folder:
                          INGESTION_LOG.csv, STAGED_MANIFEST.csv, VALIDATION.csv,
                          COVERAGE_BEFORE_AFTER.csv, RECONCILIATION_UPDATE_C12.csv
  --check [--online]      Rebuild into a temporary directory and compare every record above byte for
                          byte. Also checks HF_COMMITS.csv / VERIFICATION.csv against STAGED_MANIFEST.csv.
                          With --online, re-downloads every recorded path at its pinned HF commit
                          into a fresh directory and re-hashes it.
  upload  --commit A|B    One HF commit with parent_commit pinned (A = derived files of the 4 held
                          originals, B = the ingestion). Refuses if any target path already exists.
  verify  --commit A|B    Download every path of that commit at the pinned revision into a fresh
                          directory and compare SHA-256 with STAGED_MANIFEST.csv.

Inputs (read-only): the C12 acquisition manifest, the C11 excluded re-acquisition manifest
(crawler-logged values), the C12 HF hash ledger and retrieved-candidates list, the held-original
sidecars (inputs/held_original_sidecars), the review decisions (inputs/REVIEW_DECISIONS.csv), the
corpus snapshot ad77758d in the git object store, and the bytes in the scratchpad.
Pipeline code reused from the worktree: pipeline.extract (page text, language check, marking rule),
pipeline.judgments (keyword relevance pass, statute references), pipeline.schemas (validation).
"""
from __future__ import annotations

import argparse
import csv
import filecmp
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent                                   # judicial_recovery_c12/
C12 = OUT.parent                                    # C12-CONSOLIDATION/
WT = C12.parents[2]                                 # worktree root
sys.path.insert(0, str(WT))

from pipeline.extract import MARKING, MIN_CHARS_PER_PAGE, page_text, reads_as_english  # noqa: E402
from pipeline.judgments import KEYWORDS, classify, keyword_counts, statute_refs  # noqa: E402
from pipeline.records import section_key  # noqa: E402
from pipeline.schemas import errors as schema_errors  # noqa: E402
from pipeline.schemas import validator  # noqa: E402

SCRATCH = Path("/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad")
DEFAULT_STAGE = SCRATCH / "jr12" / "stage"
C7 = "/home/user/c7"
CORPUS_COMMIT = "ad77758d4569ba6aafa955cc7843d874489e10f7"
REPO = "hariomahlawat/mimamsa-corpus"
HF_BASE_REV = "5524c3d99b6a069249012fecea75093b875a22c7"
RUN_DATE = "2026-11-24"
SCHEMA_VERSION = "0.2.0"
TOOL = "judicial_recovery_c12.py/1.0.0"

ACQ = C12 / "acquisition" / "ACQUISITION_MANIFEST.csv"
REQLOG = C12 / "acquisition" / "REQUEST_LOG.csv"
SOURCES = C12 / "acquisition" / "sources.yaml.snapshot"
T1P = C12 / "acquisition" / "T1_PRIORITISATION.csv"
REACQ = C12.parent / "C11-JUDICIAL-QUALITY" / "excluded" / "RE_ACQUISITION_MANIFEST.csv"
EXCL_SUMMARY = C12.parent / "C11-JUDICIAL-QUALITY" / "excluded" / "EXCLUDED_RANK_SUMMARY.json"
IDENTITY = C12.parent / "C11-JUDICIAL-QUALITY" / "identity" / "outputs" / "IDENTITY_SUMMARY.json"
INC23 = C12.parent / "C11-JUDICIAL-QUALITY" / "identity" / "outputs" / "INCOMPLETE_23_RECOVERY_PLAN.csv"
LEDGER = C12 / "hf_verification_c12" / "HASH_LEDGER.csv.gz"
HF_CAND = C12 / "hf_verification_c12" / "HF_RETRIEVED_CANDIDATES.csv"
SIDECARS = OUT / "inputs" / "held_original_sidecars"
REVIEW = OUT / "inputs" / "REVIEW_DECISIONS.csv"

LETTER_SHARE = 0.5
TERMS = [("for_official_use_only", r"for\s+official\s+use\s+only"), ("restricted", r"\brestricted\b"),
         ("confidential", r"\bconfidential\b"), ("secret", r"\bsecret\b")]

HELD = {   # sha256 -> (doc_id, sidecar file, source enum)
    "187bfd9e00f239529f1bfa088fd5415331f46893713b7af5794e049bebaa2855":
        ("sc-2025-chandrabhan-sudam-sanap-2025insc116", "chandrabhan_sudam_sanap_2025.json", "sci"),
    "adae1b11687f9606ed2d09d3d901590edfcb4a88c747ccde3ccaec9e15315b5d":
        ("sc-2024-ravishankar-tandon-2024insc299", "ravishankar_tandon_2024.json", "sci"),
    "88f84411abdb3028e974792fef51a224770c987a9aa5ff7bc5a58654304738fd":
        ("sc-1963-ram-sarup-judis-3387", "ram_sarup_1963.json", "sci"),
    "cce64004ab57b9747a85482bfddc7a4ebf0d35c5e56a6547b51065754d766787":
        ("sc-2016-ex-hav-mani-ram-bhaira-ca4409-2011", "mani_ram_bhaira_mirror_2016.json", "manual_upload"),
}
HELD_DERIVED = "legal_knowledge/judgment_originals_derived/c12"
ADD = "data/manifest_additions"
ADD_STEM = f"c12_{RUN_DATE}"
PORTAL = {"indian-supreme-court-judgments": "the Supreme Court's e-SCR portal",
          "indian-high-court-judgments": "the eCourts judgments portal"}


# ------------------------------------------------------------------ helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", "-C", C7, *args], capture_output=True, check=True, text=True).stdout


def write_csv(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def corpus_index():
    """doc_id -> selected meta fields of every record in data/meta at the corpus snapshot."""
    names = git("ls-tree", "-r", "--name-only", CORPUS_COMMIT, "data/meta").split()
    p = subprocess.Popen(["git", "-C", C7, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out = {}
    for n in names:
        p.stdin.write(f"{CORPUS_COMMIT}:{n}\n".encode())
        p.stdin.flush()
        size = int(p.stdout.readline().split()[2])
        m = json.loads(p.stdout.read(size))
        p.stdout.read(1)
        out[m["doc_id"]] = {k: m.get(k) for k in ("doc_type", "sha256", "title", "court", "issue_date", "case_numbers",
                                                  "neutral_citation", "needs_ocr", "text_quality", "raw_path")}
    p.stdin.close()
    p.wait()
    sections = set(git("ls-tree", "-r", "--name-only", CORPUS_COMMIT, "data/sections").split())
    return out, sections


def hf_ledger():
    by_sha, paths = defaultdict(list), set()
    with gzip.open(LEDGER, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            by_sha[r["computed_sha256"]].append(r["path"])
            paths.add(r["path"])
    return by_sha, paths


def allowed_hosts():
    """allowed_hosts of every source in the C12 sources.yaml snapshot, minus blocked hosts and the never-contact list."""
    import yaml
    cfg = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    hosts = {h.lower() for s in cfg["sources"].values() for h in s.get("allowed_hosts", [])}
    return hosts - {h.lower() for h in cfg.get("blocked_hosts", [])} - {"aftjabalpur.in", "www.aftjabalpur.in"}


def pdf_analysis(path: Path):
    import pymupdf
    raw = path.read_bytes()
    eof = b"%%EOF" in raw[-1024:]
    with pymupdf.open(path) as d:
        pages = [page_text(p)[0] for p in d]
        raw_pages = [p.get_text("text") for p in d]
    empty = [i + 1 for i, t in enumerate(pages) if len(re.sub(r"\s", "", t)) < MIN_CHARS_PER_PAGE]
    # the brief's sanity test ("mostly dictionary words"): a page whose non-space characters are mostly not
    # letters is a text layer without a usable Unicode map (P&H HC PDFs): counted as a page without usable text.
    # pipeline.extract.reads_as_english alone accepts such files because the e-signature block is English.
    def letter_share(t):
        ns = re.sub(r"\s", "", t)
        return sum(ch.isalpha() for ch in ns) / len(ns) if ns else 0.0
    garbled = [i + 1 for i, t in enumerate(pages) if i + 1 not in empty and letter_share(t) < LETTER_SHARE]
    sample = "\n".join(pages)
    english = reads_as_english(sample)
    counts, lines, ctx = Counter(), Counter(), {}
    for i, t in enumerate(raw_pages):
        for key, rx in TERMS:
            for m in re.finditer(rx, t, flags=re.I):
                counts[key] += 1
                if key not in ctx:
                    a, b = max(0, m.start() - 60), min(len(t), m.end() + 60)
                    ctx[key] = "p%d: %s" % (i + 1, re.sub(r"\s+", " ", t[a:b]).strip())
        for ln in t.splitlines():
            s = ln.strip()
            if s and len(s) <= 40:
                for key, rx in TERMS:
                    m = re.search(rx, s, flags=re.I)
                    if m and (key == "for_official_use_only" or m.group(0).isupper()):
                        lines[key] += 1
    marking = MARKING.search("\n".join(pages[:2]))
    return {"pages": pages, "n": len(pages), "empty": empty, "eof": eof, "english": english,
            "term_counts": dict(counts), "marking_lines": dict(lines), "marking_ctx": ctx,
            "garbled": garbled, "access_marking": marking.group(1) if marking else None, "bytes": len(raw), "sha256": sha256_bytes(raw)}


def page_marked(pages):
    return "\n".join(f"[[page {i + 1}]]\n{t}\n" for i, t in enumerate(pages))


def ck(s):
    m = re.match(r"\s*([A-Za-z.() ]+?)[/ -]+(?:No\.?\s*)?(\d+)\s*(?:/|-|\s+of\s+)\s*(\d{4})", s or "", re.I)
    return (re.sub(r"[^A-Z]", "", m.group(1).upper()), int(m.group(2)), m.group(3)) if m else None


def first_names(title):
    head = re.split(r"\s+(?:versus|Vs\.?|v\.)\s+", title, maxsplit=1, flags=re.I)[0]
    head = re.sub(r"^[A-Za-z.() ]+/\d+/\d{4}\s+of\s+", "", head)
    stop = {"UNION", "INDIA", "OTHERS", "WING", "COMMANDER", "CHIEF", "STAFF", "ARMED", "FORCES", "TRIBUNAL",
            "STATE", "THROUGH", "SECRETARY", "AND", "ORS", "ANOTHER", "RETD", "COMMANDING"}
    return [w for w in re.sub(r"[^A-Z ]", " ", head.upper()).split() if len(w) > 3 and w not in stop]


def marking_text(a):
    return ";".join(f"{k}={v}" for k, v in sorted(a["term_counts"].items())) or "none"


# ------------------------------------------------------------------ duplicate detection
def duplicates(sha, doc_id, court, title, decided, nc, case_nos, idx, by_sha_meta, nc_map, cn_map, ledger):
    hits = []
    if sha in by_sha_meta:
        hits.append("SHA256_IN_CORPUS_META:" + by_sha_meta[sha])
    hf_other = [p for p in ledger.get(sha, [])]
    if hf_other:
        hits.append("SHA256_ON_HF:" + ";".join(sorted(hf_other)))
    if doc_id in idx:
        hits.append("DOC_ID_IN_CORPUS")
    if nc and nc in nc_map:
        hits.append("NEUTRAL_CITATION:" + nc_map[nc])
    for c in case_nos:
        k = ck(c)
        if k and (court, k) in cn_map:
            hits.append("CASE_NUMBER:" + ";".join(sorted(cn_map[(court, k)])))
    if decided:
        names = first_names(title)
        same = sorted(d for d, v in idx.items() if v["court"] == court and v["issue_date"] == decided
                      and any(w in (v["title"] or "").upper() for w in names))
        if same:
            hits.append("PARTY_AND_DATE:" + ";".join(same))
    return hits


# ------------------------------------------------------------------ records
def base_record(doc_id, source, url, retrieved_at, sha, raw_path, n):
    return {"schema_version": SCHEMA_VERSION, "doc_id": doc_id, "doc_type": "judgment", "title": None,
            "number": None, "issuing_authority": None, "issue_date": None, "effective_date": None,
            "status": "unknown", "status_note": None, "status_as_of": RUN_DATE, "source": source,
            "source_url": url, "source_aliases": [], "retrieved_at": retrieved_at, "sha256": sha,
            "raw_path": raw_path, "mime_type": "application/pdf", "page_count": n, "access_marking": None,
            "text_method": None, "ocr_confidence": None, "ocr_low_confidence_pages": [], "relations": [],
            "field_provenance": {}}


def text_fields(rec, a, text_path, kw, have_section, doc_ids):
    usable = a["english"] and (len(a["empty"]) + len(a["garbled"])) / max(a["n"], 1) <= 0.5
    if usable:
        rec.update({"text_method": "pdf_text", "text_path": text_path, "text_quality": "ok", "needs_ocr": False,
                    "pages_without_text": a["empty"], "access_marking": a["access_marking"]})
        rec["field_provenance"].update({"page_count": "rule", "text_method": "rule"})
        if classify(keyword_counts("\n".join(a["pages"]))) == "rejected" and not kw:
            cited, edges = [], []                  # pipeline rule: no statute pass on a keyword-rejected text
        else:
            cited, edges = statute_refs(page_marked(a["pages"]), have_section)
        rec["statutes_cited"] = [{**c, "act_doc_id": c["act_doc_id"] if c["act_doc_id"] in doc_ids else None}
                                 for c in cited]
        rec["relations"] = [{"schema_version": SCHEMA_VERSION, "source_doc_id": rec["doc_id"], "type": "cites",
                             "target_doc_id": t, "target_ref_raw": raw, "effective_date": None, "evidence": ev,
                             "confidence": "extracted"} for t, raw, ev in edges]
        if cited:
            rec["field_provenance"]["statutes_cited"] = "rule"
    else:
        rec.update({"text_method": None, "text_path": None, "text_quality": "suspect", "needs_ocr": True,
                    "pages_without_text": list(range(1, a["n"] + 1)), "access_marking": None,
                    "statutes_cited": []})
        rec["field_provenance"].update({"page_count": "rule"})
    return usable


def relevance_obj(a, usable, decision, reason):
    if not usable:
        return {"status": "not_checked", "hits": 0, "keywords": {},
                "note": ("Text layer unusable (font without a Unicode map; does not read as English): keyword pass "
                         "not possible until OCR. C12 review of the page images: " + reason)}
    counts = keyword_counts("\n".join(a["pages"]))
    status = classify(counts)
    if status == "rejected" and decision == "RELEVANT":
        return {"status": "relevant", "hits": 0, "keywords": {},
                "note": ("Keyword pass: 0 hits (the brief's keyword rule alone would reject it). C12 LLM review of "
                         "the text found an armed-forces service-law subject: " + reason)}
    return {"status": status, "hits": sum(counts.values()), "keywords": counts, "note": None}


def validate(rec, held=False):
    errs = schema_errors("document", rec)
    if not held:
        return errs, "VALID" if not errs else "INVALID"
    # held originals: raw_path is the HF held-original path outside data/raw (by design, see README)
    other = [e for e in errs if not e.startswith("raw_path:")]
    probe = dict(rec, raw_path=f"data/raw/sci/0000/{rec['sha256']}.pdf")
    other2 = schema_errors("document", probe)
    if not other and not other2:
        return errs, ("VALID" if not errs else "VALID_EXCEPT_RAW_PATH_PATTERN (held original outside data/raw)")
    return errs, "INVALID"


# ------------------------------------------------------------------ build
def build(stage: Path, out: Path):
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    idx, sections = corpus_index()
    doc_ids = set(idx)
    have_section = lambda d, n: f"data/sections/{d}/{section_key(n)}.json" in sections  # noqa: E731
    by_sha_meta = {v["sha256"]: k for k, v in idx.items()}
    nc_map = {v["neutral_citation"]: k for k, v in idx.items() if v.get("neutral_citation")}
    cn_map = defaultdict(set)
    for k, v in idx.items():
        for c in v.get("case_numbers") or []:
            if ck(c):
                cn_map[(v["court"], ck(c))].add(k)
    ledger, hf_paths = hf_ledger()
    hosts = allowed_hosts()
    reqlog = read_csv(REQLOG)
    review = {r["key"]: r for r in read_csv(REVIEW)}
    reacq = {r["sha256"]: r for r in read_csv(REACQ)}
    acq = [r for r in read_csv(ACQ) if r["workstream_target"] == "5"]
    cand = read_csv(HF_CAND)

    log, staged, valid = [], [], []

    def stage_file(commit, rel, data: bytes, kind):
        p = stage / commit / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        staged.append([commit, rel, kind, len(data), sha256_bytes(data),
                       "PATH_ABSENT_AT_" + HF_BASE_REV[:8] if rel not in hf_paths else "PATH_EXISTS_REFUSE"])

    # ---------------- task 1: the 4 HF-held SC originals -> derived text + meta (commit A)
    for c in sorted(cand, key=lambda r: r["hf_sha256"]):
        sha = c["hf_sha256"]
        doc_id, side_name, source = HELD[sha]
        side = json.loads((SIDECARS / side_name).read_text(encoding="utf-8"))
        path = Path(c["saved_to"])
        a = pdf_analysis(path)
        assert a["sha256"] == sha, f"held original {sha[:12]} re-hash mismatch"
        p1 = a["pages"][0] if a["pages"] else ""
        rec = base_record(doc_id, source, side.get("source_url") or side.get("original_url"),
                          (side.get("retrieved_at_utc") or side.get("archived_at_utc")).replace("+00:00", "Z"),
                          sha, c["hf_path"], a["n"])
        text_rel = f"{HELD_DERIVED}/text/{doc_id}.txt"
        usable = text_fields(rec, a, text_rel, None, have_section, doc_ids)
        name = side["case_name"]
        pet, _, resp = name.partition(" v ")
        nc = re.search(r"^\s*(\d{4} INSC \d+)\s*$", p1, re.M)
        cause = re.split(r"J\s*U\s*D\s*G\s*M\s*E\s*N\s*T|O\s*R\s*D\s*E\s*R", p1, maxsplit=1)[0]   # cause title only
        cases = sorted(set(re.sub(r"\s+", " ", m.group(0)).upper() for m in re.finditer(
            r"(?:CRIMINAL|CIVIL)\s+APPEAL\s+No\.?\s*\d+\s+OF\s+\d{4}", cause, re.I)))
        reported = []
        cit = re.search(r"CITATION:\s*\n(.*?)\n", p1)
        if cit:
            reported = [re.sub(r"\s+", " ", x.strip()) for x in re.split(r"\s{3,}", cit.group(1).strip()) if x.strip()]
        judges = []
        mb = re.search(r"BENCH:\n(.*?)\n\s*CITATION:", p1, re.S)
        if mb:
            judges = list(dict.fromkeys(l.strip() for l in mb.group(1).splitlines()
                                        if l.strip() and l.strip() != "BENCH:"))
        rel_status = relevance_obj(a, usable, "", "")
        tier = side.get("source_tier") or ("SC_OFFICIAL_COURT_PDF" if "api.sci.gov.in" in rec["source_url"] else "")
        rec.update({
            "title": name, "number": nc.group(1) if nc else (cases[0] if cases else None),
            "issuing_authority": "Supreme Court of India",
            "issue_date": side.get("decision_date") or side.get("date"), "language": "en", "parent_doc_id": None,
            "original_filename": Path(c["hf_path"]).name,
            "source_record": {"system": "hf-held-original", "record_id": side.get("case_id") or Path(c["hf_path"]).stem,
                              "collection": str(Path(c["hf_path"]).parent), "act_id": None, "handle": None,
                              "listing_raw_path": None},
            "curation_note": (f"Held original on the project HF dataset at {c['hf_path']} (sidecar "
                              f"{Path(c['hf_path']).with_suffix('.json').name}); source tier: {tier}. "
                              "Derived in C12 from bytes re-hashed equal to the sidecar sha256. "
                              + ("NOT an official court copy: third-party mirror of a signed SC order; "
                                 "parity with the official copy not tested. " if source == "manual_upload" else "")
                              + "Not registered as a data/ corpus document (see judicial_recovery_c12/README.md)."),
            "court": "Supreme Court of India", "bench": None, "case_numbers": cases,
            "neutral_citation": nc.group(1) if nc else None, "reported_citations": reported,
            "parties": {"petitioner": [pet.strip()], "respondent": [resp.strip()]} if resp else None,
            "judges": judges, "outcome": None, "cases_cited": [], "topics": [], "relevance": rel_status,
        })
        rec["field_provenance"].update({"title": "human", "issue_date": "human", "parties": "rule",
                                        "case_numbers": "rule", "neutral_citation": "rule", "judges": "rule",
                                        "reported_citations": "rule", "source_url": "human"})
        errs, vres = validate(rec, held=True)
        valid.append([doc_id, f"{HELD_DERIVED}/meta/{doc_id}.json", vres, " | ".join(errs)])
        if usable:
            stage_file("A", text_rel, page_marked(a["pages"]).encode("utf-8"), "text")
        stage_file("A", f"{HELD_DERIVED}/meta/{doc_id}.json",
                   (json.dumps(rec, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), "meta")
        dups = duplicates(sha, doc_id, "Supreme Court of India", name, rec["issue_date"], rec["neutral_citation"],
                          cases, idx, by_sha_meta, nc_map, cn_map, {})
        log.append(["T1-HELD", sha[:12], sha, doc_id, "Supreme Court of India", rec["issue_date"], name,
                    rec["source_url"], "n/a (held original on HF: " + c["hf_path"] + ")", "n/a", "SHA256_EQUALS_SIDECAR",
                    "YES" if a["eof"] else "NO", a["n"], len(a["empty"]), "COMPLETE" if a["eof"] and not a["empty"] else "CHECK",
                    ";".join(dups) or "NONE_IN_DATA_META",
                    f"{rel_status['status']} ({rel_status['hits']} hits)", "rule", marking_text(a),
                    "NO", "DERIVED_TEXT_AND_META_TO_VERSIONED_PATH", "A",
                    "no data/meta or data/text record existed for this doc_id"
                    + ("; an earlier complete page-text version exists at legal_knowledge/full_text_working/v3.5/pages/"
                       + side["case_id"] + ".jsonl (not truncated)" if side.get("case_id") in ("DCLR-SC-1964-A11", "DCLR-SC-2016-L04") else "")])

    # ---------------- task 2: the 25 first-tier files (commit B)
    new_manifest, new_raw, new_sums, overrides, rel_add = [], [], [], [], []
    for r in acq:
        sha = r["sha256"]
        path = Path(r["stored_path"])
        e = reacq[sha]
        rv = review[r["target_id"]]
        a = pdf_analysis(path)
        is_sc = "supreme-court" in r["host"]
        dataset = "indian-supreme-court-judgments" if is_sc else "indian-high-court-judgments"
        year = re.search(r"/year=(\d{4})/", r["url"]).group(1)
        src = "sci" if is_sc else "hc"
        raw_rel = f"data/raw/{src}/{year}/{sha}.pdf"
        doc_id = e["doc_id"]
        fname = r["url"].rsplit("/", 1)[1]
        stem = fname[:-4]
        title = e["title"].strip()
        provenance = []
        provenance.append("SHA256_MATCH" if a["sha256"] == sha == r["expected_sha256"] or a["sha256"] == sha else "SHA256_MISMATCH")
        provenance.append("CRAWLER_LOGGED_SHA256_EQUAL" if sha == e["sha256"] else "CRAWLER_SHA256_DIFFERS")
        provenance.append("HOST_ALLOW_LISTED" if r["host"] in hosts else "HOST_NOT_ALLOW_LISTED")
        provenance.append("URL_EQUALS_CRAWLER_SOURCE_URL" if r["url"] == e["source_url"] else "URL_DIFFERS_FROM_CRAWLER")
        logged = [q for q in reqlog if q["url"] == r["url"] and q["status"] == "200" and q["purpose"] == "document"]
        provenance.append(f"REQUEST_LOG_200x{len(logged)}" if logged else "NOT_IN_REQUEST_LOG")
        sha_ok = a["sha256"] == sha
        complete = a["eof"] and a["n"] > 0
        if is_sc:
            m = re.search(r"(\d{4})insc(\d+)$", doc_id)
            nc = f"{m.group(1)} INSC {m.group(2)}" if m else None
            parts = re.split(r"\s+versus\s+", title, maxsplit=1, flags=re.I)
            parties = ({"petitioner": [parts[0].strip()], "respondent": [parts[1].strip()]} if len(parts) == 2 else None)
            case_numbers = []
            p1 = a["pages"][0]
            scr = re.search(r"\[(\d{4})\]\s*(\d+)\s*S\.\s*C\.\s*R\.\s*(\d+)", p1)
            reported = [f"[{scr.group(1)}] {scr.group(2)} S.C.R. {scr.group(3)}"] if scr else []
            judges, bench, nc_prov = [], None, "crawler"
        else:
            m = re.match(r"^\s*([A-Za-z.() ]{1,25}/\d+/\d{4})\s+of\s+(.*)$", title, re.S)
            case_numbers = [m.group(1).strip()] if m else []
            sides = re.split(r"\s+V[sS]\.?\s+", m.group(2) if m else title, maxsplit=1)
            parties = {"petitioner": [sides[0].strip()], "respondent": [sides[1].strip()]} if len(sides) == 2 else None
            nc = rv["neutral_citation_visual"] or None
            judges = [j for j in rv["judges_visual"].split(";") if j]
            bench = rv["bench_visual"] or None
            reported, nc_prov = [], "llm"
        dups = duplicates(sha, doc_id, e["court"], title, e["decided"], nc, case_numbers, idx, by_sha_meta,
                          nc_map, cn_map, ledger)
        rec = base_record(doc_id, src, r["url"], re.sub(r"\.\d+", "", r["retrieved_at"]), sha, raw_rel, a["n"])
        usable = text_fields(rec, a, f"data/text/{doc_id}.txt", rv["relevance_decision"].startswith("RELEVANT"), have_section, doc_ids)
        relv = relevance_obj(a, usable, "RELEVANT" if rv["relevance_decision"].startswith("RELEVANT") else "",
                             rv["relevance_reason"])
        topics = [t for t in rv["topics"].split(";") if t] if rv["relevance_decision"].startswith("RELEVANT") else []
        rec.update({
            "title": title, "number": nc or (case_numbers[0] if case_numbers else None),
            "issuing_authority": e["court"], "issue_date": e["decided"], "language": "en" if is_sc else None,
            "parent_doc_id": None, "original_filename": fname,
            "source_record": {"system": f"aws-open-data:{dataset}",
                              "record_id": stem.split("_")[0] if not is_sc else stem,
                              "collection": None if is_sc else re.search(r"/bench=([^/]+)/", r["url"]).group(1),
                              "act_id": None, "handle": None, "listing_raw_path": None},
            "curation_note": (f"From the AWS Open Data bucket '{dataset}' (CC-BY-4.0, maintained by P. Vanga / Dattam Labs), "
                              f"a copy of records from {PORTAL[dataset]}. Excluded by the crawler's keyword pass "
                              f"('{e['crawler_reason']}'), ranked first tier in C11, re-acquired in C12 ({r['target_id']}) "
                              "with SHA-256 equal to the crawler-logged value, and ingested in C12 after review "
                              "(judicial_recovery_c12)."),
            "court": e["court"], "bench": bench, "case_numbers": case_numbers, "neutral_citation": nc,
            "reported_citations": reported, "parties": parties, "judges": judges, "outcome": None,
            "cases_cited": [], "topics": topics, "relevance": relv,
        })
        fp = rec["field_provenance"]
        fp.update({"title": "crawler", "issue_date": "crawler", "neutral_citation": nc_prov, "parties": "rule"})
        if not is_sc:
            fp.update({"case_numbers": "rule", "judges": "llm", "bench": "llm"})
        if reported:
            fp["reported_citations"] = "rule"
        if topics:
            fp["topics"] = "llm"
        if relv["status"] != classify(keyword_counts("\n".join(a["pages"]))) or not usable:
            fp["relevance"] = "llm"
        if not nc:
            fp.pop("neutral_citation")
        marked = bool(a["marking_lines"].get("for_official_use_only") or a["access_marking"]
                      or any(a["marking_lines"].values()))
        relevant = rv["relevance_decision"].startswith("RELEVANT")
        if not sha_ok:
            action, reason = "EXCLUDED", "SHA-256 mismatch"
        elif dups:
            action, reason = "ALIAS_ONLY", "duplicate of a held document"
        elif not complete:
            action, reason = "EXCLUDED", "incomplete file"
        elif marked:
            action, reason = "EXCLUDED_MARKING", "access-marking-like line found"
        elif not relevant:
            action, reason = "EXCLUDED_NOT_RELEVANT", rv["relevance_reason"]
        else:
            action, reason = "INGESTED", ("keyword pass not possible (unusable text layer); relevant by scope "
                                          "(writ against an AFT order), confirmed on page images"
                                          if not usable else "relevant on C12 LLM review (keyword pass 0 hits)")
        errs, vres = validate(rec)
        if action == "INGESTED":
            valid.append([doc_id, f"data/meta/{doc_id}.json", vres, " | ".join(errs)])
            stage_file("B", raw_rel, path.read_bytes(), "raw")
            if usable:
                stage_file("B", f"data/text/{doc_id}.txt", page_marked(a["pages"]).encode("utf-8"), "text")
            stage_file("B", f"data/meta/{doc_id}.json",
                       (json.dumps(rec, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), "meta")
            new_manifest.append([doc_id, "judgment", "unknown", r["url"], sha, rec["retrieved_at"]])
            new_raw.append([sha, raw_rel, a["bytes"], "application/pdf", rec["retrieved_at"], r["url"], "", doc_id,
                            "hc-ph" if not is_sc else "sci", "judgment", title, fname, "yes"])
            new_sums.append(f"{sha}  {raw_rel}")
            overrides.append({"sha256": sha, "doc_id": doc_id, "excluded_reason_was": e["crawler_reason"],
                              "now": "ingested", "by": "C12 judicial_recovery_c12", "date": RUN_DATE,
                              "relevance": relv["status"]})
            rel_add += rec["relations"]
        log.append([r["target_id"], sha[:12], sha, doc_id, e["court"], e["decided"], title, r["url"], r["host"],
                    "YES" if r["host"] in hosts else "NO", ";".join(provenance), "YES" if a["eof"] else "NO",
                    a["n"], len(a["empty"]) if usable else a["n"],
                    ("COMPLETE" if complete and usable and not a["empty"] else
                     "COMPLETE_FILE_TEXT_LAYER_UNUSABLE_NEEDS_OCR" if complete and not usable else
                     f"COMPLETE_FILE_PAGES_WITHOUT_TEXT:{','.join(map(str, a['empty']))}" if complete else "INCOMPLETE"),
                    ";".join(dups) or "NONE", f"{relv['status']} ({relv['hits']} hits); review={rv['relevance_decision']}",
                    "llm" if fp.get("relevance") == "llm" else "rule",
                    marking_text(a) + ("; visual: " + rv["visual_check"] if rv["visual_check"] else ""),
                    "YES" if marked else "NO", action, "B" if action == "INGESTED" else "",
                    reason])

    # additive manifest files (commit B)
    if new_manifest:
        def csv_bytes(header, rows):
            s = io.StringIO()
            w = csv.writer(s, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
            return s.getvalue().encode("utf-8")
        stage_file("B", f"{ADD}/{ADD_STEM}_manifest.csv",
                   csv_bytes(["doc_id", "type", "status", "source_url", "sha256", "retrieved_at"], sorted(new_manifest)), "manifest")
        stage_file("B", f"{ADD}/{ADD_STEM}_raw_manifest.csv",
                   csv_bytes(["sha256", "raw_path", "bytes", "content_type", "retrieved_at", "source_url", "source_aliases",
                              "doc_id", "parent_doc_id", "category", "title", "original_filename", "on_this_branch"],
                             sorted(new_raw, key=lambda x: x[1])), "manifest")
        stage_file("B", f"{ADD}/{ADD_STEM}_SHA256SUMS", ("\n".join(sorted(new_sums, key=lambda l: l[66:])) + "\n").encode(), "manifest")
        stage_file("B", f"{ADD}/{ADD_STEM}_excluded_overrides.jsonl",
                   "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in sorted(overrides, key=lambda o: o["doc_id"])).encode(),
                   "manifest")
        if rel_add:
            stage_file("B", f"{ADD}/{ADD_STEM}_relations.jsonl",
                       "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rel_add).encode(), "manifest")
        stage_file("B", f"{ADD}/README.md", MANIFEST_README.encode(), "manifest")

    write_csv(out / "INGESTION_LOG.csv",
              ["target", "sha12", "sha256", "doc_id", "court", "decided", "title", "source_url", "host",
               "host_allow_listed", "provenance_checks", "trailing_eof", "pages", "pages_without_usable_text",
               "completeness", "duplicate_hits", "relevance", "relevance_basis", "marking_scan",
               "marking_excluded", "action", "hf_commit_label", "reason"], log)
    write_csv(out / "STAGED_MANIFEST.csv", ["commit_label", "hf_path", "kind", "bytes", "sha256", "pre_upload_path_state"],
              sorted(staged, key=lambda x: (x[0], x[1])))
    write_csv(out / "VALIDATION.csv", ["doc_id", "record_path", "result", "errors"], valid)
    coverage(out, idx, log)
    return log, staged, valid


MANIFEST_README = """# data/manifest_additions/

Additive manifest files for corpus refreshes made directly on the HF dataset under the standing owner
instruction (docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md). The base files data/manifest.csv,
data/raw_manifest.csv, data/SHA256SUMS and data/excluded_judgments.jsonl are never rewritten in place.

The current corpus view is: base file + every additions file, applied in file-name (date) order.

- `<stem>_manifest.csv`, `<stem>_raw_manifest.csv`: rows with the same columns as the base files.
- `<stem>_SHA256SUMS`: checksum lines for the raw files added.
- `<stem>_excluded_overrides.jsonl`: sha256 values listed in data/excluded_judgments.jsonl that are now
  ingested; for these the exclusion no longer applies.
- `<stem>_relations.jsonl`: edges to append to data/relations.jsonl (only when non-empty).

Records of each refresh (tool, HF commit id, verification) are in GitHub:
legal_knowledge/audit_work/C12-CONSOLIDATION/judicial_recovery_c12/ for c12_2026-11-24.
"""


# ------------------------------------------------------------------ coverage
def coverage(out: Path, idx, log):
    excl = json.loads(EXCL_SUMMARY.read_text(encoding="utf-8"))
    ident = json.loads(IDENTITY.read_text(encoding="utf-8"))
    inc = read_csv(INC23)
    t1 = read_csv(T1P)
    jud = {k: v for k, v in idx.items() if v["doc_type"] in ("judgment", "order")}
    inc_shas = {r["sha256"] for r in inc}
    held_shas = set(HELD)
    ing = [r for r in log if r[20] == "INGESTED"]
    courts = sorted({v["court"] for v in jud.values()})
    rows = []

    def add(ind, scope, before, after, basis):
        rows.append([ind, scope, before, after, after - before if isinstance(before, int) else "", basis])

    add("judgment_metadata_records", "all", len(jud), len(jud) + len(ing), "data/meta records with doc_type judgment/order")
    for c in courts:
        b = sum(1 for v in jud.values() if v["court"] == c)
        add("judgment_metadata_records", c, b, b + sum(1 for r in ing if r[4] == c), "per court")
    files_b = {v["sha256"] for v in jud.values()}
    add("distinct_judgment_files", "data/ corpus", len(files_b), len(files_b | {r[2] for r in ing}), "distinct sha256 among judgment records")
    for c in courts:
        b = {v["sha256"] for v in jud.values() if v["court"] == c}
        add("distinct_judgment_files", c, len(b), len(b | {r[2] for r in ing if r[4] == c}), "per court")
    dj = ident["distinct_judgments"]["revised_distinct_judgments"]
    add("distinct_judgments_c11_identity", "all", dj, dj + len(ing),
        "C11 identity register (3,625) + ingested files; no ingested file matched a held judgment (sha256, case number, "
        "neutral citation, party+date); automated, not a reviewed identity statement")
    inc_data = {s for s in inc_shas if s not in held_shas}
    add("incomplete_files", "C11 INCOMPLETE_23 list", len(inc_shas), len(inc_shas) - len(held_shas),
        "the 4 HF-held SC originals were retrieved, open with %%EOF, every page has text: resolved; 19 remain "
        "(18 truncated HC copies identical on the mirror + d992ac2b with a complete-content copy)")
    add("incomplete_files", "data/ corpus judgment files", len(inc_data & files_b), len(inc_data & files_b),
        "unchanged: no complete replacement exists on any allow-listed host")
    add("complete_judgment_files", "data/ corpus", len(files_b - inc_data), len((files_b | {r[2] for r in ing}) - inc_data),
        "distinct judgment files not in the incomplete list")
    needs_ocr_b = sum(1 for v in jud.values() if v["needs_ocr"] or v["text_quality"] == "suspect")
    add("judgment_records_needing_ocr_or_suspect_text", "data/ corpus", needs_ocr_b,
        needs_ocr_b + sum(1 for r in ing if "NEEDS_OCR" in r[14]), "needs_ocr true or text_quality suspect")
    t1_total = excl["tiers"]["T1"]
    add("t1_titles_held", "all courts", 0, len(ing), f"of {t1_total} first-tier excluded titles (C11 ranking)")
    t1_by_court = {k.split("|", 1)[1]: v for k, v in excl["tier_by_court"].items() if k.startswith("T1|")}
    for c in sorted(t1_by_court):
        add("t1_titles_held", c, 0, sum(1 for r in ing if r[4] == c), f"of {t1_by_court[c]} T1 titles")
    add("t1_titles_acquired_and_reviewed", "all courts", 0, sum(1 for r in log if r[0].startswith("T5-")),
        f"25 acquired in C12; {sum(1 for r in log if r[20] == 'EXCLUDED_NOT_RELEVANT')} excluded on relevance review")
    add("t1_party_and_court_test_titles_held", "C12 T1_PRIORITISATION (71)", 0,
        sum(1 for r in ing if r[3] in {x['doc_id'] for x in t1}), "titles meeting both C12 tests")
    write_csv(out / "COVERAGE_BEFORE_AFTER.csv", ["indicator", "scope", "before", "after", "change", "basis"], rows)

    rec = []
    for r in log:
        rec.append([r[2], r[3], r[0], r[20],
                    {"INGESTED": "C11 excluded tier T1 -> HELD (C12 ingestion, HF commit label B)",
                     "EXCLUDED_NOT_RELEVANT": "C11 excluded tier T1 -> ACQUIRED_REVIEWED_NOT_RELEVANT (bytes kept in scratchpad, not ingested)",
                     "DERIVED_TEXT_AND_META_TO_VERSIONED_PATH":
                         "C11 INCOMPLETE_23 RETRIEVE_HELD_BYTES / C10 UNREGISTERED_HELD -> HELD_ORIGINAL_RETRIEVED_COMPLETE_DERIVED (HF commit label A)"
                     }.get(r[20], r[20]),
                    "overlay; frozen C10/C11 outputs unchanged"])
    write_csv(out / "RECONCILIATION_UPDATE_C12.csv",
              ["sha256", "doc_id", "target", "c12_action", "status_change", "note"], rec)


# ------------------------------------------------------------------ HF
def api():
    from huggingface_hub import HfApi
    return HfApi()


def upload(label: str, stage: Path, out: Path):
    from huggingface_hub import CommitOperationAdd
    rows = [r for r in read_csv(out / "STAGED_MANIFEST.csv") if r["commit_label"] == label]
    commits = read_csv(out / "HF_COMMITS.csv") if (out / "HF_COMMITS.csv").exists() else []
    if any(c["label"] == label for c in commits):
        sys.exit(f"commit {label} already recorded")
    a = api()
    head = a.dataset_info(REPO).sha
    existing = set(a.list_repo_files(REPO, repo_type="dataset", revision=head))
    clash = [r["hf_path"] for r in rows if r["hf_path"] in existing]
    if clash:
        sys.exit(f"refusing: {len(clash)} target paths exist at {head}: {clash[:5]}")
    ops = []
    for r in rows:
        p = stage / label / r["hf_path"]
        assert sha256_file(p) == r["sha256"], p
        ops.append(CommitOperationAdd(path_in_repo=r["hf_path"], path_or_fileobj=str(p)))
    msg = {"A": "C12 judicial recovery: derived text and metadata for 4 HF-held Supreme Court originals",
           "B": "C12 judicial ingestion: 18 first-tier judgments (raw, text, meta) and additive manifests"}[label]
    desc = ("Additive only: new paths, nothing overwritten or deleted. Records: GitHub "
            "legal_knowledge/audit_work/C12-CONSOLIDATION/judicial_recovery_c12/ (STAGED_MANIFEST.csv).")
    info = a.create_commit(REPO, operations=ops, commit_message=msg, commit_description=desc,
                           repo_type="dataset", parent_commit=head)
    cid = info.oid
    commits.append({"label": label, "hf_commit": cid, "parent_commit": head, "files_added": str(len(ops)),
                    "bytes_added": str(sum(int(r["bytes"]) for r in rows)), "message": msg,
                    "paths_prefixes": ";".join(sorted({"/".join(r["hf_path"].split("/")[:3]) for r in rows}))})
    write_csv(out / "HF_COMMITS.csv", list(commits[0].keys()), [list(c.values()) for c in commits])
    print(label, cid, "parent", head)


def verify(label: str, out: Path, dest: Path | None = None):
    from huggingface_hub import hf_hub_download
    commits = {c["label"]: c for c in read_csv(out / "HF_COMMITS.csv")}
    cid = commits[label]["hf_commit"]
    rows = [r for r in read_csv(out / "STAGED_MANIFEST.csv") if r["commit_label"] == label]
    tmp = Path(tempfile.mkdtemp(prefix=f"verify_{label}_", dir=str(dest or SCRATCH / "jr12")))
    res = []
    a = api()
    listed = set(a.list_repo_files(REPO, repo_type="dataset", revision=cid))
    parent = set(a.list_repo_files(REPO, repo_type="dataset", revision=commits[label]["parent_commit"]))
    for r in rows:
        f = hf_hub_download(REPO, r["hf_path"], repo_type="dataset", revision=cid, local_dir=str(tmp))
        got = sha256_file(f)
        res.append([label, cid, r["hf_path"], r["sha256"], got, os.path.getsize(f),
                    "MATCH" if got == r["sha256"] and os.path.getsize(f) == int(r["bytes"]) else "MISMATCH"])
    added = listed - parent
    removed = parent - listed
    res.append([label, cid, "<tree-diff vs parent>", "", "", len(added),
                "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED" if added == {r["hf_path"] for r in rows} and not removed
                else f"UNEXPECTED added={len(added)} removed={len(removed)}"])
    return res


def write_verification(out: Path, labels):
    rows = []
    for lb in labels:
        rows += verify(lb, out)
    write_csv(out / "VERIFICATION.csv", ["label", "hf_commit", "hf_path", "expected_sha256", "downloaded_sha256",
                                         "bytes", "result"], rows)
    bad = [r for r in rows if r[-1] not in ("MATCH", "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED")]
    print("verification rows", len(rows), "problems", len(bad))
    return not bad


# ------------------------------------------------------------------ check
RECORDS = ["INGESTION_LOG.csv", "STAGED_MANIFEST.csv", "VALIDATION.csv", "COVERAGE_BEFORE_AFTER.csv",
           "RECONCILIATION_UPDATE_C12.csv"]


def check(online: bool):
    ok = True
    with tempfile.TemporaryDirectory(dir=str(SCRATCH / "jr12")) as td:
        td = Path(td)
        build(td / "stage", td / "out")
        for n in RECORDS:
            same = filecmp.cmp(OUT / n, td / "out" / n, shallow=False)
            print(("OK      " if same else "DIFFERS ") + n)
            ok &= same
        staged = read_csv(OUT / "STAGED_MANIFEST.csv")
        if (OUT / "VERIFICATION.csv").exists():
            ver = {(r["label"], r["hf_path"]): r for r in read_csv(OUT / "VERIFICATION.csv")}
            for s in staged:
                v = ver.get((s["commit_label"], s["hf_path"]))
                if not v or v["downloaded_sha256"] != s["sha256"] or v["result"] != "MATCH":
                    print("VERIFICATION missing/mismatch", s["hf_path"])
                    ok = False
            commits = {c["label"]: c["hf_commit"] for c in read_csv(OUT / "HF_COMMITS.csv")}
            for v in ver.values():
                if commits.get(v["label"]) != v["hf_commit"]:
                    print("VERIFICATION commit id differs from HF_COMMITS", v["hf_path"])
                    ok = False
            print("OK      VERIFICATION.csv consistent with STAGED_MANIFEST.csv and HF_COMMITS.csv" if ok else "")
        if online:
            for lb in sorted({s["commit_label"] for s in staged}):
                for r in verify(lb, OUT, td):
                    if r[-1] not in ("MATCH", "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED"):
                        print("ONLINE MISMATCH", r)
                        ok = False
            print("online re-download done")
    sums = OUT / "SHA256SUMS"
    if sums.exists():
        for ln in sums.read_text().splitlines():
            h, n = ln.split("  ", 1)
            if sha256_file(OUT / n) != h:
                print("SHA256SUMS mismatch", n)
                ok = False
    print("CHECK", "PASS" if ok else "FAIL")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", choices=["build", "upload", "verify", "sums"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--commit", choices=["A", "B"])
    ap.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check(a.online) else 1)
    if a.cmd == "build":
        log, staged, valid = build(a.stage, OUT)
        print(Counter(r[20] for r in log), len(staged), "staged files", Counter(v[2] for v in valid))
    elif a.cmd == "upload":
        upload(a.commit, a.stage, OUT)
    elif a.cmd == "verify":
        labels = [c["label"] for c in read_csv(OUT / "HF_COMMITS.csv")]
        sys.exit(0 if write_verification(OUT, labels) else 1)
    elif a.cmd == "sums":
        files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*")
                       if p.is_file() and p.name != "SHA256SUMS" and "__pycache__" not in p.parts)
        (OUT / "SHA256SUMS").write_text("".join(f"{sha256_file(OUT / f)}  {f}\n" for f in files))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
