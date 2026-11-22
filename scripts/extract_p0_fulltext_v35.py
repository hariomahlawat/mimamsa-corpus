"""Extract page-addressable full judgment text from 11 P0 source dossiers.

The extraction is forensic working evidence, not a judicial holding, citation
validation, current-law classification, or JAG approval. Immutable originals
remain in their existing locations. Output is additive to private HF.
"""
from __future__ import annotations
import csv,hashlib,io,json,re
from datetime import datetime,timezone
from pathlib import Path
import fitz
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
SOURCE="legal_knowledge/holding_review/v3.4/01_P0_PDF_Provenance.jsonl"
DEST="legal_knowledge/full_text_working/v3.5"

def get(path,revision=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",
                                filename=path,revision=revision,force_download=True))

def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Only private legal archive permitted")
    refs=[json.loads(s) for s in get(SOURCE).read_text(encoding="utf-8").splitlines() if s.strip()]
    if len(refs)!=11:
        raise RuntimeError("Expected exactly 11 original P0 records")
    files={}
    manifest=[]
    for r in refs:
        cid=r["case_id"]
        path=r.get("pdf_path")
        if not path:
            manifest.append({"case_id":cid,"state":"NO_ORIGINAL_PDF_ARCHIVED","page_count":0})
            continue
        raw=get(path).read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        if sha!=r["sha256"]:
            raise RuntimeError("Source PDF SHA mismatch "+cid)
        with fitz.open(stream=raw,filetype="pdf") as doc:
            pages=[]
            for i,page in enumerate(doc,1):
                text=page.get_text("text",sort=True)
                pages.append({
                  "case_id":cid,"pdf_page_1based":i,
                  "source_path":path,
                  "source_sha256":sha,
                  "text":text,
                  "text_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),
                  "extraction_method":"pymupdf_text_sort_true",
                  "source_tier":r.get("source_tier",""),
                  "source_is_court_original_byte_verified":r.get("source_tier")=="OFFICIAL_SUPREME_COURT_JUDIS",
                  "judgment_holding_verified":False,
                  "jag_approved":False
                })
        data=("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in pages)).encode("utf-8")
        outfile=f"{DEST}/pages/{cid}.jsonl"
        files[outfile]=data
        manifest.append({
          "case_id":cid,"state":"PAGES_EXTRACTED_SHA_OF_PDF_VERIFIED",
          "source_path":path,"source_sha256":sha,
          "source_tier":r.get("source_tier",""),"page_count":len(pages),
          "extracted_utf8_bytes":len(data),"output_path":outfile,
          "legal_holding_verified":False,"jag_approved":False
        })
        print("V35_FULL_TEXT_EXTRACTED",cid,"pages",len(pages),"bytes",len(data))
    summary={
       "version":"3.5",
       "generated_utc":datetime.now(timezone.utc).isoformat(),
       "case_count":len(refs),
       "source_pdf_verified":sum("PAGES_EXTRACTED" in x["state"] for x in manifest),
       "source_pdf_missing":sum(x["state"]=="NO_ORIGINAL_PDF_ARCHIVED" for x in manifest),
       "extractable_pdf_pages":sum(x.get("page_count",0) for x in manifest),
       "manifest":manifest,
       "limitations":[
         "OCR or embedded PDF text may misprint person names and paragraph numbers",
         "Full case PDF can contain headnotes and unrelated connected orders",
         "Do not infer holdings from headnotes or a matching keyword alone",
         "A stored SHA check is source integrity, not current legal force or source-origin authentication",
         "No JAG approval, no original-case mutation"
       ]
    }
    files[f"{DEST}/01_Extraction_Manifest.json"]=(json.dumps(summary,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    files[f"{DEST}/README.md"]=(
      "# v3.5 source-based page-by-page full judgment text working set\n\n"
      "Ten P0 source PDFs are verified byte-for-byte against v3.4 source manifest SHA-256 "
      "and exported with PDF page numbers and page text (PyMuPDF). One case lacks a PDF. "
      "Some sources are SCR copies, one a third-party multi-order mirror; original court byte "
      "parity is not established for those. No legal holdings, subsequent treatment, JAG, or "
      "commander-facing readiness is certified by text extraction.\n"
    ).encode()
    operations=[CommitOperationAdd(path_in_repo=k,path_or_fileobj=io.BytesIO(v)) for k,v in files.items()]
    res=api.create_commit(repo_id=REPO,repo_type="dataset",operations=operations,
                          commit_message="Add page-addressable full P0 court text evidence with original-source SHA provenance v3.5")
    revision=getattr(res,"oid",None)
    if not revision:
        raise RuntimeError("No HF dataset revision received")
    for p,data in files.items():
        observed=get(p,revision).read_bytes()
        if hashlib.sha256(observed).digest()!=hashlib.sha256(data).digest():
            raise RuntimeError("Remote full-text readback mismatch: "+p)
    print("V35_FULL_TEXT_VERIFIED",len(files),"files",summary["extractable_pdf_pages"],"pages revision="+revision)

if __name__=="__main__":
    main()
