"""Archive 2024 Supreme Court primary judgment treating a different Navjot Sandhu proposition.

All source bytes preserved; SHA-256 readback verified; no JAG-approval promotion.
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import fitz
import requests
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

DATASET = "hariomahlawat/mimamsa-corpus"
URL = "https://api.sci.gov.in/supremecourt/2023/27190/27190_2023_3_1502_52269_Judgement_10-Apr-2024.pdf"
PDF = "legal_knowledge/judgment_originals/sci/2024/ravishankar_tandon_2024.pdf"
META = "legal_knowledge/judgment_originals/sci/2024/ravishankar_tandon_2024.json"

def load(path, revision=None):
    return Path(hf_hub_download(repo_id=DATASET, repo_type="dataset", filename=path,
                                revision=revision, force_download=True))

def main():
    api=HfApi()
    if not api.repo_info(repo_id=DATASET, repo_type="dataset").private:
        raise RuntimeError("Private canonical Hugging Face dataset is mandatory")
    if api.file_exists(repo_id=DATASET, repo_type="dataset", filename=PDF):
        if not api.file_exists(repo_id=DATASET, repo_type="dataset", filename=META):
            raise RuntimeError("Court PDF found without associated source provenance")
        record=json.loads(load(META).read_text(encoding="utf-8"))
        pdf=load(PDF).read_bytes()
        if hashlib.sha256(pdf).hexdigest()!=record["sha256"]:
            raise RuntimeError("Existing official judgment failed SHA-256 checksum")
        print("V33_SC_2024_ALREADY_VERIFIED", record["sha256"])
        return

    response=requests.get(URL,timeout=50,
                          headers={"User-Agent":"Mimamsa Legal Research Private Source Archive/1.0"})
    response.raise_for_status()
    pdf=response.content
    if not pdf.startswith(b"%PDF-") or len(pdf)<12000:
        raise RuntimeError("Court-hosted URL returned invalid PDF response")
    with fitz.open(stream=pdf,filetype="pdf") as doc:
        pages=len(doc)
        head=" ".join(doc[i].get_text("text") for i in range(min(3,pages))).casefold()
        full=" ".join(p.get_text("text") for p in doc).casefold()
    for token in ("ravishankar", "tandon", "state of chhattisgarh", "2024 insc 299"):
        if token not in head:
            raise RuntimeError("Source identity mismatch; token not found: "+token)
    for token in ("navjot sandhu", "section 27", "fact discovered"):
        if token not in full:
            raise RuntimeError("Expected section 27 / Navjot Sandhu reference not found: "+token)
    sha=hashlib.sha256(pdf).hexdigest()
    meta={
        "case_name":"Ravishankar Tandon v State of Chhattisgarh",
        "court":"Supreme Court of India",
        "neutral_citation":"2024 INSC 299",
        "decision_date":"2024-04-10",
        "source_url":URL,
        "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
        "path":PDF,"sha256":sha,"bytes":len(pdf),"pages":pages,
        "focus":"Prior case Navjot Sandhu (2005), distinct Section 27 discovery-of-fact passage",
        "reviewed_paragraphs":"12–14",
        "legal_treatment_scope":"CITED_AND_DISCUSSSED_NOT_WHOLE_CASE_REHABILITATION",
        "historical_statute":"Indian Evidence Act, 1872, section 27",
        "current_bsa_2023_checked":False,
        "subsequent_treatment_exhaustively_checked":False,
        "holding_cleared_for_operational_use":False,
        "jag_approved":False,
    }
    encoded=(json.dumps(meta,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    commit=api.create_commit(repo_id=DATASET,repo_type="dataset",
                             operations=[
                                 CommitOperationAdd(path_in_repo=PDF,path_or_fileobj=io.BytesIO(pdf)),
                                 CommitOperationAdd(path_in_repo=META,path_or_fileobj=io.BytesIO(encoded))
                             ],commit_message="Archive official SC 2024 Section 27 precedent with verified SHA and provenance")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("Missing HF commit revision")
    if hashlib.sha256(load(PDF,rev).read_bytes()).hexdigest()!=sha:
        raise RuntimeError("Uploaded 2024 Supreme Court PDF readback SHA mismatch")
    if load(META,rev).read_bytes()!=encoded:
        raise RuntimeError("Court source metadata readback mismatch")
    print(f"V33_SC_2024_VERIFIED pages={pages} sha256={sha} revision={rev}")

if __name__=="__main__":
    main()
