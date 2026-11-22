"""Obtain direct judicial context for seven older P0 cases cited in 2026 INSC 993.

Read exact Supreme Court PDF pages. Selection by paragraph/party text is an
evidence locator, never automatic judicial-treatment approval.
"""
import hashlib,io,json,re
from pathlib import Path
import fitz
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
SOURCE="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.pdf"
META="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.json"
OUT="legal_knowledge/judicial_treatment/v3.5/03_Isaac_Reasoning_Context.jsonl"
TERMS=["balachandran nair","baljit singh","surinder singh rathore",
       "manjeet singh","angad singh titaria","dharamvir singh",
       "medical board","onus of proof","15 years"]
PAGES=[48,49,50,51,52,59,60,61,62,68,69,70,72,73,74,85,86,92,93]

def get(p,rev=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=p,revision=rev,force_download=True))
def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Private original source required")
    src=get(SOURCE).read_bytes()
    meta=json.loads(get(META).read_text())
    sha=hashlib.sha256(src).hexdigest()
    if sha!=meta["sha256"] or meta["source_tier"]!="OFFICIAL_SUPREME_COURT_API":
        raise RuntimeError("2026 SC original identity check failed")
    out=[]
    with fitz.open(stream=src,filetype="pdf") as doc:
        if len(doc)!=93:
            raise RuntimeError("Unexpected official PDF page count")
        for n in PAGES:
            text=doc[n-1].get_text("text",sort=True)
            flattened=" ".join(text.split()).lower()
            hits=[word for word in TERMS if word in flattened]
            record={"judgment":"2026 INSC 993","pdf_page_1based":n,
                    "source_original_sha256":sha,
                    "source_pdf_path":SOURCE,
                    "legal_review_material":text,
                    "page_text_sha256":hashlib.sha256(text.encode()).hexdigest(),
                    "topics_or_names_found":hits,
                    "page_is_court_original":True,
                    "legal_holding_verified":False,"jag_approved":False}
            out.append(record)
            print("V35_REASONING_SOURCE_PAGE",n,"topics",",".join(hits))
    payload="".join(json.dumps(x,ensure_ascii=False)+"\n" for x in out).encode()
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",
         operations=[CommitOperationAdd(path_in_repo=OUT,path_or_fileobj=io.BytesIO(payload))],
         commit_message="Preserve selected official SC 2026 reasoning pages for seven older P0 pension case review")
    rev=getattr(commit,"oid",None)
    if not rev or get(OUT,rev).read_bytes()!=payload:
        raise RuntimeError("Court source-page extraction remote mismatch")
    print("V35_ISAAC_REASONING_PAGES_VERIFIED",len(out),"SHA",sha,"revision",rev)
if __name__=="__main__":
    main()
