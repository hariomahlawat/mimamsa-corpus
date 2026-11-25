#!/usr/bin/env python3
"""C13-A0 stage 2: deterministic corpus classification frame over every judicial record.

Runs from committed files only (CI-reproducible):
  outputs/frame/TEXT_FEATURES.csv (stage 1), C10 metadata audit / copy register / relevance / legal issues,
  C11 identity register, C12 HF hash ledger (HASH_LEDGER.csv.gz), C12 ingestion log and staged manifest,
  outputs/exclusions/EXCLUDED_JUDGMENTS.csv.

Each record gets: court, year band, structural strata (proceeding structure, party-specific candidate, subject),
text quality (USABLE / GARBLED / IMAGE_ONLY / TRUNCATED / UNREADABLE), in-scope flag, raw-path validation and spent
sets. Unreadable, corrupted and incomplete files keep explicit states and are reported as their own population
(NON_USABLE_POPULATION.csv); nothing is dropped. The judgment-level frame (one row per judgment_key, the sampling
unit) chooses a representative copy deterministically and records holdout eligibility with the reason.

  python -I -B c13_frame.py [--check]
"""
import gzip
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import (C10, C11, C12, OUT, FOUO_EXCLUDED_SHA256, read_csv, render_csv, render_json,  # noqa: E402
                        write_or_check, argv_check)
import csv  # noqa: E402

COURTS = {"Supreme Court of India": "SC", "High Court of Delhi": "DEL", "High Court of Punjab and Haryana": "PH",
          "High Court of Jammu and Kashmir": "JK", "Allahabad High Court": "ALL"}
COURT_ORDER = ["SC", "DEL", "PH", "JK", "ALL"]
YEAR_BANDS = [(0, 1989, "<=1989"), (1990, 1999, "1990-1999"), (2000, 2009, "2000-2009"), (2010, 2014, "2010-2014"),
              (2015, 2019, "2015-2019"), (2020, 2022, "2020-2022"), (2023, 2100, "2023-2026")]
PENSION = {"disability_pension", "service_pension", "family_pension", "attributability_aggravation", "medical_board",
           "orop_pay_fixation"}
DISCIPLINARY = {"court_martial", "summary_court_martial", "summary_of_evidence", "court_of_inquiry",
                "desertion_absence", "dismissal_discharge_termination", "sentence_punishment"}
TOPIC_MIN_MENTIONS = 2          # a C10 topic counts when it is mentioned at least twice
STRATA = ["BATCH_OR_MULTI", "PARTY_SPECIFIC", "PENSION_OR_DISCIPLINARY", "OTHER"]
TEXT_QUALITY = ["USABLE", "GARBLED", "IMAGE_ONLY", "TRUNCATED", "UNREADABLE"]
IN_SCOPE_CLASSES = {"DIRECT_MILITARY_LAW", "MILITARY_ADMIN_SERVICE_PENSION", "GENERAL_LAW_POTENTIALLY_APPLICABLE"}
V3_TOPICS = {"disability_pension", "court_martial", "pension", "summary_court_martial", "dismissal_discharge"}


def year_band(y):
    if not y:
        return "UNKNOWN"
    for lo, hi, lab in YEAR_BANDS:
        if lo <= y <= hi:
            return lab
    return "UNKNOWN"


def keys_n(s):
    return len([k for k in (s or "").split(";") if k])


def load_inputs():
    I = {}
    I["features"] = read_csv(OUT / "frame" / "TEXT_FEATURES.csv")
    I["meta_audit"] = {r["doc_id"]: r for r in read_csv(C10 / "outputs" / "HF_JUDGMENT_METADATA_AUDIT.csv")}
    I["copies"] = {r["sha256"]: r for r in read_csv(C10 / "outputs" / "HF_JUDGMENT_COPY_REGISTER.csv")}
    I["relevance"] = {r["sha256"]: r for r in read_csv(C10 / "outputs" / "HF_JUDGMENT_RELEVANCE.csv")}
    I["identity"] = {r["sha256"]: r for r in read_csv(C11 / "identity" / "outputs" / "JUDGMENT_IDENTITY_REGISTER.csv")}
    I["topics"] = {}
    with open(C10 / "outputs" / "HF_JUDGMENT_LEGAL_ISSUES.jsonl", encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            I["topics"][o["sha256"]] = o.get("topics") or {}
    with gzip.open(C12 / "hf_verification_c12" / "HASH_LEDGER.csv.gz", "rt", encoding="utf-8") as f:
        I["ledger"] = {r["path"]: r for r in csv.DictReader(f)}
    I["ingestion"] = {r["doc_id"]: r for r in read_csv(C12 / "judicial_recovery_c12" / "INGESTION_LOG.csv")}
    I["staged_raw"] = {r["hf_path"]: r for r in read_csv(C12 / "judicial_recovery_c12" / "STAGED_MANIFEST.csv")
                       if r["kind"] == "raw"}
    I["excluded"] = {r["judgment_key"]: r["spent_sets"] for r in read_csv(OUT / "exclusions" / "EXCLUDED_JUDGMENTS.csv")}
    return I


def text_quality(f, copy, ident, ing):
    """Explicit text-quality state for one record (rules pre-registered in PROTOCOL_C13.md section 2)."""
    held = f["population"] == "C12_HELD_ORIGINAL_DERIVED"
    completeness = (ing or {}).get("completeness", "")
    if not held and copy and (copy.get("pdf_status") == "UNREADABLE"
                              or copy.get("disposition") == "NOT_PROCESSED_BYTES_UNAVAILABLE"):
        return "UNREADABLE", "pdf does not open or bytes unavailable (C10 copy register)"
    if not held and copy and copy.get("source_completeness") == "STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING":
        return "TRUNCATED", "stored copy truncated; content may be missing (C10/C11)"
    if "TEXT_LAYER_UNUSABLE" in completeness:
        return "GARBLED", "text layer unusable (C12 ingestion letter-share test); needs OCR"
    if f["text_present"] != "true" or int(f["letters"]) < 200:
        return "IMAGE_ONLY", "no text layer or near-empty text (<200 letters)"
    if f["meta_text_method"] == "ocr" or (copy or {}).get("text_extraction") == "NO_TEXT_LAYER" \
            or (ident or {}).get("text_quality") == "EMPTY_OR_NEAR_EMPTY":
        return "IMAGE_ONLY", "image-only PDF (no usable text layer); corpus text is OCR (confidence %s)" % (
            f["meta_ocr_confidence"] or "n/a")
    pages, usable = int(f["text_pages"]), int(f["pages_usable"])
    if float(f["letter_share"]) < 0.5 or (ident or {}).get("text_quality") == "NON_READABLE_TEXT_LAYER" \
            or (pages and usable / pages < 0.5):
        return "GARBLED", "letter share < 0.5, C11 NON_READABLE_TEXT_LAYER, or < 50% of pages usable"
    return "USABLE", ("partial: %d/%d pages usable" % (usable, pages)) if usable < pages else "all pages usable"


def raw_store(path, sha, I):
    """F06: validate the raw path against a pinned store. Returns (store, valid)."""
    if not path:
        return "NONE", False
    if path in I["staged_raw"] and I["staged_raw"][path]["sha256"] == sha:
        return "HF@15bd03cc (C12 staged)", True
    led = I["ledger"].get(path)
    if led and (led.get("lfs_sha256") == sha or led.get("computed_sha256") == sha):
        return "HF@5524c3d9 (C12 hash ledger)", True
    return "NOT_FOUND_IN_PINNED_STORES", False


def classify(I):
    recs = []
    for f in I["features"]:
        d = f["doc_id"]
        ma = I["meta_audit"].get(d)
        ing = I["ingestion"].get(d)
        sha = (ma or {}).get("sha256") or f["meta_sha256_file"] or (ing or {}).get("sha256", "")
        copy = I["copies"].get(sha)
        ident = I["identity"].get(sha)
        court_name = (ma or {}).get("court") or f["meta_court"] or (ing or {}).get("court", "")
        court = COURTS.get(court_name, "OTHER")
        date = (ma or {}).get("issue_date_meta") or f["meta_issue_date"] or (ing or {}).get("decided", "")
        year = int(date[:4]) if date[:4].isdigit() else None
        tq, tq_basis = text_quality(f, copy, ident, ing)
        if f["population"] == "C12_HELD_ORIGINAL_DERIVED":
            raw_path = (copy or {}).get("path") or f["meta_raw_path"]
        else:
            raw_path = f["meta_raw_path"] or (copy or {}).get("path", "")
        store, valid = raw_store(raw_path, sha, I)
        led = I["ledger"].get(raw_path, {})
        jkey = (ident or {}).get("judgment_key") or ("JK-" + sha[:16])
        # topics: C10 counts for base records; crawler topic list for C12 additions
        if sha in I["topics"]:
            tops = {k for k, v in I["topics"][sha].items() if v >= TOPIC_MIN_MENTIONS}
            v3tops = set(I["topics"][sha].keys())
        else:
            tops = set(t for t in f["meta_topics"].split(";") if t)
            v3tops = tops
        pen, dis = bool(tops & PENSION), bool(tops & DISCIPLINARY)
        subject = ("PENSION_AND_DISCIPLINARY" if pen and dis else "PENSION" if pen else "DISCIPLINARY" if dis
                   else "OTHER")
        assessable = tq == "USABLE"
        multi_meta = max(keys_n((ident or {}).get("proceeding_keys_meta")), int(f["meta_case_numbers_n"] or 0))
        multi_title = keys_n((ident or {}).get("proceeding_keys_cause_title_partial"))
        rel = I["relevance"].get(sha, {}).get("relevance_class", "")
        if not rel and ing:
            rel = ("INGESTED_C12_" + ("NOT_CHECKED_AFT_WRIT" if "TEXT_LAYER_UNUSABLE" in ing["completeness"]
                                      else "RELEVANT_LLM_REVIEW" if ing["action"] == "INGESTED"
                                      else "CURATED_HELD_ORIGINAL"))
        in_scope = ("OUT_OF_SCOPE" if rel == "NOT_RELEVANT_CURRENT_SCOPE" else
                    "UNCERTAIN" if rel in ("RELEVANCE_UNCERTAIN_REVIEW", "") else "IN_SCOPE")
        contradictions = (ma or {}).get("contradictions", "")
        recs.append(dict(
            doc_id=d, population=f["population"], sha256=sha, judgment_id=(ident or {}).get("judgment_id_c10", ""),
            judgment_key=jkey, court=court, court_name=court_name, issue_date=date, year=year or "",
            year_band=year_band(year), text_quality=tq, text_quality_basis=tq_basis,
            file_state=(copy or {}).get("source_completeness") or (ing or {}).get("completeness", ""),
            pdf_opens_hf_ledger=led.get("pdf_opens", ""), trailing_eof_hf_ledger=led.get("trailing_eof", ""),
            text_pages=f["text_pages"], pages_usable=f["pages_usable"], letter_share=f["letter_share"],
            raw_path=raw_path, raw_store=store, raw_path_valid=valid,
            meta_records_for_file="",
            proceeding_keys_meta=multi_meta, proceeding_keys_cause_title=multi_title,
            connected_matter_cues=f["connected_matter_cues"],
            party_specific_cues=f["party_specific_cues"] if assessable else "",
            multi_opinion_cues=f["multi_opinion_cues"] if assessable else "",
            subject=subject, disagreement_flag="crawler outcome" in contradictions,
            composite_flag=bool((ident or {}).get("composite_flag")),
            relevance_class=rel, in_scope=in_scope,
            access_marking=f["meta_access_marking"], fouo_excluded=sha in FOUO_EXCLUDED_SHA256,
            spent_sets=I["excluded"].get(jkey, ""),
            _v3tops=v3tops, _rel_multi=len([x for x in (ma or {}).get("case_numbers_text_p1_3", "").split(";") if x]),
            _copies=int((ident or {}).get("copies_of_judgment") or 1)))
    # record counts per file and per judgment
    per_file = Counter(r["sha256"] for r in recs)
    per_key = Counter(r["judgment_key"] for r in recs)
    for r in recs:
        r["meta_records_for_file"] = per_file[r["sha256"]]
        multi = (per_key[r["judgment_key"]] > 1 or per_file[r["sha256"]] > 1 or r["proceeding_keys_meta"] > 1
                 or r["proceeding_keys_cause_title"] > 1 or int(r["connected_matter_cues"] or 0) > 0)
        r["proceeding_structure"] = "BATCH_OR_MULTI" if multi else "SINGLE"
        r["party_specific"] = ("NOT_ASSESSABLE" if r["text_quality"] != "USABLE" else
                               "CANDIDATE" if int(r["party_specific_cues"]) > 0 else "NO_SIGNAL")
        r["stratum"] = ("BATCH_OR_MULTI" if multi else "PARTY_SPECIFIC" if r["party_specific"] == "CANDIDATE" else
                        "PENSION_OR_DISCIPLINARY" if r["subject"] != "OTHER" else "OTHER")
        # V3 rule reproduced for comparability (holdout_v3_sample_c12.py, including its topic-name mismatch)
        r["stratum_v3"] = ("batch_or_multi" if r["_copies"] > 1 or per_file[r["sha256"]] > 1 or r["_rel_multi"] > 1
                           else "disagreement" if r["disagreement_flag"] else
                           "pension_or_disciplinary" if r["_v3tops"] & V3_TOPICS else "other")
    return recs


REP_ORDER_TQ = {t: i for i, t in enumerate(TEXT_QUALITY)}


def judgments(recs, I):
    by = defaultdict(list)
    for r in recs:
        by[r["judgment_key"]].append(r)
    out = []
    for k in sorted(by):
        rs = by[k]
        def rank(r):
            ident = I["identity"].get(r["sha256"], {})
            return (REP_ORDER_TQ[r["text_quality"]], 0 if r["raw_path_valid"] else 1,
                    0 if ident.get("rendition_class", "OFFICIAL_COURT_PDF").startswith("OFFICIAL") else 1, r["sha256"])
        rep = sorted(rs, key=rank)[0]
        courts = sorted({r["court"] for r in rs})
        stratum = min((r["stratum"] for r in rs), key=STRATA.index)
        if len(rs) > 1:
            stratum = "BATCH_OR_MULTI"
        subjects = {r["subject"] for r in rs}
        scope = ("IN_SCOPE" if any(r["in_scope"] == "IN_SCOPE" for r in rs) else
                 "UNCERTAIN" if any(r["in_scope"] == "UNCERTAIN" for r in rs) else "OUT_OF_SCOPE")
        reasons = []
        if rep["text_quality"] != "USABLE":
            reasons.append("TEXT_" + rep["text_quality"])
        if not rep["raw_path_valid"]:
            reasons.append("RAW_PATH_INVALID")
        if scope == "OUT_OF_SCOPE":
            reasons.append("OUT_OF_SCOPE")
        if rep["spent_sets"]:
            reasons.append("SPENT:" + rep["spent_sets"].replace(";", "+"))
        if any(r["fouo_excluded"] or r["access_marking"] for r in rs):
            reasons.append("ACCESS_MARKING")
        if rep["court"] == "OTHER" or len(courts) > 1:
            reasons.append("COURT_UNRESOLVED")
        out.append(dict(
            judgment_key=k, court=rep["court"], year=rep["year"], year_band=rep["year_band"], stratum=stratum,
            proceeding_structure="BATCH_OR_MULTI" if stratum == "BATCH_OR_MULTI" else "SINGLE",
            party_specific=rep["party_specific"],
            subject=("PENSION_AND_DISCIPLINARY" if {"PENSION", "DISCIPLINARY"} <= subjects or
                     "PENSION_AND_DISCIPLINARY" in subjects else rep["subject"]),
            text_quality=rep["text_quality"], in_scope=scope, records=len(rs), files=len({r["sha256"] for r in rs}),
            rep_sha256=rep["sha256"], rep_doc_id=rep["doc_id"], rep_raw_path=rep["raw_path"],
            rep_raw_store=rep["raw_store"], rep_text_pages=rep["text_pages"],
            multi_opinion_cues=rep["multi_opinion_cues"], disagreement_flag=any(r["disagreement_flag"] for r in rs),
            composite_flag=any(r["composite_flag"] for r in rs), relevance_class=rep["relevance_class"],
            spent_sets=rep["spent_sets"], eligible_fresh_holdout=not reasons,
            ineligibility_reasons=";".join(reasons)))
    return out


def counts_table(recs, js):
    rows = []
    for level, items in (("record", recs), ("judgment", js)):
        c = Counter((x["court"], x["stratum"], x["text_quality"]) for x in items)
        for court in COURT_ORDER + sorted({x["court"] for x in items} - set(COURT_ORDER)):
            for s in STRATA:
                for t in TEXT_QUALITY:
                    rows.append(dict(level=level, court=court, stratum=s, text_quality=t, n=c.get((court, s, t), 0)))
    js_el = Counter((j["court"], j["stratum"]) for j in js if j["eligible_fresh_holdout"])
    for court in COURT_ORDER:
        for s in STRATA:
            rows.append(dict(level="judgment_eligible_fresh_holdout", court=court, stratum=s, text_quality="USABLE",
                             n=js_el.get((court, s), 0)))
    return rows


REC_COLS = ["doc_id", "population", "sha256", "judgment_id", "judgment_key", "court", "court_name", "issue_date",
            "year", "year_band", "proceeding_structure", "party_specific", "subject", "stratum", "stratum_v3",
            "disagreement_flag", "text_quality", "text_quality_basis", "file_state", "pdf_opens_hf_ledger",
            "trailing_eof_hf_ledger", "text_pages", "pages_usable", "letter_share", "raw_path", "raw_store",
            "raw_path_valid", "meta_records_for_file", "proceeding_keys_meta", "proceeding_keys_cause_title",
            "connected_matter_cues", "party_specific_cues", "multi_opinion_cues", "composite_flag", "relevance_class",
            "in_scope", "access_marking", "fouo_excluded", "spent_sets"]


def build():
    I = load_inputs()
    recs = classify(I)
    js = judgments(recs, I)
    non_usable = [r for r in recs if r["text_quality"] != "USABLE"]
    summ = {
        "records": len(recs), "records_by_population": dict(Counter(r["population"] for r in recs)),
        "files": len({r["sha256"] for r in recs}), "judgments": len(js),
        "records_by_court": dict(Counter(r["court"] for r in recs)),
        "records_by_text_quality": dict(Counter(r["text_quality"] for r in recs)),
        "records_by_stratum": dict(Counter(r["stratum"] for r in recs)),
        "records_by_stratum_v3": dict(Counter(r["stratum_v3"] for r in recs)),
        "records_by_year_band": dict(Counter(r["year_band"] for r in recs)),
        "records_by_in_scope": dict(Counter(r["in_scope"] for r in recs)),
        "records_raw_path_invalid": sum(not r["raw_path_valid"] for r in recs),
        "judgments_by_court": dict(Counter(j["court"] for j in js)),
        "judgments_by_stratum": dict(Counter(j["stratum"] for j in js)),
        "judgments_by_text_quality": dict(Counter(j["text_quality"] for j in js)),
        "judgments_eligible_fresh_holdout": sum(j["eligible_fresh_holdout"] for j in js),
        "judgments_ineligible_by_reason": dict(Counter(x.split(":")[0] for j in js
                                                       for x in j["ineligibility_reasons"].split(";") if x)),
        "judgments_spent_by_set": dict(Counter(s for j in js for s in j["spent_sets"].split(";") if s)),
        "non_usable_records": len(non_usable),
        "fouo_records": sum(r["fouo_excluded"] for r in recs),
        "status": "AUTOMATED_CLASSIFICATION_NOT_LEGALLY_VERIFIED",
    }
    return {"frame/FRAME_RECORDS.csv": render_csv(recs, REC_COLS),
            "frame/FRAME_JUDGMENTS.csv": render_csv(js),
            "frame/STRATUM_COUNTS.csv": render_csv(counts_table(recs, js)),
            "frame/NON_USABLE_POPULATION.csv": render_csv(non_usable, REC_COLS),
            "frame/FRAME_SUMMARY.json": render_json(summ)}


def load_frame():
    return read_csv(OUT / "frame" / "FRAME_JUDGMENTS.csv")


def main():
    return write_or_check(build(), OUT, argv_check(), "c13_frame")


if __name__ == "__main__":
    sys.exit(main())
