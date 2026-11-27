"""Archive Supreme Court official 2022 office-report citation for Mani Ram Bhaira.

It corroborates a 2016 appeal's identity and disposition; it is NOT the original
2016 judgment or an approval of its legal holding. Only the private dataset is used.
"""
import hashlib, html, io, json, re
from datetime import datetime, timezone
from pathlib import Path

import requests
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

DATASET="hariomahlawat/mimamsa-corpus"
URL="https://api.sci.gov.in/officereport/2022/10779/10779_2022_2022-07-22_916.html"
BASE="legal_knowledge/judgment_sources/sci_office_reports/v3.3"
ORIGINAL=BASE+"/mani_ram_bhaira_citation_2022.html"
META=BASE+"/mani_ram_bhaira_citation_2022.json"

def fetch(path,rev=None):
    return Path(hf_hub_download(repo_id=DATASET,repo_type="dataset",
                                filename=path,revision=rev,force_download=True))
def main():
    api=HfApi()
    if not api.repo_info(repo_id=DATASET,repo_type="dataset").private:
        raise RuntimeError("Dataset is not private")
    if api.file_exists(repo_id=DATASET,repo_type="dataset",filename=ORIGINAL):
        if not api.file_exists(repo_id=DATASET,repo_type="dataset",filename=META):
            raise RuntimeError("Existing report has no source metadata")
        record=json.loads(fetch(META).read_text())
        if hashlib.sha256(fetch(ORIGINAL).read_bytes()).hexdigest()!=record["sha256"]:
            raise RuntimeError("Existing official SC office report does not match checksum")
        print("V33_MANIRAM_OFFICE_REPORT_ALREADY_VERIFIED",record["sha256"])
        return
    response=requests.get(URL,timeout=50,headers={"User-Agent":"Mimamsa Legal Provenance Archive/1.0"})
    response.raise_for_status()
    raw=response.content
    if len(raw)<2500 or b"<html" not in raw[:4000].lower():
        raise RuntimeError("Official court case-management URL returned non-HTML document")
    rendered=html.unescape(re.sub(r"<[^>]*>"," ",response.text))
    rendered=" ".join(rendered.split()).casefold()
    for token in ("supreme court of india","mani ram bhaira","2016"):
        if token not in rendered:
            raise RuntimeError("Original court report identity missing: "+token)
    if not ("4409" in rendered or "004409" in rendered):
        raise RuntimeError("Mani Ram Bhaira appeal number not found")
    sha=hashlib.sha256(raw).hexdigest()
    record={
        "document_type":"LATER_SUPREME_COURT_OFFICE_REPORT_CITATION_NOT_ORIGINAL_2016_ORDER",
        "court":"Supreme Court of India",
        "report_date":"2022-07-22",
        "cited_case":"Ex Hav Mani Ram Bhaira v Union of India and Others",
        "cited_case_number":"Civil Appeal 4409 of 2011",
        "cited_decision_date":"2016-02-11",
        "cited_disposition":"Allowed (as described by later office report, subject to original signed order check)",
        "source_url":URL,
        "retrieved_utc":datetime.now(timezone.utc).isoformat(),
        "path":ORIGINAL,"sha256":sha,"bytes":len(raw),
        "is_cited_original_judgment":False,
        "source_identity_corrob_official_court":True,
        "original_signed_2016_judgment_pdf_archived":False,
        "full_holding_review_complete":False,
        "subsequent_treatment_checked_exhaustively":False,
        "jag_approved":False
    }
    encoded=(json.dumps(record,indent=2)+"\n").encode()
    res=api.create_commit(repo_id=DATASET,repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=ORIGINAL,path_or_fileobj=io.BytesIO(raw)),
                    CommitOperationAdd(path_in_repo=META,path_or_fileobj=io.BytesIO(encoded))],
        commit_message="Archive official SC 2022 court office report citing Mani Ram Bhaira, distinct from original judgment")
    revision=getattr(res,"oid",None)
    if not revision:
        raise RuntimeError("Missing Hugging Face commit revision")
    if hashlib.sha256(fetch(ORIGINAL,revision).read_bytes()).hexdigest()!=sha or fetch(META,revision).read_bytes()!=encoded:
        raise RuntimeError("Official court office report remote read-back mismatch")
    print(f"V33_MANIRAM_OFFICE_REPORT_VERIFIED sha256={sha} bytes={len(raw)} revision={revision}")

if __name__=="__main__":
    main()
