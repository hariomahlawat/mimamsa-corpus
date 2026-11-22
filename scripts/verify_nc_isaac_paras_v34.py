"""Pinpoint passages in the official Supreme Court 2026 INSC 993 PDF.

Store exact PDF page and limited extracted judicial text, not just a secondary
summary. These are source-located propositions, NOT JAG-approved legal advice.
"""
import hashlib,io,json,re
from datetime import datetime,timezone
from pathlib import Path
import fitz
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
PDF="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.pdf"
META="legal_knowledge/judgment_originals/sci/2026/nc_isaac_2026.json"
DEST="legal_knowledge/holding_review/v3.4/nc_isaac_2026"

TARGETS=[
("V34-ISAAC-01","2026_INSC_993_P22",r"\b22\.\s+The difficulty arises", "Original source of 2008 entitlement rules and purported displacement of 1982"),
("V34-ISAAC-02","2026_INSC_993_P30_1",r"\b30\.1\s+Presumption at Entry", "1982 presumption versus wording of 2008 rule 5"),
("V34-ISAAC-03","2026_INSC_993_P30_3",r"\b30\.3\s+Onus of Proof", "Burden of proof as compared across schemes"),
("V34-ISAAC-04","2026_INSC_993_P30_4",r"\b30\.4\s+However", "Fifteen-year exception discussion"),
("V34-ISAAC-05","2026_INSC_993_P39",r"\b39\.\s+Having considered", "Final relief and directions"),
]
def remote(path,rev=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=path,revision=rev,force_download=True))

def main():
    api=HfApi()
    info=api.repo_info(repo_id=REPO,repo_type="dataset")
    if not info.private:
        raise RuntimeError("Private canonical dataset required")
    blob=remote(PDF).read_bytes()
    meta=json.loads(remote(META).read_text(encoding="utf-8"))
    if meta.get("source_tier")!="OFFICIAL_SUPREME_COURT_API" or hashlib.sha256(blob).hexdigest()!=meta["sha256"]:
        raise RuntimeError("Official source tier or SHA-256 invalid; refuse textual legal review")
    with fitz.open(stream=blob,filetype="pdf") as doc:
        pages=[ " ".join(p.get_text("text").split()) for p in doc ]
    found=[]
    for evidence_id,locator,pattern,subject in TARGETS:
        picks=[]
        for i,page in enumerate(pages,1):
            mt=re.search(pattern,page,re.I)
            if mt:
                excerpt=page[max(0,mt.start()-80):min(len(page),mt.start()+1900)]
                span_pages=[i]
                # Paragraph 39 begins at the foot of PDF p92; its operative
                # i/ii/iii directions continue on p93. Never truncate a ruling
                # at the source-page boundary.
                if locator=="2026_INSC_993_P39" and i<len(pages):
                    excerpt += " [NEXT_PDF_PAGE] " + pages[i][:2200]
                    span_pages.append(i+1)
                picks.append({
                  "pdf_page_1based":i, "pdf_page_span_1based":span_pages,
                  "excerpt":excerpt,
                  "excerpt_sha256":hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
                })
        if len(picks)>1:
            # Table of contents and prior-case quotation may match; no auto legal interpretation.
            status="MULTIPLE_LOCATORS_REQUIRING_REVIEW"
        elif picks:
            status="EXACT_PARAGRAPH_START_FOUND_IN_OFFICIAL_PDF"
        else:
            status="PARAGRAPH_ANCHOR_NOT_FOUND_REVIEW_REQUIRED"
        found.append({
          "evidence_id":evidence_id,
          "case":"Union of India v Col NC Isaac (Retd.)",
          "neutral_citation":"2026 INSC 993",
          "source_path":PDF,"source_sha256":meta["sha256"],
          "paragraph_locator":locator,"issue":subject,
          "locator_status":status,"matches":picks,
          "legal_holding_approved":False,"jag_approved":False
        })
        print("ISAAC_PINPOINT",evidence_id,status,"pages",[x["pdf_page_1based"] for x in picks])
    if not any(x["paragraph_locator"]=="2026_INSC_993_P39" and x["matches"] for x in found):
        raise RuntimeError("Primary disposition paragraph could not be located")
    data=("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in found)).encode()
    summary={
       "title":"2026 NC Isaac official source pinpoint audit",
       "date_utc":datetime.now(timezone.utc).isoformat(),
       "pdf":PDF,"official_pdf_sha256":meta["sha256"],"source_pages":len(pages),
       "issues":len(found),
       "exact_found":sum(x["locator_status"]=="EXACT_PARAGRAPH_START_FOUND_IN_OFFICIAL_PDF" for x in found),
       "missing":sum(not x["matches"] for x in found),
       "safety":"Source text located, not independent legal or JAG approval",
       "originals_mutated":False
    }
    out={
       DEST+"/01_Official_Judgment_Paragraph_Packets.jsonl":data,
       DEST+"/02_Source_Passages_Summary.json":(json.dumps(summary,indent=2)+"\n").encode(),
       DEST+"/README.md":(
         "# 2026 INSC 993 source pinpoint verification\n\n"
         "Short textual excerpts anchored to actual official Supreme Court PDF pages, "
         "each source file byte-checked against original SHA-256. "
         "A paragraph-start match may include prior case quotation or a table; "
         "review the opinion's full reasoning before treating any candidate as ratio. "
         "The court's legal framework, temporal applicability and all later treatment "
         "must be reviewed independently. No JAG approval.\n"
       ).encode()
    }
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",
          operations=[CommitOperationAdd(path_in_repo=k,path_or_fileobj=io.BytesIO(v)) for k,v in out.items()],
          commit_message="Locate exact official SC Isaac 2026 paragraph evidence for P0 pension case review")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("No HF revision returned")
    for path,content in out.items():
        if remote(path,rev).read_bytes()!=content:
            raise RuntimeError("Pinpoint source packet checksum mismatch")
    print("V34_ISAAC_PINPOINT_PACKET_VERIFIED",len(found),"parapoints",rev)
if __name__=="__main__":
    main()
