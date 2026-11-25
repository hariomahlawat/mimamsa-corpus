"""C13 A1: OCR recovery and false-negative audit. One tool, deterministic outputs, `--check`.

    python -I -B c13_a1_ocr.py population        # RECOVERY_POPULATION.csv, POPULATION_SUMMARY.json
    python -I -B c13_a1_ocr.py detector-eval     # DETECTOR_VALIDATION.csv/.json from labels + page verdicts
    python -I -B c13_a1_ocr.py bench-score       # OCR_BENCHMARK.csv/.json from benchmark/<engine>/ vs ground_truth/
    python -I -B c13_a1_ocr.py assemble --cache DIR     # OCR page cache -> ocr_text/<doc_id>.txt (+ OCR_PAGES.csv)
    python -I -B c13_a1_ocr.py relevance [--bytes]      # RELEVANCE_RERUN.csv (states) from ocr_text/ and text layers
    python -I -B c13_a1_ocr.py risk              # RISK_FIGURES.json (measured vs estimated inputs to MISSED_JUDGMENT_RISK.md)
    python -I -B c13_a1_ocr.py hf-stage|hf-upload|hf-verify   # task 5: OCR text of the 12 P&H writs to HF (additive)
    python -I -B c13_a1_ocr.py sums              # SHA256SUMS
    python -I -B c13_a1_ocr.py --check           # rebuild every deterministic output in memory and compare byte for byte

No network except hf-upload / hf-verify (huggingface.co, governance standing instruction).
Byte-dependent steps (text layers of held PDFs) read the session scratchpad; when those bytes are absent
`--check` reports them SKIPPED rather than failing silently.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
REPO = OUT.parents[2]
sys.path.insert(0, str(REPO))

from pipeline import relevance_states as rs  # noqa: E402
from pipeline import text_quality as tq  # noqa: E402

AUDIT = REPO / "legal_knowledge" / "audit_work"
C11_MANIFEST = AUDIT / "C11-JUDICIAL-QUALITY" / "excluded" / "RE_ACQUISITION_MANIFEST.csv"
C12_INGEST = AUDIT / "C12-CONSOLIDATION" / "judicial_recovery_c12" / "INGESTION_LOG.csv"
SOURCES = REPO / "config" / "sources.yaml"
INP = OUT / "inputs"
SCRATCH = Path("/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/a1_work")
HF_REPO = "hariomahlawat/mimamsa-corpus"
HF_PARENT = "3864faf3bb24edef4bfb18fa0916cc788eb68d79"
NEVER_CONTACT = {"aftjabalpur.in"}
GARBLE = {"control_chars", "private_use", "cid_glyphs", "low_letter_share", "low_dictionary", "implausible_chars",
          "reversed_order", "vertical_order"}


# ------------------------------------------------------------------ helpers
def read_csv(p):
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def csv_text(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    return buf.getvalue()


def js(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def restricted():
    cfg = json.loads((INP / "restricted_material.snapshot.json").read_text(encoding="utf-8"))
    shas, ids = set(), set()
    for it in cfg["items"]:
        shas.add(it["source_sha256"])
        shas.update(it.get("derived_sha256", []))
        ids.add(it["doc_id"])
    return shas, ids


def allow_listed_hosts():
    hosts = set()
    for line in SOURCES.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*allowed_hosts:\s*\[(.*)\]", line)
        if m:
            hosts.update(h.strip() for h in m.group(1).split(","))
    return hosts - NEVER_CONTACT


# ------------------------------------------------------------------ task 1: population
TIER_PRIORITY = {"T1": 1, "T2": 2, "T3": 3, "T4": 3, "T5": 4}


def build_population():
    rsha, rids = restricted()
    held = {r["sha256"]: r for r in read_csv(INP / "HELD_COPIES.csv")}
    quality = {r["sha256"]: r for r in read_csv(INP / "HELD_DOC_TEXT_QUALITY.csv")}
    hosts = allow_listed_hosts()
    rows = []
    for r in read_csv(C11_MANIFEST):
        if r["sha256"] in rsha or r["doc_id"] in rids:
            continue
        host = urllib.parse.urlparse(r["source_url"]).hostname or ""
        h = held.get(r["sha256"])
        q = quality.get(r["sha256"], {})
        ph_t1 = r["tier"] == "T1" and r["court"] == "High Court of Punjab and Haryana"
        if h:
            acq = "HELD_ON_HF"
        elif host in hosts:
            acq = "REACQUIRE_FROM_SOURCE_URL_PENDING_OWNER_APPROVAL_FOR_DOWNLOAD_RUN"
        else:
            acq = "BLOCKED_HOST_NOT_ALLOW_LISTED"
        tranche = 0 if ph_t1 else TIER_PRIORITY.get(r["tier"], 5)
        rows.append({
            "population_id": f"C11X-{int(r['rank']):05d}", "group": "C11_EXCLUDED_FLAGGED", "doc_id": r["doc_id"],
            "court": r["court"], "decided": r["decided"], "c11_tier": r["tier"], "c11_score": r["score"],
            "c11_signals": r["signals"], "sha256": r["sha256"], "source_url": r["source_url"], "host": host,
            "host_allow_listed": "YES" if host in hosts else "NO", "prior_state": "DELETED_AS_NO_MILITARY_KEYWORD",
            "held": "YES" if h else "NO", "held_hf_path": h["hf_path"] if h else "",
            "held_hf_commit": h["hf_commit"] if h else "", "held_as": h["held_as"] if h else "",
            "text_layer_verdict": q.get("verdict", "UNKNOWN_NOT_HELD"), "acquisition_status": acq,
            "priority_tranche": f"P{tranche}"})
    for r in read_csv(INP / "INCORPUS_TEXT_RISK.csv"):
        if r["sha256"] in rsha or r["doc_id"] in rids:
            continue
        q = quality.get(r["sha256"], {})
        rows.append({
            "population_id": "", "group": "IN_CORPUS_TEXT_RISK", "doc_id": r["doc_id"], "court": r["court"],
            "decided": "", "c11_tier": "", "c11_score": "", "c11_signals": "", "sha256": r["sha256"],
            "source_url": "", "host": "", "host_allow_listed": "", "prior_state":
                f"IN_CORPUS relevance={r['relevance']} text_method={r['text_method'] or 'none'} ocr_conf={r['ocr_conf'] or ''}",
            "held": "YES", "held_hf_path": r["raw_path"], "held_hf_commit": "5524c3d9 (byte-verified corpus; git ad77758d)",
            "held_as": "IN_CORPUS_DATA_RAW", "text_layer_verdict": q.get("verdict", ""),
            "acquisition_status": "HELD_IN_CORPUS", "priority_tranche": "P0" if r["relevance"] == "not_checked" else "P1"})
    rows.sort(key=lambda r: (r["group"], r["priority_tranche"], r["population_id"], r["doc_id"]))
    ids = Counter()
    for r in rows:
        if not r["population_id"]:
            ids["ICR"] += 1
            r["population_id"] = f"ICR-{ids['ICR']:04d}"
    log = json.loads((INP / "EXCLUDED_LOG_SUMMARY.json").read_text(encoding="utf-8"))
    c11 = [r for r in rows if r["group"] == "C11_EXCLUDED_FLAGGED"]
    by = defaultdict(Counter)
    for r in c11:
        by[f"{r['c11_tier']}|{r['court']}"][r["acquisition_status"]] += 1
    ph_t1 = [r for r in c11 if r["priority_tranche"] == "P0"]
    summary = {
        "c11_flagged_titles": len(c11),
        "c11_flagged_held": sum(r["held"] == "YES" for r in c11),
        "c11_flagged_need_reacquisition": sum(r["held"] == "NO" for r in c11),
        "c11_flagged_hosts_not_allow_listed": sum(r["host_allow_listed"] == "NO" for r in c11),
        "ph_t1_titles": len(ph_t1), "ph_t1_held": sum(r["held"] == "YES" for r in ph_t1),
        "ph_t1_by_year": dict(sorted(Counter(r["decided"][:4] for r in ph_t1).items())),
        "by_tier_court_acquisition": {k: dict(v) for k, v in sorted(by.items())},
        "by_priority_tranche": dict(sorted(Counter(r["priority_tranche"] for r in c11).items())),
        "excluded_log_total": log["entries"], "excluded_log_not_flagged_by_c11": sum(log["not_flagged_by_court"].values()),
        "excluded_log_not_flagged_by_court": log["not_flagged_by_court"],
        "excluded_log_held": log["held_anywhere_by_sha256"],
        "in_corpus_text_risk_records": sum(r["group"] == "IN_CORPUS_TEXT_RISK" for r in rows),
        "in_corpus_text_risk_distinct_files": len({r["sha256"] for r in rows if r["group"] == "IN_CORPUS_TEXT_RISK"}),
        "download_policy": "No download run was made in C13 A1: CLAUDE.md and the governance file require owner approval for "
                           "each real download run, and no owner directive authorising this run was found. Re-acquisition "
                           "rows are a dry-run plan only.",
    }
    fields = ["population_id", "group", "doc_id", "court", "decided", "c11_tier", "c11_score", "c11_signals", "sha256",
              "source_url", "host", "host_allow_listed", "prior_state", "held", "held_hf_path", "held_hf_commit", "held_as",
              "text_layer_verdict", "acquisition_status", "priority_tranche"]
    return {"RECOVERY_POPULATION.csv": csv_text(rows, fields), "POPULATION_SUMMARY.json": js(summary)}


# ------------------------------------------------------------------ task 2: detector validation
def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(c - h, 3), round(c + h, 3)]


def build_detector_eval():
    verdict = {(r["sha256"], int(r["page"])): r for r in read_csv(INP / "DETECTOR_PAGE_VERDICTS.csv")}
    labels = read_csv(OUT / "ground_truth" / "DETECTOR_LABELS.csv")
    rows, res = [], {}
    for lab in labels:
        v = verdict[(lab["sha256"], int(lab["page"]))]
        # a page flagged only `blank` is "no OCR needed", as in text_quality.document_summary
        pred = v["usable"] == "NO" and v["flags"] != "blank"
        rows.append({**lab, "detector_flags": v["flags"], "detector_unusable": "YES" if pred else "NO"})
    def score(marginal_as, key="label"):
        tp = fp = fn = tn = 0
        for r in rows:
            lab = r[key]
            if lab == "MARGINAL":
                if marginal_as is None:
                    continue
                truth = marginal_as
            elif lab == "NO_CONTENT":
                truth = False
            else:
                truth = lab == "UNUSABLE_NEEDS_OCR"
            pred = r["detector_unusable"] == "YES"
            tp += truth and pred
            fp += (not truth) and pred
            fn += truth and not pred
            tn += (not truth) and not pred
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(tp / (tp + fp), 3) if tp + fp else None, "precision_ci95": wilson(tp, tp + fp),
                "recall": round(tp / (tp + fn), 3) if tp + fn else None, "recall_ci95": wilson(tp, tp + fn)}
    res["marginal_excluded"] = score(None)
    res["marginal_as_unusable"] = score(True)
    res["marginal_as_usable"] = score(False)
    res["with_original_uncorrected_labels"] = score(None, "original_label")
    res["label_corrections"] = sum(1 for r in rows if r.get("correction"))
    res["labels"] = dict(Counter(r["label"] for r in labels))
    res["by_stratum"] = {s: dict(Counter((r["label"], r["detector_unusable"]) for r in rows if r["sample_stratum"] == s).most_common())
                         for s in sorted({r["sample_stratum"] for r in rows})}
    res["by_stratum"] = {s: {f"{k[0]}|pred_unusable={k[1]}": n for k, n in v.items()} for s, v in res["by_stratum"].items()}
    res["errors"] = [{"label_id": r["label_id"], "label": r["label"], "flags": r["detector_flags"]}
                     for r in rows if (r["label"] == "UNUSABLE_NEEDS_OCR") != (r["detector_unusable"] == "YES")
                     and r["label"] != "MARGINAL"]
    res["note"] = ("Labels: one AI labeller (Claude), blind to detector flags, from text-layer excerpts (start/middle/end) "
                   "and, for pages with under 100 characters, a contact sheet of page images. Sample stratified by detector "
                   "stratum (so it over-represents flagged pages); precision/recall are for this stratified sample, not "
                   "corpus prevalence. Not a human review.")
    fields = ["label_id", "sha256", "page", "sample_stratum", "label", "original_label", "correction", "detector_flags",
              "detector_unusable"]
    return {"DETECTOR_VALIDATION.csv": csv_text(rows, fields), "DETECTOR_VALIDATION.json": js(res)}


# ------------------------------------------------------------------ task 3: OCR benchmark scoring
def norm(s: str) -> str:
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def lev(a, b) -> int:
    """Levenshtein distance over sequences (characters or word lists)."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def bag_recall(gt_words, hyp_words):
    g, h = Counter(gt_words), Counter(hyp_words)
    return sum(min(n, h[w]) for w, n in g.items()) / max(1, sum(g.values()))


def content_words(text):
    return [w.lower() for w in re.findall(r"[A-Za-zऀ-ॿ]{4,}", text)]


def build_bench_score():
    gts = read_csv(OUT / "ground_truth" / "GT_MANIFEST.csv")
    bench = OUT / "benchmark"
    engines = sorted(p.name for p in bench.iterdir() if p.is_dir()) if bench.exists() else []
    rows, timings_meta = [], {}
    for e in engines:
        timing = {}
        tf = bench / e / "timing.json"
        if tf.exists():
            t = json.loads(tf.read_text(encoding="utf-8"))
            timing = {p["gt_id"]: p for p in t["pages"]}
            timings_meta[e] = {"dpi": t["dpi"], "threads": t["threads"], "model_load_seconds": t["model_load_seconds"]}
        for g in gts:
            hp = bench / e / f"{g['gt_id']}.txt"
            if not hp.exists():
                continue
            gt = norm((OUT / "ground_truth" / g["gt_file"]).read_text(encoding="utf-8"))
            hyp = norm(hp.read_text(encoding="utf-8"))
            cer = lev(hyp, gt) / max(1, len(gt))
            gw, hw = gt.split(), hyp.split()
            wer = lev(hw, gw) / max(1, len(gw))
            cer_ci = lev(hyp.lower(), gt.lower()) / max(1, len(gt))
            rows.append({"engine": e, "gt_id": g["gt_id"], "category": g["category"], "gt_chars": len(gt),
                         "cer": round(cer, 4), "cer_caseless": round(cer_ci, 4), "wer": round(wer, 4),
                         "char_accuracy": round(max(0.0, 1 - cer), 4), "word_accuracy": round(max(0.0, 1 - wer), 4),
                         "content_word_recall": round(bag_recall(content_words(gt), content_words(hyp)), 4),
                         "seconds": timing.get(g["gt_id"], {}).get("seconds", ""),
                         "page_covered": "YES" if len(hyp) >= 0.5 * len(gt) else "NO"})
    agg = {}
    for e in engines:
        rr = [r for r in rows if r["engine"] == e]
        if not rr:
            continue
        en = [r for r in rr if "bilingual" not in r["category"]]
        def mean(k, L):
            vals = [r[k] for r in L if r[k] != ""]
            return round(sum(vals) / len(vals), 4) if vals else None
        agg[e] = {"pages": len(rr), "mean_char_accuracy_all": mean("char_accuracy", rr),
                  "mean_word_accuracy_all": mean("word_accuracy", rr),
                  "mean_char_accuracy_english_pages": mean("char_accuracy", en),
                  "mean_word_accuracy_english_pages": mean("word_accuracy", en),
                  "mean_content_word_recall": mean("content_word_recall", rr),
                  "pages_covered": sum(r["page_covered"] == "YES" for r in rr),
                  "mean_seconds_per_page": mean("seconds", rr)}
    agg["tesseract"] = {"status": "BLOCKED_PENDING_OWNER_APPROVAL_FOR_SYSTEM_PACKAGE",
                        "note": "Tesseract is not installed and apt is not allowed; not installed, not benchmarked."}
    agg["paddle_hi (PP-OCRv5_server_det + devanagari rec)"] = {
        "status": "FAILED", "note": "MemoryError: tried to allocate 20,150,747,136 bytes on this 15 GB host "
                                    "(benchmark/paddle_hi_server_det_FAILED.txt); replaced by paddle_hi_mobile."}
    for e, t in timings_meta.items():
        if e in agg:
            agg[e].update(t)
    fields = ["engine", "gt_id", "category", "gt_chars", "cer", "cer_caseless", "wer", "char_accuracy", "word_accuracy",
              "content_word_recall", "seconds", "page_covered"]
    return {"OCR_BENCHMARK.csv": csv_text(rows, fields), "OCR_BENCHMARK.json": js(agg)}


# ------------------------------------------------------------------ OCR text assembly
def jobs_index():
    p = INP / "OCR_JOBS.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


CACHE_BY_ENGINE = {"rapidocr": "ocr_cache", "paddle_v5_mobile": "ocr_cache_paddle"}


def assemble(cache: Path):
    """Copy OCR page cache into ocr_text/<doc_id>.txt (page markers) and OCR_PAGES.csv. Writes files."""
    jobs = jobs_index()
    tdir = OUT / "ocr_text"
    tdir.mkdir(exist_ok=True)
    rows = []
    for j in jobs:
        d = (cache.parent / CACHE_BY_ENGINE[j["engine"]]) / j["sha256"]
        pages = []
        for p in j["pages"]:
            f = d / f"page-{p:04d}.json"
            if f.exists():
                pages.append(json.loads(f.read_text(encoding="utf-8")))
        if not pages:
            continue
        es = d / "early_stop.json"
        skipped = json.loads(es.read_text())["pages_not_ocrd"] if es.exists() else []
        body = "".join(f"[[page {p['page']}]]\n{p['text']}\n" for p in pages)
        (tdir / f"{j['doc_id']}.txt").write_text(body, encoding="utf-8")
        for p in pages:
            v = tq.page_verdict(p["text"])
            rows.append({"doc_id": j["doc_id"], "sha256": j["sha256"], "page": p["page"], "seconds": p["seconds"],
                         "load1": p.get("load1", ""), "chars": v["metrics"]["chars"],
                         "ocr_text_usable": "YES" if v["usable"] else "NO", "ocr_text_flags": ";".join(v["flags"]),
                         "dict_ratio": v["metrics"]["dict_ratio"], "engine_conf_mean": p.get("engine_conf_mean", ""),
                         "early_stop_skipped_pages": len(skipped) if p is pages[-1] else "", "engine": j["engine"]})
    fields = ["doc_id", "sha256", "page", "seconds", "load1", "chars", "ocr_text_usable", "ocr_text_flags", "dict_ratio",
              "engine_conf_mean", "early_stop_skipped_pages", "engine"]
    (OUT / "OCR_PAGES.csv").write_text(csv_text(rows, fields), encoding="utf-8")
    return len(rows)


# ------------------------------------------------------------------ task 4: relevance re-run
def text_layer_pages(path):
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)
    from pipeline.extract import page_text
    out = {}
    with pymupdf.open(path) as d:
        for i in range(d.page_count):
            try:
                out[i + 1] = page_text(d[i])[0]
            except Exception:
                out[i + 1] = ""
    return out


def build_relevance(use_bytes: bool):
    """States for every held population document. Text = text layer for usable pages + OCR text for OCR'd pages."""
    quality = read_csv(INP / "HELD_DOC_TEXT_QUALITY.csv")
    pv = defaultdict(dict)
    for r in read_csv(INP / "DETECTOR_PAGE_VERDICTS.csv"):
        pv[r["sha256"]][int(r["page"])] = r
    jobs = {j["sha256"]: j for j in jobs_index()}
    layer_cache = INP / "TEXT_LAYER_USABLE_PAGES.jsonl"
    layer = {}
    if layer_cache.exists():
        for line in layer_cache.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            layer[e["sha256"]] = {int(k): v for k, v in e["pages"].items()}
    titles = {r["doc_id"]: r["title"] for r in read_csv(INP / "TITLES.csv")}
    ocr_engine = {}
    if (OUT / "OCR_PAGES.csv").exists():
        ocr_engine = {(r["sha256"], int(r["page"])): r["engine"] for r in read_csv(OUT / "OCR_PAGES.csv")}
    rsha, rids = restricted()
    rows, seen = [], set()
    for q in quality:
        if q["group"] == "CORPUS_RANDOM_CONTROL" or q["sha256"] in seen:
            continue
        if q["sha256"] in rsha or q["doc_id"] in rids:
            continue
        seen.add(q["sha256"])
        sha = q["sha256"]
        ocr_pages = {}
        tf = OUT / "ocr_text" / f"{q['doc_id']}.txt"
        if sha in jobs and tf.exists():
            for m in re.finditer(r"\[\[page (\d+)\]\]\n(.*?)(?=\n\[\[page \d+\]\]\n|\Z)", tf.read_text(encoding="utf-8"), re.S):
                ocr_pages[int(m.group(1))] = m.group(2)
        lp = layer.get(sha, {})
        n = int(q["pages"])
        texts, pq = [], []
        for p in range(1, n + 1):
            if p in ocr_pages:
                texts.append(ocr_pages[p])
                v = tq.page_verdict(ocr_pages[p])
                pq.append({"page": p, **v})
            else:
                t = lp.get(p, "")
                texts.append(t)
                v = pv[sha].get(p)
                flags = v["flags"].split(";") if v and v["flags"] else []
                pq.append({"page": p, "usable": bool(v) and v["usable"] == "YES", "flags": flags})
        summary = tq.document_summary({"pages": pq, "truncated": q["truncated"] == "YES",
                                       "open_error": "open error" if q["verdict"] == "EXTRACTION_FAILED" and n == 0 else None})
        layer_bad = [p for p in range(1, n + 1) if not (pv[sha].get(p) and pv[sha][p]["usable"] == "YES")
                     and (pv[sha].get(p) or {}).get("flags") not in ("blank",)]
        ocr_done = all(p in ocr_pages for p in layer_bad)
        es = None if ocr_done or not ocr_pages else f"{sum(p not in ocr_pages for p in layer_bad)} unusable pages not OCR'd"
        ocr_v = [tq.page_verdict(t)["metrics"] for t in ocr_pages.values()]
        ocr_quality_ok = all(m["dict_ratio"] >= rs.MIN_OCR_DICT_RATIO or m["devanagari_share"] >= 0.5 or m["chars"] == 0
                             for m in ocr_v)
        engines = sorted({ocr_engine.get((sha, p), "") for p in ocr_pages})
        text = "\n".join(f"[[page {i + 1}]]\n{t}" for i, t in enumerate(texts))
        if q["verdict"] == "EXTRACTION_FAILED" and n == 0:
            d = rs.decide(text=None, quality=None, extraction_error="file does not open (truncated download)")
            if q["truncated"] == "YES":
                d["state"] = "SOURCE_INCOMPLETE"
                d["reasons"] = ["file does not open and has no %%EOF: incomplete at source (C11/C12: remote copy also truncated)"]
        else:
            d = rs.decide(text=text, quality=summary, truncated=q["truncated"] == "YES", ocr_done=ocr_done,
                          ocr_quality_ok=ocr_quality_ok, title=titles.get(q["doc_id"]))
        rows.append({"group": q["group"], "doc_id": q["doc_id"], "court": q["court"], "sha256": sha,
                     "prior_relevance": q["prior_relevance"], "text_layer_verdict": q["verdict"],
                     "pages": n, "ocr_pages": len(ocr_pages), "ocr_incomplete": es or "",
                     "ocr_engines": ";".join(e for e in engines if e),
                     "ocr_min_dict_ratio": min((m["dict_ratio"] for m in ocr_v if m["chars"]), default=""),
                     "provisional": "YES (RapidOCR text)" if "rapidocr" in engines and d["state"] in ("IRRELEVANT", "INSUFFICIENT_TEXT") else "",
                     "text_source": ("ocr+layer" if ocr_pages and lp else "ocr" if ocr_pages else "layer" if lp else "none"),
                     "usable_share_after": summary["usable_share"], "state": d["state"],
                     "keyword_status": d["keyword_status"] or "", "keywords": ";".join(f"{k}={v}" for k, v in sorted((d["keywords"] or {}).items())),
                     "second_check_families": ";".join((d["second_check"] or {}).get("families", [])),
                     "reasons": " | ".join(d["reasons"])})
    rows.sort(key=lambda r: (r["group"], r["doc_id"]))
    fields = ["group", "doc_id", "court", "sha256", "prior_relevance", "text_layer_verdict", "pages", "ocr_pages",
              "ocr_incomplete", "ocr_engines", "ocr_min_dict_ratio", "provisional", "text_source", "usable_share_after", "state", "keyword_status", "keywords",
              "second_check_families", "reasons"]
    summ = {"documents": len(rows), "by_state": dict(sorted(Counter(r["state"] for r in rows).items())),
            "by_group_state": {g: dict(sorted(Counter(r["state"] for r in rows if r["group"] == g).items()))
                               for g in sorted({r["group"] for r in rows})},
            "transitions": dict(sorted(Counter(f"{r['prior_relevance']} -> {r['state']}" for r in rows).items()))}
    # task 6: ingestion decisions. Only held files outside data/ can be newly ingested (C12_PRESERVED_NOT_INGESTED);
    # anything not RELEVANT goes to the review queue instead of being ingested.
    dec = []
    for r in rows:
        if r["group"] in ("C12_PRESERVED_NOT_INGESTED", "C13_A7_PRESERVED_EXCLUDED"):
            action = "INGEST_AS_CANDIDATE" if r["state"] == "RELEVANT" else (
                "NOT_INGESTED_IRRELEVANT" if r["state"] == "IRRELEVANT" else "NOT_INGESTED_MANUAL_REVIEW_REQUIRED")
        elif r["group"] == "C12_INGESTED_T1":
            action = "ALREADY_INGESTED_C12" + ("" if r["state"] == "RELEVANT" else "_MANUAL_REVIEW_REQUIRED")
        else:
            action = "IN_CORPUS_NO_INGESTION" + ("" if r["state"] == "RELEVANT" else f"_{r['state']}")
        dec.append({"doc_id": r["doc_id"], "group": r["group"], "state": r["state"], "action": action,
                    "review_queue": "YES" if r["state"] not in ("RELEVANT", "IRRELEVANT") or r["group"] != "IN_CORPUS_TEXT_RISK" and r["state"] == "IRRELEVANT" else "NO"})
    summ["ingestion_actions"] = dict(sorted(Counter(d["action"] for d in dec).items()))
    summ["newly_ingested_as_candidates"] = sum(d["action"] == "INGEST_AS_CANDIDATE" for d in dec)
    return {"RELEVANCE_RERUN.csv": csv_text(rows, fields), "RELEVANCE_RERUN.json": js(summ),
            "INGESTION_DECISIONS.csv": csv_text(dec, ["doc_id", "group", "state", "action", "review_queue"])}


def dump_text_layers():
    """Cache usable-page text layers of held population PDFs (scratchpad bytes) for the relevance step."""
    inv = {x["sha256"]: x for x in json.loads((SCRATCH / "inventory.json").read_text())}
    pv = defaultdict(dict)
    for r in read_csv(INP / "DETECTOR_PAGE_VERDICTS.csv"):
        pv[r["sha256"]][int(r["page"])] = r
    lines = []
    for q in read_csv(INP / "HELD_DOC_TEXT_QUALITY.csv"):
        if q["group"] == "CORPUS_RANDOM_CONTROL" or q["verdict"] == "EXTRACTION_FAILED":
            continue
        x = inv[q["sha256"]]
        pages = text_layer_pages(str(SCRATCH / x["path"]))
        keep = {p: t for p, t in pages.items() if pv[q["sha256"]].get(p, {}).get("usable") == "YES"}
        lines.append(json.dumps({"sha256": q["sha256"], "pages": keep}, ensure_ascii=False, sort_keys=True))
    (INP / "TEXT_LAYER_USABLE_PAGES.jsonl").write_text("\n".join(sorted(set(lines))) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ task 7: risk figures
def build_risk():
    """Measured figures only; estimates are derived in MISSED_JUDGMENT_RISK.md from these, with stated assumptions."""
    ing = {r["doc_id"]: r for r in read_csv(C12_INGEST)}
    rel = {r["doc_id"]: r for r in read_csv(OUT / "RELEVANCE_RERUN.csv")}
    rd = {r["key"]: r for r in read_csv(AUDIT / "C12-CONSOLIDATION" / "judicial_recovery_c12" / "inputs" / "REVIEW_DECISIONS.csv")}
    held = read_csv(INP / "HELD_COPIES.csv")
    tl = {r["sha256"]: r for r in read_csv(INP / "HELD_DOC_TEXT_QUALITY.csv")}
    sample = []
    for h in held:
        g = ing.get(h["doc_id"], {})
        key = g.get("target", "")
        llm = rd.get(key, {}).get("relevance_decision", "")
        r = rel.get(h["doc_id"], {})
        sample.append({"doc_id": h["doc_id"], "court": g.get("court", ""), "text_layer": tl.get(h["sha256"], {}).get("verdict", ""),
                       "c12_llm_relevance": llm, "c13_state": r.get("state", "")})
    by = defaultdict(Counter)
    for x in sample:
        c = x["court"]
        by[c]["titles"] += 1
        by[c]["text_layer_unusable"] += x["text_layer"] != "TEXT_OK"
        rel_llm = x["c12_llm_relevance"].startswith("RELEVANT")
        by[c]["relevant_by_c12_review_i.e._false_negative_of_old_rule"] += rel_llm
        by[c][f"c13_state={x['c13_state']}|c12={'REL' if rel_llm else 'NOT'}"] += 1
    fn = {c: {**dict(v), "fn_rate": round(v["relevant_by_c12_review_i.e._false_negative_of_old_rule"] / v["titles"], 3),
              "fn_rate_ci95": wilson(v["relevant_by_c12_review_i.e._false_negative_of_old_rule"], v["titles"])}
          for c, v in sorted(by.items())}
    corpus = defaultdict(Counter)
    cm = {"control_chars", "private_use", "cid_glyphs"}
    for r in read_csv(INP / "CORPUS_TEXT_LAYER_SCAN.csv"):
        f = set(r["flags"].split(";"))
        k = corpus[r["court"]]
        k["documents"] += 1
        k["cmap_garbled_any_page"] += bool(f & cm)
        k["cmap_garbled_majority_pages"] += bool(f & cm) and float(r["usable_share"]) < 0.5
        k["any_unusable_page"] += r["verdict"] == "OCR_REQUIRED"
        k["image_only_any_page"] += "image_only" in f
        k["does_not_open"] += r["verdict"] == "EXTRACTION_FAILED"
        k["no_eof_trailer"] += r["truncated"] == "YES"
        if r["court"] == "High Court of Punjab and Haryana":
            band = "2023-2026" if r["year"] >= "2023" else "2014-2015" if r["year"] in ("2014", "2015") else "other_years"
            corpus["P&H_cmap_by_year_band"][f"{band}|documents"] += 1
            corpus["P&H_cmap_by_year_band"][f"{band}|cmap_garbled_any_page"] += bool(f & cm)
    dv = json.loads((OUT / "DETECTOR_VALIDATION.json").read_text(encoding="utf-8"))
    rr = json.loads((OUT / "RELEVANCE_RERUN.json").read_text(encoding="utf-8"))
    pop = json.loads((OUT / "POPULATION_SUMMARY.json").read_text(encoding="utf-8"))
    out = {"measured": {
        "held_t1_sample_c12_25": {"note": "The 25 C11 first-tier titles acquired in C12 (selected by rank: 13 SC + 12 P&H AFT writs; "
                                          "not a random sample). Relevance reference = C12 LLM review (page images for P&H), not human.",
                                  "by_court": fn, "rows": sample},
        "kept_corpus_text_layers": {k: dict(v) for k, v in sorted(corpus.items())},
        "detector": {k: dv[k] for k in ("marginal_excluded", "with_original_uncorrected_labels")},
        "relevance_rerun_states": rr["by_group_state"],
        "population": {k: pop[k] for k in ("c11_flagged_titles", "c11_flagged_held", "ph_t1_titles", "ph_t1_held",
                                           "ph_t1_by_year", "excluded_log_total", "excluded_log_not_flagged_by_court")},
    }}
    return {"RISK_FIGURES.json": js(out)}


# ------------------------------------------------------------------ SHA256SUMS
SUM_EXCLUDE = {"SHA256SUMS"}


def build_sums():
    lines = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in SUM_EXCLUDE and "__pycache__" not in p.parts:
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT).as_posix()}")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ main
BUILDERS = {"population": build_population, "detector-eval": build_detector_eval, "bench-score": build_bench_score}
def build_throughput():
    pages = read_csv(OUT / "OCR_PAGES.csv")
    jobs = jobs_index()
    done = {(r["sha256"], int(r["page"])) for r in pages}
    planned = sum(len(j["pages"]) for j in jobs)
    left = [(j["doc_id"], p) for j in jobs for p in j["pages"] if (j["sha256"], p) not in done]
    skipped = sum(int(r["early_stop_skipped_pages"] or 0) for r in pages)
    corpus = read_csv(INP / "CORPUS_TEXT_LAYER_SCAN.csv")
    avg_pages = sum(int(r["pages"]) for r in corpus) / len(corpus)
    lines = ["# OCR throughput and remainder (C13 A1)", "",
             "Generated by `tools/c13_a1_ocr.py` from `OCR_PAGES.csv` and `inputs/OCR_JOBS.json`. Seconds are wall-clock",
             "recognition time per page at 200 dpi, 2 threads, on a shared 4-core host (`load1` is recorded per page).", "",
             "| Engine | Pages | Mean s/page | Median s/page | Mean load1 |", "| --- | --- | --- | --- | --- |"]
    for e in sorted({r["engine"] for r in pages}):
        sec = sorted(float(r["seconds"]) for r in pages if r["engine"] == e)
        ld = [float(r["load1"]) for r in pages if r["engine"] == e and r["load1"]]
        lines.append(f"| {e} | {len(sec)} | {sum(sec) / len(sec):.1f} | {sec[len(sec) // 2]:.1f} | "
                     f"{(sum(ld) / len(ld)) if ld else float('nan'):.1f} |")
    allsec = [float(r["seconds"]) for r in pages]
    mean = sum(allsec) / len(allsec)
    lines += ["", f"- Planned pages (unusable pages of held population files, full documents for the 12 P&H writs): **{planned}**.",
              f"- OCR'd: **{len(pages)}**; skipped by early stop (document already RELEVANT): **{skipped}**; "
              f"not reached (other than early-stop skips): **{len(left) - skipped}**.",
              f"- Corpus mean pages per judgment file: {avg_pages:.1f}. At the measured mean of {mean:.1f} s/page per process "
              f"and 2 processes, OCR of every page of the 8,052 not-held flagged titles would take about "
              f"{8052 * avg_pages * mean / 2 / 3600:.0f} hours; of the 550 P&H T1 titles (tranche P0) about "
              f"{550 * avg_pages * mean / 2 / 3600:.0f} hours. Pages with a usable text layer need no OCR, so these are upper bounds.",
              "- No re-acquired file was OCR'd: no download run was authorised."]
    return {"OCR_THROUGHPUT.md": "\n".join(lines) + "\n"}


LATE_BUILDERS = {"risk": build_risk, "throughput": build_throughput}


def write(outputs):
    for name, text in outputs.items():
        (OUT / name).write_text(text, encoding="utf-8")
        print("wrote", name)


def check() -> int:
    bad = 0
    for name, fn in [*BUILDERS.items(), ("relevance", lambda: build_relevance(False)), *LATE_BUILDERS.items()]:
        for fname, text in fn().items():
            p = OUT / fname
            ok = p.exists() and p.read_text(encoding="utf-8") == text
            print(("OK  " if ok else "DIFF"), fname)
            bad += not ok
    from hf_ocr_c13 import check_records  # noqa: E402
    bad += check_records()
    sums = (OUT / "SHA256SUMS")
    ok = sums.exists() and sums.read_text(encoding="utf-8") == build_sums()
    print(("OK  " if ok else "DIFF"), "SHA256SUMS")
    bad += not ok
    rsha, rids = restricted()
    leak = [p for p in OUT.rglob("*") if p.is_file() and p.name != "restricted_material.snapshot.json"
            and any(s in p.read_text(encoding="utf-8", errors="ignore") for s in rsha | rids)]
    print(("OK  " if not leak else "FAIL"), "no restricted sha256/doc_id in outputs", [str(x) for x in leak][:3])
    bad += bool(leak)
    print("CHECK", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


def main():
    sys.path.insert(0, str(HERE))
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--cache", default=str(SCRATCH / "ocr_cache"))
    a = ap.parse_args()
    if a.check:
        sys.exit(check())
    if a.cmd in BUILDERS or a.cmd in LATE_BUILDERS:
        write({**BUILDERS, **LATE_BUILDERS}[a.cmd]())
    elif a.cmd == "assemble":
        print(assemble(Path(a.cache)), "OCR pages assembled")
    elif a.cmd == "text-layers":
        dump_text_layers()
    elif a.cmd == "relevance":
        write(build_relevance(False))
    elif a.cmd == "sums":
        (OUT / "SHA256SUMS").write_text(build_sums(), encoding="utf-8")
    elif a.cmd and a.cmd.startswith("hf-"):
        import hf_ocr_c13
        hf_ocr_c13.main(a.cmd)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
