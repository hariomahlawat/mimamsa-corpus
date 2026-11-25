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
    def score(marginal_as):
        tp = fp = fn = tn = 0
        for r in rows:
            lab = r["label"]
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
    fields = ["label_id", "sha256", "page", "sample_stratum", "label", "detector_flags", "detector_unusable"]
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
    rows = []
    for e in engines:
        timing = {}
        tf = bench / e / "timing.json"
        if tf.exists():
            t = json.loads(tf.read_text(encoding="utf-8"))
            timing = {p["gt_id"]: p for p in t["pages"]}
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
    fields = ["engine", "gt_id", "category", "gt_chars", "cer", "cer_caseless", "wer", "char_accuracy", "word_accuracy",
              "content_word_recall", "seconds", "page_covered"]
    return {"OCR_BENCHMARK.csv": csv_text(rows, fields), "OCR_BENCHMARK.json": js(agg)}


# ------------------------------------------------------------------ OCR text assembly
def jobs_index():
    p = INP / "OCR_JOBS.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def assemble(cache: Path):
    """Copy OCR page cache into ocr_text/<doc_id>.txt (page markers) and OCR_PAGES.csv. Writes files."""
    jobs = jobs_index()
    tdir = OUT / "ocr_text"
    tdir.mkdir(exist_ok=True)
    rows = []
    for j in jobs:
        d = cache / j["sha256"]
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
                         "early_stop_skipped_pages": len(skipped) if p is pages[-1] else ""})
    fields = ["doc_id", "sha256", "page", "seconds", "load1", "chars", "ocr_text_usable", "ocr_text_flags", "dict_ratio",
              "engine_conf_mean", "early_stop_skipped_pages"]
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
        ocr_done = bool(ocr_pages)
        es = None
        if sha in jobs:
            missing = [p for p in jobs[sha]["pages"] if p not in ocr_pages]
            if missing and ocr_done:
                es = f"{len(missing)} unusable pages not OCR'd"
        text = "\n".join(f"[[page {i + 1}]]\n{t}" for i, t in enumerate(texts))
        if q["verdict"] == "EXTRACTION_FAILED" and n == 0:
            d = rs.decide(text=None, quality=None, extraction_error="file does not open (truncated download)")
            if q["truncated"] == "YES":
                d["state"] = "SOURCE_INCOMPLETE"
                d["reasons"] = ["file does not open and has no %%EOF: incomplete at source (C11/C12: remote copy also truncated)"]
        else:
            d = rs.decide(text=text, quality=summary, truncated=q["truncated"] == "YES", ocr_done=ocr_done and not es)
        prior_text = layer and sha in layer
        rows.append({"group": q["group"], "doc_id": q["doc_id"], "court": q["court"], "sha256": sha,
                     "prior_relevance": q["prior_relevance"], "text_layer_verdict": q["verdict"],
                     "pages": n, "ocr_pages": len(ocr_pages), "ocr_incomplete": es or "",
                     "text_source": ("ocr+layer" if ocr_pages and lp else "ocr" if ocr_pages else "layer" if lp else "none"),
                     "usable_share_after": summary["usable_share"], "state": d["state"],
                     "keyword_status": d["keyword_status"] or "", "keywords": ";".join(f"{k}={v}" for k, v in sorted((d["keywords"] or {}).items())),
                     "second_check_families": ";".join((d["second_check"] or {}).get("families", [])),
                     "reasons": " | ".join(d["reasons"])})
    rows.sort(key=lambda r: (r["group"], r["doc_id"]))
    fields = ["group", "doc_id", "court", "sha256", "prior_relevance", "text_layer_verdict", "pages", "ocr_pages",
              "ocr_incomplete", "text_source", "usable_share_after", "state", "keyword_status", "keywords",
              "second_check_families", "reasons"]
    summ = {"documents": len(rows), "by_state": dict(sorted(Counter(r["state"] for r in rows).items())),
            "by_group_state": {g: dict(sorted(Counter(r["state"] for r in rows if r["group"] == g).items()))
                               for g in sorted({r["group"] for r in rows})},
            "transitions": dict(sorted(Counter(f"{r['prior_relevance']} -> {r['state']}" for r in rows).items()))}
    return {"RELEVANCE_RERUN.csv": csv_text(rows, fields), "RELEVANCE_RERUN.json": js(summ)}


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


def write(outputs):
    for name, text in outputs.items():
        (OUT / name).write_text(text, encoding="utf-8")
        print("wrote", name)


def check() -> int:
    bad = 0
    for name, fn in [*BUILDERS.items(), ("relevance", lambda: build_relevance(False))]:
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
    if a.cmd in BUILDERS:
        write(BUILDERS[a.cmd]())
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
