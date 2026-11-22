"""Mimamsa v3.5 primary-source integrity, case treatment and non-release gate.

Technical checks do not replace independent legal merits review or JAG approval.
"""
from __future__ import annotations
import csv,hashlib,io,json
from pathlib import Path
from datetime import datetime,timezone
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
BASE="legal_knowledge"
OUT="legal_knowledge/quality_audit/v3.5/01_Integrity_Treatment_NonRelease_Result.json"
SOURCE_SHA={
  "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl":
    "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a",
  "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl":
    "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1"
}
def dl(p,rev=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=p,
                                revision=rev,force_download=True))
def csvrows(p):
    with dl(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def jsonl(p):
    return [json.loads(s) for s in dl(p).read_text().splitlines() if s.strip()]
def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Private HF destination required")
    for path,sha in SOURCE_SHA.items():
        if hashlib.sha256(dl(path).read_bytes()).hexdigest()!=sha:
            raise RuntimeError("Original unapproved research source unexpectedly changed: "+path)
    work=json.loads(dl(BASE+"/full_text_working/v3.5/01_Extraction_Manifest.json").read_text())
    if work["case_count"]!=11 or work["source_pdf_verified"]!=10 or work["source_pdf_missing"]!=1 or work["extractable_pdf_pages"]!=259:
        raise RuntimeError("Unexpected full-source case/page count")
    for item in work["manifest"]:
        if item["state"]=="NO_ORIGINAL_PDF_ARCHIVED":
            if item["case_id"]!="DCLR-SC-2008-L05":
                raise RuntimeError("New missing case in v3.5")
            continue
        if item["legal_holding_verified"] is not False or item["jag_approved"] is not False:
            raise RuntimeError("Unapproved case text was promoted")
        page_recs=jsonl(item["output_path"])
        if len(page_recs)!=item["page_count"]:
            raise RuntimeError("Incomplete page text for "+item["case_id"])
        if any(x["source_sha256"]!=item["source_sha256"] or
               hashlib.sha256(x["text"].encode()).hexdigest()!=x["text_sha256"] or
               x["judgment_holding_verified"] or x["jag_approved"] for x in page_recs):
            raise RuntimeError("Page text-source provenance or legal gate failed for "+item["case_id"])
    treatments=jsonl(BASE+"/judicial_treatment/v3.5/01_Seven_Pension_Case_Express_Citation_Checks.jsonl")
    if len(treatments)!=7 or sum(x["express_case_name_found_in_extracted_text"] for x in treatments)!=5:
        raise RuntimeError("2026 SC express citation counts mismatch")
    for t in treatments:
        if t["jag_approved"] is not False or t["legal_effect_on_older_case"]!="NOT_DETERMINED":
            raise RuntimeError("Judicial treatment determination issued without legal review")
    not_found={x["older_case_id"] for x in treatments if not x["express_case_name_found_in_extracted_text"]}
    if not_found!={"DCLR-SC-2016-L04","DCLR-SC-2007-L10"}:
        raise RuntimeError("Unexpected 2026 SC indirect-only cases")
    reasoning=jsonl(BASE+"/judicial_treatment/v3.5/03_Isaac_Reasoning_Context.jsonl")
    if len(reasoning)!=19 or not {61,69,93}.issubset({x["pdf_page_1based"] for x in reasoning}):
        raise RuntimeError("Original 2026 SC contextual reasons incomplete")
    if any(x["legal_holding_verified"] or x["jag_approved"] for x in reasoning):
        raise RuntimeError("Automatic SC reasoning source was promoted")
    gaz=json.loads(dl(BASE+"/gazette_discovery/v3.5/01_1954_Gazette_Source_Probe.json").read_text())
    if gaz["original_official_gazette_pdf_archived"] or gaz["rule23_original_wording_authenticated"] or gaz["direct_gazette_scan_identified"]:
        raise RuntimeError("Original Gazette authenticated without actual Gazette-source validation")
    held=csvrows(BASE+"/verification_batches/v3.5/04_Seven_Pension_Source_Treatment_Findings.csv")
    if len(held)!=7 or any(x["jag_approved"]!="NO" or not x["present_release_status"].startswith("HOLD_") for x in held):
        raise RuntimeError("Seven cases unexpectedly released")
    discrepancy=csvrows(BASE+"/verification_batches/v3.5/05_Angad_2015_vs_Isaac_2026_Regulation_Label_Conflict.csv")
    if len(discrepancy)!=2 or any(x["jag_approved"]!="NO" for x in discrepancy):
        raise RuntimeError("IAF-versus-Army original-citation conflict missing")
    counsel=csvrows(BASE+"/verification_batches/v3.5/06_Court_Holding_Versus_Counsel_Argument_Gates.csv")
    if len(counsel)!=3 or not any(x["role_of_text"]=="RESPONDENTS_SUBMISSION_SUMMARISED_BY_COURT" and x["release_status"]=="BLOCK" for x in counsel):
        raise RuntimeError("Court-vs-counsel statement gate missing")
    dhingra=csvrows(BASE+"/verification_batches/v3.5/02_Dhingra_2007_Civilian_Comparator_Decision.csv")
    if len(dhingra)!=4 or any(x["original_court_pdf_archived"]!="NO" or x["operational_release"]!="NO" for x in dhingra):
        raise RuntimeError("Noncore Dhingra case improperly promoted")
    report={
       "batch":"v3.5", "completed_utc":datetime.now(timezone.utc).isoformat(),
       "result":"PASSED_SOURCE_INTEGRITY_AND_NO_PREMATURE_LEGAL_RELEASE",
       "original_sources_sha256_unchanged":True,
       "p0_judgments_sha_verified":10,"p0_case_original_missing":1,
       "page_text_sources_verified":259,
       "2026_pension_cases_directly_named":5,"2026_pension_cases_not_named":2,
       "2026_pension_cases_certified_legal_treatment":0,
       "gazette_1954_original_authenticated":False,
       "rule23_1954_wording_issue_resolved":False,
       "dhingra_source_original_archived":False,
       "angad_regulation_source_discrepancy_open":True,
       "no_counsel_submission_promoted_to_court_holding":True,
       "case_treatment_jag_approved":0,
       "commander_facing_release":False,
       "note":"This test proves only source-byte/page/provenance and release-status invariants, not legal correctness or JAG review."
    }
    encoded=(json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode()
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=OUT,path_or_fileobj=io.BytesIO(encoded))],
        commit_message="Record v3.5 legal source integrity, direct-citation counts, counsel and JAG non-release gate")
    rev=getattr(commit,"oid",None)
    if not rev or dl(OUT,rev).read_bytes()!=encoded:
        raise RuntimeError("HF v3.5 integrity report readback mismatch")
    print("V35_LEGAL_NONRELEASE_GATE_PASSED",json.dumps(report,sort_keys=True),"revision="+rev)

if __name__=="__main__":main()
