"""Test whether 2026 INSC 993 expressly names seven older P0 pension cases.

A thematic overlap is NOT an express judicial citation or an overruling.
Only matched PDF pages and snippets may be described as direct references.
"""
from __future__ import annotations
import hashlib,io,json,re
from pathlib import Path
import fitz
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
PDF="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.pdf"
META="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.json"
DEST="legal_knowledge/judicial_treatment/v3.5"

CASES={
"DCLR-SC-2015-L02":("Union of India v Manjeet Singh",("manjeet singh","manjit singh")),
"DCLR-SC-2015-L03":("Union of India v Angad Singh Titaria",("angad singh titaria","angad titaria")),
"DCLR-SC-2016-L04":("Ex Hav Mani Ram Bhaira v Union of India",("mani ram bhaira","maniram bhaira")),
"DCLR-SC-1996-L07":("Union of India v Baljit Singh",("baljit singh","baltit singh")),
"DCLR-SC-2005-L08":("Controller of Defence Accounts (Pension) v S Balachandran Nair",("balachandran nair","s. balachandran")),
"DCLR-SC-2008-L09":("Union of India v Surinder Singh Rathore",("surinder singh rathore","surinder rathore")),
"DCLR-SC-2007-L10":("Union of India v Keshar Singh",("keshar singh","kesar singh")),
}

def remote(path,revision=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=path,revision=revision,force_download=True))

def flatten(s):
    return re.sub(r"\s+"," ",s).casefold()

def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Private HF dataset required")
    data=remote(PDF).read_bytes()
    meta=json.loads(remote(META).read_text())
    sha=hashlib.sha256(data).hexdigest()
    if sha!=meta["sha256"] or meta["source_tier"]!="OFFICIAL_SUPREME_COURT_API":
        raise RuntimeError("Official 2026 source checksum/tier mismatch")
    with fitz.open(stream=data,filetype="pdf") as pdf:
        pages=[flatten(x.get_text("text")) for x in pdf]
    results=[]
    for id,(name,patterns) in CASES.items():
        located=[]
        for pageno,txt in enumerate(pages,1):
            for namevariant in patterns:
                position=txt.find(namevariant)
                if position>=0:
                    excerpt=txt[max(0,position-110):min(len(txt),position+260)]
                    located.append({"pdf_page_1based":pageno,"search_variant":namevariant,
                                    "context_excerpt":excerpt,
                                    "excerpt_sha256":hashlib.sha256(excerpt.encode()).hexdigest()})
                    break
        direct=bool(located)
        results.append({
         "older_case_id":id,"older_case":name,
         "newer_decision":"Union of India v Col NC Isaac (Retd.)",
         "newer_neutral_citation":"2026 INSC 993",
         "newer_source_path":PDF,"newer_source_sha256":sha,
         "full_pdf_text_pages_examined":len(pages),
         "express_case_name_found_in_extracted_text":direct,
         "observations":located,
         "relationship_status":("EXPRESS_REFERENCE_CONTEXT_MUST_BE_REVIEWED" if direct else
                                "TOPIC_RELEVANCE_ONLY_NO_EXPRESS_NAME_MATCH"),
         "legal_effect_on_older_case":"NOT_DETERMINED",
         "no_express_name_is_not_proof_of_no_indirect_treatment":True,
         "jag_approved":False
        })
        print("V35_CASE_CITATION",id,"express_name",direct,"pages",[x["pdf_page_1based"] for x in located])
    if len(results)!=7:
        raise RuntimeError("Seven pension source citations expected")
    output="".join(json.dumps(z,ensure_ascii=False)+"\n" for z in results).encode("utf-8")
    summary={
       "cases_checked":7,
       "official_source_sha256":sha,
       "cases_expressly_named":sum(x["express_case_name_found_in_extracted_text"] for x in results),
       "cases_not_expressly_named":sum(not x["express_case_name_found_in_extracted_text"] for x in results),
       "treatment_certified":0,
       "method":"Exact normalized name variations in all 93 official source PDF pages, contextual snippets; no semantic inferences",
       "caveats":["A case's absence from the judgment text is not proof of absence of indirect legal impact.",
                  "A named citation is not proof it was followed, distinguished or overruled.",
                  "Governing rule dates and later decisions remain to be independently assessed.",
                  "No JAG approval."]
    }
    files={
      DEST+"/01_Seven_Pension_Case_Express_Citation_Checks.jsonl":output,
      DEST+"/02_Seven_Pension_Case_Check_Summary.json":(json.dumps(summary,indent=2)+"\n").encode(),
      DEST+"/README.md":(
         "# 2026 NC Isaac versus seven earlier pension cases, source-level test\n\n"
         "All 93 original Supreme Court PDF pages were checked for distinct party-name strings "
         "after verifying the original SHA. This narrowly reports **express mentions only**. "
         "It does not equate mention with treatment or imply a nonmentioned case was not indirectly "
         "affected. Each older-case ratio, applicable entitlement-rule version and later case law "
         "requires manual legal review before JAG approval.\n"
      ).encode()
    }
    res=api.create_commit(repo_id=REPO,repo_type="dataset",
       operations=[CommitOperationAdd(path_in_repo=k,path_or_fileobj=io.BytesIO(v)) for k,v in files.items()],
       commit_message="Test actual express references to seven pension cases in official 2026 NC Isaac judgment")
    rev=getattr(res,"oid",None)
    if not rev:
        raise RuntimeError("Source citation audit commit absent")
    for p,blob in files.items():
        if hashlib.sha256(remote(p,rev).read_bytes()).digest()!=hashlib.sha256(blob).digest():
            raise RuntimeError("HF readback SHA mismatch: "+p)
    print("V35_EXPRESS_CITATIONS_VERIFIED",len(results),"direct",summary["cases_expressly_named"],"revision",rev)

if __name__=="__main__":
    main()
