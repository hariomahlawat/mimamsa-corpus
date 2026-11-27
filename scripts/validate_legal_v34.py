"""Enforce provenance and non-release invariants for Mimamsa v3.4.

Automated integrity checks DO NOT constitute judicial-holding or JAG validation.
"""
import csv,hashlib,io,json
from pathlib import Path
from datetime import datetime,timezone
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
ROOT="legal_knowledge"
EXPECTED={
"curated_originals/case_law/v0.9/cases_53.jsonl":"8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a",
"curated_originals/knowledge_base/v0.9/records_658.jsonl":"9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1"
}
BASE="legal_knowledge/holding_review/v3.4"
P0="legal_knowledge/quality_audit/v3.0/01_Case_Metadata_Findings.jsonl"
CAND="legal_knowledge/verification_batches/v3.4/01_Eleven_P0_Holding_Candidates.csv"
PENSION="legal_knowledge/verification_batches/v3.4/02_Pension_2026_Treatment_Queue.csv"
IMPACT="legal_knowledge/verification_batches/v3.4/04_Targeted_658_KB_Impact_Register.csv"
AFSPA="legal_knowledge/verification_batches/v3.4/05_AFSPA_Later_Treatment_Queue.csv"
ISAAC_CLAIMS="legal_knowledge/verification_batches/v3.4/06_Isaac_2026_Source_Checked_Propositions.csv"
ISAAC_META="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.json"
ISAAC_PDF="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.pdf"
OUT="legal_knowledge/quality_audit/v3.4"

def dl(path):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=path,force_download=True))

def records(path):
    return [json.loads(s) for s in dl(path).read_text(encoding="utf-8").splitlines() if s.strip()]

def csvrows(path):
    with dl(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Private HF dataset required")

    for path,expected in EXPECTED.items():
        observed=hashlib.sha256(dl(ROOT+"/"+path).read_bytes()).hexdigest()
        if observed!=expected:
            raise RuntimeError("Immutable original SHA changed: "+path)
    qa=records(P0)
    p0={x["case_id"] for x in qa if x["metadata_priority"]=="P0"}
    if len(p0)!=11:
        raise RuntimeError("Unexpected P0 population")
    candidates=csvrows(CAND)
    if len(candidates)!=11 or {r["case_id"] for r in candidates}!=p0:
        raise RuntimeError("Holding candidate register not exactly 11 P0 cases")
    matrix=csvrows(BASE+"/03_P0_Source_Review_Matrix.csv")
    if len(matrix)!=11 or {r["case_id"] for r in matrix}!=p0:
        raise RuntimeError("Source review matrix mismatches P0 cases")
    if any(x["holding_verified"]!="NO" or x["jag_approved"]!="NO" or x["release_for_command_guidance"]!="NO" for x in matrix):
        raise RuntimeError("Unreviewed case was promoted into operational release")
    if sum(x["archived_sha_verified"]=="YES" for x in matrix)!=10:
        raise RuntimeError("Expected 10/11 corroborated PDF checksum statuses")
    if sum(x["source_tier"]=="THIRD_PARTY_MIRROR_OF_SUPREME_COURT_ORDER" for x in matrix)!=1:
        raise RuntimeError("Third-party source tier was lost")
    link=csvrows(BASE+"/04_P0_KB_Candidate_Links.csv")
    if len(link)!=74 or any(r["status"]!="LEXICAL_CANDIDATE_NOT_LEGAL_CROSSLINK" or r["jag_approved"]!="False" for r in link):
        raise RuntimeError("Candidate KB links were promoted or changed without review")
    cases=records(BASE+"/02_P0_Bounded_Paragraph_Review_Packets.jsonl")
    if len(cases)!=11 or sum(len(x["excerpts"]) for x in cases)!=80:
        raise RuntimeError("Source evidence packet counts changed")
    pension=csvrows(PENSION)
    if len(pension)!=7 or any(x["jag_approved"]!="NO" or x["current_law_cleared"]!="NO" for x in pension):
        raise RuntimeError("Pension treatment review prematurely cleared")
    impacts=csvrows(IMPACT)
    if len(impacts)!=14 or any(x["release_status"]!="HOLD_NONAPPROVED" for x in impacts):
        raise RuntimeError("KB impact was prematurely released")
    afspa=csvrows(AFSPA)
    if len(afspa)!=3 or any(x["jag_approved"]!="NO" for x in afspa):
        raise RuntimeError("AFSPA subsequent treatment queue incorrectly promoted")
    claims=csvrows(ISAAC_CLAIMS)
    if len(claims)!=6 or any(x["source_check_status"]!="SC_JUDGMENT_TEXT_CONFIRMED"
                             or x["exhaustive_later_treatment_verified"]!="NO"
                             or x["jag_approved"]!="NO" for x in claims):
        raise RuntimeError("2026 source-checked propositions missing or prematurely certified")
    isaac=json.loads(dl(ISAAC_META).read_text())
    if isaac["source_tier"]!="OFFICIAL_SUPREME_COURT_API" or hashlib.sha256(dl(ISAAC_PDF).read_bytes()).hexdigest()!=isaac["sha256"]:
        raise RuntimeError("2026 Isaac official judgment identity or checksum failed")
    if isaac["jag_approved"] is not False or isaac["legal_holding_verified"] is not False:
        raise RuntimeError("Official source illegally promoted to approved holding")
    report={
      "schema":"Mimamsa v3.4 provenance and non-release gate",
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "canonical_dataset":REPO,
      "result":"PASSED",
      "immutable_original_53_sha":EXPECTED["curated_originals/case_law/v0.9/cases_53.jsonl"],
      "immutable_original_658_sha":EXPECTED["curated_originals/knowledge_base/v0.9/records_658.jsonl"],
      "p0_cases":len(p0),"pdf_sha_verified":10,
      "raw_or_scr_pdfs":7,"official_judis_pdfs":2,"third_party_pdfs":1,"missing_pdfs":1,
      "auto_excerpts":80,"unapproved_lexical_kb_links":74,"unapproved_holding_candidates":len(candidates),
      "pension_2026_treatment_queues":len(pension),"targeted_kb_references":len(impacts),
      "afspa_treatment_leads":len(afspa),"source_checked_isaac_propositions_jag_pending":len(claims),
      "isaac_2026_official_original_sha":isaac["sha256"],
      "legal_holdings_jag_approved":0,"operational_propositions_released":0,
      "disclaimer":"Provenance/read-back and release gating are technical tests; no independent substantive legal review was performed by this workflow."
    }
    serialized=(json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode()
    path=OUT+"/01_Integrity_And_NonRelease_Result.json"
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=path,path_or_fileobj=io.BytesIO(serialized))],
        commit_message="Log v3.4 invariant pass: 11 P0, 10 PDFs, original SHA, no premature JAG release")
    rev=getattr(commit,"oid",None)
    if not rev or dl(path).read_bytes()!=serialized:
        raise RuntimeError("HF v3.4 integrity report read-back mismatch")
    print("V34_INVARIANTS_PASSED",json.dumps(report,ensure_ascii=False),"revision",rev)

if __name__=="__main__":
    main()
