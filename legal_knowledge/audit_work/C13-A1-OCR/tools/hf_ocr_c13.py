"""Task 5: OCR text of the 12 C12-ingested Punjab and Haryana writs, as NEW versioned HF paths.

    hf-stage    build the staged files + HF_STAGED_MANIFEST.csv + HF_VALIDATION.csv (no network)
    hf-upload   one additive HF commit, parent_commit pinned to the live head (refuses existing paths)
    hf-verify   re-download every staged path at the new commit into a fresh dir; SHA-256 + tree diff

HF layout (nothing existing is touched; the base records at data/meta/<doc_id>.json stay as they are):
    data/text_ocr/c13/<doc_id>.txt                      OCR text with [[page N]] markers
    data/meta_ocr/c13/<doc_id>.json                     overlay metadata record (schema-valid), text_method=ocr
    data/manifest_additions/c13_2026-11-25_ocr_overlays.csv    one row per overlay, with quality indicators
    data/manifest_additions/c13_2026-11-25_SHA256SUMS
    data/manifest_additions/c13_2026-11-25_README.md
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
REPO = OUT.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from c13_a1_ocr import HF_REPO, csv_text, read_csv, restricted  # noqa: E402

from pipeline import relevance_states as rs  # noqa: E402
from pipeline import text_quality as tq  # noqa: E402
from pipeline.judgments import statute_refs  # noqa: E402

STEM = "c13_2026-11-25"
BASE_META = OUT / "inputs" / "c12_base_meta"
STAGE = Path(os.environ.get("C13_A1_STAGE", str(REPO.parent / "a1_work" / "hf_stage")))
ENGINE = ("PaddleOCR 3.7.0 on PaddlePaddle 3.3.1 (Apache-2.0), PP-OCRv5_mobile_det + en_PP-OCRv5_mobile_rec, "
          "CPU, oneDNN off, 200 dpi")
CORPUS_ACTS = {"act-army-1950", "act-air-force-1950", "act-navy-1957", "act-armed-forces-tribunal-2007", "act-ipc-1860",
               "act-crpc-1973", "act-evidence-1872", "act-bns-2023", "act-bnss-2023", "act-bsa-2023"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ocr_pages_meta():
    rows = read_csv(OUT / "OCR_PAGES.csv")
    by = {}
    for r in rows:
        by.setdefault(r["doc_id"], []).append(r)
    return by


def build_files(meta_dir: str = "c13", stem: str = STEM, readme: str | None = None):
    """{hf_path: bytes} for the overlay set, deterministic."""
    rsha, rids = restricted()
    pages_meta = ocr_pages_meta()
    files, overlay_rows, validation = {}, [], []
    from pipeline.schemas import errors
    for mp in sorted(BASE_META.glob("*.json")):
        base = json.loads(mp.read_text(encoding="utf-8"))
        doc = base["doc_id"]
        assert base["sha256"] not in rsha and doc not in rids
        tpath = OUT / "ocr_text" / f"{doc}.txt"
        text = tpath.read_text(encoding="utf-8")
        pm = sorted(pages_meta[doc], key=lambda r: int(r["page"]))
        assert [int(r["page"]) for r in pm] == list(range(1, base["page_count"] + 1)), doc   # full OCR, no early stop
        bad = [int(r["page"]) for r in pm if r["ocr_text_usable"] != "YES"]
        empty = [int(r["page"]) for r in pm if int(r["chars"]) == 0]
        confs = [float(r["engine_conf_mean"]) for r in pm if r["engine_conf_mean"]]
        pq = [{"page": int(r["page"]), **tq.page_verdict(seg)} for r, seg in
              zip(pm, re.split(r"\[\[page \d+\]\]\n", text)[1:])]
        summary = tq.document_summary({"pages": pq, "truncated": False, "open_error": None})
        d = rs.decide(text=text, quality=summary, ocr_done=True)
        cited, _ = statute_refs(text, lambda *_: False)
        meta = dict(base)
        meta.update({
            "text_method": "ocr", "text_path": f"data/text_ocr/c13/{doc}.txt", "needs_ocr": False,
            "ocr_confidence": round(sum(confs) / len(confs), 1) if confs else None,
            "ocr_low_confidence_pages": bad, "pages_without_text": empty,
            "text_quality": "ok" if not bad else "suspect",
            "relevance": rs.legacy_relevance(d, "C13 A1 re-run on OCR text (keyword pass + rule second check). "),
            "statutes_cited": [{**c, "act_doc_id": c["act_doc_id"] if c["act_doc_id"] in CORPUS_ACTS else None}
                               for c in cited],
            "curation_note": (base.get("curation_note") or "") +
            f" C13 A1: OCR text by {ENGINE} at data/text_ocr/c13/{doc}.txt; this record is an overlay of "
            f"data/meta/{doc}.json, which is unchanged. ocr_confidence is the engine's own mean score (0-100), "
            "recorded but not used for any decision; ocr_low_confidence_pages lists pages whose OCR text fails the "
            "C13 text-quality detector. Status AUTOMATED_CANDIDATE_NOT_VERIFIED.",
        })
        prov = dict(meta.get("field_provenance") or {})
        prov.update({"text_method": "rule", "relevance": "rule", "statutes_cited": "rule"})
        meta["field_provenance"] = prov
        if meta.get("language") is None:
            letters = [c for c in text if c.isalpha()]
            deva = sum("ऀ" <= c <= "ॿ" for c in letters) / max(1, len(letters))
            if deva <= 0.05:
                meta["language"] = "en"
                prov["language"] = "rule"
        errs = errors("document", meta)
        validation.append({"doc_id": doc, "valid": "YES" if not errs else "NO", "errors": "; ".join(errs)[:300]})
        tb = text.encode("utf-8")
        mb = (json.dumps(meta, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        files[f"data/text_ocr/c13/{doc}.txt"] = tb
        files[f"data/meta_ocr/{meta_dir}/{doc}.json"] = mb
        overlay_rows.append({
            "doc_id": doc, "base_meta_path": f"data/meta/{doc}.json", "raw_path": base["raw_path"],
            "raw_sha256": base["sha256"], "overlay_meta_path": f"data/meta_ocr/{meta_dir}/{doc}.json",
            "overlay_meta_sha256": hashlib.sha256(mb).hexdigest(), "ocr_text_path": f"data/text_ocr/c13/{doc}.txt",
            "ocr_text_sha256": hashlib.sha256(tb).hexdigest(), "pages": base["page_count"],
            "pages_ocr_text_usable": base["page_count"] - len(bad), "engine_conf_mean": meta["ocr_confidence"],
            "detector_usable_share": summary["usable_share"], "c13_state": d["state"],
            "keyword_hits": sum((d["keywords"] or {}).values()), "engine": ENGINE,
            "benchmark_class_char_accuracy": "see GitHub OCR_BENCHMARK.json (garbled_text_layer_PH pages GT01-GT02)"})
    ofields = list(overlay_rows[0].keys())
    files[f"data/manifest_additions/{stem}_ocr_overlays.csv"] = csv_text(overlay_rows, ofields).encode("utf-8")
    sums = "".join(f"{hashlib.sha256(b).hexdigest()}  {p}\n" for p, b in sorted(files.items()))
    files[f"data/manifest_additions/{stem}_SHA256SUMS"] = sums.encode("utf-8")
    files[f"data/manifest_additions/{stem}_README.md"] = (readme or README).encode("utf-8")
    return files, validation


README = f"""# data/manifest_additions/{STEM}_* (Cycle 13 workstream A1: OCR overlays)

Additive files only. Nothing existing was changed or removed.

- `data/text_ocr/c13/<doc_id>.txt`: OCR text of a judgment whose PDF text layer is unusable (the
  font has no Unicode map), with `[[page N]]` markers. Engine: {ENGINE}.
- `data/meta_ocr/c13/<doc_id>.json`: an overlay of `data/meta/<doc_id>.json` (which stays as it was),
  valid against `schema/document.schema.json`, with `text_method = ocr`, `text_path` pointing at the OCR
  text, `ocr_confidence` (the engine's own mean score, recorded but never used for decisions) and the
  relevance result of the C13 explicit-state pipeline (`pipeline/relevance_states.py`).
- `{STEM}_ocr_overlays.csv`: one row per overlay with hashes and quality indicators (detector usable-page
  share, pages with usable OCR text).
- `{STEM}_SHA256SUMS`: checksums of every file in this addition (except itself and this README).

Corpus view: for a doc_id listed in `{STEM}_ocr_overlays.csv`, the overlay record replaces the base
record when read; the base file is not rewritten. Status: AUTOMATED_CANDIDATE_NOT_VERIFIED.
Records (tool, commit id, verification): GitHub `legal_knowledge/audit_work/C13-A1-OCR/`.
"""


R1_STEM = "c13_2026-11-25r1"
README_R1 = f"""# data/manifest_additions/{R1_STEM}_* (C13 A1, revision 1 of the OCR overlays)

Supersedes `data/meta_ocr/c13/` and `c13_2026-11-25_ocr_overlays.csv` (which stay unchanged on HF). After an
independent review (C13 A1 findings A1-02..A1-04, A1-08) the explicit-state rule was tightened: IRRELEVANT now
needs usable text on every page, bare service vocabulary blocks removal, and an Armed Forces Tribunal party in the
title makes a writ RELEVANT. Re-derived on the same OCR text (`data/text_ocr/c13/`, unchanged), all 12 writs are
RELEVANT (2 changed from CLASSIFICATION_UNCERTAIN). Corpus view: for these doc_ids read
`data/meta_ocr/c13_r1/<doc_id>.json`. Status AUTOMATED_CANDIDATE_NOT_VERIFIED. Records: GitHub
`legal_knowledge/audit_work/C13-A1-OCR/`.
"""


def build_r1_files():
    files, validation = build_files("c13_r1", R1_STEM, README_R1)
    return {p: b for p, b in files.items() if not p.startswith("data/text_ocr/")}, validation


def stage():
    files, validation = build_files()
    if STAGE.exists():
        shutil.rmtree(STAGE)
    rows = []
    for p, b in sorted(files.items()):
        f = STAGE / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b)
        rows.append({"hf_path": p, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    (OUT / "HF_STAGED_MANIFEST.csv").write_text(csv_text(rows, ["hf_path", "bytes", "sha256"]), encoding="utf-8")
    (OUT / "HF_VALIDATION.csv").write_text(csv_text(validation, ["doc_id", "valid", "errors"]), encoding="utf-8")
    print("staged", len(rows), "valid", sum(v["valid"] == "YES" for v in validation), "/", len(validation))


def upload():
    from huggingface_hub import CommitOperationAdd, HfApi
    sys.path.insert(0, str(REPO / "scripts"))
    from hf_protect import assert_additive
    if (OUT / "HF_COMMITS.csv").exists():
        sys.exit("commit already recorded")
    rows = read_csv(OUT / "HF_STAGED_MANIFEST.csv")
    a = HfApi()
    head = a.dataset_info(HF_REPO).sha
    existing = set(a.list_repo_files(HF_REPO, repo_type="dataset", revision=head))
    clash = [r["hf_path"] for r in rows if r["hf_path"] in existing]
    if clash:
        sys.exit(f"refusing: {len(clash)} target paths exist at {head}: {clash[:5]}")
    local = [(STAGE / r["hf_path"], r["hf_path"]) for r in rows]
    for p, r in zip(local, rows):
        assert sha(p[0]) == r["sha256"], p
    assert_additive(a, HF_REPO, local, revision=head)
    ops = [CommitOperationAdd(path_in_repo=rp, path_or_fileobj=str(lp)) for lp, rp in local]
    msg = "C13 A1: OCR text and overlay metadata for 12 Punjab and Haryana writs with unusable text layers"
    desc = ("Additive only: new versioned paths (data/text_ocr/c13, data/meta_ocr/c13, data/manifest_additions/c13_*); "
            "nothing overwritten or deleted. Records: GitHub legal_knowledge/audit_work/C13-A1-OCR/ (HF_STAGED_MANIFEST.csv).")
    info = a.create_commit(HF_REPO, operations=ops, commit_message=msg, commit_description=desc,
                           repo_type="dataset", parent_commit=head)
    rec = [{"label": "C13-A1-OCR", "hf_commit": info.oid, "parent_commit": head, "files_added": len(ops),
            "bytes_added": sum(int(r["bytes"]) for r in rows), "message": msg}]
    (OUT / "HF_COMMITS.csv").write_text(csv_text(rec, list(rec[0].keys())), encoding="utf-8")
    print(info.oid, "parent", head)


def verify():
    from huggingface_hub import HfApi, hf_hub_download
    c = read_csv(OUT / "HF_COMMITS.csv")[0]
    rows = read_csv(OUT / "HF_STAGED_MANIFEST.csv")
    a = HfApi()
    tmp = Path(tempfile.mkdtemp(prefix="verify_c13a1_", dir=str(STAGE.parent)))
    res = []
    for r in rows:
        f = Path(hf_hub_download(HF_REPO, r["hf_path"], repo_type="dataset", revision=c["hf_commit"], local_dir=str(tmp)))
        got = sha(f)
        res.append({"hf_commit": c["hf_commit"], "hf_path": r["hf_path"], "expected_sha256": r["sha256"],
                    "downloaded_sha256": got, "bytes": f.stat().st_size,
                    "result": "MATCH" if got == r["sha256"] and f.stat().st_size == int(r["bytes"]) else "MISMATCH"})
    now = set(a.list_repo_files(HF_REPO, repo_type="dataset", revision=c["hf_commit"]))
    before = set(a.list_repo_files(HF_REPO, repo_type="dataset", revision=c["parent_commit"]))
    added, removed = now - before, before - now
    staged = {r["hf_path"] for r in rows}
    res.append({"hf_commit": c["hf_commit"], "hf_path": "<tree-diff vs parent>", "expected_sha256": "",
                "downloaded_sha256": "", "bytes": len(added),
                "result": "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED" if added == staged and not removed
                else f"UNEXPECTED added={len(added)} removed={len(removed)} extra={sorted(added - staged)[:3]}"})
    (OUT / "HF_VERIFICATION.csv").write_text(csv_text(res, list(res[0].keys())), encoding="utf-8")
    bad = [r for r in res if r["result"] not in ("MATCH", "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED")]
    print("verified", len(res), "problems", len(bad))


def check_records() -> int:
    """Offline: rebuild staged bytes and compare with HF_STAGED_MANIFEST; VERIFICATION consistent."""
    if not (OUT / "HF_STAGED_MANIFEST.csv").exists():
        print("SKIP HF records (not staged)")
        return 0
    files, validation = build_files()
    staged = {r["hf_path"]: r for r in read_csv(OUT / "HF_STAGED_MANIFEST.csv")}
    bad = 0
    # the OCR texts of the first commit must rebuild byte for byte; its meta overlays were superseded by r1
    # (rule revision after review), so they are checked only against the verification record
    texts = {p: b for p, b in files.items() if p.startswith("data/text_ocr/")}
    same = all(hashlib.sha256(b).hexdigest() == staged[p]["sha256"] for p, b in texts.items()) and len(texts) == 12
    print(("OK  " if same else "DIFF"), "HF_STAGED_MANIFEST.csv: 12 OCR texts rebuild byte for byte (meta superseded by r1)")
    bad += not same
    if (OUT / "HF_VERIFICATION.csv").exists():
        ver = {r["hf_path"]: r for r in read_csv(OUT / "HF_VERIFICATION.csv")}
        ok = all(ver.get(p, {}).get("downloaded_sha256") == r["sha256"] and ver[p]["result"] == "MATCH"
                 for p, r in staged.items()) and ver["<tree-diff vs parent>"]["result"] == "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED"
        print(("OK  " if ok else "FAIL"), "HF_VERIFICATION.csv vs staged manifest")
        bad += not ok
    return bad


def main(cmd):
    {"hf-stage": stage, "hf-upload": upload, "hf-verify": verify, "hf-cand-stage": lambda: stage_candidates(),
     "hf-cand-upload": lambda: upload_candidates(), "hf-cand-verify": lambda: verify_candidates()}[cmd]()


# ====================================================================== candidates (review A1-01)
CAND_PREFIX = "legal_knowledge/ingestion_candidates/c13_a1"
CAND_STAGE = STAGE.parent / "hf_stage_candidates"


def build_candidates():
    """Candidate records for held, previously deleted judgments that the C13 rule puts at RELEVANT.
    Not registered in data/ (that needs the bytes copied to data/raw, an owner decision); raw_path points at the
    preserved original on HF, the only schema deviation (as for the C12 held originals)."""
    import c13_a1_ocr as T
    from pipeline.extract import MARKING
    from pipeline.schemas import errors
    T.build_relevance(False)                                   # fills T.BEST_TEXT
    rsha, rids = restricted()
    dec = {r["doc_id"]: r for r in read_csv(OUT / "INGESTION_DECISIONS.csv") if r["action"] == "INGEST_AS_CANDIDATE"}
    rel = {r["doc_id"]: r for r in read_csv(OUT / "RELEVANCE_RERUN.csv")}
    held = {r["doc_id"]: r for r in read_csv(OUT / "inputs" / "HELD_COPIES.csv")}
    c11 = {r["doc_id"]: r for r in read_csv(T.C11_MANIFEST)}
    template = json.loads(sorted(BASE_META.glob("*.json"))[0].read_text(encoding="utf-8"))
    files, rows, validation = {}, [], []
    for doc in sorted(dec):
        h, c, r = held[doc], c11[doc], rel[doc]
        assert h["sha256"] not in rsha and doc not in rids
        side = json.loads((OUT / "inputs" / "a7_sidecars" / f"{h['sha256']}.meta.json").read_text(encoding="utf-8"))
        text = T.BEST_TEXT[doc]
        pages = re.split(r"\[\[page \d+\]\]\n", text)[1:]
        marking = MARKING.search("\n".join(pages[:2]))
        if marking:
            rows.append({"doc_id": doc, "action": "EXCLUDED_ACCESS_MARKING", "marking": marking.group(1)})
            continue
        m = re.match(r"^\s*([A-Za-z.() -]{1,25}/\d+/\d{4})\s+of\s+(.*)$", c["title"], re.S)
        case_no = m.group(1).strip() if m else None
        sides = re.split(r"\s+V[sS]\.?\s+", m.group(2) if m else c["title"], maxsplit=1)
        kws = {k: int(v) for k, v in (x.split("=") for x in r["keywords"].split(";") if x)}
        ocr = r["ocr_engines"]
        meta = {k: None for k in template}
        meta.update({
            "schema_version": template["schema_version"], "doc_id": doc, "doc_type": "judgment", "title": c["title"],
            "number": case_no, "issuing_authority": c["court"], "issue_date": c["decided"] or None, "effective_date": None,
            "status": "unknown", "status_note": None, "status_as_of": side["retrieved_at"][:10], "source": "hc",
            "source_url": c["source_url"], "source_aliases": [], "retrieved_at": side["retrieved_at"], "sha256": h["sha256"],
            "raw_path": h["hf_path"], "mime_type": "application/pdf", "page_count": int(r["pages"]),
            "access_marking": None, "text_method": ("mixed" if ocr and r["ocr_pages"] != r["pages"] else "ocr") if ocr else "pdf_text",
            "ocr_confidence": None, "ocr_low_confidence_pages": [], "relations": [],
            "field_provenance": {"title": "crawler", "issue_date": "crawler", "parties": "rule", "case_numbers": "rule",
                                 "text_method": "rule", "relevance": "rule", "page_count": "rule"},
            "text_path": f"{CAND_PREFIX}/text/{doc}.txt", "text_quality": "ok", "needs_ocr": False,
            "pages_without_text": [], "statutes_cited": [], "language": "en", "parent_doc_id": None,
            "original_filename": side.get("original_filename"),
            "source_record": {"system": "aws-open-data:indian-high-court-judgments",
                              "record_id": (side.get("original_filename") or c["source_url"].rsplit("/", 1)[-1]).split("_")[0],
                              "collection": (re.search(r"bench=([^/]+)", c["source_url"]) or [None, None])[1],
                              "act_id": None, "handle": None, "listing_raw_path": None},
            "curation_note": ("Deleted by the crawler's keyword pass ('no military keyword in the text'); C11 first tier; "
                              f"re-acquired and preserved by C13 A7 ({h['hf_path']}); C13 A1 relevance state RELEVANT "
                              f"({r['reasons'][:200]}). INGESTION CANDIDATE ONLY, not registered in data/. Status "
                              "AUTOMATED_CANDIDATE_NOT_VERIFIED."),
            "court": c["court"], "bench": None, "case_numbers": [case_no] if case_no else [], "neutral_citation": None,
            "reported_citations": [], "parties": ({"petitioner": [sides[0].strip()], "respondent": [sides[1].strip()]}
                                                  if len(sides) == 2 else None),
            "judges": [], "outcome": None, "cases_cited": [], "topics": [],
            "relevance": {"status": "relevant" if r["keyword_status"] == "relevant" else "borderline" if kws else "not_checked",
                          "hits": sum(kws.values()), "keywords": kws, "note": f"C13 state RELEVANT: {r['reasons'][:300]}"},
        })
        meta = {k: v for k, v in meta.items() if v is not None or k in template}
        errs = [e for e in errors("document", meta) if "raw_path" not in e]
        validation.append({"doc_id": doc, "valid_except_raw_path": "YES" if not errs else "NO", "errors": "; ".join(errs)[:300]})
        tb = text.encode("utf-8")
        mb = (json.dumps(meta, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        files[f"{CAND_PREFIX}/text/{doc}.txt"] = tb
        files[f"{CAND_PREFIX}/meta/{doc}.json"] = mb
        rows.append({"doc_id": doc, "action": "CANDIDATE_RECORD_WRITTEN", "marking": "", "preserved_raw": h["hf_path"],
                     "raw_sha256": h["sha256"], "text_sha256": hashlib.sha256(tb).hexdigest(),
                     "meta_sha256": hashlib.sha256(mb).hexdigest(), "text_source": r["text_source"], "ocr_engines": ocr,
                     "keyword_hits": sum(kws.values()), "reason": r["reasons"][:200]})
    fields = ["doc_id", "action", "marking", "preserved_raw", "raw_sha256", "text_sha256", "meta_sha256", "text_source",
              "ocr_engines", "keyword_hits", "reason"]
    files[f"{CAND_PREFIX}/CANDIDATES.csv"] = csv_text(rows, fields).encode("utf-8")
    files[f"{CAND_PREFIX}/README.md"] = (
        "# C13 A1 ingestion candidates\n\nJudgments the crawler deleted as 'no military keyword', later re-acquired and "
        "preserved by C13 A7, that the C13 explicit-state rule (`pipeline/relevance_states.py`) puts at RELEVANT. "
        "Text is the PDF text layer for usable pages and PaddleOCR PP-OCRv5 mobile for unusable pages, with "
        "`[[page N]]` markers. These are candidates only: they are NOT registered in `data/` (that needs the original "
        "bytes copied to `data/raw/`, an owner decision). `raw_path` points at the preserved original, the only "
        "schema deviation. Status AUTOMATED_CANDIDATE_NOT_VERIFIED. Records: GitHub "
        "`legal_knowledge/audit_work/C13-A1-OCR/`.\n").encode("utf-8")
    sums = "".join(f"{hashlib.sha256(b).hexdigest()}  {p}\n" for p, b in sorted(files.items()))
    files[f"{CAND_PREFIX}/SHA256SUMS"] = sums.encode("utf-8")
    r1, r1_val = build_r1_files()
    files.update(r1)
    validation += [{"doc_id": v["doc_id"] + " (overlay r1)", "valid_except_raw_path": v["valid"], "errors": v["errors"]}
                   for v in r1_val]
    return files, validation


def stage_candidates():
    files, validation = build_candidates()
    if CAND_STAGE.exists():
        shutil.rmtree(CAND_STAGE)
    rows = []
    for p, b in sorted(files.items()):
        f = CAND_STAGE / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b)
        rows.append({"hf_path": p, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    (OUT / "HF_CANDIDATES_STAGED_MANIFEST.csv").write_text(csv_text(rows, ["hf_path", "bytes", "sha256"]), encoding="utf-8")
    (OUT / "HF_CANDIDATES_VALIDATION.csv").write_text(
        csv_text(validation, ["doc_id", "valid_except_raw_path", "errors"]), encoding="utf-8")
    print("staged", len(rows), "valid", sum(v["valid_except_raw_path"] == "YES" for v in validation), "/", len(validation))


def upload_candidates():
    from huggingface_hub import CommitOperationAdd, HfApi
    commits = read_csv(OUT / "HF_COMMITS.csv")
    if any(c["label"] == "C13-A1-CANDIDATES" for c in commits):
        sys.exit("candidates commit already recorded")
    rows = read_csv(OUT / "HF_CANDIDATES_STAGED_MANIFEST.csv")
    a = HfApi()
    head = a.dataset_info(HF_REPO).sha
    existing = set(a.list_repo_files(HF_REPO, repo_type="dataset", revision=head))
    clash = [r["hf_path"] for r in rows if r["hf_path"] in existing]
    if clash:
        sys.exit(f"refusing: {len(clash)} target paths exist at {head}")
    ops = []
    for r in rows:
        lp = CAND_STAGE / r["hf_path"]
        assert sha(lp) == r["sha256"], lp
        ops.append(CommitOperationAdd(path_in_repo=r["hf_path"], path_or_fileobj=str(lp)))
    msg = ("C13 A1: ingestion candidates for 12 deleted-then-preserved P&H judgments classified RELEVANT; "
           "revision r1 of the 12 OCR overlay records")
    info = a.create_commit(HF_REPO, operations=ops, commit_message=msg, repo_type="dataset", parent_commit=head,
                           commit_description="Additive only; candidates, not registered in data/. Records: GitHub "
                                              "legal_knowledge/audit_work/C13-A1-OCR/ (HF_CANDIDATES_STAGED_MANIFEST.csv).")
    commits.append({"label": "C13-A1-CANDIDATES", "hf_commit": info.oid, "parent_commit": head, "files_added": len(ops),
                    "bytes_added": sum(int(r["bytes"]) for r in rows), "message": msg})
    (OUT / "HF_COMMITS.csv").write_text(csv_text(commits, list(commits[0].keys())), encoding="utf-8")
    print(info.oid, "parent", head)


def verify_candidates():
    from huggingface_hub import HfApi, hf_hub_download
    c = [x for x in read_csv(OUT / "HF_COMMITS.csv") if x["label"] == "C13-A1-CANDIDATES"][0]
    rows = read_csv(OUT / "HF_CANDIDATES_STAGED_MANIFEST.csv")
    a = HfApi()
    tmp = Path(tempfile.mkdtemp(prefix="verify_c13a1c_", dir=str(STAGE.parent)))
    res = []
    for r in rows:
        f = Path(hf_hub_download(HF_REPO, r["hf_path"], repo_type="dataset", revision=c["hf_commit"], local_dir=str(tmp)))
        got = sha(f)
        res.append({"hf_commit": c["hf_commit"], "hf_path": r["hf_path"], "expected_sha256": r["sha256"],
                    "downloaded_sha256": got, "bytes": f.stat().st_size,
                    "result": "MATCH" if got == r["sha256"] and f.stat().st_size == int(r["bytes"]) else "MISMATCH"})
    now = set(a.list_repo_files(HF_REPO, repo_type="dataset", revision=c["hf_commit"]))
    before = set(a.list_repo_files(HF_REPO, repo_type="dataset", revision=c["parent_commit"]))
    added, removed = now - before, before - now
    staged = {r["hf_path"] for r in rows}
    res.append({"hf_commit": c["hf_commit"], "hf_path": "<tree-diff vs parent>", "expected_sha256": "", "downloaded_sha256": "",
                "bytes": len(added), "result": "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED" if added == staged and not removed
                else f"UNEXPECTED added={len(added)} removed={len(removed)}"})
    (OUT / "HF_CANDIDATES_VERIFICATION.csv").write_text(csv_text(res, list(res[0].keys())), encoding="utf-8")
    print("verified", len(res), "problems", sum(r["result"] not in ("MATCH", "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED") for r in res))


def check_candidates() -> int:
    if not (OUT / "HF_CANDIDATES_STAGED_MANIFEST.csv").exists():
        return 0
    files, validation = build_candidates()
    staged = {r["hf_path"]: r["sha256"] for r in read_csv(OUT / "HF_CANDIDATES_STAGED_MANIFEST.csv")}
    ok = staged == {p: hashlib.sha256(b).hexdigest() for p, b in files.items()}
    print(("OK  " if ok else "DIFF"), "HF_CANDIDATES_STAGED_MANIFEST.csv (rebuilt bytes)")
    bad = not ok
    if (OUT / "HF_CANDIDATES_VERIFICATION.csv").exists():
        ver = {r["hf_path"]: r for r in read_csv(OUT / "HF_CANDIDATES_VERIFICATION.csv")}
        v = all(ver.get(p, {}).get("downloaded_sha256") == h for p, h in staged.items()) and \
            ver["<tree-diff vs parent>"]["result"] == "ONLY_STAGED_PATHS_ADDED_NONE_REMOVED"
        print(("OK  " if v else "FAIL"), "HF_CANDIDATES_VERIFICATION.csv")
        bad += not v
    return int(bad)
