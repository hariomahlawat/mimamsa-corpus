"""Archive an official Indian Railways publication containing the S.R. Dhingra SC judgment.

The archived file is a *government-hosted reproduction* inside railway circulars,
NOT a byte-verified original Supreme Court PDF. Research only, no JAG approval.
"""
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import fitz
import requests
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
URL="https://scr.indianrailways.gov.in/uploads/files/1306491517676-2008sc.pdf"
PDF="legal_knowledge/judgment_sources/government_reproductions/2007/dhingra_indian_railways_2008_compilation.pdf"
META="legal_knowledge/judgment_sources/government_reproductions/2007/dhingra_indian_railways_2008_compilation.json"

def remote(path,rev=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=path,
                                revision=rev,force_download=True))

def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Private research dataset required")
    if api.file_exists(repo_id=REPO,repo_type="dataset",filename=PDF):
        if not api.file_exists(repo_id=REPO,repo_type="dataset",filename=META):
            raise RuntimeError("Source PDF missing corresponding provenance metadata")
        obj=json.loads(remote(META).read_text())
        if hashlib.sha256(remote(PDF).read_bytes()).hexdigest()!=obj["sha256"]:
            raise RuntimeError("Existing Indian Railways Dhingra copy failed SHA check")
        print("D33_DHINGRA_GOV_REPRO_ALREADY_VERIFIED",obj["sha256"])
        return

    response=requests.get(URL,timeout=65,
                          headers={"User-Agent":"Mimamsa Original Source Provenance 1.0"})
    response.raise_for_status()
    data=response.content
    if len(data)<60000 or b"%PDF-" not in data[:1024]:
        raise RuntimeError("Indian Railways URL did not return valid PDF payload")
    with fitz.open(stream=data,filetype="pdf") as doc:
        pages=len(doc)
        if pages<30 or pages>5000:
            raise RuntimeError("Unexpected source compilation page count")
        matched_pages=[]
        for n,page in enumerate(doc):
            text=" ".join(page.get_text("text").split()).casefold()
            if "s.r. dhingra" in text or "s.r.dhingra" in text:
                matched_pages.append(n+1)
        fullcheck=" ".join(doc[n-1].get_text("text").casefold() for n in matched_pages[:8])
    if not matched_pages or not ("supreme court" in fullcheck and "dhingra" in fullcheck):
        raise RuntimeError("Case title and Supreme Court text not demonstrated in government reproduction")
    sha=hashlib.sha256(data).hexdigest()
    source={
      "curated_case_id":"DCLR-SC-2008-L05",
      "judgment_title":"Union of India v S.R. Dhingra and Others",
      "judgment_date":"2007-12-14",
      "case_number":"Transferred Case (Civil) No. 106 of 2006",
      "source_tier":"INDIAN_RAILWAYS_GOVERNMENT_HOSTED_COMPILATION_CONTAINING_SC_JUDGMENT_COPY",
      "court":"Supreme Court of India",
      "publisher_and_source_host":"Indian Railways, Government of India",
      "source_url":URL,"retrieval_utc":datetime.now(timezone.utc).isoformat(),
      "path":PDF,"bytes":len(data),"pages":pages,"sha256":sha,
      "pages_with_dhingra_name_one_based":matched_pages[:30],
      "judgment_title_text_checked":True,
      "original_supreme_court_source_byte_identical":"NOT_TESTED",
      "source_original_is_compilation_not_standalone_court_decision":True,
      "domain_classification":"CIVIL_SERVICE_RAILWAYS_PENSION_NOT_ARMY_SPECIFIC",
      "commander_facing_release":False,
      "legal_holding_verified":False,
      "subsequent_treatment_exhaustive":False,
      "jag_approved":False
    }
    encoded=(json.dumps(source,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    result=api.create_commit(repo_id=REPO,repo_type="dataset",
        operations=[
          CommitOperationAdd(path_in_repo=PDF,path_or_fileobj=io.BytesIO(data)),
          CommitOperationAdd(path_in_repo=META,path_or_fileobj=io.BytesIO(encoded))
        ],
        commit_message="Preserve Indian Railways government reproduction of 2007 SC Dhingra judgment, comparison only")
    rev=getattr(result,"oid",None)
    if not rev:
        raise RuntimeError("Hugging Face commit has no revision")
    if hashlib.sha256(remote(PDF,rev).read_bytes()).hexdigest()!=sha or remote(META,rev).read_bytes()!=encoded:
        raise RuntimeError("Government source reproduction upload/readback failed")
    print("D33_DHINGRA_GOV_REPRO_VERIFIED", "pages",pages,"sha256",sha,
          "judgment_pages",matched_pages[:10],"revision",rev)

if __name__=="__main__":
    main()
