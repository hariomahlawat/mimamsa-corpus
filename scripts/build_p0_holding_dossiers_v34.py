"""Build review packets for eleven P0 Mimamsa cases from actual archived PDF bytes.
No automated excerpt or KB keyword link is a legally verified proposition.
"""
from __future__ import annotations

import csv, hashlib, io, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import fitz
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
ROOT="legal_knowledge/holding_review/v3.4"
CASES="legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"
KB="legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
P0="legal_knowledge/quality_audit/v3.0/01_Case_Metadata_Findings.jsonl"
CROSSWALK="legal_knowledge/crosswalk/v3.1/01_P0_PDF_Source_Crosswalk.csv"
JUDIS="legal_knowledge/source_acquisition/v3.3/01_Historical_JUDIS_Source_Attempts.json"
MIRROR="legal_knowledge/judgment_sources/third_party_court_document_copies/2016/mani_ram_bhaira_mirror_2016.json"

TOPIC={
"DCLR-SC-1964-A11":(("article 33","court martial","court-martial","section 125","section 191","fundamental rights"),("article 33","army act","court martial")),
"DCLR-SC-2005-L01":(("section 65b","electronic record","electronic evidence","section 27","discovery","certificate"),("electronic evidence","section 65b","section 27")),
"DCLR-SC-2015-L02":(("disability pension","medical board","attributable","aggravated","service"),("disability pension","attributable","medical board")),
"DCLR-SC-2015-L03":(("air force","disability pension","medical board","attributable","aggravated"),("air force","disability pension","medical board")),
"DCLR-SC-2016-L04":(("disability pension","pension","attributable","medical board","service"),("disability pension","attributable","medical board")),
"DCLR-SC-2008-L05":(("railway","pension","pay"),("railway","civil service","pension")),
"DCLR-SC-1996-L07":(("medical board","disability pension","pension","aggravated","attributable"),("disability pension","medical board","aggravated")),
"DCLR-SC-2005-L08":(("medical board","opinion","disability pension","attributable","aggravated"),("medical board","disability pension","attributable")),
"DCLR-SC-2008-L09":(("medical board","pension","disability","service"),("disability pension","medical board","service")),
"DCLR-SC-2007-L10":(("medical board","disability pension","attributable","aggravated","service"),("disability pension","medical board","attributable")),
"DCLR-SC-1997-L11":(("disturbed area","armed forces","special powers","section 4","section 5","section 6"),("afspa","disturbed area","special powers")),
}
# Post-publication source types are deliberately not presented as official judgments.
JUDIS_1963="legal_knowledge/judgment_originals/sci/historical/v3.3/ram_sarup_1963.pdf"
JUDIS_2005="legal_knowledge/judgment_originals/sci/historical/v3.3/navjot_sandhu_2005.pdf"

def download(path):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",
                                filename=path,force_download=True))

def rows(path):
    return [json.loads(s) for s in download(path).read_text(encoding="utf-8").splitlines() if s.strip()]

def csvrows(path):
    with download(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def out_csv(rs,cols):
    out=io.StringIO()
    wr=csv.DictWriter(out,fieldnames=cols,lineterminator="\n")
    wr.writeheader()
    wr.writerows([{k:r.get(k,"") for k in cols} for r in rs])
    return out.getvalue().encode()

def passage(page_text,needle):
    p=page_text.casefold().find(needle.casefold())
    if p<0:
        return None
    start=max(0,p-160)
    end=min(len(page_text),p+400)
    return " ".join(page_text[start:end].split())

def main():
    api=HfApi()
    info=api.repo_info(repo_id=REPO,repo_type="dataset")
    if not info.private:
        raise RuntimeError("Private canonical destination mandatory")
    p0={r["case_id"] for r in rows(P0) if r.get("metadata_priority")=="P0"}
    if len(p0)!=11 or set(TOPIC)!=p0:
        raise RuntimeError("Unexpected P0 identity scope")
    originals={r["id"]:r for r in rows(CASES)}
    kbs=rows(KB)
    if len(kbs)!=658 or len(originals)!=53:
        raise RuntimeError("Unexpected canonical original record counts")
    verified={r["curated_id"]:r for r in csvrows(CROSSWALK)}
    judis={r["case_id"]:r for r in json.loads(download(JUDIS).read_text())["cases"]}
    mani=json.loads(download(MIRROR).read_text())
    paths={}
    for caseid in TOPIC:
        if caseid in judis and judis[caseid].get("source_file_archived"):
            j=judis[caseid]
            paths[caseid]=(j["path"],j["sha256"],"OFFICIAL_SUPREME_COURT_JUDIS")
        elif caseid=="DCLR-SC-2016-L04":
            paths[caseid]=(mani["path"],mani["sha256"],"THIRD_PARTY_MIRROR_OF_SUPREME_COURT_ORDER")
        elif verified[caseid]["source_path"]:
            j=verified[caseid]
            paths[caseid]=(j["source_path"],j["sha256"],"EXISTING_RAW_CORPUS_PDF_UNPROVEN_OFFICIAL_BYTE_PARITY")
        else:
            paths[caseid]=None

    anchors, packets, matrix, links=[],[],[],[]
    for cid in TOPIC:
        source=paths[cid]
        original=originals[cid]
        docsha=None
        status="NO_ARCHIVED_SOURCE_PDF"
        pages=0
        extractable_pages=0
        all_snippets=[]
        if source:
            path,expected,tier=source
            content=download(path).read_bytes()
            actual=hashlib.sha256(content).hexdigest()
            if actual!=expected:
                raise RuntimeError("Source content SHA mismatch: "+cid+" "+path)
            with fitz.open(stream=content,filetype="pdf") as doc:
                pages=len(doc)
                topic_terms, _=TOPIC[cid]
                for number, page in enumerate(doc,1):
                    text=page.get_text("text")
                    if len(text.strip())>70:
                        extractable_pages+=1
                    for needle in topic_terms:
                        snip=passage(text,needle)
                        if snip:
                            all_snippets.append({
                              "case_id":cid, "source_path":path, "source_sha256":actual,
                              "pdf_page_1based":number,
                              "match_term":needle, "excerpt":snip,
                              "excerpt_sha256":hashlib.sha256(snip.encode()).hexdigest(),
                              "paragraph_label":None,
                              "status":"AUTO_LOCATED_EVIDENCE_HUMAN_REVIEW_REQUIRED"
                            })
            # Lexical selection only: diversifies pages and subjects, not legal ranking.
            seen_page=set()
            selected=[]
            for item in all_snippets:
                if item["pdf_page_1based"] in seen_page and len(seen_page)>=3:
                    continue
                selected.append(item)
                seen_page.add(item["pdf_page_1based"])
                if len(selected)>=8:
                    break
            if not selected:
                status="PDF_SHA_VERIFIED_NO_TOPIC_PASSAGE_FOUND"
            else:
                status="PDF_SHA_VERIFIED_TOPIC_PASSAGES_EXTRACTED"
            docsha=actual
            anchors.append({
              "case_id":cid,"original_title":original["title"],
              "original_case_record_source_status":original.get("source_status",""),
              "pdf_path":path,"sha256":actual,"pages":pages,
              "extractable_pages":extractable_pages,"source_tier":tier,
              "acquisition_status":status,"judgment_holding_legally_verified":False,
              "later_treatment_exhaustive":False,"jag_approved":False
            })
            packets.append({
              "case_id":cid,"title_original":original["title"],"source_path":path,
              "source_sha256":actual,"pdf_page_count":pages,
              "source_tier":tier, "excerpts":selected,
              "original_v09_holding_or_research_lead":original.get("holding",""),
              "original_v09_legal_question":original.get("legal_question",""),
              "original_v09_scope_caveat":original.get("scope_and_caveats",""),
              "source_excerpts_are_not_verified_holdings":True,
              "case_holding_status":"PRIMARY_TEXT_EVIDENCE_AWAITING_LEGAL_REVIEW",
              "jag_approved":False
            })
        else:
            anchors.append({
              "case_id":cid,"original_title":original["title"],
              "source_tier":"NOT_ARCHIVED","acquisition_status":status,
              "judgment_holding_legally_verified":False,
              "later_treatment_exhaustive":False,"jag_approved":False
            })
            packets.append({
              "case_id":cid, "title_original":original["title"],
              "source_path":None, "excerpts":[],
              "original_v09_holding_or_research_lead":original.get("holding",""),
              "case_holding_status":"SOURCE_PDF_NOT_ARCHIVED", "jag_approved":False
            })
        matrix.append({
          "case_id":cid,"case_title":original["title"],
          "source_status":status,"pdf_pages":pages,
          "archived_sha_verified":"YES" if source else "NO",
          "source_tier":source[2] if source else "MISSING",
          "automated_evidence_excerpts":len(packets[-1]["excerpts"]),
          "holding_verified":"NO",
          "later_treatment_exhaustive":"NO","jag_approved":"NO",
          "release_for_command_guidance":"NO"
        })
        _,kbterms=TOPIC[cid]
        scored=[]
        for kb in kbs:
            txt=(str(kb.get("title",""))+" "+str(kb.get("body",""))+" "+str(kb.get("references",""))).casefold()
            terms=[w for w in kbterms if w in txt]
            if not terms:
                continue
            # Multi-term matching required for generic pensions to suppress false positives.
            if cid in ("DCLR-SC-2015-L02","DCLR-SC-2015-L03","DCLR-SC-2016-L04","DCLR-SC-1996-L07","DCLR-SC-2005-L08","DCLR-SC-2008-L09","DCLR-SC-2007-L10") and len(terms)<2:
                continue
            scored.append((len(terms),kb,terms))
        scored.sort(key=lambda t:(-t[0],t[1]["id"]))
        for weight,kb,terms in scored[:10]:
            links.append({
              "case_id":cid,"kb_record_id":kb["id"],
              "kb_record_title":kb["title"],
              "matching_search_terms":"; ".join(terms),
              "candidate_score":weight,
              "status":"LEXICAL_CANDIDATE_NOT_LEGAL_CROSSLINK",
              "proposition_id":None,"reviewed":False,"jag_approved":False
            })

    anchor_bytes="".join(json.dumps(x,ensure_ascii=False)+"\n" for x in anchors).encode()
    packet_bytes="".join(json.dumps(x,ensure_ascii=False)+"\n" for x in packets).encode()
    fields=["case_id","case_title","source_status","pdf_pages","archived_sha_verified","source_tier",
      "automated_evidence_excerpts","holding_verified","later_treatment_exhaustive",
      "jag_approved","release_for_command_guidance"]
    links_fields=["case_id","kb_record_id","kb_record_title","matching_search_terms",
       "candidate_score","status","proposition_id","reviewed","jag_approved"]
    out={
      f"{ROOT}/01_P0_PDF_Provenance.jsonl":anchor_bytes,
      f"{ROOT}/02_P0_Bounded_Paragraph_Review_Packets.jsonl":packet_bytes,
      f"{ROOT}/03_P0_Source_Review_Matrix.csv":out_csv(matrix,fields),
      f"{ROOT}/04_P0_KB_Candidate_Links.csv":out_csv(links,links_fields),
      f"{ROOT}/05_P0_Dossier_Summary.json":
         (json.dumps({
            "version":"v3.4","generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "canonical_HF_revision_before":info.sha,
            "source_case_count":len(matrix),
            "archived_pdf_sha_verified":sum(x["archived_sha_verified"]=="YES" for x in matrix),
            "official_judis_sources":sum(x["source_tier"]=="OFFICIAL_SUPREME_COURT_JUDIS" for x in matrix),
            "third_party_copies":sum(x["source_tier"]=="THIRD_PARTY_MIRROR_OF_SUPREME_COURT_ORDER" for x in matrix),
            "source_missing_count":sum(x["source_tier"]=="MISSING" for x in matrix),
            "kb_originals":len(kbs),"kb_lexical_candidate_pairs":len(links),
            "source_excerpt_count":sum(x["automated_evidence_excerpts"] for x in matrix),
            "legal_holdings_cleared":0,"jag_approved":0,
            "limits":["Extracted passages chosen by keywords, not court holding analysis",
              "PDF page is a byte-traceable locator but printed paragraph number is not automatically inferred",
              "Sources in existing crawler are checksum verified without being independently matched to the official SCI byte stream",
              "All links to KB are keyword suggestions, not verified judicial-to-statutory dependencies",
              "Military disability pension cases require later-treatment and effective-rule verification"]
          },indent=2)+"\n").encode(),
      f"{ROOT}/README.md":(
       "# Mimamsa v3.4 P0 holding-review evidence packets\n\n"
       "These packets are auto-extracted from **actual stored PDFs** by SHA-256 verification and page-located "
       "lexical search. **They are NOT judicial holdings or legal clearance.** Each case is paired with its "
       "unchanged v0.9 research record; unrelated text may appear as a result of keyword matching. "
       "A legal reviewer must read the entire opinion, distinguish facts/arguments/ratio, identify precise "
       "paragraphs, statutory versions, later positive/negative treatment and decision-specific relief, "
       "and sign off each proposition. Source missing/third-party are held below full primary-source status.\n\n"
       "Do not merge these automated candidate links into the 658-record canonical database. "
       "No original files or crawler data are overwritten, and all JAG flags remain false.\n"
      ).encode()
    }
    operations=[CommitOperationAdd(path_in_repo=p,path_or_fileobj=io.BytesIO(v)) for p,v in out.items()]
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",operations=operations,
                             commit_message="Add P0 full-PDF holding-review evidence packets and tentative KB links v3.4")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("HF commit did not return revision")
    for p,blob in out.items():
        received=Path(hf_hub_download(repo_id=REPO,repo_type="dataset",filename=p,
                                      revision=rev,force_download=True)).read_bytes()
        if hashlib.sha256(received).digest()!=hashlib.sha256(blob).digest():
            raise RuntimeError("HF readback checksum discrepancy: "+p)
    print("V34_HOLDING_DOSSIERS_VERIFIED",len(out),"revision",rev,
          "cases",len(matrix),"source_verified",sum(x["archived_sha_verified"]=="YES" for x in matrix),
          "excerpts",sum(x["automated_evidence_excerpts"] for x in matrix),
          "candidate_kb_links",len(links))
if __name__=="__main__":
    main()
