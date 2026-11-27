"""Preserve a third-party PDF copy of Supreme Court's Mani Ram Bhaira signed 2016 order.

The hosting domain is not official SCI. Court identity checked within the PDF;
source-byte identity with an SCI-hosted original remains UNVERIFIED.
"""
import hashlib, io, json
from datetime import datetime, timezone
from pathlib import Path
import requests, fitz
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
URL="https://virendersinghkadian.com/wp-content/uploads/2023/09/CA-4409-OF-2011-EX-HAV-MANI-RAM-BHAIRA-PIVD-SUPREME-COURT-JUDGEMENT.pdf"
PDF="legal_knowledge/judgment_sources/third_party_court_document_copies/2016/mani_ram_bhaira_mirror_2016.pdf"
META="legal_knowledge/judgment_sources/third_party_court_document_copies/2016/mani_ram_bhaira_mirror_2016.json"

def remote(path,revision=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=path,
                                revision=revision,force_download=True))
def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Private canonical dataset required")
    if api.file_exists(repo_id=REPO,repo_type="dataset",filename=PDF):
        if not api.file_exists(repo_id=REPO,repo_type="dataset",filename=META):
            raise RuntimeError("Existing mirror file lacks provenance")
        record=json.loads(remote(META).read_text())
        if hashlib.sha256(remote(PDF).read_bytes()).hexdigest()!=record["sha256"]:
            raise RuntimeError("Existing third-party judgment copy checksum mismatch")
        print("V33_MANIRAM_MIRROR_ALREADY_VERIFIED",record["sha256"])
        return
    resp=requests.get(URL,timeout=50,headers={"User-Agent":"Mimamsa legal source preservation/1.0"})
    resp.raise_for_status()
    data=resp.content
    if len(data)<12000 or b"%PDF-" not in data[:1024]:
        raise RuntimeError("Third-party link did not return a valid PDF header")
    with fitz.open(stream=data,filetype="pdf") as doc:
        pages=len(doc)
        text=" ".join(p.get_text("text") for p in doc).casefold()
        first=" ".join(doc[i].get_text("text") for i in range(min(pages,7))).casefold()
    for token in ("supreme court of india","mani ram bhaira","4409","2011"):
        if token not in first:
            raise RuntimeError("Case identity mismatch for mirrored 2016 signed court order: "+token)
    if not ("11th february, 2016" in text or "11/02/2016" in text or "11th february 2016" in text):
        raise RuntimeError("Date of decision not identified in signed order text")
    if not ("t.s.thakur" in first or "t.s. thakur" in first):
        raise RuntimeError("Judicial bench identification not found in text")
    sha=hashlib.sha256(data).hexdigest()
    meta={
        "case_id":"DCLR-SC-2016-L04",
        "case_name":"Ex Hav Mani Ram Bhaira v Union of India and Ors",
        "case_number":"Civil Appeal 4409 of 2011",
        "decision_date":"2016-02-11",
        "judgment_authority":"Supreme Court of India",
        "host_domain":"virendersinghkadian.com",
        "source_tier":"THIRD_PARTY_MIRROR_OF_SUPREME_COURT_SIGNED_ORDER_TEXT",
        "original_court_hosted_pdf_acquired":False,
        "original_signed_order_byte_for_byte_parity_to_official_sci":"NOT_TESTED",
        "judgment_order_text_case_identity_checked":True,
        "source_url":URL,"source_url_is_official_court":False,
        "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
        "path":PDF,"bytes":len(data),"pages":pages,"sha256":sha,
        "contains_multiple_orders":"Also includes a Satwinder Singh order and a court record of proceedings",
        "historical_context":"Army disability pension; review governing regulations and later Supreme Court case law before use",
        "legal_holding_exhaustively_verified":False,
        "later_treatment_checked_exhaustively":False,
        "jag_approved":False
    }
    enc=(json.dumps(meta,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=PDF,path_or_fileobj=io.BytesIO(data)),
                    CommitOperationAdd(path_in_repo=META,path_or_fileobj=io.BytesIO(enc))],
        commit_message="Archive unverified-provenance third-party copy of SC Mani Ram Bhaira signed order (research)")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("Hugging Face upload revision missing")
    if hashlib.sha256(remote(PDF,rev).read_bytes()).hexdigest()!=sha or remote(META,rev).read_bytes()!=enc:
        raise RuntimeError("Mirrored source archival SHA-256 readback failed")
    print("V33_MANIRAM_MIRROR_VERIFIED", "pages",pages,"sha256",sha,"revision",rev)

if __name__=="__main__":
    main()
