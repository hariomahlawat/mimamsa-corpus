"""Review 11 P0 curated cases against existing immutable private Mimamsa judgment corpus.

The original 53 research records and raw documents remain unchanged. Matching a
name/year or PDF checksum is evidence of source identification, not verification of
a holding, current law, or JAG approval.
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import io
import json
from pathlib import Path
import re

import fitz
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO = "hariomahlawat/mimamsa-corpus"
PROPOSALS = "legal_knowledge/verification_batches/v3.1/01_P0_Proposed_Metadata.csv"
AUDIT = "legal_knowledge/quality_audit/v3.0/01_Case_Metadata_Findings.jsonl"
RAW = "data/raw_manifest.csv"
DEST = "legal_knowledge/crosswalk/v3.1"

def get(path):
    return Path(hf_hub_download(repo_id=REPO, repo_type="dataset", filename=path, force_download=True))

def csvrows(path):
    with get(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def normalize(s):
    s = str(s or "").casefold()
    s = re.sub(r"\b(vs|v|versus|the|others|ors|and|of|union|india|state|nct|government|or|anr)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def filing_year(row):
    path = row.get("raw_path", "")
    url = row.get("source_url", "")
    mt = re.search(r"/sci/((?:19|20)\d{2})/", path)
    if not mt:
        mt = re.search(r"/year=((?:19|20)\d{2})/", url)
    return mt.group(1) if mt else ""

def year_compatible(candidate_year, expected):
    if not candidate_year:
        return False
    # Allow +1 because SCR publication/report year may be after judgment year,
    # but the canonical raw repository path should normally be decision year.
    return candidate_year == expected or int(candidate_year)==int(expected)+1

def pdf_probe(rawpath, manifest_sha, required_tokens, year):
    original = get(rawpath)
    data = original.read_bytes()
    computed=hashlib.sha256(data).hexdigest()
    if computed!=manifest_sha:
        raise RuntimeError(f"Hash mismatch in immutable raw corpus: {rawpath}")
    if not data.startswith(b"%PDF-"):
        raise RuntimeError(f"Raw file is not PDF: {rawpath}")
    with fitz.open(stream=data,filetype="pdf") as pdf:
        pages=len(pdf)
        relevant = " ".join(pdf[i].get_text("text") for i in range(min(5,pages)))
        if len(relevant.strip()) < 400:
            # Only an aid: full text may still be scanned.
            relevant=" ".join(p.get_text("text") for p in pdf)
    norm=normalize(relevant)
    present=all(tok in norm.split() for tok in required_tokens)
    year_present=year in relevant or (str(int(year)+1) in relevant)
    return {"bytes":len(data),"pages":pages,"source_sha256":computed,
            "pdf_party_tokens_observed":present,"date_year_or_report_year_in_pdf_text":year_present,
            "extractable_characters":len(relevant.strip())}

def main():
    api=HfApi()
    info=api.repo_info(repo_id=REPO,repo_type="dataset")
    if not info.private:
        raise RuntimeError("Private repository required")
    proposals=csvrows(PROPOSALS)
    p0=[json.loads(s) for s in get(AUDIT).read_text().splitlines() if s.strip()]
    p0={r["case_id"] for r in p0 if r.get("metadata_priority")=="P0"}
    if len(p0)!=11 or set(r["curated_id"] for r in proposals)!=p0:
        raise RuntimeError("P0 proposals do not exactly match eleven audit-flagged cases")
    raw=csvrows(RAW)
    if len(raw)<2000:
        raise RuntimeError("Unexpected raw corpus dimensions")
    all_results=[]
    summary=Counter()
    for proposal in proposals:
        year=proposal["candidate_year"]
        required=normalize(proposal["identity_tokens"]).split()
        if not required:
            raise RuntimeError("Missing distinct-party identifying tokens")
        best=[]
        for record in raw:
            path=record.get("raw_path","")
            if "/sci/" not in path and "/sc/" not in path:
                continue
            ryear=filing_year(record)
            if not year_compatible(ryear,year):
                continue
            title=normalize(record.get("title",""))
            # Exact distinct-party tokens are mandatory. This intentionally
            # declines near matches rather than creating false legal links.
            if not all(token in title.split() for token in required):
                continue
            score=SequenceMatcher(None,normalize(proposal["proposed_authoritative_case_title"]),title).ratio()
            best.append((score,record))
        best.sort(key=lambda x:x[0],reverse=True)
        if best:
            best=best[:3]
            score,hit=best[0]
            source_status="TITLE_YEAR_CANDIDATE_ONLY"
            pdf_evidence={"bytes":None,"pages":None,"source_sha256":None,
                          "pdf_party_tokens_observed":False,
                          "date_year_or_report_year_in_pdf_text":False,
                          "extractable_characters":None}
            error=""
            try:
                pdf_evidence=pdf_probe(hit["raw_path"],hit["sha256"],required,year)
                if pdf_evidence["pdf_party_tokens_observed"]:
                    source_status="RAW_MANIFEST_SHA_AND_PDF_PARTY_TOKENS_CORROBORATED"
                else:
                    source_status="RAW_MANIFEST_SHA_CONFIRMED_PDF_IDENTITY_PENDING"
            except Exception as exc:
                error=type(exc).__name__+": "+str(exc)[:300]
                source_status="MATCHED_RAW_MANIFEST_SOURCE_PROBE_FAILED"
            result={
                "curated_id":proposal["curated_id"],
                "research_case_title":proposal["curated_original_title"],
                "proposed_title":proposal["proposed_authoritative_case_title"],
                "proposed_decision_date":proposal["proposed_decision_date"],
                "candidate_count":len(best),
                "highest_title_similarity":round(score,4),
                "candidate_title_from_raw_manifest":hit.get("title",""),
                "canonical_source_path":hit.get("raw_path",""),
                "source_url_from_manifest":hit.get("source_url",""),
                "manifest_sha256":hit.get("sha256",""),
                "source_status":source_status,
                "source_probe_error":error,
                "candidate_alternatives":[{"title":rec.get("title",""),
                                           "source_path":rec.get("raw_path",""),
                                           "score":round(s,4)} for s,rec in best[1:]],
                "jag_approved":False,"holding_verified":False,"subsequent_treatment_verified":False,
                **pdf_evidence
            }
        else:
            result={
                "curated_id":proposal["curated_id"],
                "research_case_title":proposal["curated_original_title"],
                "proposed_title":proposal["proposed_authoritative_case_title"],
                "proposed_decision_date":proposal["proposed_decision_date"],
                "candidate_count":0,
                "highest_title_similarity":None,
                "candidate_title_from_raw_manifest":"",
                "canonical_source_path":"",
                "source_url_from_manifest":"",
                "manifest_sha256":"",
                "source_status":"NO_EXACT_PARTY_AND_YEAR_MATCH_IN_RAW_MANIFEST",
                "source_probe_error":"",
                "candidate_alternatives":[],
                "jag_approved":False,"holding_verified":False,"subsequent_treatment_verified":False,
            }
        summary[result["source_status"]]+=1
        all_results.append(result)
        print(f"P0_RESULT {result['curated_id']} {result['source_status']} candidates={result['candidate_count']}")

    buf=io.StringIO()
    flat=[]
    for row in all_results:
        flat.append({
            "curated_id":row["curated_id"],
            "proposed_decision_date":row["proposed_decision_date"],
            "source_status":row["source_status"],
            "candidate_count":row["candidate_count"],
            "highest_title_similarity":row["highest_title_similarity"],
            "candidate_title":row["candidate_title_from_raw_manifest"],
            "source_path":row["canonical_source_path"],
            "sha256":row.get("source_sha256") or row.get("manifest_sha256") or "",
            "pdf_party_tokens_observed":row.get("pdf_party_tokens_observed",False),
            "full_holding_verified":"NO",
            "jag_approved":"NO",
        })
    csvwriter=csv.DictWriter(buf,fieldnames=list(flat[0]),lineterminator="\n")
    csvwriter.writeheader();csvwriter.writerows(flat)
    summary_doc={
        "title":"P0 curated case original-source crosswalk v3.1",
        "date_utc":datetime.now(timezone.utc).isoformat(),
        "dataset_revision_before_run":info.sha,
        "original_p0_record_count":11,
        "raw_manifest_records":len(raw),
        "status_counts":dict(summary),
        "legally_verified_holdings":0,
        "jag_approved":0,
        "limitations":[
            "Proposed identity and date fields are researched candidates, not corrections to the original 53 records.",
            "A raw manifest SHA-256 match verifies file integrity, not legal holding or original SCI JUDIS byte identity.",
            "An absent exact title+year candidate does not prove the case absent from any dataset.",
            "PDF party names elsewhere in text do not alone establish exact case identity; manual legal review remains required.",
            "No exhaustive subsequent-decision treatment review or current-law verification was performed."
        ]
    }
    files={
        f"{DEST}/01_P0_PDF_Source_Crosswalk.csv":buf.getvalue().encode("utf-8"),
        f"{DEST}/02_P0_Candidate_Details.jsonl":"".join(json.dumps(z,ensure_ascii=False)+"\n" for z in all_results).encode("utf-8"),
        f"{DEST}/03_P0_Source_Status_Summary.json":(json.dumps(summary_doc,ensure_ascii=False,indent=2)+"\n").encode("utf-8"),
        f"{DEST}/README.md":(
            "# P0 11-case source-discovery crosswalk v3.1\n\n"
            "Based on original 53-case metadata QA and separately proposed identity/citation fields. "
            "Strict party-name and year matching in the existing private raw-source manifest, followed "
            "by checksum-and-text inspection for the best candidate only. "
            "No official PDF equivalence, complete holding, current law, or JAG approval claimed. "
            "Do not modify original cases or crawler data.\n"
        ).encode("utf-8")
    }
    commit=api.create_commit(repo_id=REPO,repo_type="dataset",
        operations=[CommitOperationAdd(path_in_repo=k,path_or_fileobj=io.BytesIO(v)) for k,v in files.items()],
        commit_message="Publish conservatively verified P0 source candidates v3.1; no approval change")
    rev=getattr(commit,"oid",None)
    if not rev:
        raise RuntimeError("No HF commit revision for readback")
    for k,v in files.items():
        check=get(k)
        if check.read_bytes()!=v:
            raise RuntimeError("Readback mismatch: "+k)
    print("P0_V31_HF_VERIFIED 4 files revision="+rev)
    print("P0_SUMMARY "+json.dumps(summary_doc["status_counts"],sort_keys=True))

if __name__=="__main__":
    main()
