"""Acquire two unresolved historical Supreme Court JUDIS originals if authenticated.

Never infer that a case is absent from a failed web request. All outcomes are
persisted to the private canonical dataset, with SHA-256 read-back validation.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import fitz
import requests
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

DATASET="hariomahlawat/mimamsa-corpus"
BASE="legal_knowledge/source_acquisition/v3.3"
CASES=[
    {
      "case_id":"DCLR-SC-1964-A11",
      "case_name":"Ram Sarup v Union of India",
      "decision_date":"1963-12-12",
      "url":"https://api.sci.gov.in/jonew/judis/3387.pdf",
      "title_tokens":["ram sarup","union of india"],
      "pdf_path":"legal_knowledge/judgment_originals/sci/historical/v3.3/ram_sarup_1963.pdf",
    },
    {
      "case_id":"DCLR-SC-2005-L01",
      "case_name":"State (NCT of Delhi) v Navjot Sandhu @ Afsan Guru",
      "decision_date":"2005-08-04",
      "url":"https://api.sci.gov.in/jonew/judis/27092.pdf",
      "title_tokens":["navjot sandhu","supreme court"],
      "pdf_path":"legal_knowledge/judgment_originals/sci/historical/v3.3/navjot_sandhu_2005.pdf",
    },
]

def remote(path, revision=None):
    return Path(hf_hub_download(repo_id=DATASET,repo_type="dataset",
                                filename=path,revision=revision,force_download=True))

def main():
    api=HfApi()
    if not api.repo_info(repo_id=DATASET,repo_type="dataset").private:
        raise RuntimeError("Refuse operation on public dataset")

    records, archives=[],{}
    for case in CASES:
        row={
            "case_id":case["case_id"],"case_name":case["case_name"],
            "expected_decision_date":case["decision_date"],
            "attempted_official_url":case["url"],
            "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
            "source_file_archived":False,
            "original_case_holding_verified":False,
            "subsequent_judicial_treatment_verified":False,
            "jag_approved":False,
        }
        pdf_path=case["pdf_path"]
        if api.file_exists(repo_id=DATASET,repo_type="dataset",filename=pdf_path):
            meta_path=pdf_path[:-4]+".json"
            if not api.file_exists(repo_id=DATASET,repo_type="dataset",filename=meta_path):
                raise RuntimeError("Existing court PDF lacks provenance record: "+pdf_path)
            meta=json.loads(remote(meta_path).read_text(encoding="utf-8"))
            if hashlib.sha256(remote(pdf_path).read_bytes()).hexdigest()!=meta["sha256"]:
                raise RuntimeError("Remote court PDF SHA mismatch: "+pdf_path)
            row.update({"source_file_archived":True,"status":"ALREADY_ARCHIVED_AND_SHA256_VERIFIED",
                        "sha256":meta["sha256"],"path":pdf_path})
            records.append(row)
            print("HIST_JUDIS_ALREADY_ARCHIVED",case["case_id"])
            continue
        try:
            response=requests.get(case["url"],timeout=40,headers={"User-Agent":"Mimamsa Source Authentication/1.0"})
            row.update({"http_status":response.status_code,
                        "content_type":response.headers.get("content-type","")[:96],
                        "response_bytes":len(response.content)})
            response.raise_for_status()
            data=response.content
            # Legacy JUDIS may prepend a non-PDF wrapper. Record the binary
            # signature position without claiming that a MIME label proves PDF.
            magic_offset=data[:1024].find(b"%PDF-")
            row["first_24_octets_hex"]=data[:24].hex()
            row["pdf_header_position_first_1024"]=magic_offset
            if magic_offset<0 or len(data)<12000:
                row["status"]="RESPONSE_NOT_A_VALID_PDF"
                records.append(row)
                print("HIST_JUDIS_UNAVAILABLE",case["case_id"],row["status"],row["http_status"],
                      "bytes",len(data),"first24",data[:24].hex(),"pdf_magic",magic_offset)
                continue
            if len(data)>30000000:
                row["status"]="PDF_EXCEEDS_ARCHIVAL_SIZE_GATE"
                records.append(row)
                continue
            with fitz.open(stream=data,filetype="pdf") as doc:
                pages=len(doc)
                extracted=" ".join(page.get_text("text") for page in doc).casefold()
            extracted=" ".join(extracted.split())
            if not all(t in extracted for t in case["title_tokens"]):
                row.update({"status":"DOCUMENT_IDENTITY_NOT_ESTABLISHED_FROM_EXTRACTABLE_TEXT",
                            "pages":pages})
                records.append(row)
                print("HIST_JUDIS_IDENTITY_PENDING",case["case_id"],pages)
                continue
            if case["decision_date"][:4] not in extracted:
                row.update({"status":"CASE_DECISION_YEAR_NOT_IN_SOURCE_TEXT",
                            "pages":pages})
                records.append(row)
                continue

            sha=hashlib.sha256(data).hexdigest()
            meta_path=pdf_path[:-4]+".json"
            metadata={
              "case_id":case["case_id"],"case_name":case["case_name"],
              "date":case["decision_date"],"court":"Supreme Court of India",
              "source_url":case["url"],"final_url":response.url,
              "source_tier":"official_sci_judis_pdf_case_title_verified",
              "archived_at_utc":datetime.now(timezone.utc).isoformat(),
              "sha256":sha,"bytes":len(data),"pages":pages,"path":pdf_path,
              "document_identity_evidence":"case-name tokens and decision year in full official PDF text",
              "later_treatment_reviewed_exhaustively":False,
              "legal_holding_verified":False,"jag_approved":False,
            }
            archives[pdf_path]=data
            archives[meta_path]=(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n").encode()
            row.update({"source_file_archived":True,"status":"OFFICIAL_SOURCE_PDF_IDENTITY_AND_SHA_VERIFIED",
                        "sha256":sha,"path":pdf_path,"pages":pages})
            print("HIST_JUDIS_VALIDATED",case["case_id"],"pages",pages,"sha",sha)
        except requests.RequestException as exc:
            row.update({"status":"OFFICIAL_ENDPOINT_RETRIEVAL_FAILED",
                        "failure_type":type(exc).__name__,
                        "detail":str(exc).split("\n")[0][:280]})
            print("HIST_JUDIS_RETRIEVAL_FAILED",case["case_id"],type(exc).__name__)
        records.append(row)

    if len(records)!=len(CASES):
        raise RuntimeError("All requested source attempts must be accounted for")
    receipt={
      "batch":"v3.3","source_authority":"Supreme Court of India (JUDIS URL candidates)",
      "completed_utc":datetime.now(timezone.utc).isoformat(),
      "attempts":len(records),
      "archived_verified_count":sum(x["source_file_archived"] for x in records),
      "new_archived_verified_count":sum(x.get("status")=="OFFICIAL_SOURCE_PDF_IDENTITY_AND_SHA_VERIFIED" for x in records),
      "cases":records,
      "critical_caveats":[
        "A failed endpoint response does not establish case or court judgment absence.",
        "The source PDF is archived only when the case name and year are checked against extractable PDF text.",
        "A verified judgment source does not establish its continuing legal force or JAG approval.",
        "Never use the whole-case status 'overruled' for Navjot Sandhu based only on its older Section65B proposition."
      ]
    }
    receipt_path=BASE+"/01_Historical_JUDIS_Source_Attempts.json"
    archives[receipt_path]=(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n").encode()
    commit=api.create_commit(repo_id=DATASET,repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=name,path_or_fileobj=io.BytesIO(data))
                    for name,data in archives.items()],
        commit_message="Record official JUDIS historical judgment-source acquisition attempts v3.3")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("Hugging Face source acquisition commit has no revision")
    for name, data in archives.items():
        if hashlib.sha256(remote(name,rev).read_bytes()).hexdigest()!=hashlib.sha256(data).hexdigest():
            raise RuntimeError("Hugging Face source acquisition read-back checksum mismatch: "+name)
    print("HIST_JUDIS_SOURCE_AUDIT_VERIFIED",len(records),
          "archived",receipt["archived_verified_count"],"new",receipt["new_archived_verified_count"],
          "revision",rev)

if __name__=="__main__":
    main()
