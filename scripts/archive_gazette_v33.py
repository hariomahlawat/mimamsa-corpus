"""Acquire and verify the official eGazette 2022 Army Rules amendment.

This is a proof of official Gazette archival, NOT proof of 1954 or current Rule 23(3).
"""
from __future__ import annotations
import hashlib, io, json
from datetime import datetime, timezone
from pathlib import Path
import requests, fitz
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
URL="https://egazette.gov.in/WriteReadData/2022/236353.pdf"
PDF="legal_knowledge/gazette_originals/2022/army_rules_sro_6e_2022.pdf"
META="legal_knowledge/gazette_originals/2022/army_rules_sro_6e_2022.json"

def remote(path, revision=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",
                                filename=path,revision=revision,force_download=True))

def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Primary dataset must be private")
    if api.file_exists(repo_id=REPO,repo_type="dataset",filename=PDF):
        if not api.file_exists(repo_id=REPO,repo_type="dataset",filename=META):
            raise RuntimeError("Existing Gazette PDF lacks source metadata")
        manifest=json.loads(remote(META).read_text())
        if hashlib.sha256(remote(PDF).read_bytes()).hexdigest()!=manifest["sha256"]:
            raise RuntimeError("Existing Gazette primary-source checksum mismatch")
        print("V33_EGAZETTE_2022_ALREADY_VERIFIED",manifest["sha256"])
        return

    response=requests.get(URL,timeout=45,
                          headers={"User-Agent":"Mimamsa Army Rules Gazette Source Verification/1.0"})
    response.raise_for_status()
    body=response.content
    if not body.startswith(b"%PDF-") or len(body)<6000:
        raise RuntimeError("Official eGazette endpoint returned non-PDF / insufficient content")
    with fitz.open(stream=body,filetype="pdf") as pdf:
        pages=len(pdf)
        extracted=" ".join(p.get_text("text") for p in pdf)
        searchable=" ".join(extracted.split()).casefold()
    if not ("army" in searchable and "2022" in searchable and "16a" in searchable):
        raise RuntimeError("Gazette PDF content does not match Army Rule16A amendment")
    if not ("6(e)" in searchable or "6 (e)" in searchable):
        raise RuntimeError("Instrument SRO 6(E) not identifiable in PDF")
    checksum=hashlib.sha256(body).hexdigest()
    manifest={
        "source":"Government of India eGazette",
        "publisher":"Ministry of Defence / Department of Publication",
        "instrument":"Army (Amendment) Rules, 2022",
        "notification":"S.R.O. 6(E)",
        "notification_date":"2022-06-06",
        "part":"Gazette of India Extraordinary Part II Section 4",
        "official_source_url":URL,"final_url":response.url,
        "downloaded_utc":datetime.now(timezone.utc).isoformat(),
        "path":PDF,"sha256":checksum,"bytes":len(body),"pages":pages,
        "amendment_scope_as_printed":"Rule 16A only",
        "does_this_instrument_modify_rules_22_23_180_182":False,
        "does_this_prove_original_rule_23_wording":False,
        "full_amendment_currency_checked_through_2026":False,
        "jag_approved":False
    }
    obj=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=PDF,path_or_fileobj=io.BytesIO(body)),
                    CommitOperationAdd(path_in_repo=META,path_or_fileobj=io.BytesIO(obj))],
        commit_message="Archive official eGazette S.R.O. 6(E) Army Rules 2022 with source SHA and safeguards")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("No Hugging Face commit revision")
    if hashlib.sha256(remote(PDF,rev).read_bytes()).hexdigest()!=checksum or remote(META,rev).read_bytes()!=obj:
        raise RuntimeError("Official eGazette archival readback failed")
    print(f"V33_EGAZETTE_2022_VERIFIED pages={pages} sha256={checksum} revision={rev}")

if __name__=="__main__":
    main()
