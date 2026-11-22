"""Archive and legally stage 2026 INSC 993 with transparent source-tier provenance.

Only preserves a PDF with identity-checked pages and verified SHA-256 read-back.
A PDF archive is not JAG approval, holding clearance or full subsequent treatment.
"""
from __future__ import annotations
import hashlib,io,json
from datetime import datetime,timezone
from pathlib import Path
import requests,fitz
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
PDF="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.pdf"
META="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.json"
SOURCES=[
("OFFICIAL_SUPREME_COURT_API",
 "https://api.sci.gov.in/supremecourt/2025/129/129_2025_4_1501_74249_Judgement_15-Sep-2026.pdf"),
("THIRD_PARTY_MIRROR_LIVELAW",
 "https://www.livelaw.in/pdf_upload/2026/10/12/2026-livelaw-sc-935-union-of-india-v-col-nc-isaac-retd-15-sep-2026-705949.pdf"),
("THIRD_PARTY_MIRROR_SAINIKWELFARE",
 "https://sainikwelfare.in/wp-content/uploads/2026/09/SC-Judgement-on-Dis-Pension-15th-Sept-2026.pdf")
]

def remote(path,revision=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",
                                filename=path,revision=revision,force_download=True))

def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("The legal archive must remain private")
    if api.file_exists(repo_id=REPO,repo_type="dataset",filename=PDF):
        if not api.file_exists(repo_id=REPO,repo_type="dataset",filename=META):
            raise RuntimeError("Existing Isaac PDF has no provenance record")
        m=json.loads(remote(META).read_text())
        if hashlib.sha256(remote(PDF).read_bytes()).hexdigest()!=m["sha256"]:
            raise RuntimeError("Existing NC Isaac source checksum mismatch")
        print("V34_ISAAC_ALREADY_VERIFIED source_tier="+m["source_tier"]+" sha256="+m["sha256"])
        return

    attempts=[]
    for tier,url in SOURCES:
        item={"tier":tier,"url":url}
        try:
            resp=requests.get(url,timeout=38,headers={"User-Agent":"Mimamsa Military Law Source Archive/1.0"})
            item.update({"status_code":resp.status_code,"bytes":len(resp.content),
                         "content_type":resp.headers.get("content-type")})
            resp.raise_for_status()
            data=resp.content
            magic=data[:1024].find(b"%PDF-")
            if magic<0 or len(data)<85000:
                raise ValueError("No PDF magic in first 1024 bytes or insufficient payload")
            with fitz.open(stream=data,filetype="pdf") as doc:
                pages=len(doc)
                beginning=" ".join(doc[i].get_text("text") for i in range(min(8,pages))).casefold()
                full=" ".join(p.get_text("text") for p in doc).casefold()
            if pages<70 or not all(t in full for t in ("2026 insc 993","isaac","entitlement rules 2008","medical board")):
                raise ValueError("SC 2026 INSC 993 case identity / pagination mismatch")
            if not ("15 september 2026" in full or "september 15 2026" in full or "september 15, 2026" in full):
                raise ValueError("Judgment decision date not corroborated")
            if not ("39." in full and "fifteen years" in full and "rule 7" in full):
                raise ValueError("Required concluding discussion not found")
            sha=hashlib.sha256(data).hexdigest()
            meta={
                "case_name":"Union of India & Ors v Col NC Isaac (Retd.)",
                "neutral_citation":"2026 INSC 993",
                "decision_date":"2026-09-15",
                "court":"Supreme Court of India",
                "source_url":url,"source_tier":tier,
                "source_is_official_court_domain":tier.startswith("OFFICIAL"),
                "retrieved_utc":datetime.now(timezone.utc).isoformat(),
                "path":PDF,"bytes":len(data),"pages":pages,"sha256":sha,
                "pdf_magic_offset":magic,
                "legal_topic":"Armed forces disability pension, 1982 vs 2008 entitlement rules",
                "review_locations":["paras 21-30: rule history and presumptions",
                                    "para 33: onus/time exception",
                                    "para 39: dismissal, medical-board scrutiny, 15-year claims"],
                "case_identity_passed":True,
                "source_byte_parity_with_official_sc_pdf":True if tier.startswith("OFFICIAL") else "NOT_TESTED",
                "legal_holding_verified":False,
                "subsequent_treatment_exhaustive":False,
                "jag_approved":False,
                "attempt_log":attempts
            }
            encoded=(json.dumps(meta,ensure_ascii=False,indent=2)+"\n").encode()
            commit=api.create_commit(repo_id=REPO,repo_type="dataset",
                operations=[CommitOperationAdd(path_in_repo=PDF,path_or_fileobj=io.BytesIO(data)),
                            CommitOperationAdd(path_in_repo=META,path_or_fileobj=io.BytesIO(encoded))],
                commit_message="Preserve 2026 NC Isaac pension ruling with source provenance and SHA verification")
            rev=getattr(commit,"oid",None)
            if not rev:
                raise RuntimeError("Hugging Face commit missing revision")
            if hashlib.sha256(remote(PDF,rev).read_bytes()).hexdigest()!=sha or remote(META,rev).read_bytes()!=encoded:
                raise RuntimeError("Remote primary-source read-back mismatch")
            print("V34_ISAAC_VERIFIED",tier,"pages",pages,"sha256",sha,"revision",rev)
            return
        except (requests.RequestException,ValueError,fitz.FileDataError) as e:
            item["status"]="NOT_ARCHIVED"
            item["failure_type"]=type(e).__name__
            item["failure_reason"]=str(e)[:180]
            attempts.append(item)
            print("V34_ISAAC_SOURCE_FAILED",tier,type(e).__name__)

    # Persist failed attempts rather than falsely saying original was archived.
    status="legal_knowledge/source_acquisition/v3.4/isaac_2026_acquisition_attempts.json"
    report={"case":"2026 INSC 993","attempted_utc":datetime.now(timezone.utc).isoformat(),
            "source_archived":False,"attempts":attempts,"legal_holding_verified":False,
            "jag_approved":False}
    payload=(json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode()
    rev=api.create_commit(repo_id=REPO,repo_type="dataset",
      operations=[CommitOperationAdd(path_in_repo=status,path_or_fileobj=io.BytesIO(payload))],
      commit_message="Record unsuccessful 2026 NC Isaac primary-source acquisition without legal promotion").oid
    if remote(status,rev).read_bytes()!=payload:
        raise RuntimeError("Source acquisition failure audit readback mismatch")
    print("V34_ISAAC_SOURCE_NOT_ARCHIVED",len(attempts),"attempts")

if __name__=="__main__":
    main()
