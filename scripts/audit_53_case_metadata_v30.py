"""Mimamsa v3.0 provenance and metadata audit of the original 53 curated case records.

Original JSONL and crawler corpus remain immutable. Quality gaps are derived from
actual original records, with previous crosswalk candidate and PDF-source statuses
preserved independently. Publishing the audit does not confer legal verification.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

DATASET = "hariomahlawat/mimamsa-corpus"
ROOT = "legal_knowledge/quality_audit/v3.0"
ORIG = "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
PRIOR = "legal_knowledge/crosswalk/v2.7/01_Curated_53_Case_Source_Crosswalk.csv"
CONFIRMED = "legal_knowledge/crosswalk/v2.9/01_Original_Source_Matches.csv"
FIELDS = ("decision_date","case_number","primary_source_url","reporter_citation",
          "holding","pinpoint_paragraphs")


def remote(path):
    return Path(hf_hub_download(repo_id=DATASET, repo_type="dataset",
                                filename=path, force_download=True))

def table(path):
    with remote(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def valid_date(s):
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def main():
    api = HfApi()
    info = api.repo_info(repo_id=DATASET, repo_type="dataset")
    if not info.private:
        raise RuntimeError("Only the private canonical dataset may be used")
    input_file = remote(ORIG)
    original_bytes = input_file.read_bytes()
    originals = [json.loads(s) for s in original_bytes.splitlines() if s.strip()]
    if len(originals) != 53:
        raise RuntimeError(f"Expected 53 original case records, found {len(originals)}")
    ids = [x.get("id") for x in originals]
    if len(set(ids)) != 53 or any(not x for x in ids):
        raise RuntimeError("Duplicate or missing curated case ID")

    previous = {x["curated_case_id"]: x for x in table(PRIOR)}
    selected = {x["curated_case_id"]: x for x in table(CONFIRMED)}
    if set(previous) != set(ids):
        raise RuntimeError("Case crosswalk inconsistent with canonical original 53")
    findings = []
    counts = Counter()
    for row in originals:
        case_id = row["id"]
        missing = [field for field in FIELDS if row.get(field) in (None,"",[])]
        counts.update(missing)
        date = row.get("decision_date") or ""
        idyear = re.search(r"\b(?:19|20)\d{2}\b",case_id)
        id_year_disagrees = bool(valid_date(date) and idyear and date[:4] != idyear.group())
        candidates = previous.get(case_id,{})
        pdf = selected.get(case_id,{})
        quality_flags = []
        if id_year_disagrees:
            quality_flags.append("CASE_ID_YEAR_DIFFERS_FROM_DECISION_DATE_REVIEW_NOT_ERROR")
        if not row.get("source_document_archived"):
            quality_flags.append("ORIGINAL_CASE_RECORD_HAS_NO_ARCHIVED_PDF")
        if not row.get("original_pdf_sha256"):
            quality_flags.append("ORIGINAL_CASE_RECORD_HAS_NO_PDF_SHA256")
        if not row.get("primary_source_url"):
            quality_flags.append("NO_PRIMARY_SOURCE_URL_IN_CURATED_ORIGINAL")
        if case_id in selected and pdf.get("corpus_raw_manifest_sha256_match") == "YES":
            quality_flags.append("SEPARATELY_CHECKED_CANONICAL_CORPUS_SOURCE_PDF")
        priority = (
            "P0" if "holding" in missing or (not date and not row.get("primary_source_url")) else
            "P1" if "decision_date" in missing or "primary_source_url" in missing or "case_number" in missing else
            "P2" if missing or candidates.get("comparison_status") != "TITLE_CANDIDATES_ONLY" else
            "P3"
        )
        result = {
            "case_id":case_id, "case_title":row.get("title",""),
            "case_date":date,"metadata_priority":priority,
            "missing_fields":missing, "quality_flags":quality_flags,
            "source_status_as_recorded":row.get("source_status"),
            "original_source_document_archived_flag":bool(row.get("source_document_archived")),
            "original_pdf_sha256_recorded":bool(row.get("original_pdf_sha256")),
            "treatment_status_as_recorded":row.get("post_decision_treatment_status"),
            "jag_approved":False,
            "v27_source_match_status":candidates.get("comparison_status",""),
            "v27_candidate_score":candidates.get("candidate_1_score",""),
            "v29_pdf_source_sha_and_title_verified":
                bool(pdf.get("corpus_raw_manifest_sha256_match")=="YES" and
                     pdf.get("case_title_verified_in_pdf_text")=="YES"),
            "v29_canonical_raw_pdf_path":pdf.get("canonical_hf_source_path",""),
            "complete_holding_and_later_treatment_review":False,
            "metadata_finding_only":True
        }
        findings.append(result)

    priority_count = Counter(row["metadata_priority"] for row in findings)
    output_a = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True)+"\n" for row in findings).encode("utf-8")
    report = {
        "title":"Curated Military Law case-law metadata and source audit v3.0",
        "date_utc":datetime.now(timezone.utc).isoformat(),
        "canonical_private_dataset":DATASET,
        "source_revision":info.sha,
        "original_dataset_path":ORIG,
        "original_53_jsonl_sha256":hashlib.sha256(original_bytes).hexdigest(),
        "case_count":len(findings),
        "field_missing_counts":dict(counts),
        "case_priority_counts":dict(priority_count),
        "original_case_records_with_pdf_archived_flag":sum(bool(x.get("source_document_archived")) for x in originals),
        "original_case_records_with_pdf_sha256_value":sum(bool(x.get("original_pdf_sha256")) for x in originals),
        "separately_corrob_corpus_pdf_title_and_sha":sum(x["v29_pdf_source_sha_and_title_verified"] for x in findings),
        "legally_verified_cases_added":0,
        "important": [
          "This is a source completeness audit, not a statement that all unlinked PDFs are absent from the HF corpus.",
          "Original curated case rows remain unmodified; v2.9 source verification is held as separate evidence.",
          "A title/manifest hash check of a source PDF does not authenticate a full judicial holding or later treatment.",
          "CASE_ID year mismatch is a review cue, not proof of a data error.",
          "All 53 cases retain JAG_REVIEW_PENDING status and have no formal JAG approval."
        ]
    }
    output_b = (json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    rows = []
    for x in findings:
        rows.append({
          "case_id":x["case_id"],"title":x["case_title"],
          "priority":x["metadata_priority"],
          "missing_fields":"; ".join(x["missing_fields"]),
          "v27_match":x["v27_source_match_status"],
          "v29_hf_corpus_pdf_sha_title_check":"YES" if x["v29_pdf_source_sha_and_title_verified"] else "NO",
          "jag_approved":"NO"
        })
    stream=io.StringIO()
    cw=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n")
    cw.writeheader();cw.writerows(rows)
    output_c=stream.getvalue().encode("utf-8")
    output_d = (
      "# Metadata completeness audit — curated 53 cases (v3.0)\n\n"
      "Generated only from the original v0.9 53-case JSONL in the private canonical HF dataset, "
      "and existing v2.7/v2.9 case-source crosswalk files. No source originals are edited.\n\n"
      "Missing metadata, legacy unarchived-PDF flags and candidate match status do not establish that "
      "the judgment is unavailable or the case is legally unsound. The separate two-PDF SHA and case-title "
      "corroboration is reflected without conflating with original v0.9 metadata.\n\n"
      "Legal holdings, amendment versions and subsequent treatment remain unverified. No JAG approval.\n"
    ).encode("utf-8")
    files = {
      f"{ROOT}/01_Case_Metadata_Findings.jsonl": output_a,
      f"{ROOT}/02_Case_Metadata_Summary.json": output_b,
      f"{ROOT}/03_Case_Review_Priorities.csv": output_c,
      f"{ROOT}/README.md": output_d,
    }
    operations = [CommitOperationAdd(path_in_repo=k,path_or_fileobj=io.BytesIO(v))
                  for k,v in files.items()]
    commit=api.create_commit(repo_id=DATASET,repo_type="dataset",operations=operations,
                             commit_message="Publish v3.0 curated case metadata/source quality audit (53 original cases)")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("HF commit did not return a revision")
    for name, content in files.items():
        rd=Path(hf_hub_download(repo_id=DATASET,repo_type="dataset",
                                filename=name,revision=rev,force_download=True))
        if hashlib.sha256(content).hexdigest()!=hashlib.sha256(rd.read_bytes()).hexdigest():
            raise RuntimeError("HF readback SHA mismatch for "+name)
    print("AUDIT_V30_VERIFIED 4 files revision="+rev)
    print("AUDIT_SUMMARY "+json.dumps({
       "cases":len(findings),"missing":dict(counts),"priority":dict(priority_count),
       "v29_source_verified":report["separately_corrob_corpus_pdf_title_and_sha"]
    },sort_keys=True))

if __name__=="__main__":
    main()
