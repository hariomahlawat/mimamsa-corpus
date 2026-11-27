"""Archive the 2025 official Supreme Court judgment discussing Navjot Sandhu's limited overruling.

Purpose: offline primary-source corpus with immutable checksum/readback verification,
not a legal approval of the extracted proposition or current BSA 2023 construction.
"""
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import fitz
import requests
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
URL="https://api.sci.gov.in/supremecourt/2019/13316/13316_2019_1_1501_58853_Judgement_28-Jan-2025.pdf"
PATH="legal_knowledge/judgment_originals/sci/2025/chandrabhan_sudam_sanap_2025.pdf"
META="legal_knowledge/judgment_originals/sci/2025/chandrabhan_sudam_sanap_2025.json"

def get(path):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",
                                filename=path,force_download=True))

def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Target private dataset required")
    if api.file_exists(repo_id=REPO,repo_type="dataset",filename=PATH):
        if not api.file_exists(repo_id=REPO,repo_type="dataset",filename=META):
            raise RuntimeError("Existing judgment has no provenance manifest")
        obj=json.loads(get(META).read_text())
        blob=get(PATH).read_bytes()
        if hashlib.sha256(blob).hexdigest()!=obj["sha256"]:
            raise RuntimeError("Existing precedent PDF checksum mismatch")
        print("V32_ADVERSE_TREATMENT_ORIGINAL_ALREADY_VERIFIED sha256="+obj["sha256"])
        return

    resp=requests.get(URL,timeout=45,headers={"User-Agent":"Mimamsa-Legal-Research/1.0"})
    resp.raise_for_status()
    payload=resp.content
    if len(payload)<15000 or not payload.startswith(b"%PDF-"):
        raise RuntimeError("Official source did not return valid PDF")
    with fitz.open(stream=payload,filetype="pdf") as pdf:
        pages=len(pdf)
        first=" ".join(pdf[i].get_text("text") for i in range(min(2,pages))).lower()
        all_text=" ".join(p.get_text("text") for p in pdf).lower()
    if not ("chandrabhan" in first and "sanap" in first and "supreme court" in first):
        raise RuntimeError("Court case title identity check failed")
    if not ("navjot sandhu" in all_text and "anvar" in all_text and "arjun panditrao" in all_text):
        raise RuntimeError("Judicial treatment reference absent from source")
    digest=hashlib.sha256(payload).hexdigest()
    meta={
        "court":"Supreme Court of India",
        "case_name":"Chandrabhan Sudam Sanap v State of Maharashtra",
        "neutral_citation":"2025 INSC 116",
        "decision_date":"2025-01-28",
        "criminal_appeal_number":"879 of 2019",
        "original_url":URL,
        "response_url":resp.url,
        "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
        "sha256":digest,"bytes":len(payload),"pages":pages,
        "hf_original_pdf_path":PATH,
        "legal_propositions_referenced":["Navjot Sandhu (2005): restricted electronic secondary evidence proposition","Anvar P.V. (2014)","Arjun Panditrao Khotkar (2020)"],
        "primary_source_appearance_checked":True,
        "post_2025_treatment_checked":False,
        "full_judicial_holding_verified":False,
        "jag_approved":False
    }
    obj=(json.dumps(meta,ensure_ascii=False,indent=2)+"\n").encode()
    res=api.create_commit(repo_id=REPO,repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=PATH,path_or_fileobj=io.BytesIO(payload)),
                    CommitOperationAdd(path_in_repo=META,path_or_fileobj=io.BytesIO(obj))],
        commit_message="Archive original SC 2025 Chandrabhan Sanap judgment for limited electronic evidence treatment")
    rev=getattr(res,"oid",None)
    if not rev:
        raise RuntimeError("Missing HF commit revision")
    doc=Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=PATH,revision=rev,force_download=True))
    receipt=Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=META,revision=rev,force_download=True))
    if hashlib.sha256(doc.read_bytes()).hexdigest()!=digest or receipt.read_bytes()!=obj:
        raise RuntimeError("HF upload readback integrity failure")
    print(f"V32_ADVERSE_TREATMENT_ORIGINAL_VERIFIED pages={pages} sha256={digest} revision={rev}")

if __name__=="__main__":
    main()
